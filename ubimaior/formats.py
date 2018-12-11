# -*- coding: utf-8 -*-
"""Formats that are handled by the package, and utilities to manage them"""

import abc
import collections

# The module enum does not exist for Python < 3.4,
# so we are relying on an external substitute for Python 2.7
try:
    import enum
except ImportError:
    import enum34 as enum

import json

import six

import ubimaior

#: Maps the format name to the formatter object
FORMATTERS = {}


class Loader(six.with_metaclass(abc.ABCMeta, object)):  # pylint: disable=too-few-public-methods
    """Abstract base class for something that could load an object from a stream."""
    @abc.abstractmethod
    def load(self, stream):
        """Load an object from stream and returns it.

        Args:
            stream: any file-like object

        Returns:
            the object loaded from the stream
        """


class Dumper(six.with_metaclass(abc.ABCMeta, object)):  # pylint: disable=too-few-public-methods
    """Abstract base class for something that could dump an object to a stream."""
    @abc.abstractmethod
    def dump(self, obj, stream):
        """Dump an object to a stream.

        Args:
            obj: object to be dumped
            stream: any file-like object
        """


# pylint: disable=too-few-public-methods
class PrettyPrinter(six.with_metaclass(abc.ABCMeta, object)):
    """Abstract base class for something that could dump an object to a pretty printed string."""
    def pprint(self, obj, formatters=None):
        """Produce a pretty printed string representing a hierarchical configuration and
        the provenance of each attribute or value.

        Args:
            obj (hierarchical configuration): object to be processed
            formatters (dict): dictionary mapping token types to a function
                that will format their value

        Returns:
            tuple of 2 elements, where the first is a list of strings (the lines that are to be
            printed) while the second is a list of scopes encoding the provenance of each line.
        """
        # Tokenize the object to be printed
        tokens = _tokenize_object(obj)

        # Construct a representation for each token
        formatters = formatters or collections.defaultdict(lambda: lambda x: x)
        indent_block = ' '*2
        cfg_lines, cfg_scopes = [], []
        for token in tokens:
            current = self.format_token(token, indent_block, formatters[token.obj_type])
            cfg_lines.append(current)
            cfg_scopes.append(token.scope or [])

        return cfg_lines, cfg_scopes

    @abc.abstractmethod
    def format_token(self, token, indent_block, format_fn):
        """Format a token to be pretty printed

        Args:
            token: token that needs to be formatted
            indent_block: block used to indent the token
            format_fn: custom function that accepts a value and transforms it

        Returns:
            formatted token
        """


def formatter(name, attribute=None):
    """Register a class as a valid formatter.

    Args:
        name (str): name of the formatter
        attribute (str or None): name of the mnemonic attribute
            that will be created in in the root module

    Returns:
       The actual decorator

    Raises:
        TypeError: if the type of any argument is not correct
        ValueError: if the attribute to be set is already present
    """
    # Check the input
    if not isinstance(name, six.string_types):
        raise TypeError('the argument "name" needs to be of string type')

    if not isinstance(attribute, six.string_types) and attribute is not None:
        raise TypeError('the argument "attribute" needs to be of string type')

    if attribute is not None and hasattr(ubimaior, attribute):
        raise ValueError('ubimaior.{0} is already defined'.format(attribute))

    def _decorator(cls):
        FORMATTERS[name] = cls()
        if attribute:
            setattr(ubimaior, attribute, name)

    return _decorator


_Token = collections.namedtuple('Token', [
    'line', 'scope', 'indent_lvl', 'obj_type'
])


class TokenTypes(enum.Enum):
    """Enumerate the token types used to display merged mappings."""
    #: An attribute in a dictionary
    ATTRIBUTE = 1
    #: An item in a list
    LIST_ITEM = 2
    #: A scalar Value
    VALUE = 3


def _tokenize_object(obj, scope=None, indent_lvl=0):
    tokens = []
    if isinstance(obj, ubimaior.OverridableMapping):
        for attribute, value in obj.items():
            scope = obj.get_scopes(attribute)
            # scope = [sc for sc, m in obj.mappings.items() if attribute in m]
            tokens.append(_Token(
                line=str(attribute), scope=scope, indent_lvl=indent_lvl,
                obj_type=TokenTypes.ATTRIBUTE
            ))
            # Descend on the current value
            tokens.extend(_tokenize_object(value, scope=scope, indent_lvl=indent_lvl+1))

    elif isinstance(obj, ubimaior.MergedSequence):
        assert len(scope) == len(obj.sequences), 'unexpected number of scopes'

        for component_scope, component_list in zip(scope, obj.sequences):
            for value in component_list:
                tokens.append(_Token(
                    line=str(value), scope=[component_scope], indent_lvl=indent_lvl + 1,
                    obj_type=TokenTypes.LIST_ITEM
                ))

    else:
        assert len(scope) == 1, 'expected a single scope for a scalar value'
        tokens.append(_Token(
            line=str(obj), scope=scope, indent_lvl=indent_lvl, obj_type=TokenTypes.VALUE
        ))

    return tokens


@formatter('json', attribute='JSON')
class JsonFormatter(Dumper, Loader, PrettyPrinter):
    """Formatter for JSON"""
    def load(self, stream):
        return json.load(stream)

    def dump(self, obj, stream):
        json.dump(obj, stream)

    def format_token(self, token, indent_block, format_fn):
        line = format_fn(token.line)
        if token.obj_type == TokenTypes.ATTRIBUTE:
            line = indent_block * token.indent_lvl + line + ':'
        elif token.obj_type == TokenTypes.LIST_ITEM:
            line = (token.indent_lvl - 1) * indent_block + '- ' + line
        else:
            line = indent_block * token.indent_lvl + line

        return line


try:
    import yaml

    @formatter('yaml', attribute='YAML')
    class YamlFormatter(Dumper, Loader, PrettyPrinter):
        """Formatter for YAML"""
        def load(self, stream):
            return yaml.load(stream)

        def dump(self, obj, stream):
            yaml.dump(obj, stream)

        def format_token(self, token, indent_block, format_fn):
            line = format_fn(token.line)
            if token.obj_type == TokenTypes.ATTRIBUTE:
                line = indent_block*token.indent_lvl + line + ':'
            elif token.obj_type == TokenTypes.LIST_ITEM:
                line = (token.indent_lvl-1)*indent_block + '- ' + line
            else:
                line = indent_block*token.indent_lvl + line

            return line

except ImportError:  # pragma: no cover
    pass  # pragma: no cover


try:
    import toml

    @formatter('toml', attribute='TOML')
    class TomlFormatter(Dumper, Loader, PrettyPrinter):
        """Formatter for TOML"""
        def load(self, stream):
            return toml.load(stream)

        def dump(self, obj, stream):
            toml.dump(obj, stream)

        def format_token(self, token, indent_block, format_fn):
            line = format_fn(token.line)
            if token.obj_type == TokenTypes.ATTRIBUTE:
                line = indent_block*token.indent_lvl + line + ':'
            elif token.obj_type == TokenTypes.LIST_ITEM:
                line = (token.indent_lvl-1)*indent_block + '- ' + line
            else:
                line = indent_block*token.indent_lvl + line

            return line

except ImportError:  # pragma: no cover
    pass  # pragma: no cover
