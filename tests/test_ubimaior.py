#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `ubimaior` package."""

import pytest


from ubimaior import ubimaior


@pytest.fixture()
def sequence():
    """An instance of a merged sequence """
    return ubimaior.MergedSequence([
        [1, 2, 3],
        ['a', 'b', 'c'],
        [False, True, None],
        [1, 'a', False]
    ])


class TestMergedMapping(object):
    def test_errors_on_init(self):
        """Tests that errors occurring when constructing an
        instance are handled in a proper way
        """

        # not a list
        with pytest.raises(TypeError) as excinfo:
            ubimaior.MergedMapping('not_the_correct_type')
        assert '"mappings" should be a list' in str(excinfo.value)

        # items are not of the correct type
        with pytest.raises(TypeError) as excinfo:
            ubimaior.MergedMapping([1, 2, 3])
        assert 'items in "mappings" should be' in str(excinfo.value)

    def test_reading_non_container_types(self):
        """Tests that reading non-container types from a MergedMapping
        behaves as designed.
        """

        highest_priority = {
            'foo': 1
        }

        middle_priority = {
            'foo': 6,  # type(foo) is always an int
            'bar': 'this_is_bar'
        }

        lowest_priority = {
            'bar': '4',  # type(bar) is always a string
            'baz': False
        }

        merged = ubimaior.MergedMapping([
            ('highest', highest_priority),
            ('middle', middle_priority),
            ('lowest', lowest_priority)
        ])

        assert merged['foo'] == 1
        assert merged['bar'] == 'this_is_bar'
        assert merged['baz'] is False

        with pytest.raises(KeyError):
            merged['this_key_does_not_exit']

    def test_errors_when_reading(self):
        """Tests all the errors that may happen when reading from a mapping."""
        # Type mismatch on a key
        merged = ubimaior.MergedMapping([
            ('high', {'foo': 1}),
            ('low', {'foo': 'bar'})
        ])

        msg = 'expected TypeError, because a str is overridden with an int'
        with pytest.raises(TypeError, message=msg) as excinfo:
            merged['foo']
        assert 'type mismatch for key' in str(excinfo.value)


