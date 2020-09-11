import pytest

from pickyoptions import Option, Options
from pickyoptions.options.exceptions import OptionsInvalidError


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


def test_restore_options_multiple_overrides():
    options = Options(
        Option('color', default='red'),
        Option('height', required=True, enforce_types=(int, float)),
        Option('width', required=False, default=0.0, enforce_types=(int, float))
    )
    options.populate(color='blue', height=2.0)

    options.override(color='red')
    options.override(color='green', height=10.0)
    options.override(width=2.0)

    options.restore()
    assert dict(options) == {
        'color': 'blue',
        'height': 2.0,
        'width': 0.0,
    }


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


def test_validate_options_on_population():
    def validate_options(options):
        if options.height < options.width:
            options.raise_invalid("The height must be greater than the width.")

    options = Options(
        Option('color', default='red'),
        Option('height', required=True, enforce_types=(int, float)),
        Option('width', required=False, default=0.0, enforce_types=(int, float)),
        validate=validate_options
    )
    with pytest.raises(OptionsInvalidError) as e:
        options.populate(width=5.0, height=1.0, color='green')
    assert str(e.value) == "Invalid Options: The height must be greater than the width."


def test_validate_options_on_override():
    def validate_options(options):
        if options.height < options.width:
            options.raise_invalid("The height must be greater than the width.")

    options = Options(
        Option('color', default='red'),
        Option('height', required=True, enforce_types=(int, float)),
        Option('width', required=False, default=0.0, enforce_types=(int, float)),
        validate=validate_options
    )
    options.populate(width=1.0, height=4.0, color='green')

    with pytest.raises(OptionsInvalidError) as e:
        options.override(width=5.0)
    assert str(e.value) == "Invalid Options: The height must be greater than the width."


def test_options_deepcopy():
    # TODO: Test with and without applying the populated values.
    pass
