import inspect
import six

from .arrays import *  # noqa
from .functions import *  # noqa
from .path_utils import *  # noqa


def is_null(value):
    if hasattr(value, '__iter__') and len(value) == 0:
        return True
    elif value is None:
        return True
    return False


def classlookup(cls):
    c = list(cls.__bases__)
    for base in c:
        c.extend(classlookup(base))
    return c


# TODO: Make Python2.7/3 Compatible.
def get_class_from_frame(fr):
    """
    Given a frame in the stack, returns the class local to the frame.  This is
    used so we can determine who the caller of a given method is when there
    is circular calling dependencies between parent/child classes.
    """
    args, _, _, value_dict = inspect.getargvalues(fr)
    # Check the first parameter of the frame function is named `self` - if it is,
    # `self` will be referenced in `value_dict`.
    if len(args) != 0 and args[0] == 'self':
        instance = value_dict.get('self', None)
        if instance:
            return getattr(instance, '__class__', None)
    return None


def extends_or_instance_of(child, parent):
    """
    Given a child and a parent, tries to infer whether or not the child is
    an extension of the parent.

    Parameters:
    ----------
    child: `obj:type` or `obj:object`
        The child for which we want to determine if it is an extension of the
        parent.  The child can be a class instance or the class itself.

    parent: `obj:type` or `obj:str` or `obj:object`
        The parent for which we want to determine if the child is an extension
        of.  The parent can either be a class instance, a class name string or
        a class itself.


    Usage:
    -----
    >>> class Parent(object):
    >>>     pass
    >>>
    >>> class Child(Parent):
    >>>     pass
    >>>
    >>> extends_or_instance_of(Child, Parent)
    >>> True
    >>>
    >>> extends_or_instance_of(Child(), Parent)
    >>> True
    >>>
    >>> extends_or_instance_of(Child, Parent())
    >>> True
    >>>
    >>> extends_or_instance_of(Child(), "Parent")
    >>> True
    """
    if isinstance(child, six.string_types):
        raise ValueError("The child cannot be of string type.")

    if isinstance(parent, six.string_types):
        if isinstance(child, type):
            bases = classlookup(child)
            return (
                parent in [base.__name__ for base in bases]
                or child.__name__ == parent
            )
        elif hasattr(child, '__class__'):
            return extends_or_instance_of(child.__class__, parent)
        else:
            raise ValueError("Invalid child type.")

    elif hasattr(parent, '__iter__'):
        extensions = [extends_or_instance_of(child, p) for p in parent]
        return any(extensions)

    # The parent is a class.
    elif isinstance(parent, type):
        if isinstance(child, type):
            # Note: We could probably also call recursively here.
            return parent in classlookup(child) or parent == child
        elif hasattr(child, '__class__'):
            return extends_or_instance_of(child.__class__, parent)
        else:
            raise ValueError("Invalid child type.")

    # The parent is a class instance.
    elif hasattr(parent, '__class__'):
        if isinstance(child, type):
            # Note: We could probably also call recursively here.
            return extends_or_instance_of(child, parent.__class__)
        elif hasattr(child, '__class__'):
            return extends_or_instance_of(child.__class__, parent.__class__)
        else:
            raise ValueError("Invalid child type.")

    else:
        raise ValueError("Invalid parent type.")
