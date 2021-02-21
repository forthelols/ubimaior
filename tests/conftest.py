import pytest

import contextlib
import os.path


@pytest.fixture()
def data_dir():
    """Returns the data directory within the test folder"""
    return os.path.join(os.path.dirname(__file__), "data", "configurations")


@pytest.fixture()
def working_dir():
    """Returns a context-manager that permits to change the working directory."""

    @contextlib.contextmanager
    def _impl(dir):
        try:
            old_dir = os.getcwd()
            yield os.chdir(dir)
        finally:
            os.chdir(old_dir)

    return _impl
