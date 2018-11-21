# -*- coding: utf-8 -*-
"""I/O of hierarchical configurations in various formats."""

import os.path

import jsonschema
import six

import ubimaior
import ubimaior.formats
import ubimaior.mappings


class ConfigSettings(ubimaior.mappings.MutableMapping):
    """Manages the settings for hierarchical configurations."""

    #: Settings that are currently permitted
    valid_settings = (
        'scopes', 'format', 'schema'
    )

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

    @staticmethod
    def _validate_value(key, value):
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

            if value not in ubimaior.formats.FORMATTERS:
                msg = 'unknown format type. Allowed values are {0}'
                raise ValueError(msg.format(', '.join(ubimaior.formats.FORMATTERS)))

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

#: Schema for the global configuration file
_UBIMAIOR_CFG_SCHEMA = {
    'type': 'object',
    'additionalProperties': True,
    'properties': {
        'format': {
            'description': 'The format used for the configuration file',
            'enum': [x for x in ubimaior.formats.FORMATTERS]
        },
        'scopes': {
            'description': 'The hierarchical scopes of the configuration as'
                           ' a list of (name, path) tuples',
            'type': 'array',
            'minItems': 1,
            'uniqueItems': True,
            'items': {
                'type': 'array',
                'minItems': 2,
                'maxItems': 2,
                'items': {
                    'type': 'string'
                }
            }
        },
        'schema': {
            'description': 'Path to the schema file used to validate the hierarchy',
            'type': 'string'
        }
    },
    'required': ['format', 'scopes']
}


def setup_from_file(configuration_file):
    """Sets ubimaior global defaults from a configuration file.

    Args:
        configuration_file (str): path to the configuration file
    """
    # Check if the configuration file exists
    if not os.path.exists(configuration_file):
        msg = 'configuration file "{0}" does not exist'
        raise IOError(msg.format(configuration_file))

    configuration_file = os.path.abspath(configuration_file)
    configuration_dir = os.path.dirname(configuration_file)

    def make_abs(path):
        if os.path.isabs(path):
            return path
        return os.path.abspath(os.path.join(configuration_dir, path))

    # Retrieve the correct formatter to load the configuration
    _, fmt = os.path.splitext(configuration_file)
    formatter = ubimaior.formats.FORMATTERS[fmt.strip('.')]

    # Load the settings and return them
    with open(configuration_file) as cfg_stream:
        configuration = formatter.load(cfg_stream)
        jsonschema.validate(configuration, _UBIMAIOR_CFG_SCHEMA)

    # Ensure that scopes is a list of tuples
    scopes = [(name, make_abs(d)) for name, d in configuration['scopes']]
    set_default_scopes(scopes)

    set_default_format(configuration['format'])

    if 'schema' in configuration:
        set_default_schema(make_abs(configuration['schema']))


def search_file_in_path(filename, start_dir=None):
    """Searches for a file starting from the directory passed as argument and proceeding
    up to parent directories, until root. Raises if the file is not found.

    Args:
        filename (str): name of the file to look for
        start_dir (path): directory where to start looking for the file

    Returns:
        Absolute path to the file

    Raises:
        IOError: if the file is not found.
    """
    # If the file is given with an absolute path just check it exists (or raise)
    if os.path.isabs(filename):
        if os.path.exists(filename) and os.path.isfile(filename):
            return filename
        raise IOError('file not found [{0}]'.format(filename))

    # Otherwise search in start_dir and proceed up to parent until root is reached
    start_dir = start_dir or os.getcwd()
    start_dir = os.path.realpath(os.path.abspath(start_dir))

    while True:
        abs_filename = os.path.join(start_dir, filename)
        if os.path.exists(abs_filename) and os.path.isfile(abs_filename):
            return abs_filename

        start_dir, is_root = os.path.dirname(start_dir), os.path.dirname(start_dir) == start_dir
        if is_root:
            raise IOError('file not found [{0}]'.format(filename))


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


def set_default_schema(schema):
    """Sets the default schema to validate configuration

    Args:
        schema (dict): a valid jsonschema schema

    """
    DEFAULTS['schema'] = schema


