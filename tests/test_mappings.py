#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `ubimaior` package."""

import pytest

import ubimaior


@pytest.fixture(params=[ubimaior.MergedMapping, ubimaior.OverridableMapping])
def mapping_type(request):
    return request.param


@pytest.fixture()
def mapping_nc(mapping_type):
    """An instance of a merged mapping, with non-container values."""
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

    merged = mapping_type([
        ('highest', highest_priority),
        ('middle', middle_priority),
        ('lowest', lowest_priority)
    ])

    return merged


@pytest.fixture()
def mapping_l():
    """An instance of a merged mapping, with list values."""
    highest_priority = {
        'foo': [1],
        'baz': [1, 2, 3],
        'foobar': []
    }

    middle_priority = {
        'foo': [11],  # type(foo) is always an int
        'bar': ['a']
    }

    lowest_priority = {
        'foo': [111],
        'bar': ['b'],  # type(bar) is always a string
        'baz': [4, 5, 6]
    }

    merged = ubimaior.MergedMapping([
        ('highest', highest_priority),
        ('middle', middle_priority),
        ('lowest', lowest_priority)
    ])

    return merged


@pytest.fixture()
def mapping_d():
    """An instance of a merged mapping, with dict values."""

    highest_priority = {
        'foo': {'a': 1},
        'baz': {'a': [1, 2, 3]},
    }

    middle_priority = {
        'foo': {'a': 11, 'b': 22},
        'bar': {'a': 'one'}
    }

    lowest_priority = {
        'foo': {'c': 111},
        'bar': {'b': 'two'},
        'baz': {'a': [4, 5, 6]}
    }

    merged = ubimaior.MergedMapping([
        ('highest', highest_priority),
        ('middle', middle_priority),
        ('lowest', lowest_priority)
    ])

    return merged


@pytest.fixture()
def overridable_l():
    """An instance of a merged mapping, with list values."""
    highest_priority = {
        'foo': [11, 22],
        'baz': [1, 2, 3],
        'foobar': []
    }

    middle_priority = {
        'foo:': ['a', 'b'],
        'bar': ['a']
    }

    lowest_priority = {
        'foo': [111],
        'bar': ['b'],  # type(bar) is always a string
        'baz': [4, 5, 6]
    }

    merged = ubimaior.OverridableMapping([
        ('highest', highest_priority),
        ('middle', middle_priority),
        ('lowest', lowest_priority)
    ])

    return merged


@pytest.fixture()
def overridable_d():
    """An instance of a merged mapping, with list values."""
    highest_priority = {
        'foo': {'a': 1, 'b': {'xx': 1}},
    }

    middle_priority = {
        'foo:': {'c': 2},
    }

    lowest_priority = {
        'foo': {'d': 3},
    }

    merged = ubimaior.OverridableMapping([
        ('highest', highest_priority),
        ('middle', middle_priority),
        ('lowest', lowest_priority)
    ])

    return merged


class TestAllMappings(object):
    def test_errors_on_init(self, mapping_type):
        # not a list
        with pytest.raises(TypeError) as excinfo:
            mapping_type('not_the_correct_type')
        assert '"mappings" should be a list' in str(excinfo.value)

        # items are not of the correct type
        with pytest.raises(TypeError) as excinfo:
            mapping_type([1, 2, 3])
        assert 'items in "mappings" should be' in str(excinfo.value)

    def test_reading_non_container_types(self, mapping_nc):

        assert mapping_nc['foo'] == 1
        assert mapping_nc['bar'] == 'this_is_bar'
        assert mapping_nc['baz'] is False

        with pytest.raises(KeyError):
            mapping_nc['this_key_does_not_exit']

    def test_setting_non_container_types(self, mapping_nc):

        mapping_nc.preferred_scope = 'middle'

        mapping_nc['foo'] = 11
        assert mapping_nc['foo'] == 11

        # OverridableMapping uses a top layer to override
        # the overall result in the view
        if isinstance(mapping_nc, ubimaior.OverridableMapping):
            assert mapping_nc.mappings[
                ubimaior.OverridableMapping.scratch_key
            ]['foo:'] == 11

        # MergedMapping instead writes directly in the input mappings
        if isinstance(mapping_nc, ubimaior.MergedMapping):
            assert mapping_nc.mappings['highest']['foo'] == 11
            assert mapping_nc.mappings['middle']['foo'] == 6

        mapping_nc['bar'] = 'overwritten'
        assert mapping_nc['bar'] == 'overwritten'

        if isinstance(mapping_nc, ubimaior.OverridableMapping):
            assert mapping_nc.mappings[
                ubimaior.OverridableMapping.scratch_key
            ]['bar:'] == 'overwritten'

        if isinstance(mapping_nc, ubimaior.MergedMapping):
            assert 'bar' not in mapping_nc.mappings['highest']
            assert mapping_nc.mappings['middle']['bar'] == 'overwritten'
            assert mapping_nc.mappings['lowest']['bar'] == '4'

        assert 'baz' not in mapping_nc.mappings['middle']
        mapping_nc['baz'] = True
        assert mapping_nc['baz'] is True

        if isinstance(mapping_nc, ubimaior.OverridableMapping):
            assert mapping_nc.mappings[
                ubimaior.OverridableMapping.scratch_key
            ]['baz:'] is True

        if isinstance(mapping_nc, ubimaior.MergedMapping):
            assert 'baz' not in mapping_nc.mappings['highest']
            assert mapping_nc.mappings['middle']['baz'] is True
            assert mapping_nc.mappings['lowest']['baz'] is False

        with pytest.raises(TypeError) as excinfo:
            mapping_nc['foo'] = 'a_string'
        assert 'cannot assign value of type' in str(excinfo.value)

    def test_deleting_types(self, mapping_nc):

        mapping_nc.preferred_scope = 'middle'

        for key in ('foo', 'bar', 'baz'):
            assert key in mapping_nc
            del mapping_nc[key]
            assert key not in mapping_nc
            for v in mapping_nc.mappings.values():
                assert key not in v

    def test_iteration(self, mapping_nc):

        for key, expected in zip(mapping_nc, ['foo', 'bar', 'baz']):
            assert key == expected

        assert list(mapping_nc.keys()) == ['foo', 'bar', 'baz']

    def test_accessing_non_existing_attribute(self, mapping_nc):
        with pytest.raises(AttributeError) as excinfo:
            mapping_nc.does_not_exist
        assert 'object has no attribute' in str(excinfo.value)


