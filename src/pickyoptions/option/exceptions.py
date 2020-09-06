from pickyoptions.exceptions import PickyOptionsError, ObjectTypeError


class OptionError(PickyOptionsError):
    """
    Abstract base class for all exceptions that are raised in reference to a specific
    `obj:Option`.
    """
    pass


class OptionNotPopulatedError(OptionError):
    """
    Raised when trying to access the `obj:Option` value before it has been populated.
    """
    default_message = "The option for field `{field}` has not been populated yet."


class OptionUnrecognizedError(OptionError):
    """
    Raised when a provided option is not recognized - this means that it was never configured
    as a part of the `obj:Options`.
    """
    identifier = "Unrecognized Option"
    default_message = "There is no configured option for field `{field}`."


class OptionInvalidError(OptionError):
    """
    Base class for all exceptions that are raised when a an option value is invalid.
    """
    default_message = "The option for field `{field}` is invalid."
    identifier = "Invalid Option"


class OptionRequiredError(OptionError):
    """
    Raised when an option value is required but not specified.
    """
    default_message = "The option for field `{field}` is required, but was not provided."


class OptionTypeError(ObjectTypeError, OptionInvalidError):
    """
    Raised when an option value is required to be of a specific type but is not of that type.
    """
    @property
    def default_message(self):
        if getattr(self, 'field', None) is not None:
            return "The option for field `{field}` must be an instance of {types}."
        return "Must be an instance of {types}."
