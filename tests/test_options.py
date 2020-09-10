from copy import deepcopy
import pytest

from pickyoptions import Option, Options
from pickyoptions.exceptions import ConfigurationTypeError


def test_restore_options():
    options = Options(
        Option('color', default='red'),
        Option('height', required=True, enforce_types=(int, float)),
        Option('width', required=False, default=0.0, enforce_types=(int, float))
    )
    options.populate(color='blue', height=5)
    assert options.color == 'blue'
    assert options.height == 5
    assert options.width == 0.0

    options.override(color='red')
    assert options.color == 'red'
    options.restore()
    assert options.color == 'blue'


def test_populate_unspecified_unrequired_value():
    options = Options(
        Option('color', default='red'),
        Option('height', required=True, enforce_types=(int, float)),
        Option('width', required=False, default=0.0, enforce_types=(int, float)),
        strict=True
    )
    options.populate(color='blue', height=2.0)
    assert dict(options) == {
        'color': 'blue',
        'height': 2.0,
        'width': 0.0,
    }
    assert options['color'] == options.color == 'blue'
    assert options['height'] == options.height == 2.0
    assert options['width'] == options.width == 0.0
    assert options.strict is True


def test_deepcopy_option():
    options = Options()
    # TODO: Right now this type of methodology is not possible, but we want it to be.
    # option = Option('width', required=False, default=0.0, enforce_types=(int, float),
    #     parent=options)
    # option.populate(1.0)
    options = Options(
        Option('width', required=False, default=0.0, enforce_types=(int, float))
    )
    options.populate(width=1.0)
    option = options.options[0]
    new_option = deepcopy(option)

    assert new_option.configured
    assert new_option.field == 'width'
    assert new_option.required is False
    assert new_option.default == 0.0
    assert new_option.enforce_types == (int, float)
    assert new_option.populated is True
    assert new_option.value == 1.0


def test_option_default_not_of_type():
    with pytest.raises(ConfigurationTypeError):
        Options(
            Option('width', required=False, default=0.0, enforce_types=(int, )),
        )


def test_validate_options():
    pass


def test_options_deepcopy():
    # TODO: Test with and without applying the populated values.
    pass
