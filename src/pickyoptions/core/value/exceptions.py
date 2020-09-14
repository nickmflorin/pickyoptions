from pickyoptions.lib.utils import ensure_iterable
from pickyoptions.core.exceptions import PickyOptionsError


class PickyOptionsValueError(PickyOptionsError, ValueError):
    default_injection = {"name": "value"}


class ValueNotSetError(PickyOptionsValueError):
    default_message = "The {name} has not been set yet."


class ValueSetError(PickyOptionsValueError):
    default_message = "The {name} has already been set."


class ValueLockedError(PickyOptionsValueError):
    default_message = "The {name} is locked and cannot be changed."


class ValueRequiredError(PickyOptionsValueError):
    default_message = "The {name} is required."


class ValueNotRequiredError(PickyOptionsValueError):
    default_message = "The {name} is not required."


class ValueInvalidError(PickyOptionsValueError):
    identifier = "Invalid Value"
    default_message = "The {name} is invalid."


class ValueTypeError(ValueInvalidError):
    identifier = "Invalid Value Type"

    def __init__(self, *args, **kwargs):
        kwargs['types'] = ensure_iterable(kwargs.get('types'))
        super(ValueTypeError, self).__init__(*args, **kwargs)

    @property
    def default_message(self):
        if len(self.types) != 0:
            return "The {name} must be of type {types}."
        return "The {name} is not of the correct type."
