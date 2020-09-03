from pickyoptions.exceptions import OptionConfigurationError


def test_configuration_error():
    exc = OptionConfigurationError(
        field='normalize',
        message=(
            "Must be a callable that takes the option value as it's first "
            "argument, the option instance as it's second argument and the overall "
            "combined options instance as it's third argument."
        )
    )
    print(exc)
