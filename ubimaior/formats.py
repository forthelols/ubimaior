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
class JsonFormatter(Dumper, Loader):
    """Formatter for JSON"""
    def load(self, stream):
        return json.load(stream)

    def dump(self, obj, stream):
        json.dump(obj, stream)


try:
    import yaml

    @formatter('yaml', attribute='YAML')
    class YamlFormatter(Dumper, Loader):
        """Formatter for YAML"""
        def load(self, stream):
            return yaml.load(stream)

        def dump(self, obj, stream):
            yaml.dump(obj, stream)

except ImportError:  # pragma: no cover
    pass  # pragma: no cover


try:
    import toml

    @formatter('toml', attribute='TOML')
    class TomlFormatter(Dumper, Loader):
        """Formatter for TOML"""
        def load(self, stream):
            return toml.load(stream)

        def dump(self, obj, stream):
            toml.dump(obj, stream)

except ImportError:  # pragma: no cover
    pass  # pragma: no cover
