# -*- coding: utf-8 -*-
"""Contain classes and functions that help to manage merged sequences"""
import itertools

try:
    from collections.abc import Sequence, MutableSequence, Iterable  # novm
except ImportError:
    from collections import Sequence, MutableSequence, Iterable  # pylint: disable=deprecated-class


def _raise_if_not_slice_or_integer(item):
    """Raise a TypeError if the argument is not a slice or an integer.

    Args:
        item: object to be checked

    Raises:
        TypeError: when ``not isinstance(item, (slice, int))``
    """
    if not isinstance(item, (slice, int)):
        msg = "list indices must be integers or slices, not str"
        raise TypeError(msg)


class MergedSequence(Sequence):
    """Non-mutable view over a list of sequences.

    An object of this type is created passing the list of sequences on
    initialization. It behaves like a single non-mutable sequence
    (i.e. a tuple) composed chaining all the inputs.

    Args:
        sequences (list): list of sequences that constitute the view

    Raises:
        TypeError: when sequences is not a list of sequences

    Examples:

        >>> view = ubimaior.MergedSequence([[1, 2], (3, 4), (5, 6, 7)])
        >>> assert tuple(view) == (1, 2, 3, 4, 5, 6, 7)
        >>> view[1:3]
        (2, 3)
    """

    _type_to_accept = Sequence
    _builtin_return_type = tuple

    def __init__(self, sequences):
        # Check that sequences is a list of sequences
        if not isinstance(sequences, list):
            msg = '"sequences" should be a list of sequences'
            raise TypeError(msg)

        # Check that the items in the list have the correct type
        if any(not isinstance(x, self._type_to_accept) for x in sequences):
            msg = 'items in "sequences" should be MutableSequences'
            raise TypeError(msg)

        self.sequences = sequences

    def __getitem__(self, idx):
        _raise_if_not_slice_or_integer(idx)

        # Handle slices
        if isinstance(idx, slice):
            iterator = itertools.chain(*self.sequences)
            return self._builtin_return_type(
                itertools.islice(iterator, idx.start, idx.stop, idx.step)
            )

        # Handle integers
        item_idx, idx = self._return_item_and_index(idx)
        return self.sequences[item_idx][idx]

    def __len__(self):
        return sum([len(x) for x in self.sequences])

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

        raise IndexError("list index out of range")

    def __eq__(self, other):
        # Following what built-in lists do, compare False to
        # other types.
        if isinstance(other, type(self)):
            if len(self) != len(other):
                return False

            for rsequence, lsequence in zip(self.sequences, other.sequences):
                if rsequence != lsequence:
                    return False
                return True

        return NotImplemented


# pylint: disable=too-many-ancestors
class MergedMutableSequence(MutableSequence, MergedSequence):
    """Like a ``MergedSequence``, but provides a mutable view over the list
    of sequences.

    As this class permits mutable operations, it may modify the sequences that
    are passed to it during initialization.

    Args:
          sequences (list): list of mutable sequences that constitute the view

    Raises:
        TypeError: when sequences is not a list of mutable sequences

    Examples:

        >>> view = ubimaior.MergedMutableSequence([[1, 2], [3, 4], [5, 6, 7]])
        >>> assert view[:] == [1, 2, 3, 4, 5, 6, 7]
        >>> view[1:3]
        [2, 3]
        >>> view[1:3] = []
        >>> list(view)
        [1, 4, 5, 6, 7]
    """

    _type_to_accept = MutableSequence
    _builtin_return_type = list

    def __setitem__(self, idx, value):
        _raise_if_not_slice_or_integer(idx)

        # Mimic built-in list for this case
        if isinstance(idx, slice) and not isinstance(value, Iterable):
            raise TypeError("can only assign an iterable")

        # Handle slices
        if isinstance(idx, slice):
            # TODO: extend to slices of stride different from 1
            if isinstance(idx.step, int) and idx.step != 1:
                msg = "attempt to use an extended slice with step {0}"
                msg += " [Only step == 1 is allowed]"
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
            msg = "'{0}' object cannot be interpreted as an integer"
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
                    (v for sl, v, x in zip(slices, values, self.sequences) if sl.start < len(x)),
                    values[-1],
                ).extend(value)

        return values
