import os.path
import pytest

import ubimaior
import ubimaior.configurations


@pytest.fixture()
def mock_scopes(data_dir):
    return [
        ("highest", os.path.join(data_dir, "highest")),
        ("middle", os.path.join(data_dir, "middle")),
        ("doesnotexist", os.path.join(data_dir, "doesnotexist")),
        ("lowest", os.path.join(data_dir, "lowest")),
    ]


@pytest.fixture()
def tmp_scopes(tmpdir):
    highest = tmpdir.mkdir("highest")
    middle = tmpdir.mkdir("middle")
    doesnotexist = os.path.join(str(tmpdir), "doesnotexist")
    lowest = tmpdir.mkdir("lowest")
    return [
        ("highest", str(highest)),
        ("middle", str(middle)),
        ("doesnotexist", doesnotexist),
        ("lowest", str(lowest)),
    ]


@pytest.fixture(params=[ubimaior.JSON, ubimaior.YAML, ubimaior.TOML])
def config_format(request):
    return request.param


@pytest.fixture(
    params=[
        None,  # No schema validation
        {"type": "object"},  # Validate from an object in memory
        os.path.join(
            os.path.dirname(__file__),
            "data",
            "configurations",
            "schema",
            "config_nc_schema.json",
        ),  # Validate from a schema stored in a file
    ]
)
def schema(request):
    return request.param


@pytest.fixture()
def schema_with_wrong_format(tmpdir):
    p = tmpdir.join("schema.txt")
    p.write("foo")
    return str(p)


