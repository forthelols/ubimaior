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
        config_nc_default = ubimaior.configurations.load(
            'config_nc', scopes=mock_scopes
        )

        assert config_nc == config_nc_default
