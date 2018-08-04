# -*- coding: utf-8 -*-

"""Manage hierarchy of objects as if they were one"""

__author__ = """Massimiliano Culpo"""
__email__ = 'massimiliano.culpo@gmail.com'
__version__ = '0.1.0'

from .sequences import MergedMutableSequence, MergedSequence
from .mappings import OverridableMapping, MergedMapping

__all__ = [
    'MergedSequence',
    'MergedMutableSequence',
    'MergedMapping',
    'OverridableMapping'
]

# A few mnemonic constant
JSON = 'json'
