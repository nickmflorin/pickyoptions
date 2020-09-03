from pickyoptions.exceptions import PickyOptionsConfigurationError


def test_configuration_error():
    exc = PickyOptionsConfigurationError("The options configuration is invalid.")
    assert str(exc) == "The options configuration is invalid."
