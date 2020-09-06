from pickyoptions.lib.utils import ensure_iterable


class PickyOptionsError(Exception):
    """
    Base class for all pickyoptions exceptions.
    """
    default_message = "There was an error."

    def __init__(self, *args, **kwargs):
        super(PickyOptionsError, self).__init__()
        self._injectable_arguments = []

        self.identifier = kwargs.pop('identifier', getattr(self, 'identifier', None))

        for k, v in kwargs.items():
            if k != 'message':
                self._injectable_arguments.append(k)
                setattr(self, k, v)

        try:
            self._message = args[0] if len(args) != 0 else kwargs.pop('message',
                getattr(self, 'default_message'))
        except AttributeError:
            raise AttributeError(
                "Must provide the exception message or set a default on the class."
            )

    def _inject_message_parameters(self, message):
        injection = {}
        for k in self._injectable_arguments:
            if "{%s}" % k in message:
                injection[k] = getattr(self, k)
        return message.format(**injection)

    @property
    def _injectable_message(self):
        injectables = []
        for argument in self._injectable_arguments:
            value = getattr(self, argument, None)
            if value is not None and "{%s}" % argument not in self.message:
                injectables.append((argument, value))
        if injectables:
            return "(%s)" % ", ".join([
                "%s = %s" % (argument, value)
                for argument, value in injectables
            ]) + " " + self.message
        return self.message

    @property
    def _injected_message(self):
        return self._inject_message_parameters(self._injectable_message)

    @property
    def message(self):
        return self._message

    @property
    def full_message(self):
        if self.identifier is not None:
            return "%s: %s" % (self.identifier, self._injected_message)
        return self._injected_message

    def __str__(self):
        return self.full_message

    def __repr__(self):
        return self.full_message


class ObjectTypeError(PickyOptionsError):
    """
    Raised when an option user provided value is required to be of a specific type but is
    not of that type.
    """
    def __init__(self, *args, **kwargs):
        kwargs['types'] = ensure_iterable(kwargs['types'])
        super(ObjectTypeError, self).__init__(*args, **kwargs)

    @property
    def default_message(self):
        if getattr(self, 'field', None) is not None:
            return "The field {field} must be an instance of {types}."
        return "Must be an instance of {types}."
