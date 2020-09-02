from ..exceptions import InvalidOption
from ..utils import ensure_iterable


class Option(object):
    """
    Represents a single option configuration for an option in the `obj:Options`.

    Parameters:
    ----------
    field: `obj:str`
        The field name of the specific `obj:Option` that will allow the `obj:Option` to be accessible on the
        `obj:Options` instance.

    default: `obj:any` (optional)
        The default value of the option.
        Default: None

    validator: `obj:func` (optional)
        A function that will be used to validate the `obj:Option`.  The function must take the value and the
        `obj:Options` instance as arguments and returns a string message if the `obj:Option` is invalid.

        The validator indicates a valid option by not returning anything.  It can indicate an invalid option by
        either:
          1.  Returning a message string.
          2.  Raising InvalidOption
          3.  Returning True (Allows conditional checks to be performed as validators)
        Default: None

    allow_null: `obj:bool` (optional)
        Whether or not the `obj:Option` value is allowed to be None.
        Default: False

    type: `obj:type` (optional)
        The type of the `obj:Option` value to enforce.
        Default: None

    mergable: `obj:boolean` (optional)
        Whether or not the `obj:Option` is mergable.  If the `obj:Option` is mergable, than updating the
        `obj:Options` with a new value for the option will cause it to do a partial update on the existing
        value.  This is only applicable if the new and old values are of type `obj:dict`.
        Default: False

    normalize: `obj:func` (optional)
        A function to be called to normalize the `obj:Option` value before it is set on the `obj:Options`.
        The function must take the value of the `obj:Option` and the current `obj:Options` instance as
        arguments.

        The normalize method can also raise InvalidOption.
        Default: None

    post_process: `obj:func` (optional)
        A function to be called whenever the option is set on the `obj:Options` instance.  The function takes
        the set value of the option as it's first argument and the overall `obj:Options` instance as it's second
        argument.
        Default: None

    help_text: `obj:str` (optional)
        Help text to describe what the option does.
        Default: ""
    """
    def __init__(self, field, default=None, validator=None, allow_null=False, type=None, mergable=False,
            normalize=None, post_process=None, help_text=""):

        self.field = field
        self.default = default
        self.allow_null = allow_null
        self.type = type
        self.help_text = help_text
        self.mergable = mergable

        self._validator = validator
        self._normalize = normalize
        self._post_process = post_process

    def __repr__(self):
        return "<Option field={field} help={help}>".format(
            field=self.field,
            help=self.help_text
        )

    def raise_invalid(self, value=None, message="The option is invalid."):
        raise InvalidOption(param=self.field, value=value, message=message)

    @property
    def display(self):
        return (
            "Option:\n"
            "  Field: {field}\n"
            "  Default: {default}\n"
            "  Allow Null: {allow_null}\n\n"
            "  {help_text}"
        ).format(
            field=self.field,
            allow_null=self.allow_null,
            default=self.default,
            help_text=self.help_text,
        )

    def normalize(self, value, options):
        if self._normalize:
            return self._normalize(value, options)
        return value

    def post_process(self, value, options):
        if self._post_process:
            self._post_process(value, options)
        return value

    def validate(self, value, options):
        """
        Validates the `obj:Option` value before it is set on the `obj:Options` instance.

        The `obj:Option` value is validated against the following criteria:
          (1) Whether or not the `obj:Option` value is allowed to be None and whether or not it is None.
          (2) Whether or not the `obj:Option` value has restricted types and if it is of those types.
          (3) Whether or not the `obj:Option` validator indicates that the `obj:Option` value is invalid.
        """
        if value is None and not self.allow_null:
            self.raise_invalid(message="The option cannot be None.")

        if value is not None and self.type is not None:
            if not isinstance(value, self.type):
                tps = ["%s" % tp for tp in ensure_iterable(self.type)]
                self.raise_invalid(message="Must be of type %s." % ", ".join(tps))

        if value is not None and self._validator:
            # The validation method returns a string message if the option is invalid, or it raises InvalidOption
            # if the option is invalid, otherwise it returns None.
            validation_result = self._validator(value, options)
            if validation_result is not None:
                assert type(validation_result) is bool or type(validation_result) is str
                if isinstance(validation_result, str):
                    self.raise_invalid(value=value, message=validation_result)
                elif validation_result is True:
                    self.raise_invalid(value=value)
