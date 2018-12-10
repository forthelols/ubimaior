# -*- coding: utf-8 -*-

"""Manage hierarchy of objects as if they were one"""

__author__ = """Massimiliano Culpo"""
__email__ = 'massimiliano.culpo@gmail.com'
__version__ = '0.1.0'

from .mappings import OverridableMapping, MergedMapping
from .sequences import MergedMutableSequence, MergedSequence
from .configurations import load, dump  # pylint: disable=cyclic-import
from .formats import formatter  # pylint: disable=cyclic-import

__all__ = [
    'formatter',
    'load',
    'dump',
    'MergedSequence',
    'MergedMutableSequence',
    'MergedMapping',
    'OverridableMapping'
]
