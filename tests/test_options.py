from pickyoptions import Option, Options


def test_restore_options():
    options = Options(
        Option('foo', default='fooey_default'),
        Option('bar')
    )
    options.populate(foo='fooey_non_default', bar='barrey')
    assert options.foo == 'fooey_non_default'
    options.override(foo='fooey_override')
    assert options.foo == 'fooey_override'
    options.restore()
    assert options.foo == 'fooey_non_default'


def test_populate_unspecified_unrequired_value():
    options = Options(
        Option('foo', required=True),
        Option('bar')
    )
    options.populate(foo='bar')
    assert options.foo == 'bar'
    options.foo = None
