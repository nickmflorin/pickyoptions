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

    def __init__(self, *args, **kwargs):
        super(PickyOptionsError, self).__init__()

        # This is tough to do recursively because of the stipulation that other
        # built in errors should be able to be nested.
        self._children = kwargs.pop('children', [])

        # TODO: Figure out how to do this for an infinite level of nesting.
        self._indent_level = 0
        for child in self.children:
            child._indent_level = self._indent_level + 1
            if isinstance(child, PickyOptionsError):
                for grandchild in child.children:
                    grandchild._indent_level = child._indent_level + 1

        self._numbered_children = kwargs.pop('numbered_children', True)
        self._indent_children = kwargs.pop('indent_children', "--> ")
        self._child_format = kwargs.pop('child_format', None)
        self._newline = kwargs.pop('newline', True)
        self._bold_identifier = kwargs.pop('bold_identifier', True)
        self._detail = kwargs.pop('detail', None)
        self._include_prefix = kwargs.pop('include_prefix', True)

        # Add in the injection arguments.
        self._injection = {}
        for k, v in kwargs.items():
            if k != 'message':
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
        return "{%s}" % argument in self.message

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
            indentation = "    " * (child._indent_level)
            return space_join(
                indentation,
                self._indent_children,
                formatted_child
            )
        return formatted_child

    @property
    def _formatted_children(self):
        return "\n".join([
            self._format_child(child, i)
            for i, child in enumerate(self._children)
        ])

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
        return self._message

    @property
    def full_message(self):
        injection, prefix_injection = self.injection

        full_message = self.message.format(**injection)
        if not full_message.endswith('.'):
            full_message = "%s." % full_message
        assert full_message[0] != " "

        detail = self._detail or ""
        if (detail != "" and not detail.endswith('(')
                and not detail.startswith('(')):
            detail = "(%s)" % detail

        prefix = ""
        if self._include_prefix:
            prefix = " ".join([
                "(%s=%s)" % (k, v)
                for k, v in prefix_injection.items()
            ])

        full_message = space_join(
            (self.identifier, "", ":"),
            prefix,
            full_message,
            detail
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
