class PickyOptionsError(Exception):
    """
    Base class for all pickyoptions exceptions.
    """
    default_message = "There was an error."

    def __init__(self, *args, **kwargs):
        super(PickyOptionsError, self).__init__()
        try:
            self._message = args[0] if len(args) != 0 else kwargs.pop('message',
                getattr(self, 'default_message'))
        except AttributeError:
            raise AttributeError(
                "Must provide the exception message or set a default on the class."
            )

    @property
    def arguments(self):
        return ()

    def _inject_message_parameters(self, message):
        injection = {}
        for k in self.arguments:
            if "{%s}" % k in message:
                injection[k] = getattr(self, k)
        return message.format(**injection)

    @property
    def bare_message(self):
        return self._message or self.default_message

    @property
    def message(self):
        bare_message = self._inject_message_parameters(self.bare_message)
        if hasattr(self, "identifier"):
            return "\n%s: %s" % (self.identifier, bare_message)
        return bare_message

    def __str__(self):
        return self.message

    def __repr__(self):
        return self.message


class PickyOptionsAttributeError(PickyOptionsError, AttributeError):
    pass


class PickyOptionsUserError(PickyOptionsError):
    """
    Base class for exceptions that are raised due to user supplied options.
    """
    pass


class FieldParameterizedError(PickyOptionsError):
    """
    Abstract base class for exceptions that include a parameter argument.
    """
    def __init__(self, *args, **kwargs):
        self._field = kwargs.pop('field', None)
        super(FieldParameterizedError, self).__init__(*args, **kwargs)

    @property
    def arguments(self):
        arguments = super(FieldParameterizedError, self).arguments
        return arguments + ('field', )

    @property
    def field(self):
        return self._field

    @property
    def bare_message(self):
        if self.field is None:
            return super(FieldParameterizedError, self).bare_message
        elif self._message is not None:
            return "(field = {field}) - %s" % self._message
        return "(field = {field})"


class ValueParameterizedError(FieldParameterizedError):
    """
    Abstract base class for exceptions that include a value argument.
    """
    def __init__(self, *args, **kwargs):
        self._value = kwargs.pop("value", None)
        super(ValueParameterizedError, self).__init__(*args, **kwargs)

    @property
    def arguments(self):
        arguments = super(ValueParameterizedError, self).arguments
        return arguments + ('value', )

    @property
    def value(self):
        return self._value

    @property
    def bare_message(self):
        if self.value is None:
            return super(ValueParameterizedError, self).bare_message
        elif self.field is None:
            if self._message is not None:
                return "{value} - %s" % self._message
            return "{value}"
        else:
            if self._message is not None:
                return "{field} = {value} - %s" % self._message
            return "{field} = {value}"
