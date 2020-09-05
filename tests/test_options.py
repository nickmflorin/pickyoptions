import pytest

from pickyoptions import Option, Options


@pytest.fixture
def options():
    yield Options(
        Option('foo', default='fooey_default'),
        Option('bar')
    )


def test_restore_options(options):
    options.populate(foo='fooey_non_default', bar='barrey')
    assert options.foo == 'fooey_non_default'
    options.override(foo='fooey_override')
    assert options.foo == 'fooey_override'
    options.restore()
    assert options.foo == 'fooey_non_default'


def test_populate_unspecified_unrequired_value(options, caplog):
    options.populate(foo='bar')
    assert dict(options) == {
        'foo': 'bar',
        'bar': None
    }
