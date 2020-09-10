from copy import deepcopy
import pytest

from pickyoptions import Option, Options
from pickyoptions.configuration.exceptions import ConfigurationTypeError


def test_deepcopy_option():
    options = Options()
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
    assert new_option.routines.populating.finished is True
    assert new_option.value == 1.0


def test_option_default_not_of_type():
    with pytest.raises(ConfigurationTypeError):
        Options(
            Option('width', required=False, default=0.0, enforce_types=(int, )),
        )
