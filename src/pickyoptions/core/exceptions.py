from pickyoptions.lib.utils import ensure_iterable, is_null


def make_bold(value):
    return "\033[1m" + "%s" % value + "\033[0;0m"


class PickyOptionsError(Exception):
    """
    Base class for all pickyoptions exceptions.
    """
    default_message = "There was an error."

    def __init__(self, *args, **kwargs):
        super(PickyOptionsError, self).__init__()
        self._injectable_arguments = []
        self._children = kwargs.get('children', [])
        self._numbered_children = kwargs.get('numbered_children', True)
        self._indent_children = kwargs.get('indent_children', "--> ")
        self._child_format = kwargs.get('child_format')
        self._newline = kwargs.get('newline', True)
        self._bold_identifier = kwargs.get('bold_identifier', True)

        self.identifier = kwargs.pop('identifier',
            getattr(self, 'identifier', None))

        for k, v in kwargs.items():
            if k not in ('message', 'children'):
                self._injectable_arguments.append(k)
                setattr(self, k, v)

        try:
            self._message = args[0] if len(args) != 0 else kwargs.pop('message',
                getattr(self, 'default_message'))
        except AttributeError:
            raise AttributeError(
                "Must provide the exception message or set a default on the "
                "class."
            )

    def _inject_message_parameters(self, message):
        injection = {}
        for k in self._injectable_arguments:
            if "{%s}" % k in message:
                injection[k] = getattr(self, k)
        # Note: This can raise KeyError's if there are references to {...} in
        # the string message but the parameter defined is not provided.  We
        # should figure out a way around this.
        return message.format(**injection)

    @property
    def _injectable_message(self):
        injectables = []
        for argument in self._injectable_arguments:
            value = getattr(self, argument, None)
            if not is_null(value) and "{%s}" % argument not in self.message:
                injectables.append((argument, value))
        if injectables:
            return "(%s)" % ", ".join([
                "%s = %s" % (argument, v)
                for argument, v in injectables
            ]) + " " + self.message
        return self.message

    @property
    def _injected_message(self):
        return self._inject_message_parameters(self._injectable_message)

    @property
    def _formatted_children(self):
        formatted_children = []
        for i, child in enumerate(self._children):
            child._newline = False
            formatted_child = "%s" % child
            if self._child_format:
                formatted_child = self._child_format(formatted_child)
            if self._numbered_children:
                formatted_child = "(%s) %s" % (i + 1, formatted_child)
            if self._indent_children:
                formatted_child = "%s%s" % (
                    self._indent_children, formatted_child)
            formatted_children.append(formatted_child)
        return "\n".join(formatted_children)

    @property
    def has_children(self):
        return len(self._children) != 0

    def append(self, e):
        self._children.append(e)

    @property
    def message(self):
        return self._message

    @property
    def full_message(self):
        full_message = self._injected_message
        if self.identifier is not None:
            if self._bold_identifier:
                full_message = "%s: %s" % (
                    make_bold(self.identifier),
                    self._injected_message
                )
            else:
                full_message = "%s: %s" % (
                    self.identifier,
                    self._injected_message
                )
        if self._newline:
            full_message = "\n%s" % full_message
        if self._formatted_children:
            return full_message + "\n" + self._formatted_children
        return full_message

    def __str__(self):
        return self.full_message

    def __repr__(self):
        return self.full_message


class ObjectTypeError(PickyOptionsError):
    """
    Raised when an option user provided value is required to be of a specific
    type but is not of that type.
    """
    def __init__(self, *args, **kwargs):
        kwargs['types'] = ensure_iterable(kwargs.get('types'))
        super(ObjectTypeError, self).__init__(*args, **kwargs)

    @property
    def default_message(self):
        if len(self.types) != 0:
            if getattr(self, 'field', None) is not None:
                return "The field `{field}` must be of type {types}."
            return "Must be of type {types}."
        if getattr(self, 'field', None) is not None:
            return "The field `{field}` is not of the correct type."
        return "Invalid type."


class ParentHasChildError(PickyOptionsError):
    default_message = "The parent already has the child in it's children."


class DoesNotExistError(PickyOptionsError, AttributeError):
    """
    NOTE:
    ----
    This exception has to extend AttributeError because it is raised in the
    __getattr__ method, and we want that error to trigger __hasattr__ to return
    False.
    """
    default_message = "The attribute `{field}` does not exist on the instance."


class PickyOptionsValueError(PickyOptionsError, ValueError):
    pass


class ValueNotSetError(PickyOptionsValueError):
    default_message = "The value has not been set yet."


class ValueLockedError(PickyOptionsValueError):
    default_message = "The value is locked and cannot be changed."


class ValueRequiredError(PickyOptionsValueError):
    default_message = "The value is required."


class ValueInvalidError(PickyOptionsValueError):
    default_message = "The value is invalid."


class ValueTypeError(ObjectTypeError, ValueInvalidError):
    @property
    def default_message(self):
        if len(self.types) != 0:
            if getattr(self, 'field', None) is not None:
                return "The value for field `{field}` must be of type {types}."
            return "The value must be of type {types}."
        if getattr(self, 'field', None) is not None:
            return "The value for field `{field}` is not of the correct type."
        return "The value is of invalid type."
