# -*- coding: utf-8 -*-
"""Unit tests for sequence classes"""

import ubimaior

import pytest


@pytest.fixture()
def sequence():
    """An instance of a merged sequence"""
    return ubimaior.MergedMutableSequence(
        [[1, 2, 3], ["a", "b", "c"], [False, True, None], [1, "a", False]]
    )


def test_errors_on_init():
    # not a list
    with pytest.raises(TypeError) as excinfo:
        ubimaior.MergedMutableSequence("not_the_correct_type")
    assert '"sequences" should be a list' in str(excinfo.value)

    # items are not of the correct type
    with pytest.raises(TypeError) as excinfo:
        ubimaior.MergedMutableSequence([1, 2, 3])
    assert 'items in "sequences" should be' in str(excinfo.value)

    # a MergedSequence can be built using tuples
    mrs = ubimaior.MergedSequence([(1, 2), (3, 4)])
    assert [1, 2, 3, 4] == list(mrs)

    # a MergedMutableSequence cannot
    with pytest.raises(TypeError) as excinfo:
        ubimaior.MergedMutableSequence([(1, 2), (3, 4)])
    assert 'items in "sequences" should be' in str(excinfo.value)


def test_type_when_getting_slices():
    # A MergedSequence behaves like a tuple, and thus returns a tuple
    nonmut = ubimaior.MergedSequence([[1, 2], (3, 4, 5), [6, 7]])
    assert isinstance(nonmut[2:], tuple)

    # A MergedMutableSequence behaves like a list, and returns a list
    nonmut = ubimaior.MergedMutableSequence([[1, 2], [3, 4, 5], [6, 7]])
    assert isinstance(nonmut[2:], list)


def test_getting_items(sequence):
    # Length is the sum of the lengths of items
    assert len(sequence) == 12

    # Getting items should work like in built-in lists
    assert sequence[:3] == [1, 2, 3]
    assert sequence[:4] == [1, 2, 3, "a"]
    assert sequence[::2] == [1, 3, "b", False, None, "a"]
    assert sequence[0] == 1
    assert sequence[6] is False
    assert sequence[11] == sequence[-1]

    assert list(reversed(sequence))[:3] == [False, "a", 1]

    with pytest.raises(IndexError) as excinfo:
        sequence[12]
    assert "list index out of range" in str(excinfo.value)

    with pytest.raises(TypeError) as excinfo:
        sequence["a"]
    assert "list indices must be integers or slices" in str(excinfo.value)


def test_modifying_mutable_items():
    lists = [[1, 2, 3], ["a", "b", "c"]]
    dicts = [{1: "foo"}]

    m = ubimaior.MergedMutableSequence([lists, dicts])

    assert len(m) == 3

    m[0].append(4)
    assert lists[0] == [1, 2, 3, 4]


def test_setting_single_items(sequence):
    originals = sequence.sequences[:]

    sequence[1] = "d"
    assert sequence[1] == "d"
    assert originals[0][1] == "d"

    sequence[4] = "z"
    assert sequence[4] == "z"
    assert originals[1][1] == "z"

    sequence[-1] = "z"
    assert sequence[-1] == "z"
    assert originals[3][2] == "z"


def test_error_setting_slices(sequence):
    with pytest.raises(TypeError) as excinfo:
        sequence[0:] = 1
    assert "can only assign an iterable" in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        sequence[-4:-8:-1] = [1, 2, 3, 4, 5]
    assert "attempt to use an extended slice with step" in str(excinfo.value)


