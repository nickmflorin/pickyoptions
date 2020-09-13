from pickyoptions.core.exceptions import PickyOptionsError, ValueTypeError
from pickyoptions.core.option.exceptions import OptionTypeError


def test_picky_options_error():
    exc = PickyOptionsError("This is a test message.", field="test-field")
    assert str(exc) == "\n(field = test-field) This is a test message."

    exc = PickyOptionsError("The {field} is invalid.", field="test-field")
    assert str(exc) == '\nThe test-field is invalid.'

    exc = PickyOptionsError("The {field} value is invalid.", field="test-field",
        value="test-value")
    assert str(exc) == '\n(value = test-value) The test-field value is invalid.'

    exc = PickyOptionsError(
        "The {field} value is invalid.",
        field="test-field",
        value="test-value",
        identifier="Invalid Field Value"
    )
    assert str(exc) == (
        '\n\033[1mInvalid Field Value\033[0;0m: (value = test-value) '
        'The test-field value is invalid.'
    )


def test_value_type_error():
    exc = ValueTypeError(types=(str, int))
    assert str(exc) == (
        "\n\033[1mInvalid Value Type\033[0;0m: The value must be of type "
        "(<class 'str'>, <class 'int'>)."
    )

    exc = ValueTypeError(name="test-field", types=(str, int))
    assert str(exc) == (
        "\n\033[1mInvalid Value Type\033[0;0m: The test-field "
        "must be of type (<class 'str'>, <class 'int'>)."
    )


def test_option_type_error():
    exc = OptionTypeError(name='option-field', types=(str, int))
    assert str(exc) == (
        "\n\033[1mInvalid Option\033[0;0m: The option option-field "
        "must be of type (<class 'str'>, <class 'int'>)."
    )


def test_children_errors():
    exc = PickyOptionsError(
        message="This is a parent error message.",
        identifier="Test Error",
        children=[
            PickyOptionsError(
                message="This is a child error message.",
                field="child-field-1"
            ),
            PickyOptionsError(
                message="This is a child error message.",
                field="child-field-2"
            ),
        ]
    )
    assert str(exc) == (
        "\n\033[1mTest Error\033[0;0m: This is a parent error message."
        "\n--> (1) (field = child-field-1) This is a child error message."
        "\n--> (2) (field = child-field-2) This is a child error message."
    )


def test_default_injection():
    class TestError(PickyOptionsError):
        default_injection = {"name": "test-name"}
        default_message = "The {name} is invalid."

    exc = TestError()
    assert str(exc) == "\nThe test-name is invalid."

    exc = TestError(name='new-name')
    assert str(exc) == "\nThe new-name is invalid."
