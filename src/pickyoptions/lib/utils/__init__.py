import inspect
import six

from .arrays import *  # noqa
from .functions import *  # noqa
from .path_utils import *  # noqa


def is_null(value):
    # This first conditional takes into account empty strings.
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


def strip_if_not_blank(value):
    """
    Strips the string value if and only if all the characters in the string
    are not " ".
    """
    if any([i != " " for i in value]):
        return value.strip()
    return value


def space_join(*items):
    """
    Safely joins an array of iterables together while preventing empty/null
    values from corrupting the final string spacing and allowing prefix/suffix
    values to be included for each element if the element is not null.

    Usage:
    -----
    >>> space_join(["a", ("b", "", ":"), None, "", "c"])
    >>> "a b: c"
    """
    valid_items = []
    for item in items:
        if item is None:
            continue
        if isinstance(item, tuple):
            if item[0] is None:
                continue
            stripped = strip_if_not_blank(item[0])
            if not is_null(stripped):
                if len(item) == 2:
                    if not is_null(item[1]):
                        valid_items.append("%s%s" % (item[1], stripped))
                    else:
                        valid_items.append(stripped)
                elif len(item) >= 3:
                    if not is_null(item[1]) and not is_null(item[2]):
                        valid_items.append("%s%s%s" % (
                            item[1], stripped, item[2]))
                    elif not is_null(item[1]):
                        valid_items.append("%s%s" % (item[1], stripped))
                    elif not is_null(item[2]):
                        valid_items.append("%s%s" % (stripped, item[2]))
        else:
            stripped = strip_if_not_blank(item)
            if stripped != "":
                valid_items.append(stripped)
    return " ".join(valid_items)


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