@pytest.mark.parametrize(
    "sl,vl,expected_components",
    [
        (
            slice(1, 7),
            [2, 3, 4, 5, 6, 7, 8],
            [[1, 2, 3], [4, 5, 6], [7, 8, True, None], [1, "a", False]],
        ),
        (
            slice(11, 5),
            [101, 102],
            [
                [1, 2, 3],
                ["a", "b", "c"],
                [False, True, None],
                [1, "a", 101, 102, False],
            ],
        ),
        (
            slice(7, 4),
            [101, 102],
            [
                [1, 2, 3],
                ["a", "b", "c"],
                [False, 101, 102, True, None],
                [1, "a", False],
            ],
        ),
        (
            slice(-8, -4),
            [1, 2, 3, 4, 5],
            [[1, 2, 3], ["a", 1, 2], [3, 4, 5, None], [1, "a", False]],
        ),
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
    ],
)
def test_setting_slices(sequence, sl, vl, expected_components):
    originals = sequence.sequences[:]

    # Check that we behave like a list
    normal_list = list(sequence)
    normal_list[sl] = vl
    sequence[sl] = vl

    assert list(sequence) == normal_list

    # Check that the components are modified as we expect
    for component, expected in zip(originals, expected_components):
        assert component == expected


def test_deleting_single_items(sequence):
    originals = sequence.sequences[:]

    with pytest.raises(IndexError):
        del sequence[20]

    assert len(originals[1]) == 3
    del sequence[4]
    assert len(originals[1]) == 2
    assert originals[1] == ["a", "c"]

    assert len(originals[3]) == 3
    del sequence[-2]
    assert len(originals[3]) == 2
    assert originals[3] == [1, False]


@pytest.mark.parametrize(
    "sl,expected_components",
    [
        (slice(1, 7), [[1], [], [True, None], [1, "a", False]]),
        (
            slice(11, 5),
            [[1, 2, 3], ["a", "b", "c"], [False, True, None], [1, "a", False]],
        ),
        (slice(-8, -4), [[1, 2, 3], ["a"], [None], [1, "a", False]]),
    ],
)
def test_deleting_slices(sequence, sl, expected_components):
    originals = sequence.sequences[:]

    # Check that we behave like a list
    normal_list = list(sequence)
    del normal_list[sl]
    del sequence[sl]

    assert list(sequence) == normal_list

    # Check that the components are modified as we expect
    for component, expected in zip(originals, expected_components):
        assert component == expected


@pytest.mark.parametrize(
    "idx,vl,expected_components",
    [
        (
            0,
            101,
            [[101, 1, 2, 3], ["a", "b", "c"], [False, True, None], [1, "a", False]],
        ),
        (
            12,
            101,
            [[1, 2, 3], ["a", "b", "c"], [False, True, None], [1, "a", False, 101]],
        ),
        (
            26,
            101,
            [[1, 2, 3], ["a", "b", "c"], [False, True, None], [1, "a", False, 101]],
        ),
        # Testing negative index
        (
            -1,
            101,
            [[1, 2, 3], ["a", "b", "c"], [False, True, None], [1, "a", 101, False]],
        ),
        (
            -25,
            101,
            [[101, 1, 2, 3], ["a", "b", "c"], [False, True, None], [1, "a", False]],
        ),
    ],
)
def test_insertion(sequence, idx, vl, expected_components):
    originals = sequence.sequences[:]

    # Check that we behave like a list
    normal_list = list(sequence)
    normal_list.insert(idx, vl)
    sequence.insert(idx, vl)

    assert list(sequence) == normal_list

    # Check that the components are modified as we expect
    for component, expected in zip(originals, expected_components):
        assert component == expected


def test_insertion_errors(sequence):
    with pytest.raises(TypeError) as excinfo:
        sequence.insert("a", 101)
    msg = str(excinfo.value)
    assert "'str' object cannot be interpreted as an integer" == msg


def test_equality(sequence):
    normal_list = sequence[:]

    another_sequence = ubimaior.MergedMutableSequence(
        [[1, 2, 3], ["a", "b", "c"], [False, True, None], [1, "a", False]]
    )

    # Equality constructing a list
    assert list(sequence) == normal_list

    # Equality with the same type
    assert sequence == another_sequence
    assert another_sequence == sequence

    not_really_equal = ubimaior.MergedMutableSequence(
        [[1, 2], [3, "a", "b", "c"], [False], [True, None, 1, "a", False]]
    )

    # Test that distribution of values in items
    # enters comparison for MergedSequence objects
    assert list(not_really_equal) == sequence[:]
    assert not_really_equal != sequence
    assert sequence != not_really_equal

    assert sequence != [1, 2, 3, 4]
