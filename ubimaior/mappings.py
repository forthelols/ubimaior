# -*- coding: utf-8 -*-
"""Ubimaior is a package to manage hierarchical configurations"""

import copy
import itertools

import six

from . import sequences

try:
    import collections
    from collections.abc import MutableMapping, MutableSequence
except ImportError:
    import collections
    from collections import MutableMapping, MutableSequence


def _is_tuple_str_mapping(obj):
    """Predicate that returns True if object is a tuple of length 2,
    composed of a string and a mapping.

    Args:
        obj (object): object to be inspected

    Returns: True or False
    """
    return isinstance(obj, tuple) and len(obj) == 2 and \
        isinstance(obj[0], str) and isinstance(obj[1], MutableMapping)


def _convert_to_type_or_raise(target_type, key, value):
    """Tries to convert value to a target type. Used when
    setting items in mappings.

    Args:
        target_type: the target type for conversion
        key: originating key - used in the error message
        value: value to be converted

    Returns:
        target_type(value)

    Raises:
        TypeError: if any error occurs during the conversion
    """

    if target_type != type(value) and target_type is not None:
        try:
            value = target_type(value)
        except Exception:
            msg = 'cannot assign value of type {0} to key "{1}"'
            msg += '[{0} is not convertible to {2}]'
            raise TypeError(msg.format(
                type(value).__name__, key, target_type.__name__
            ))
    return value


# pylint: disable=too-few-public-methods,abstract-method
class _MappingBase(MutableMapping):
    def __init__(self, mappings, maybe_empty=False):
        # Check the type of mappings, which should be a list of
        # (str, Mapping) tuples
        if not isinstance(mappings, list):
            msg = '"mappings" should be a list of tuples'
            raise TypeError(msg)

        # Check that the items in the list have the correct type
        if any(not _is_tuple_str_mapping(x) for x in mappings):
            msg = 'items in "mappings" should be (str, Mapping)' \
                  ' tuples of length 2'
            raise TypeError(msg)

        # Check that the items in the list have the correct type
        if not mappings and not maybe_empty:
            msg = '"mappings" should contain one or more items (zero found)'
            raise ValueError(msg)

        #: Ordered dict that contains the priority list
        #: of mappings
        self.mappings = collections.OrderedDict(mappings)

    def __iter__(self):
        return iter(self._get_merged_keys())

    def __len__(self):
        return len(self._get_merged_keys())

    def _get_merged_keys(self):
        """Returns the list of merged keys, ensuring a partial ordering
        (all the keys of the first item come before the second, etc.)

        Returns:
            list of keys
        """
        seen_keys = set()

        def seen(k):
            """Returns True if 'k' was already seen, False otherwise"""
            res = k in seen_keys
            seen_keys.add(k)
            return res

        return [
            k for d in self.mappings.values() for k in d.keys() if not seen(k)
        ]

    def _type_for_key_or_raise(self, key):
        """Returns the type associated with a given key.

        Args:
            key: key to be searched

        Returns:
            type of the value (must be consistent among all
            the managed mappings) or None if ``key not in self``

        Raises:
            TypeError: if more than one type is associated with the key
        """
        # If the key is present in multiple mappings, and holds
        # instances of different types raise a TypeError
        types_for_mapping = {
            scope: type(v[key])
            for scope, v in self.mappings.items() if key in v
        }
        if len(set(types_for_mapping.values())) > 1:
            msg = 'type mismatch for key "{0}".'
            msg += ' Overridden keys need to be of the same type.'
            raise TypeError(msg.format(key))

        if types_for_mapping:
            return next(iter(types_for_mapping.values()))

        return None

    def __delitem__(self, key):
        # Deleting a type means deleting it from every managed scope
        for _, mapping in self.mappings.items():
            if key in mapping:
                del mapping[key]

    def __getattr__(self, item):
        if item not in self.mappings:
            msg = '{0} object has no attribute {1}'
            raise AttributeError(msg.format(type(self).__name__, item))

        return self.mappings[item]


