from pickyoptions.lib.utils import ensure_iterable, is_null


def make_bold(value):
    return "\033[1m" + "%s" % value + "\033[0;0m"


class PickyOptionsError(Exception):
    """
    Base class for all pickyoptions exceptions.
    """
    default_message = "There was an error."
    default_injection = {}
    ignore_prefix_injectable_arguments = ('instance', )
    ignore_body_injectable_arguments = ()

    def __init__(self, *args, **kwargs):
        super(PickyOptionsError, self).__init__()

        self._children = kwargs.pop('children', [])
        self._numbered_children = kwargs.pop('numbered_children', True)
        self._indent_children = kwargs.pop('indent_children', "--> ")
        self._child_format = kwargs.pop('child_format', None)
        self._newline = kwargs.pop('newline', True)
        self._bold_identifier = kwargs.pop('bold_identifier', True)
        self._detail = kwargs.pop('detail', None)

        self.identifier = kwargs.pop('identifier',
            getattr(self, 'identifier', None))

        # Add in the injection arguments.
        self._injectable_arguments = []
        for k, v in kwargs.items():
            if k != 'message':
                self._injectable_arguments.append(k)
                setattr(self, k, v)

        # Add in the default injection arguments.
        for k, v in self.default_injection.items():
            if k not in self._injectable_arguments:
                self._injectable_arguments.append(k)
                assert not hasattr(self, k)
                setattr(self, k, v)

        # NOTE: This has to come after the injectable arguments are set, because
        # the default message sometimes accesses the injectable arguments set
        # on the instance.
        self._message = (
            args[0] if len(args) != 0
            else kwargs.pop('message', getattr(self, 'default_message'))
        )

    def _has_injection_placeholder(self, argument):
        return "{%s}" % argument in self.message

    @property
    def _body_injectable_arguments(self):
        arguments = []
        for argument in self._injectable_arguments:
            if (
                self._has_injection_placeholder(argument)
                and argument not in self.ignore_body_injectable_arguments
            ):
                value = getattr(self, argument)
                if not is_null(value):
                    arguments.append((argument, value))
        return arguments

    @property
    def _prefix_injectable_arguments(self):
        arguments = []
        for argument in self._injectable_arguments:
            if (
                not self._has_injection_placeholder(argument)
                and argument not in self.ignore_prefix_injectable_arguments
            ):
                # The value should have been set on the instance.
                value = getattr(self, argument)
                if not is_null(value):
                    arguments.append((argument, value))
        return arguments

    @property
    def _injected_message_prefix(self):
        return "(%s)" % ", ".join([
            "%s = %s" % (argument, v)
            for argument, v in self._prefix_injectable_arguments
        ]) if self._prefix_injectable_arguments else ""

    @property
    def _injected_message_body(self):
        injection = {}
        for k, v in self._body_injectable_arguments:
            injection[k] = v
        # Note: This can raise KeyError's if there are references to {...} in
        # the string message but the parameter defined is not provided.  We
        # should figure out a way around this.
        return self.message.format(**injection)

    @property
    def _injected_message(self):
        if self._injected_message_prefix:
            return "%s %s" % (
                self._injected_message_prefix,
                self._injected_message_body
            )
        return self._injected_message_body

    def _format_child(self, child, index):
        assert isinstance(child, Exception)

        # Set the child to not having a new line because we will handle the
        # newline ourselves.
        if isinstance(child, PickyOptionsError):
            child._newline = False

        formatted_child = "%s" % child
        if self._child_format:
            formatted_child = self._child_format(formatted_child)
        if self._numbered_children:
            formatted_child = "(%s) %s" % (index + 1, formatted_child)
        if self._indent_children:
            if not self._indent_children.endswith(' '):
                formatted_child = "%s %s" % (
                    self._indent_children, formatted_child)
            else:
                formatted_child = "%s%s" % (
                    self._indent_children, formatted_child)
        return formatted_child

    @property
    def _formatted_children(self):
        return "\n".join([
            self._format_child(child, i)
            for i, child in enumerate(self._children)
        ])

    @property
    def _formatted_identifier(self):
        if self.identifier is not None:
            if self._bold_identifier:
                return make_bold(self.identifier)
            return self._identifier
        return None

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
        if self._formatted_identifier is not None:
            full_message = "%s: %s" % (
                self._formatted_identifier,
                full_message
            )

        if not full_message.endswith('.'):
            full_message = "%s." % full_message
        if self._detail:
            full_message = "%s %s" % (full_message, self._detail)
        if self._newline:
            full_message = "\n%s" % full_message
        if self._formatted_children:
            return full_message + "\n" + self._formatted_children
        return full_message

    def __str__(self):
        return self.full_message

    def __repr__(self):
        return self.full_message


class DoesNotExistError(PickyOptionsError, AttributeError):
    """
    NOTE:
    ----
    This exception has to extend AttributeError because it is raised in the
    __getattr__ method, and we want that error to trigger __hasattr__ to return
    False.
    """
    default_message = "The attribute `{field}` does not exist on the instance."
