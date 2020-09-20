from abc import ABCMeta
from copy import deepcopy
import logging
import six

from pickyoptions import settings
from pickyoptions.lib.utils import (
    ensure_iterable, merge_dicts, merge_lists, extends_or_instance_of,
    space_join)


logger = logging.getLogger(settings.PACKAGE_NAME)


def make_bold(value):
    return "\033[1m" + "%s" % value + "\033[0;0m"


# Until we figure out how to appropriately use the __new__ method for an object,
# without the name, bases and dct attrributes, we have to use the ABCMeta as our
# base.
class PickyOptionsErrorMeta(ABCMeta):
    """
    Metaclass for the `obj:Base` model.
    """
    def __new__(cls, name, bases, dct):
        # Conglomerate Default Injection from Parents
        default_injections = []
        for parent in bases:
            base_injection = deepcopy(getattr(parent, 'default_injection', {}))
            assert isinstance(base_injection, dict)
            default_injections.append(base_injection)
        default_injection = merge_dicts(default_injections)

        this_default_injection = deepcopy(
            dct.pop('default_injection', {}))
        assert isinstance(this_default_injection, dict)
        default_injection.update(this_default_injection)

        # Set the class default injection as the combined injections.
        dct['default_injection'] = default_injection

        # Conglomerate Ignore Prefix Injection from Parents
        ignore_prefix_injections = []
        for parent in bases:
            base_ignore = deepcopy(
                getattr(parent, 'ignore_prefix_injection', ()))
            assert isinstance(base_ignore, (tuple, list, str))
            ignore_prefix_injections.append(base_ignore)
        this_ignore = deepcopy(dct.pop('ignore_prefix_injection', ()))
        ignore_prefix_injections.append(this_ignore)

        dct['ignore_prefix_injections'] = merge_lists(
            ignore_prefix_injections, cast=tuple)

        return super(PickyOptionsErrorMeta, cls).__new__(cls, name, bases, dct)