class TestBasicAPI(object):
    def test_loading_configurations(self, mock_scopes, config_format, schema):
        # Try to call passing all the parameters explicitly
        config_nc = ubimaior.configurations.load(
            "config_nc", scopes=mock_scopes, config_format=config_format, schema=schema
        )

        assert config_nc["foo"] == 1
        assert config_nc["bar"] == "this_is_bar"
        assert config_nc["baz"] is False
        assert list(config_nc["nested"]["a"]) == [1, 2, 3, 4, 5, 6]
        assert config_nc["nested"]["b"] is True

        assert config_nc.middle == {"foo": 6, "bar": "this_is_bar"}

        assert config_nc.lowest == {
            "bar": "4",
            "baz": False,
            "nested": {"a": [4, 5, 6], "b": True},
        }

        # Call using default values
        ubimaior.configurations.set_default_scopes(mock_scopes)
        ubimaior.configurations.set_default_format(config_format)
        config_nc_default = ubimaior.configurations.load("config_nc")

        assert config_nc == config_nc_default

    def test_set_wrong_defaults(self):
        # Scopes
        with pytest.raises(TypeError):
            ubimaior.configurations.set_default_scopes("ll")

        with pytest.raises(TypeError):
            ubimaior.configurations.set_default_scopes([1, 2])

        with pytest.raises(TypeError):
            ubimaior.configurations.set_default_scopes([("a",), ("b", "dir")])

        # Formats
        with pytest.raises(TypeError):
            ubimaior.configurations.set_default_format(1)

        with pytest.raises(ValueError):
            ubimaior.configurations.set_default_format("not_registered")

    def test_default_settings(self):
        # Check that all the keys allowed in the settings are there
        assert all(
            x in ubimaior.configurations.ConfigSettings.valid_settings
            for x in ubimaior.configurations.DEFAULTS
        )

        assert not any(
            x not in ubimaior.configurations.ConfigSettings.valid_settings
            for x in ubimaior.configurations.DEFAULTS
        )

        assert len(ubimaior.configurations.DEFAULTS) == 3

        # Iterate through the keys and check that they are initialized to None.
        default = ubimaior.configurations.ConfigSettings()
        for setting in default:
            assert default[setting] is None
            assert getattr(default, setting) is None

        # Try to delete an item
        del default["scopes"]
        assert len(default) == 2

        # Assigning that key is still valid
        default["scopes"] = [("single", "somedir")]

        # Assigning other settings is an error
        with pytest.raises(KeyError):
            default["somesetting"] = 1

        # Trying to access an attribute that is not supported
        with pytest.raises(AttributeError):
            default.does_not_exist

    def test_dumping_configurations(self, mock_scopes, config_format, tmp_scopes, schema):
        # Load the test configurations
        ubimaior.configurations.set_default_scopes(mock_scopes)
        ubimaior.configurations.set_default_format(config_format)
        cfg = ubimaior.configurations.load("config_nc")

        # Dump them somewhere
        ubimaior.configurations.dump(cfg, "config_nc", scopes=tmp_scopes, schema=schema)

        # Reload and check
        cfg_dumped = ubimaior.configurations.load("config_nc", scopes=tmp_scopes, schema=schema)

        assert cfg == cfg_dumped

        # Check that I can't have modifications in scratch when dumping
        cfg["foobar"] = [1, 2, 3]
        with pytest.raises(ValueError) as excinfo:
            ubimaior.configurations.dump(cfg, "config_nc", scopes=tmp_scopes)
        assert "cannot dump an object with modifications in scratch" in str(excinfo.value)

        # Check that instead flattening the hierarchy works
        cfg = cfg.flattened()
        ubimaior.configurations.dump(cfg, "config_nc", scopes=tmp_scopes)
        cfg_dumped = ubimaior.configurations.load("config_nc", scopes=tmp_scopes)

        assert cfg == cfg_dumped

        # Check that scopes must match when dumping
        tmp_scopes[2:] = []
        with pytest.raises(ValueError) as excinfo:
            ubimaior.configurations.dump(cfg_dumped, "config_nc", scopes=tmp_scopes)
        assert "scopes in the object do not match" in str(excinfo.value)

    def test_file_errors_on_validate(self, schema_with_wrong_format):
        # Passing as argument a schema that does not exist
        with pytest.raises(ValueError) as excinfo:
            ubimaior.configurations.validate({}, schema="foo")
        assert "does not exist or is not a file" in str(excinfo.value)

        # Passing as argument a schema with the wrong format
        with pytest.raises(ValueError) as excinfo:
            ubimaior.configurations.validate({}, schema=schema_with_wrong_format)
        assert "is not a valid format [Allowed formats are:" in str(excinfo.value)

    @pytest.mark.parametrize(
        "configuration_file",
        [
            ".ubimaior.json",
            ".ubimaior.yaml",
        ],
    )
    def test_source_configuration_file(self, configuration_file, data_dir, tmp_scopes):
        # Sourcing a configuration file should properly set configuration values
        configuration_file = os.path.join(data_dir, configuration_file)
        ubimaior.configurations.setup_from_file(configuration_file)

        # Load a configuration and dump it somewhere
        cfg = ubimaior.configurations.load("config_nc")
        ubimaior.configurations.dump(cfg, "config_nc", scopes=tmp_scopes)

        # Reload and check
        cfg_dumped = ubimaior.configurations.load("config_nc", scopes=tmp_scopes)
        assert cfg == cfg_dumped

    def test_errors_when_sourcing_configuration_file(self, data_dir):
        # Try to use a non existing file
        with pytest.raises(IOError) as excinfo:
            ubimaior.configurations.setup_from_file("doesnotexist")
        assert "does not exist" in str(excinfo.value)


def test_search_for_files(data_dir, working_dir):
    # Testing with absolute path and relative path should return the same result
    abs_search = ubimaior.configurations.search_file_in_path(
        os.path.join(data_dir, ".ubimaior.json")
    )
    with working_dir(data_dir):
        rel_search = ubimaior.configurations.search_file_in_path(".ubimaior.json")

    assert rel_search == abs_search

    # If the file does not exist, the function should raise an IOError
    with pytest.raises(IOError) as exc_info:
        ubimaior.configurations.search_file_in_path("foo.txt")
    assert "file not found" in str(exc_info.value)

    with pytest.raises(IOError) as exc_info:
        ubimaior.configurations.search_file_in_path(os.path.join(data_dir, "foo.txt"))
    assert "file not found" in str(exc_info.value)