def validate(cfg_object, schema):
    """Validates a configuration object against a schema.

    Args:
        cfg_object: configuration object to be validated
        schema (dict or path): either a schema object already in
            memory or a path where to read one. If it is a file
            all the registered formats are accepted (JSON, YAML, etc.)

    Raises:
        jsonschema.ValidationError: if the configuration object doesn't conform
            to the schema
        jsonschema.SchemaError: if the schema does not conform to the jsonschema
            specifications
        ValueError: if ``schema`` is a file and either the file does not exist or
            its format is not recognized
    """
    # If schema is a string, assume it's a file containing the schema
    if isinstance(schema, six.string_types):
        # If it is not a valid file raise an appropriate error
        if not os.path.isfile(schema):
            msg = '"{0}" does not exist or is not a file'
            # TODO: in python > 3 a FileNotFoundError would be more appropriate
            raise ValueError(msg.format(schema))

        schema_format = os.path.splitext(schema)[1].lstrip('.')

        # If the format of the file is not recognized, raise an error too
        if schema_format not in ubimaior.formats.FORMATTERS:
            msg = '"{0}" is not a valid format [Allowed formats are: {1}]'
            msg = msg.format(
                schema_format,
                ', '.join(list(ubimaior.formats.FORMATTERS))
            )
            raise ValueError(msg)

        schema_formatter = ubimaior.formats.FORMATTERS[schema_format]
        schema_file = schema
        with open(schema_file) as schema_f:
            schema = schema_formatter.load(schema_f)

    flattened_obj = cfg_object.as_dict()
    jsonschema.validate(flattened_obj, schema)


def _is_empty(item):
    # If it is not a dictionary cast to bool
    if not isinstance(item, ubimaior.mappings.MutableMapping):
        return not bool(item)

    # If it is a dictionary recurse
    if not item:
        return True
    return all(_is_empty(v) for v in item.values())


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
    settings = retrieve_settings(scopes, config_format, schema)

    # Construct the filename of the configuration
    config_filename = config_name + '.' + settings.format

    # Retrieve the reader of the files
    formatter = ubimaior.formats.FORMATTERS[settings.format]

    mappings = []
    for scope_name, directory in settings.scopes:
        current = os.path.join(directory, config_filename)

        # Check if the file we are looking for exists
        if not os.path.exists(current) and not os.path.isfile(current):
            mappings.append((scope_name, {}))
            continue

        # If so load the content and append it to the hierarchy
        with open(current) as partial_cfg:
            mappings.append((scope_name, formatter.load(partial_cfg)))

    obj = ubimaior.mappings.OverridableMapping(mappings)

    # Validate the object against the supplied schema
    if schema:
        validate(obj, schema)

    return obj


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
    settings = retrieve_settings(scopes, config_format, schema)

    # Construct the filename of the configuration
    config_filename = config_name + '.' + settings.format

    # Retrieve the writer
    formatter = ubimaior.formats.FORMATTERS[settings.format]

    # Check that the configuration object is valid and consistent with settings
    _validate_cfg_consistency(cfg, settings)

    # Validate the object against the supplied schema
    if schema:
        validate(cfg, schema)

    # Dump the scopes to file
    scopes_d = dict(settings.scopes)
    for scope_name, obj in cfg.mappings.items():
        # If the object is empty, then continue to dump the hierarchy
        if _is_empty(obj):
            continue

        directory = scopes_d[scope_name]
        current = os.path.join(directory, config_filename)
        with open(current, 'w') as partial_cfg:
            formatter.dump(obj, partial_cfg)


def retrieve_settings(scopes=None, config_format=None, schema=None):
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


def _validate_cfg_consistency(cfg, settings):
    """Checks that ``cfg`` can be dumped and is consistent with settings.

    Args:
        cfg: configuration object
        settings: settings of the hierarchical configuration

    Raises:
        ValueError: if any inconsistency is found between ``cfg`` and
            ``settings``
    """
    # Check that we don't have modifications in scratch still to be merged
    if not _is_empty(cfg.mappings['_scratch_']):
        msg = 'cannot dump an object with modifications in scratch'
        raise ValueError(msg)
    # Check that the current object matches the scope that will be used
    scopes_in_object = [x for x, _ in cfg.mappings.items() if x != '_scratch_']
    scopes_in_settings = [x for x, _ in settings.scopes]
    if scopes_in_object != scopes_in_settings:
        msg = 'scopes in the object do not match with scopes in settings'
        raise ValueError(msg)