class PickyOptionsError(six.with_metaclass(PickyOptionsErrorMeta, Exception)):
    """
    Base class for all pickyoptions exceptions.
    """
    default_message = "There was an error."
    default_injection = {}
    ignore_prefix_injection = ('instance', )

    # These properties are passed down from the parent to it's children.
    child_configuration_properties = (
        'parent',
        'numbered_children',
        'child_format',
        'newline',
        'bold_identifier',
        'include_prefix',
        'indent_children',
    )

    def __init__(self, *args, **kwargs):
        super(PickyOptionsError, self).__init__()

        # Here, we have to set properties specific to the `obj:PickyOptionsError`
        # and not the children - otherwise, all of the children will be
        # overwritten to conform to the parent value.
        self._children = kwargs.pop('children', [])
        self._detail = kwargs.pop('detail', None)

        # Here, we configure values for the parent `obj:PickyOptionsError` that
        # we want the children instances to have as well.
        self.configure_self_and_children(**kwargs)

        # Add in the injection arguments.
        self._injection = {}
        for k, v in kwargs.items():
            if k != 'message' and k not in self.child_configuration_properties:
                self._injection[k] = v

        self._identifier = kwargs.pop('identifier',
            getattr(self, 'identifier', None))

        # NOTE: This has to come after the injectable arguments are set, because
        # the default message sometimes accesses the injectable arguments set
        # on the instance.
        self._message = (
            args[0] if len(args) != 0
            else kwargs.pop('message', self.default_message)
        )

    def configure_self_and_children(self, **kwargs):
        self._index = kwargs.pop('index', 0)
        self._parent = kwargs.pop('parent', None)
        self._numbered_children = kwargs.pop('numbered_children', True)
        self._child_format = kwargs.pop('child_format', None)
        self._newline = kwargs.pop('newline', True)
        self._bold_identifier = kwargs.pop('bold_identifier', True)
        self._include_prefix = kwargs.pop('include_prefix', True)
        self._indent_prefix = kwargs.pop('indent_prefix', "--> ")

        for i, child in enumerate(self.children):
            if isinstance(child, PickyOptionsError):
                child.configure_self_and_children(
                    parent=self,
                    index=i,
                    child_format=self._child_format,
                    include_prefix=self._include_prefix,
                    newline=self._newline,
                    bold_identifier=self._bold_identifier,
                    indent_prefix=self._indent_prefix,
                    numbered_children=self._numbered_children
                )

        # Must come after the children are configured.
        self.indent(n=0)

    def __getattr__(self, k):
        if k in self._injection:
            return self._injection[k]
        raise AttributeError("The attribute %s does not exist." % k)

    def __setattr__(self, k, v):
        if not k.startswith('_'):
            if k in self._injection:
                logger.debug(
                    "Overwriting exception value for %s, %s, with %s." % (
                        k, self._injection[k], v)
                )
            self._injection[k] = v
        else:
            super(PickyOptionsError, self).__setattr__(k, v)

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, deepcopy(v, memo))
        return result

    def transform(self, cls, **kwargs):
        """
        Transforms the `obj:PickyOptionsError` instance into another
        `obj:PickyOptionsError` instance, provided by `cls`, overriding the
        properties with the provided parameters.

        Parameters:
        ----------
        cls: `obj:type`
            The PickyOptionsError class for which we want to transform the
            error.  This parameter must be a class that is PickyOptionsError or
            a class that extends PickyOptionsError.
        """
        if not extends_or_instance_of(cls, PickyOptionsError):
            raise ValueError("The class must extend PickyOptionsError.")

        new_cls = cls.__new__(cls)
        for k, v in self.__dict__.items():
            if k in kwargs:
                setattr(new_cls, k, deepcopy(kwargs[k]))
            else:
                setattr(new_cls, k, deepcopy(v))
        return new_cls

    @property
    def parent(self):
        return self._parent

    @property
    def include_prefix(self):
        return self._include_prefix

    @property
    def newline(self):
        return self._newline

    @property
    def indent_level(self):
        return self._indent_level

    @property
    def indent_prefix(self):
        return self._indent_prefix

    def indent(self, n=1):
        self._indent_level = n
        for child in self.children:
            if isinstance(child, PickyOptionsError):
                child.indent(n=n + 1)
            else:
                # The error will not have any children so we don't have to
                # worry about recursive nature.
                child._indent_level = n + 1

    @property
    def indentation(self):
        return "  " * self.indent_level

    @property
    def numbered_children(self):
        return self._numbered_children

    @property
    def index(self):
        if self.numbered_children:
            return "(%s)" % (self._index + 1)
        return ""

    @property
    def injection(self):
        injection = {}
        prefix_injection = {}
        for k, v in self._injection.items():
            if self._has_injection_placeholder(k):
                injection[k] = v
            else:
                prefix_injection[k] = v
        for k, v in self.default_injection.items():
            if k not in injection and self._has_injection_placeholder(k):
                injection[k] = v
        return injection, prefix_injection

    @property
    def children(self):
        return self._children

    def _has_injection_placeholder(self, argument):
        return "{%s}" % argument in self._message

    @property
    def identifier(self):
        if self._identifier is not None:
            if self._bold_identifier:
                return make_bold(self._identifier)
            return self._identifier
        return ""

    @property
    def has_children(self):
        return len(self._children) != 0

    def append(self, e):
        self._children.append(e)

    @property
    def message(self):
        injection, prefix_injection = self.injection
        message = self._message.format(**injection)
        if not message.endswith('.'):
            message = "%s." % message
        return message

    @property
    def detail(self):
        if self._detail is not None:
            if (self._detail != "" and not self._detail.endswith('(')
                    and not self._detail.startswith('(')):
                return "(%s)" % self._detail
        return self._detail

    @property
    def prefix(self):
        injection, prefix_injection = self.injection
        if self.include_prefix:
            return " ".join([
                "(%s=%s)" % (k, v)
                for k, v in prefix_injection.items()
            ])
        return None

    @property
    def body(self):
        return space_join(
            (self.identifier, "", ":"),
            self.prefix,
            self.message,
            self.detail
        )

    @property
    def full_message(self):
        if self.parent is None:
            full_message = self.body
        else:
            full_message = space_join(
                self.indentation,
                self.indent_prefix,
                self.index,
                self.body
            )
        if self.newline:
            full_message = "\n%s" % full_message
        return full_message + "".join(["%s" % child for child in self.children])

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


class ValueNullNotAllowedError(PickyOptionsValueError):
    default_message = "The {name} is not allowed to be null."


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
