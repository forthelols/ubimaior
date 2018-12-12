import click.testing
import pytest

import ubimaior.commands
import ubimaior.formats


@pytest.fixture()
def runner():
    return click.testing.CliRunner()


@pytest.fixture(params=ubimaior.formats.FORMATTERS)
def fmt(request):
    return request.param


def test_showing_help(runner, working_dir, data_dir):
    result = runner.invoke(ubimaior.commands.main, ['--help'])
    assert result.exit_code == 0
    assert 'Manages hierarchical configuration files' in result.output

    with working_dir(data_dir):
        result = runner.invoke(ubimaior.commands.main, ['show', '--help'])
        assert result.exit_code == 0


def test_show_all_formats(runner, working_dir, data_dir, fmt):
    with working_dir(data_dir):
        result = runner.invoke(
            ubimaior.commands.main, ['--format={0}'.format(fmt), 'show', 'config_nc']
        )
        assert result.exit_code == 0


def test_failures(runner, working_dir, data_dir):
    # .ubimaior.yaml not found
    result = runner.invoke(ubimaior.commands.main, ['show', '--help'])
    assert result.exit_code == 1
    assert 'ubimaior configuration file not found' in result.output

    # Call validate without having a schema
    with working_dir(data_dir):
        result = runner.invoke(ubimaior.commands.main, ['show', '--validate', 'config_nc'])
        assert result.exit_code == 1
        assert ' validation schema not found' in result.output


def test_validate_configurations(runner, working_dir, data_dir):
    with working_dir(data_dir):
        result = runner.invoke(
            ubimaior.commands.main,
            ['--configuration=.ubimaior.json', 'show', '--validate', 'config_nc']
        )
        assert result.exit_code == 0


def test_show_blame(runner, working_dir, data_dir, fmt):
    with working_dir(data_dir):
        result = runner.invoke(
            ubimaior.commands.main, ['--format={0}'.format(fmt), 'show', '--blame', 'config_nc']
        )
        assert result.exit_code == 0