class MergedMapping(_MappingBase):  # pylint: disable=too-many-ancestors
    """Shows a list of mappings as if they were a single one.

    A ``MergedMapping`` merges a list of mappings based on priority
    levels. Items coming first in the input list have higher priority.

    When displaying entries of non-container type, the one with the
    highest priority wins. When displaying entries holding a container
    type the class is recursive, and either a ``MergedMutableSequence``
    or a ``MergedMapping`` are returned.

    This class takes ownership of the input, and modifies it when mutable
    operations are invoked.

    Args:
        mappings (list): list of tuples of the form ``(scope, mapping)``.
            ``scope`` is a name used to identify the scope.
        preferred_scope (str, optional): preferred scope for writing

    Examples:
        >>> import ubimaior
        >>> highest_priority = {'foo': {'a': 1}, 'baz': {'a': [1, 2, 3]}}
        >>> middle_priority = {'foo': {'a': 11, 'b': 22}, 'bar': {'a': 'one'}}
        >>> lowest_priority = {
        ...     'foo': {'c': 111},
        ...     'bar': {'b': 'two'},
        ...     'baz': {'a': [4, 5, 6]}
        ... }
        >>>  merged = ubimaior.MergedMapping([
        ...     ('highest', highest_priority),
        ...     ('middle', middle_priority),
        ...     ('lowest', lowest_priority)
        ...  ])
        >>> [idx for idx in merged['baz']['a']]
        [1, 2, 3, 4, 5, 6]
    """

    #: Caches the setting of the preferred scope
    _preferred_scope = None

    def __init__(self, mappings, preferred_scope=None):
        super(MergedMapping, self).__init__(mappings)
        self.preferred_scope = preferred_scope

    def __getitem__(self, key):

        # If the key is not there, mimic built-in dict
        if not any(key in x for x in self.mappings.values()):
            raise KeyError(key)

        self._type_for_key_or_raise(key)

        values = [
            v[key] for v in self.mappings.values() if key in v
        ]

        if isinstance(values[0], MutableMapping):
            return MergedMapping([
                (k, v[key]) for k, v in self.mappings.items() if key in v
            ])

        if isinstance(values[0], MutableSequence):
            return sequences.MergedMutableSequence(values)

        return values[0]

    def __setitem__(self, key, value):
        # Check that the type of value is compatible with
        current_type = self._type_for_key_or_raise(key)
        value = _convert_to_type_or_raise(current_type, key, value)

        # If I want to set a list or dictionary to be exactly
        # what is passed in, then I need to delete what's already
        # there first.
        if isinstance(value, (MutableSequence, MutableMapping)):
            del self[key]

        scope = self._get_writing_scope(key)
        self.mappings[scope][key] = value

    def _get_writing_scope(self, key):
        for scope, item in self.mappings.items():
            # The current scope is the writing scope if either:
            # 1. There's no preferred scope (always returns the first scope)
            # 2. The preferred scope IS the current one
            # 3. The key I want to write appears in this scope (which means
            # the preferred scope is lower priority than this)
            if self.preferred_scope is None or \
                    self.preferred_scope == scope or \
                    key in item:
                return scope
        return None  # pragma: no cover

    @property
    def preferred_scope(self):
        """Preferred scope for writing."""
        return self._preferred_scope

    @preferred_scope.setter
    def preferred_scope(self, value):
        if value not in itertools.chain(self.mappings.keys(), [None]):
            msg = '{0} is an invalid value for preferred scope. '
            msg += 'Allowed values are {1}'
            raise ValueError(
                msg.format(str(value), str(self.mappings.keys()))
            )

        self._preferred_scope = value


