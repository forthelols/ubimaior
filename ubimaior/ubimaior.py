# -*- coding: utf-8 -*-

import collections
import itertools

try:
    from collections.abc import MutableMapping, MutableSequence, Iterable
except ImportError:
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


class MergedMapping(MutableMapping):
    """Shows a list of mappings with different levels of priority as
    they were a single one.

    TODO: write something about merging and write rules

    FIXME: Is this implementable in terms of collections.ChainMap?
    """

    #: Caches the setting of the preferred scope
    _preferred_scope = None

    def __init__(self, mappings, preferred_scope=None):
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

        #: Ordered dict that contains the priority list
        #: of mappings
        self.mappings = collections.OrderedDict(mappings)
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
        if current_type != type(value) and current_type is not None:
            try:
                value = current_type(value)
            except Exception:
                msg = 'cannot assign value of type {0} to key "{1}"'
                msg += '[{0} is not convertible to {2}]'
                raise TypeError(msg.format(
                    type(value).__name__, key, current_type.__name__
                ))

        # If I want to set a list or dictionary to be exactly
        # what is passed in, then I need to delete what's already
        # there first.
        if isinstance(value, (MutableSequence, MutableMapping)):
            del self[key]

        scope = self._get_writing_scope(key)
        self.mappings[scope][key] = value

    def __delitem__(self, key):
        # Deleting a type means deleting it from every managed scope
        for scope, d in self.mappings.items():
            if key in d:
                del d[key]

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
            res = k in seen_keys
            seen_keys.add(k)
            return res

        return [
            k for d in self.mappings.values() for k in d.keys() if not seen(k)
        ]

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


class MergedSequence(MutableSequence):
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
        self._raise_if_not_slice_or_integer(idx)

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
        self._raise_if_not_slice_or_integer(idx)

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
            for x, sl, vl in zip(self.sequences, slices, values):
                x[sl] = vl
            return

        # Handle integers
        item_idx, idx = self._return_item_and_index(idx)
        self.sequences[item_idx][idx] = value

    def __delitem__(self, idx):
        self._raise_if_not_slice_or_integer(idx)

        # Handle slices
        if isinstance(idx, slice):
            slices = self._split_slice(idx)
            for x, sl in zip(self.sequences, slices):
                del x[sl]
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

            for x, y in zip(self.sequences, other.sequences):
                if x != y:
                    return False
                return True

        return NotImplemented

    def _raise_if_not_slice_or_integer(self, item):
        """Raise a TypeError if the argument is not a slice or an integer.

        Args:
            item: object to be checked

        Raises:
            TypeError: when ``not isinstance(item, (slice, int))``
        """
        if not isinstance(item, (slice, int)):
            msg = 'list indices must be integers or slices, not str'
            raise TypeError(msg)

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

        for ii, x in enumerate(self.sequences):
            if idx < len(x):
                return ii, idx
            idx -= len(x)

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

        for x in self.sequences:
            def next_slice(sl):
                start = max(sl.start - len(x), 0)
                stop = max(sl.stop - len(x), 0)
                return slice(start, stop, sl.step)

            local_indices = idx.indices(len(x))
            slices.append(slice(*local_indices))
            idx = next_slice(idx)

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

        for sl in slices:
            length = len(range(sl.start, sl.stop, sl.step))
            local_value, value = value[:length], value[length:]
            values.append(local_value)

        # If I still have items in value I need to append
        # them in the proper place
        if len(value) > 0:
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
