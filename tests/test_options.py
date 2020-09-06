import pytest

from pickyoptions import Option, Options


@pytest.fixture
def options():
    yield Options(
        Option('color', default='red'),
        Option('height', required=True, enforce_type=(int, float)),
        Option('width', required=False, default=0.0, enforce_type=(int, float)),
    )


def test_restore_options(options):
    options.populate(color='blue', height=5)
    assert options.color == 'blue'
    assert options.height == 5
    assert options.width == 0.0

    options.override(color='red')
    assert options.color == 'red'
    options.restore()
    assert options.color == 'blue'


def test_populate_unspecified_unrequired_value(options, caplog):
    options.populate(color='blue', height=2.0)
    assert dict(options) == {
        'color': 'blue',
        'height': 2.0,
        'width': 0.0,
    }


def test_validate_options():
    pass
