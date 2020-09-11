from pickyoptions.lib.utils import ensure_iterable, is_null


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
        self._child_format = kwargs.get('children_format')

        self.identifier = kwargs.pop('identifier',
            getattr(self, 'identifier', None))

        for k, v in kwargs.items():
            if k != 'message':
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
            formatted_child = "%s" % child
            if self._child_format:
                formatted_child = self._child_format(formatted_child)
            if self._numbered_children:
                formatted_child = "(%s) %s" % (i + 1, self._children[i])
            if self._indent_children:
                formatted_child = "%s%s" % self._indent_children
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
        if self.identifier is not None:
            return (
                "%s: %s" % (self.identifier, self._injected_message)
                + self._formatted_children
            )
        return self._injected_message + self._formatted_children

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
