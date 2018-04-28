# -*- coding: utf-8 -*-
"""Ubimaior is a package to manage hierarchical configurations"""

import itertools

try:
    import collections
    from collections.abc import MutableMapping, MutableSequence, Iterable
except ImportError:
    import collections
    from collections import MutableMapping, MutableSequence, Iterable


def _is_tuple_str_mapping(obj):
    """Predicate that returns True if object is a tuple of length 2,
    composed of a string and a mapping.

    Args:
        obj (object): object to be inspected

    Returns: True or False
    """
    return isinstance(obj, tuple) and len(obj) == 2 and \
        isinstance(obj[0], str) and isinstance(obj[1], MutableMapping)


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
            msg = '{0} object has no attrobute {1}'
            raise AttributeError(msg.format(type(self).__name__, item))

        return self.mappings[item]


def _convert_to_type_or_raise(current_type, key, value):
    if current_type != type(value) and current_type is not None:
        try:
            value = current_type(value)
        except Exception:
            msg = 'cannot assign value of type {0} to key "{1}"'
            msg += '[{0} is not convertible to {2}]'
            raise TypeError(msg.format(
                type(value).__name__, key, current_type.__name__
            ))
    return value


class MergedMapping(_MappingBase):  # pylint: disable=too-many-ancestors
    """Shows a list of mappings with different levels of priority as
    they were a single one.

    TODO: write something about merging and write rules

    FIXME: Is this implementable in terms of collections.ChainMap?
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
            return MergedSequence(values)

        return values[0]

    def __setitem__(self, key, value):
        # TODO: add an option to be strict on the scope, and fail
        # TODO: with an error? This will be useful if we want to write
        # TODO: only in a single scope.

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
        return None

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


def _raise_if_not_slice_or_integer(item):
    """Raise a TypeError if the argument is not a slice or an integer.

    Args:
        item: object to be checked

    Raises:
        TypeError: when ``not isinstance(item, (slice, int))``
    """
    if not isinstance(item, (slice, int)):
        msg = 'list indices must be integers or slices, not str'
        raise TypeError(msg)


class MergedSequence(MutableSequence):  # pylint: disable=too-many-ancestors
    """Shows a list of sequences with different levels of priority as
    they were a single one.

    TODO: write something about merging and write rules
    """
    def __init__(self, sequences):
        # Check that sequences is a list of sequences
        if not isinstance(sequences, list):
            msg = '"sequences" should be a list of sequences'
            raise TypeError(msg)

        # Check that the items in the list have the correct type
        if any(not isinstance(x, MutableSequence) for x in sequences):
            msg = 'items in "sequences" should be MutableSequences'
            raise TypeError(msg)

        self.sequences = sequences

    def __getitem__(self, idx):
        _raise_if_not_slice_or_integer(idx)

        # Handle slices
        if isinstance(idx, slice):
            iterator = itertools.chain(*self.sequences)
            return list(
                itertools.islice(iterator, idx.start, idx.stop, idx.step)
            )

        # Handle integers
        item_idx, idx = self._return_item_and_index(idx)
        return self.sequences[item_idx][idx]

    def __len__(self):
        return sum([len(x) for x in self.sequences])

    def __setitem__(self, idx, value):
        _raise_if_not_slice_or_integer(idx)

        # Mimic built-in list for this case
        if isinstance(idx, slice) and not isinstance(value, Iterable):
            raise TypeError('can only assign an iterable')

        # Handle slices
        if isinstance(idx, slice):
            # TODO: extend to slices of stride different from 1
            if isinstance(idx.step, int) and idx.step != 1:
                msg = 'attempt to use an extended slice with step {0}'
                msg += ' [Only step == 1 is allowed]'
                raise ValueError(msg.format(idx.step))

            slices = self._split_slice(idx)
            values = self._split_value(value, slices)
            for sequence, index, val in zip(self.sequences, slices, values):
                sequence[index] = val
            return

        # Handle integers
        item_idx, idx = self._return_item_and_index(idx)
        self.sequences[item_idx][idx] = value

    def __delitem__(self, idx):
        _raise_if_not_slice_or_integer(idx)

        # Handle slices
        if isinstance(idx, slice):
            slices = self._split_slice(idx)
            for sequence, index in zip(self.sequences, slices):
                del sequence[index]
            return

        # Handle integers
        item_idx, idx = self._return_item_and_index(idx)
        del self.sequences[item_idx][idx]

    def insert(self, index, value):
        if not isinstance(index, int):
            msg = '\'{0}\' object cannot be interpreted as an integer'
            raise TypeError(msg.format(type(index).__name__))

        try:
            item_idx, index = self._return_item_and_index(index)
            self.sequences[item_idx].insert(index, value)
        except IndexError:
            # An IndexError means we are outside the bounds of
            # the current list. In this case built-in lists insert
            # the value as first or last element, depending in which
            # direction we went out of bounds
            if index > 0:
                self.sequences[-1].append(value)
            else:
                self.sequences[0].insert(0, value)

    def __eq__(self, other):
        # Following what built-in lists do, compare False to
        # other types.
        if isinstance(other, MergedSequence):
            if len(self) != len(other):
                return False

            for rsequence, lsequence in zip(self.sequences, other.sequences):
                if rsequence != lsequence:
                    return False
                return True

        return NotImplemented

    def _return_item_and_index(self, idx):
        """Given an index that refers to the merged list, return the index of
        the item in ``sequences`` that holds the item and its local index.

        Args:
            idx (int): index in the merged list

        Returns:
            item_idx, idx (int): index of the sequence and of the item
                in the sequence

        Raises:
            IndexError: if ``idx`` is out of range
        """
        idx = len(self) + idx if idx < 0 else idx

        for counter, sequence in enumerate(self.sequences):
            if idx < len(sequence):
                return counter, idx
            idx -= len(sequence)

        raise IndexError('list index out of range')

    def _split_slice(self, idx):
        """Given a slice for the merged list, returns a list of slices for
        the underlying items.

        Args:
            idx (slice): slice referring to the merged list

        Returns:
            a list of slices associated with the managed items
        """
        slices = []

        # Normalize to this length
        idx = slice(*idx.indices(len(self)))

        for sequence in self.sequences:
            def next_slice(slc, seq):
                """Gives the next slice of a merged sequence"""
                start = max(slc.start - len(seq), 0)
                stop = max(slc.stop - len(seq), 0)
                return slice(start, stop, slc.step)

            local_indices = idx.indices(len(sequence))
            slices.append(slice(*local_indices))
            idx = next_slice(idx, sequence)

        return slices

    def _split_value(self, value, slices):
        """Split a list of values meant for the merged list, to components
        associated with each underlying item.

        Args:
            value (list of values): items to be assigned to the merged list
            slices (list of slices): list of slices returned by
                ``_split_slice``

        Returns:
            components associated with the underlying list
        """
        values = []

        for slc in slices:
            length = len(range(slc.start, slc.stop, slc.step))
            local_value, value = value[:length], value[length:]
            values.append(local_value)

        # If I still have items in value I need to append
        # them in the proper place
        if value:
            try:
                [x for x in values if len(x)][-1].extend(value)
            except IndexError:
                # All the slices are empty
                next(
                    (v for sl, v, x in zip(slices, values, self.sequences)
                     if sl.start < len(x)),
                    values[-1]
                ).extend(value)

        return values


class OverridableMapping(_MappingBase):  # pylint: disable=too-many-ancestors
    """A MergedMapping with some rules to override keys in the hierarchy."""

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
        if not isinstance(key, str):
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
            return MergedSequence([value for _, value in values])

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
