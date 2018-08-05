# -*- coding: utf-8 -*-
"""I/O of hierarchical configurations in various formats."""

import json
import os.path

import six

import ubimaior
import ubimaior.mappings


class ConfigSettings(ubimaior.mappings.MutableMapping):
    """Manages the settings for hierarchical configurations."""

    #: Settings that are currently permitted
    valid_settings = (
        'scopes', 'format', 'schema'
    )

    #: Formats that are currently allowed
    allowed_formats = [
        ubimaior.JSON
    ]

    def __init__(self):
        self._settings = {'scopes': None, 'format': None, 'schema': None}

    def __getitem__(self, key):
        self._validate_key(key)
        return self._settings[key]

    def __setitem__(self, key, value):
        self._validate_key(key)
        self._validate_value(key, value)
        self._settings[key] = value

    def __delitem__(self, key):
        self._validate_key(key)
        del self._settings[key]

    def __iter__(self):
        return iter(self._settings)

    def __len__(self):
        return len(self._settings)

    def _validate_value(self, key, value):
        """Validate the arguments written as defaults.

        Args:
            key (str): default setting
            value: new value to use for the setting

        """
        if key == 'scopes':
            if not isinstance(value, list):
                msg = '"scopes" must be a list of tuples [current type is {0}]'
                raise TypeError(msg.format(type(value).__name__))

            if not all(isinstance(x, tuple) and len(x) == 2 for x in value):
                msg = 'item in "scopes" must be tuples [(scope_name, dir)]'
                raise TypeError(msg)

        if key == 'format':
            if not isinstance(value, six.string_types):
                msg = '"format" must be a valid string'
                raise TypeError(msg)

            if value not in self.allowed_formats:
                msg = 'unknown format type. Allowed values are {0}'
                raise ValueError(msg.format(', '.join(self.allowed_formats)))

    def _validate_key(self, key):
        if key not in self.valid_settings:
            msg = 'allowed settings are {0}'.format(
                ', '.join(self._settings.keys())
            )
            raise KeyError(msg)

    def __getattr__(self, name):
        if name not in self.valid_settings:
            msg = '{0} object has no attribute {1}'
            raise AttributeError(msg.format(type(self).__name__, name))
        return self._settings[name]


#: Default settings for the module
DEFAULTS = ConfigSettings()


def set_default_scopes(scopes):
    """Sets the default scopes to look for configurations.

    Args:
        scopes (list of tuples): the new scopes to be used as a default

    Raises:
        TypeError: when ``scopes`` is not a list of two elements tuples

    """
    DEFAULTS['scopes'] = scopes


def set_default_format(fmt):
    """Sets the default format to encode/decode configuration files

    Args:
        fmt (str): a supported format for configuration files

    Raises:
        TypeError: if format is not a string
        ValueError: if the requested format is not among the
            supported ones
    """
    DEFAULTS['format'] = fmt


def load(config_name, scopes=None, config_format=None, schema=None):
    """Loads a hierarchical configuration into an object.

    Leaving None in any of the optional arguments below means to read its
    value from the default settings.

    Args:
        config_name (str): name of the configuration files to load
        scopes (list or None): list of ``(name, directory)`` tuples that
            represent the scopes of the hierarchical configuration
        config_format (str or None): format of the configuration files
        schema (dict or None): configuration parameters for schema

    Returns:
        Merged configuration object
    """

    # Retrieve default values
    settings = _retrieve_settings(scopes, config_format, schema)

    # Construct the filename of the configuration
    config_filename = config_name + '.' + settings.format

    # Retrieve the reader of the files
    # TODO: generalize how the reader is fetched
    reader = json

    mappings = []
    for scope_name, directory in settings.scopes:
        current = os.path.join(directory, config_filename)

        # Check if the file we are looking for exists
        if not os.path.exists(current) and not os.path.isfile(current):
            mappings.append((scope_name, {}))
            continue

        # If so load the content and append it to the hierarchy
        with open(current) as partial_cfg:
            mappings.append((scope_name, reader.load(partial_cfg)))

    return ubimaior.mappings.OverridableMapping(mappings)


def dump(cfg, config_name, scopes=None, config_format=None, schema=None):
    """Loads a hierarchical configuration into an object.

    Leaving None in any of the optional arguments below means to read its
    value from the default settings.

    Args:
        cfg: hierarchical configuration object to be dumped
        config_name (str): name of the configuration files where to dump
            the object
        scopes (list or None): list of ``(name, directory)`` tuples that
            represent the scopes of the hierarchical configuration
        config_format (str or None): format of the configuration files
        schema (dict or None): configuration parameters for schema

    Raises:
        ValueError: if ``cfg`` scopes do not match ``scopes``
    """
    # Retrieve default values
    settings = _retrieve_settings(scopes, config_format, schema)

    # Construct the filename of the configuration
    config_filename = config_name + '.' + settings.format

    # Retrieve the writer
    writer = json

    # Check that the configuration object is valid and consistent with settings
    _valdate_cfg_consistency(cfg, settings)

    # Dump the scopes to file
    scopes_d = dict(settings.scopes)
    for scope_name, obj in cfg.mappings.items():
        # If the object is empty, then continue to dump the hierarchy
        if not obj:
            continue

        directory = scopes_d[scope_name]
        current = os.path.join(directory, config_filename)
        with open(current, 'w') as partial_cfg:
            writer.dump(obj, partial_cfg)


def _retrieve_settings(scopes, config_format, schema):
    """Retrieves the settings to be used when dumping or loading a
    hierarchical configuration.

    Returns:
        ConfigSettings: object containing the current settings
    """
    settings = ConfigSettings()
    settings['scopes'] = scopes or DEFAULTS['scopes']
    settings['format'] = config_format or DEFAULTS['format']
    # TODO: still to be implemented
    settings['schema'] = schema or DEFAULTS['schema']
    return settings


def _valdate_cfg_consistency(cfg, settings):
    """Checks that ``cfg`` can be dumped and is consistent with settings.

    Args:
        cfg: configuration object
        settings: settings of the hierarchical configuration

    Raises:
        ValueError: if any inconsistency is found between ``cfg`` and
            ``settings``
    """
    # Check that we don't have modifications in scratch still to be merged
    if cfg.mappings['_scratch_']:
        msg = 'cannot dupm an object with mdifications in scratch'
        raise ValueError(msg)
    # Check that the current object matches the scope that will be used
    scopes_in_object = [x for x, _ in cfg.mappings.items() if x != '_scratch_']
    scopes_in_settings = [x for x, _ in settings.scopes]
    if scopes_in_object != scopes_in_settings:
        msg = 'scopes in the object do not match with scopes in settings'
        raise ValueError(msg)