class TestMergedSequence(object):
    def test_errors_on_init(self):
        """Tests that errors occurring when constructing an
        instance are handled in a proper way
        """
        # not a list
        with pytest.raises(TypeError) as excinfo:
            ubimaior.MergedSequence('not_the_correct_type')
        assert '"sequences" should be a list' in str(excinfo.value)

        # items are not of the correct type
        with pytest.raises(TypeError) as excinfo:
            ubimaior.MergedSequence([1, 2, 3])
        assert 'items in "sequences" should be' in str(excinfo.value)

    def test_getting_items(self, sequence):
        """Tests that retrieving elements from the merged list
        works as expected.
        """

        # Length is the sum of the lengths of items
        assert len(sequence) == 12

        # Getting items should work like in built-in lists
        assert sequence[:3] == [1, 2, 3]
        assert sequence[:4] == [1, 2, 3, 'a']
        assert sequence[::2] == [1, 3, 'b', False, None, 'a']
        assert sequence[0] == 1
        assert sequence[6] is False
        assert sequence[11] == sequence[-1]

        assert list(reversed(sequence))[:3] == [False, 'a', 1]

        with pytest.raises(IndexError) as excinfo:
            sequence[12]
        assert 'list index out of range' in str(excinfo.value)

        with pytest.raises(TypeError) as excinfo:
            sequence['a']
        assert 'list indices must be integers or slices' in str(excinfo.value)

    def test_modifying_mutable_items(self):
        """Tests the that the modification semantic is the same as
        built-in lists.
        """

        lists = [[1, 2, 3], ['a', 'b', 'c']]
        dicts = [{1: 'foo'}]

        m = ubimaior.MergedSequence([lists, dicts])

        assert len(m) == 3

        m[0].append(4)
        assert lists[0] == [1, 2, 3, 4]

    def test_setting_single_items(self, sequence):

        originals = sequence.sequences[:]

        sequence[1] = 'd'
        assert sequence[1] == 'd'
        assert originals[0][1] == 'd'

        sequence[4] = 'z'
        assert sequence[4] == 'z'
        assert originals[1][1] == 'z'

        sequence[-1] = 'z'
        assert sequence[-1] == 'z'
        assert originals[3][2] == 'z'

    def test_error_setting_slices(self, sequence):
        with pytest.raises(TypeError) as excinfo:
            sequence[0:] = 1
        assert 'can only assign an iterable' in str(excinfo.value)

        with pytest.raises(ValueError) as excinfo:
            sequence[-4:-8:-1] = [1, 2, 3, 4, 5]
        assert 'attempt to use an extended slice with step' in str(excinfo.value)

    @pytest.mark.parametrize('sl,vl,expected_components', [
        (slice(1, 7), [2, 3, 4, 5, 6, 7, 8], [
            [1, 2, 3],
            [4, 5, 6],
            [7, 8, True, None],
            [1, 'a', False]
        ]),
        (slice(11, 5), [101, 102], [
            [1, 2, 3],
            ['a', 'b', 'c'],
            [False, True, None],
            [1, 'a', 101, 102, False]
        ]),
        (slice(7, 4), [101, 102], [
            [1, 2, 3],
            ['a', 'b', 'c'],
            [False, 101, 102, True, None],
            [1, 'a', False]
        ]),
        (slice(-8, -4), [1, 2, 3, 4, 5], [
            [1, 2, 3],
            ['a', 1, 2],
            [3, 4, 5, None],
            [1, 'a', False]
        ]),
        # (slice(None, None, 2), [101, 102, 103, 104, 105, 106], [
        #     [101, 2, 102],
        #     ['a', 103, 'c'],
        #     [104, True, 105],
        #     [1, 106, False]
        # ]),
        # (slice(-4, -8, -1), [1, 2, 3, 4], [
        #     [1, 2, 3],
        #     ['a', 'b', 4],
        #     [3, 1, 1],
        #     [1, 'a', False]
        # ]),
    ])
    def test_setting_slices(self, sequence, sl, vl, expected_components):
        originals = sequence.sequences[:]

        # Check that we behave like a list
        normal_list = list(sequence)
        normal_list[sl] = vl
        sequence[sl] = vl

        assert list(sequence) == normal_list

        # Check that the components are modified as we expect
        for component, expected in zip(originals, expected_components):
            assert component == expected

    def test_deleting_single_items(self, sequence):

        originals = sequence.sequences[:]

        with pytest.raises(IndexError):
            del sequence[20]

        assert len(originals[1]) == 3
        del sequence[4]
        assert len(originals[1]) == 2
        assert originals[1] == ['a', 'c']

        assert len(originals[3]) == 3
        del sequence[-2]
        assert len(originals[3]) == 2
        assert originals[3] == [1, False]

    @pytest.mark.parametrize('sl,expected_components', [
        (slice(1, 7), [
            [1],
            [],
            [True, None],
            [1, 'a', False]
        ]),
        (slice(11, 5), [
            [1, 2, 3],
            ['a', 'b', 'c'],
            [False, True, None],
            [1, 'a', False]
        ]),
        (slice(-8, -4), [
            [1, 2, 3],
            ['a'],
            [None],
            [1, 'a', False]
        ]),
    ])
    def test_deleting_slices(self, sequence, sl, expected_components):
        originals = sequence.sequences[:]

        # Check that we behave like a list
        normal_list = list(sequence)
        del normal_list[sl]
        del sequence[sl]

        assert list(sequence) == normal_list

        # Check that the components are modified as we expect
        for component, expected in zip(originals, expected_components):
            assert component == expected

    @pytest.mark.parametrize('idx,vl,expected_components', [
        (0, 101, [
            [101, 1, 2, 3],
            ['a', 'b', 'c'],
            [False, True, None],
            [1, 'a', False]
        ]),
        (12, 101, [
            [1, 2, 3],
            ['a', 'b', 'c'],
            [False, True, None],
            [1, 'a', False, 101]
        ]),
        (26, 101, [
            [1, 2, 3],
            ['a', 'b', 'c'],
            [False, True, None],
            [1, 'a', False, 101]
        ]),
        # Testing negative index
        (-1, 101, [
            [1, 2, 3],
            ['a', 'b', 'c'],
            [False, True, None],
            [1, 'a', 101, False]
        ]),
        (-25, 101, [
            [101, 1, 2, 3],
            ['a', 'b', 'c'],
            [False, True, None],
            [1, 'a', False]
        ]),
    ])
    def test_insertion(self, sequence, idx, vl, expected_components):
        originals = sequence.sequences[:]

        # Check that we behave like a list
        normal_list = list(sequence)
        normal_list.insert(idx, vl)
        sequence.insert(idx, vl)

        assert list(sequence) == normal_list

        # Check that the components are modified as we expect
        for component, expected in zip(originals, expected_components):
            assert component == expected

    def test_insertion_errors(self, sequence):

        with pytest.raises(TypeError) as excinfo:
            sequence.insert('a', 101)
        msg = str(excinfo.value)
        assert '\'str\' object cannot be interpreted as an integer' == msg