class TestMergedMapping(object):

    def test_errors_on_init(self):
        # one or more mapping is needed
        with pytest.raises(ValueError) as excinfo:
            ubimaior.MergedMapping([])
        assert '"mappings" should contain one or more' in str(excinfo.value)

    def test_reading_lists(self, mapping_l):
        assert mapping_l['foo'][:] == [1, 11, 111]
        assert mapping_l['baz'][:] == [1, 2, 3, 4, 5, 6]
        assert mapping_l['foobar'][:] == []
        assert mapping_l['bar'][:] == ['a', 'b']

    def test_reading_dicts(self, mapping_d):

        assert len(mapping_d) == 3

        assert mapping_d['foo']['a'] == 1
        assert mapping_d['foo']['b'] == 22
        assert mapping_d['foo']['c'] == 111
        assert len(mapping_d['foo']) == 3

        assert mapping_d['baz']['a'][:] == [1, 2, 3, 4, 5, 6]
        assert len(mapping_d['baz']) == 1

        assert mapping_d['bar']['a'] == 'one'
        assert mapping_d['bar']['b'] == 'two'
        assert len(mapping_d['bar']) == 2

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

    def test_setting_invalid_preferred_scope(self, mapping_l):
        with pytest.raises(ValueError) as excinfo:
            mapping_l.preferred_scope = 'does_not_exist'
        assert 'is an invalid value for preferred scope' in str(excinfo.value)

    def test_setting_containers(self, mapping_l):

        mapping_l['foo'] = [1, 2, 3]
        assert list(mapping_l['foo']) == [1, 2, 3]
        assert mapping_l.mappings['highest']['foo'] == [1, 2, 3]
        assert 'foo' not in mapping_l.mappings['middle']
        assert 'foo' not in mapping_l.mappings['lowest']

        mapping_l.preferred_scope = 'middle'
        mapping_l['baz'] = [1, 2, 3]
        assert list(mapping_l['baz']) == [1, 2, 3]
        assert 'baz' not in mapping_l.mappings['highest']
        assert mapping_l.mappings['middle']['baz'] == [1, 2, 3]
        assert 'baz' not in mapping_l.mappings['lowest']


class TestOverridableMapping(object):
    def test_reading_lists(self, overridable_l):
        # foo is overridden
        assert list(overridable_l['foo']) == [11, 22, 'a', 'b']

        # bar and baz should behave as MergedSequence
        assert list(overridable_l['baz']) == [1, 2, 3, 4, 5, 6]
        assert list(overridable_l['bar']) == ['a', 'b']

    def test_views_are_immutable(self, overridable_l):
        with pytest.raises(AttributeError):
            overridable_l['foo'].append(1)

        with pytest.raises(TypeError):
            overridable_l['foo'][0] = 2

        with pytest.raises(TypeError):
            del overridable_l['foo'][0]

    def test_setting_lists(self, overridable_l):

        overridable_l['foo'] = [1, 2, 3]

        assert list(overridable_l['foo']) == [1, 2, 3]
        assert overridable_l.scratch['foo:'] == [1, 2, 3]
        assert overridable_l.highest['foo'] == [11, 22]

    def test_setting_dicts(self, overridable_d):

        assert dict(overridable_d['foo'].items()) == {
            'a': 1,
            'b': {'xx': 1},
            'c': 2
        }
        # Getting a key creates an empty dictionary in scratch
        assert overridable_d.scratch['foo'] == {'b': {}}

        # Setting nested keys
        overridable_d['foo']['c'] = 4
        # assert overridable_d.scratch
        assert dict(overridable_d['foo'].items()) == {
            'a': 1,
            'b': {'xx': 1},
            'c': 4
        }
        assert overridable_d.scratch['foo'] == {'b': {}, 'c:': 4}

        overridable_d['foo'] = {'a': 1}
        assert dict(overridable_d['foo'].items()) == {'a': 1}
        assert overridable_d.highest['foo'] == {'a': 1, 'b': {'xx': 1}}

    def test_using_invalid_keys(self, overridable_d):

        with pytest.raises(TypeError) as excinfo:
            key = (1, 2)
            overridable_d[key] = None
        msg = str(excinfo.value)
        assert 'unsupported key type' in msg

        with pytest.raises(TypeError) as excinfo:
            key = (1, 2)
            overridable_d[key]
        msg = str(excinfo.value)
        assert 'unsupported key type' in msg

        with pytest.raises(ValueError) as excinfo:
            overridable_d['foo:'] = None
        msg = str(excinfo.value)
        assert 'a key cannot end with a' in msg
