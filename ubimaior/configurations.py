# -*- coding: utf-8 -*-
"""I/O of hierarchical configurations in various formats."""

import json
import os.path

import ubimaior
import ubimaior.mappings


def load(config_name, scopes=None, config_format=None, schema=None):
    """Loads a hierarchical configuration into an object.

    Leaving None in any of the optional arguments below means to read its
    value from the default configuration file.

    Args:
        config_name (str): name of the configuration part to load
        scopes (list or None): list of ``(name, directory)`` tuples that
            represent the scopes of the hierarchical configuration
        config_format (str or None): format of the configuration files
        schema (dict or None): configuration parameters for schema

    Returns:
        Merged configuration object
    """

    # Retrieve default values
    # TODO: check the value of the scopes and sanitize them
    config_format = config_format or ubimaior.JSON
    schema = schema or False

    # Construct the filename of the configuration
    config_filename = config_name + '.' + config_format

    # Retrieve the reader of the files
    assert config_format == ubimaior.JSON
    reader = json

    mappings = []
    for scope_name, directory in scopes:
        current = os.path.join(directory, config_filename)

        # Check if the file we are looking for exists
        if not os.path.exists(current) and not os.path.isfile(current):
            mappings.append((scope_name, {}))
            continue

        # If so load the content and append it to the hierarchy
        with open(current) as partial_cfg:
            mappings.append((scope_name, reader.load(partial_cfg)))

    return ubimaior.mappings.OverridableMapping(mappings)
