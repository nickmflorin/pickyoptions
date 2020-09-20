from copy import deepcopy
import pytest

from pickyoptions import Option, Options
from pickyoptions.core.options.exceptions import (
    OptionConfigurationError, OptionNotSetError)


def test_get_option_value_option_not_set():
    options = Options(
        Option('color', default='red'),
        Option('height', required=True, types=(int, float)),
        Option('width', required=False, default=0.0, types=(int, float))
    )
    option = options.get_option('color')
    with pytest.raises(OptionNotSetError) as e:
        option.value
    assert e.value.name == 'color'


def test_default_option():
    options = Options(
        Option('color', default='red'),
        Option('height', required=True, types=(int, float)),
        Option('width', required=False, default=0.0, types=(int, float))
    )
    options.populate(height=1.0)
    option = options.get_option('color')
    assert option.defaulted is True

    options.reset()
    options.populate(color='green', height=1.0)
    assert option.defaulted is False


def test_deepcopy_option():
    options = Options(
        Option('width', required=False, default=0.0, types=(int, float))
    )
    options.populate(width=1.0)
    option = options.options[0]
    new_option = deepcopy(option)

    assert new_option.configured
    assert new_option.field == 'width'
    assert new_option.required is False
    assert new_option.default == 0.0
    assert new_option.types == (int, float)
    assert new_option.routines.populating.finished is True
    assert new_option.value == 1.0


def test_option_default_not_of_type():
    with pytest.raises(OptionConfigurationError):
        options = Options(
            Option('width', required=False, default=0.0, types=(int, )),
        )
        # We have to populate because the configuration validation is lazy.
        options.populate()