class OverridableMapping(_MappingBase):  # pylint: disable=too-many-ancestors
    """Shows a list of mapping as if they were a single one.

    An ``OverridableMapping`` merges a list of mappings recursively based on
    priority levels. It only accepts strings as keys.

    Whenever a key in one of the mappings finishes with the character `:`
    it overrides the same keys at lower levels of priority.

    This class doesn't write over the input dictionaries in case of changes,
    instead it writes in a temporary scratch level that is at the highest
    possible priority.

    Args:
        mappings (list): list of tuples of the form ``(scope, mapping)``.
            ``scope`` is a name used to identify the scope.
        scratch_dict (MutableMapping, optional): dictionary to be used as
            scratch
    """

    scratch_key = '_scratch_'

    def __init__(self, mappings, scratch_dict=None):
        super(OverridableMapping, self).__init__(mappings, maybe_empty=True)
        scratch_dict = {} if scratch_dict is None else scratch_dict
        self.mappings = collections.OrderedDict(
            [(self.scratch_key, scratch_dict)] + mappings
        )

    @staticmethod
    def _check_key_or_raise(key):
        # If the key is not convertible to string, raise an  exception.
        # This limitation is currently due to how we override keys
        # (appending a ':' after the key)
        if not isinstance(key, six.string_types):
            msg = 'unsupported key type [{0}]'.format(type(key))
            raise TypeError(msg)

        # Ending a key with ':' is reserved to the implementation to
        # mark key that override everything in the hierarchy
        if key.endswith(':'):
            msg = ' a key cannot end with a \':\' character [{0}]'.format(key)
            raise ValueError(msg)

    def __getitem__(self, key):
        # Ensure that the key is of the correct type,
        # and does not end with ':'
        self._check_key_or_raise(key)

        # Check that we don't have more than one key once we applied the
        # overriding rules
        scope2keys = [  # (scope, [list of matching keys])
            (scope, [k for k in d if key == str(k).rstrip(':')])
            for (scope, d) in self.mappings.items()
        ]

        # TODO: check for len(keys) > 1 and raise if necessary

        values = []
        current_key = None
        for scope, keys in scope2keys:
            # No key in this scope, continue to the next
            if not keys:
                continue

            # Append (scope, key) and break if this key
            # was an overriding one
            current_key = keys[0]
            values.append((scope, self.mappings[scope][current_key]))
            if current_key.endswith(':'):
                break

        # Mimic built-in if the key does not exist
        if not values:
            raise KeyError(key)

        first_scope, first_value = values[0]

        if isinstance(first_value, MutableMapping):
            # The first scope is not scratch
            if first_scope != self.scratch_key:
                self.mappings[self.scratch_key][current_key.rstrip(':')] = {}
                scratch_dict = self.mappings[self.scratch_key][
                    current_key.rstrip(':')
                ]
            else:
                scratch_dict = first_value
                values = values[1:]

            return OverridableMapping(values, scratch_dict=scratch_dict)

        if isinstance(first_value, MutableSequence):
            return sequences.MergedSequence([value for _, value in values])

        return first_value

    def __setitem__(self, key, value):
        # Ensure that the key is of the correct type,
        # and does not end with ':'
        self._check_key_or_raise(key)

        # Compute the key and its corresponding override
        key, override_key = key.rstrip(':'), key.rstrip(':') + ':'
        override_key_type = self._type_for_key_or_raise(override_key)
        current_type = override_key_type or self._type_for_key_or_raise(key)

        # Normalize the value or raise
        value = _convert_to_type_or_raise(current_type, key, value)
        # If the scratch layer has 'key' already stored, pop it, then
        # store 'key:' that overrides all the values below
        self.scratch.pop(key, None)
        self.mappings[self.scratch_key][override_key] = value

    def __getattr__(self, item):
        item = self.scratch_key if item == 'scratch' else item
        return super(OverridableMapping, self).__getattr__(item)

    def _get_merged_keys(self):
        keys = super(OverridableMapping, self)._get_merged_keys()
        return [key for key in keys if not key.endswith(':')]

    def flattened(self, target=None):
        """Flattens the scopes up to target.

        Args:
            target (str or None): scope on to which we should flatten. If None
                only the ``_scratch_`` scope will be flattened onto the highest
                scope available.

        Returns:
            Maps with the scopes flattened up to target

        Raises:
            TypeError: if target is of the wrong type
            ValueError: if target is not among the allowed values
        """

        target = target or next(itertools.dropwhile(lambda x: x == self.scratch_key, self.mappings))

        # Check target type
        if not isinstance(target, six.string_types):
            raise TypeError('"target" must be of string type')

        # Check if the target is in the scope list
        if target not in self.mappings:
            msg = '"target" must be a valid scope [Accepted values: {0}]'
            raise ValueError(msg.format(', '.join(
                x for x in self.mappings if x != self.scratch_key
            )))

        # Copy the current object into a temporary one that will be modified
        flattened = type(self)(
            [(key, value) for key, value in copy.deepcopy(self.mappings).items()]
        )
        scopes = list(flattened.mappings)
        for scope, next_scope in zip(scopes[:-1], scopes[1:]):
            # Break if the mapping is flattened onto target
            if scope == target:
                break

            # Merge the current map onto the next in scope
            current_map = flattened.mappings[scope]
            next_map = flattened.mappings[next_scope]
            self._merge_maps(current_map, next_map)

            # Discard the current scope or nullify scratch
            if scope == self.scratch_key:
                flattened.mappings[self.scratch_key] = {}
            else:
                del flattened.mappings[scope]

        return flattened

    @staticmethod
    def _merge_maps(current_map, next_map):
        """Merges the current map onto the next map. Modifies ``next_map``.

        Args:
            current_map: map of the current scope
            next_map: map of the next scope (lower in priority)
        """
        for key, value in current_map.items():

            is_override = key.endswith(':')
            normal_key, override_key = key.rstrip(':'), key.rstrip(':') + ':'

            # 1. If the key overrides what's below, report it as an override key
            # and pop the normal key if it was there
            if is_override:
                next_map[override_key] = current_map[override_key]
                # In case pop a normal key if it was there
                next_map.pop(normal_key, None)

            # 2. If the key is a normal key and both the normal key and the override key are
            # not not present in the next scope, then just push the normal key down one scope
            elif all(k not in next_map for k in (normal_key, override_key)):
                next_map[normal_key] = current_map[normal_key]

            # 3. If the key is present in the next scope the logic is more complicated.
            # In that case:
            #   a.) We need to use the key of next scope to preserve overriding rules
            #   b.) We need to merge Sequences and Mapping accordingly
            else:
                key_type = override_key if override_key in next_map else normal_key

                if isinstance(value, MutableMapping):
                    # Here we recurse on the two mappings
                    flattened_map = OverridableMapping([
                        ('first', current_map[normal_key]), ('second', next_map[key_type])
                    ])
                    flattened_map = flattened_map.flattened(target='second')
                    flattened_map = dict(flattened_map.second.items())
                    next_map[key_type] = flattened_map

                elif isinstance(value, MutableSequence):
                    next_map[key_type] = current_map[normal_key] + next_map[key_type]

                else:
                    next_map[key_type] = value

    def as_dict(self):
        """Converts this configuration object to built-in types."""
        lowest = next(reversed(self.mappings))
        flat_obj = self.flattened(target=lowest)
        return getattr(flat_obj, lowest)
