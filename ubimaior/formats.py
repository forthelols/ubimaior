# -*- coding: utf-8 -*-
"""Formats that are handled by the package, and utilities to manage them"""

import abc
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
    @abc.abstractmethod
    def pprint(self, obj):
        """Produce a pretty printed string representing a hierarchical configuration and
        the provenance of each attribute or value.

        Args:
            obj (hierarchical configuration): object to be processed

        Returns:
            tuple of 2 elements, where the first is a list of strings (the lines the are to be
            printed) and a list of scopes encoding the provenance of each line.
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


@formatter('json', attribute='JSON')
class JsonFormatter(Dumper, Loader, PrettyPrinter):
    """Formatter for JSON"""
    def load(self, stream):
        return json.load(stream)

    def dump(self, obj, stream):
        json.dump(obj, stream)

    def pprint(self, obj):
        cfg_str = json.dumps(obj.as_dict(), indent=2, sort_keys=True)
        cfg_lines = cfg_str.split('\n')
        return cfg_lines, ['' for _ in cfg_lines]


try:
    import yaml

    @formatter('yaml', attribute='YAML')
    class YamlFormatter(Dumper, Loader, PrettyPrinter):
        """Formatter for YAML"""
        def load(self, stream):
            return yaml.load(stream)

        def dump(self, obj, stream):
            yaml.dump(obj, stream)

        def pprint(self, obj):
            cfg_str = yaml.dump(obj.as_dict(), default_flow_style=False)
            cfg_lines = cfg_str.split('\n')
            return cfg_lines, ['' for _ in cfg_lines]

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

        def pprint(self, obj):
            cfg_str = toml.dumps(obj.as_dict())
            cfg_lines = cfg_str.split('\n')
            return cfg_lines, ['' for _ in cfg_lines]

except ImportError:  # pragma: no cover
    pass  # pragma: no cover
