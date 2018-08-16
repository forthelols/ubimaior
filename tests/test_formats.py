import ubimaior.formats

import pytest


def test_decorator_errors():
    with pytest.raises(TypeError) as excinfo:
        ubimaior.formats.formatter(1, 'FORMAT1')
    assert '"name" needs to be of string type' in str(excinfo.value)

    with pytest.raises(TypeError) as excinfo:
        ubimaior.formats.formatter('FORMAT1', 1)
    assert '"attribute" needs to be of string type' in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        ubimaior.formats.formatter('json', attribute='JSON')
    assert 'ubimaior.JSON is already defined' in str(excinfo.value)


def test_no_attribute():
    @ubimaior.formats.formatter('mock')
    class MockFormatter(object):
        pass

    assert 'mock' in ubimaior.formats.FORMATTERS
