import pytest

from pickyoptions.core.configuration import Configuration
from pickyoptions.core.configuration.configuration_lib import TypesConfiguration
from pickyoptions.core.configuration.exceptions import ConfigurationError


def test_configuration_configured_on_init():
    configuration = Configuration('field', default='test')
    assert configuration.configured is True


def test_types_configuration():
    configuration = TypesConfiguration('types')
    configuration.value = (str, int)
    assert configuration.conforms_to("foo") is True
    assert configuration.conforms_to(5) is True
    assert configuration.conforms_to(4.15) is False


def test_types_configuration_invalid_value():
    configuration = TypesConfiguration('types')
    with pytest.raises(ConfigurationError):
        configuration.value = "foo"


def test_configuration_required_default_provided():
    with pytest.raises(ConfigurationError):
        Configuration(
            'field_name',
            required=True,
            default='default_field'
        )
