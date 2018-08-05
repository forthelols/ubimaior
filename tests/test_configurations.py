import os.path
import pytest

import ubimaior.configurations


@pytest.fixture()
def mock_scopes():
    data_dir = os.path.join(os.path.dirname(__file__), 'data', 'configurations')
    return [
        ('highest', os.path.join(data_dir, 'highest')),
        ('middle', os.path.join(data_dir, 'middle')),
        ('doesnotexist', os.path.join(data_dir, 'doesnotexist')),
        ('lowest', os.path.join(data_dir, 'lowest'))
    ]


@pytest.fixture()
def tmp_scopes(tmpdir):
    highest = tmpdir.mkdir('highest')
    middle = tmpdir.mkdir('middle')
    doesnotexist = os.path.join(str(tmpdir), 'doesnotexist')
    lowest = tmpdir.mkdir('lowest')
    return [
        ('highest', str(highest)),
        ('middle', str(middle)),
        ('doesnotexist', doesnotexist),
        ('lowest', str(lowest))
    ]


class TestBasicAPI(object):
    def test_loading_configurations(self, mock_scopes):
        # Try to call passing all the parameters explicitly
        config_nc = ubimaior.configurations.load(
            'config_nc', scopes=mock_scopes, config_format='json', schema=False
        )

        assert config_nc['foo'] == 1
        assert config_nc['bar'] == 'this_is_bar'
        assert config_nc['baz'] is False

        assert config_nc.middle == {'foo': 6, 'bar': 'this_is_bar'}

        # Call using default values
        ubimaior.configurations.set_default_scopes(mock_scopes)
        ubimaior.configurations.set_default_format(ubimaior.JSON)
        config_nc_default = ubimaior.configurations.load('config_nc')

        assert config_nc == config_nc_default

    def test_set_wrong_defaults(self):
        # Scopes
        with pytest.raises(TypeError):
            ubimaior.configurations.set_default_scopes('ll')

        with pytest.raises(TypeError):
            ubimaior.configurations.set_default_scopes([1, 2])

        with pytest.raises(TypeError):
            ubimaior.configurations.set_default_scopes([('a',), ('b', 'dir')])

        # Formats
        with pytest.raises(TypeError):
            ubimaior.configurations.set_default_format(1)

        with pytest.raises(ValueError):
            ubimaior.configurations.set_default_format('toml')

    def test_default_settings(self):
        # Check that all the keys allowed in the settings are there
        assert all(x in ubimaior.configurations.ConfigSettings.valid_settings
                   for x in ubimaior.configurations.DEFAULTS)

        assert not any(x not in ubimaior.configurations.ConfigSettings.valid_settings
                       for x in ubimaior.configurations.DEFAULTS)

        assert len(ubimaior.configurations.DEFAULTS) == 3

        # Iterate through the keys and check that they are initialized to None.
        default = ubimaior.configurations.ConfigSettings()
        for setting in default:
            assert default[setting] is None
            assert getattr(default, setting) is None

        # Try to delete an item
        del default['scopes']
        assert len(default) == 2

        # Assigning that key is still valid
        default['scopes'] = [('single', 'somedir')]

        # Assigning other settings is an error
        with pytest.raises(KeyError):
            default['somesetting'] = 1

        # Trying to access an attribute that is not supported
        with pytest.raises(AttributeError):
            default.does_not_exist

    def test_dumping_configurations(self, mock_scopes, tmp_scopes):
        # Load the test configurations
        ubimaior.configurations.set_default_scopes(mock_scopes)
        ubimaior.configurations.set_default_format(ubimaior.JSON)
        cfg = ubimaior.configurations.load('config_nc')

        # Dump them somewhere
        ubimaior.configurations.dump(cfg, 'config_nc', scopes=tmp_scopes)

        # Reload and check
        cfg_dumped = ubimaior.configurations.load('config_nc', scopes=tmp_scopes)

        assert cfg == cfg_dumped

        # Check that I can't have modifications in scratch when dumping
        cfg['foobar'] = [1, 2, 3]
        with pytest.raises(ValueError):
            ubimaior.configurations.dump(cfg, 'config_nc', scopes=tmp_scopes)

        # Check that scopes ust match when dumping
        tmp_scopes[2:] = []
        with pytest.raises(ValueError):
            ubimaior.configurations.dump(cfg_dumped, 'config_nc', scopes=tmp_scopes)
