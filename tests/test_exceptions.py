from pickyoptions.exceptions import PickyOptionsError, ObjectTypeError
from pickyoptions.option.exceptions import OptionTypeError


def test_picky_options_error():
    exc = PickyOptionsError("This is a test message.", field="test-field")
    assert str(exc) == "(field = test-field) This is a test message."

    exc = PickyOptionsError("The {field} is invalid.", field="test-field")
    assert str(exc) == 'The test-field is invalid.'

    exc = PickyOptionsError("The {field} value is invalid.", field="test-field",
        value="test-value")
    assert str(exc) == '(value = test-value) The test-field value is invalid.'

    exc = PickyOptionsError(
        "The {field} value is invalid.",
        field="test-field",
        value="test-value",
        identifier="Invalid Field Value"
    )
    assert str(exc) == 'Invalid Field Value: (value = test-value) The test-field value is invalid.'

    exc = ObjectTypeError(types=(str, int))
    assert str(exc) == "Must be an instance of (<class 'str'>, <class 'int'>)."

    exc = ObjectTypeError(field="test-field", types=(str, int))
    assert str(exc) == "The field test-field must be an instance of (<class 'str'>, <class 'int'>)."

    exc = OptionTypeError(field='option-field', types=(str, int))
    assert str(exc) == (
        "Invalid Option: The option option-field must be an instance of "
        "(<class 'str'>, <class 'int'>)."
    )
