import functools
import six

from pickyoptions.lib.utils import classlookup
from .exceptions import PickyOptionsError


def validate_is_picky_options_error_class(error_cls):
    bases = classlookup(error_cls)
    if PickyOptionsError not in bases:
        raise ValueError(
            "The provided error must be an instance of PickyOptionsError."
        )


def accumulate_errors(error_cls=None, **kws):
    error_cls = error_cls or PickyOptionsError

    def decorator(func):
        @functools.wraps(func)
        def inner(instance, *args, **kwargs):
            return_children = kwargs.pop('return_children', False)
            return_error = kwargs.pop('return_error', False)

            # Allow the error class to be a string attribute on the instance.
            error_kls = error_cls
            if isinstance(error_cls, six.string_types):
                if error_cls not in instance.errors:
                    raise PickyOptionsError(
                        "The provided error %s is not in the instance "
                        "error mapping." % error_cls
                    )
                error_kls = instance.errors[error_cls]
            validate_is_picky_options_error_class(error_kls)

            # Store instance attributes in the arguments provided to the
            # exception.
            new_kws = {}
            for k, v in kws.items():
                new_kws[k] = getattr(instance, v)

            gen = func(instance, *args, **kwargs)
            new_kws['children'] = []

            def append_error(err):
                # Allows us to yield arrays of errors and have them be appended as
                # children.
                if hasattr(err, '__iter__'):
                    for erri in err:
                        append_error(erri)
                else:
                    assert isinstance(err, Exception)
                    new_kws['children'].append(err)

            for exc in gen:
                if exc is not None:
                    append_error(exc)

            if return_children:
                return new_kws['children']
            else:
                error = error_kls(**new_kws)
                if error.has_children:
                    if return_error:
                        return error
                    raise error
                else:
                    return None
        return inner
    return decorator


def raise_with_error(error=None, **kws):
    def decorator(func):
        @functools.wraps(func)
        def inner(instance, *args, **kwargs):
            for k, v in kws.items():
                kwargs.setdefault(k, getattr(instance, v))
            if error is not None:
                if isinstance(error, Exception):
                    kwargs.setdefault('cls', error)
                else:
                    assert isinstance(error, six.string_types)
                    try:
                        error_cls = getattr(instance, 'errors')[error]
                    except KeyError:
                        raise KeyError(
                            "The error for %s is not defined in the "
                            "instance %s error mapping." % (error, instance)
                        )
                    else:
                        validate_is_picky_options_error_class(error_cls)
                        kwargs.setdefault('cls', error_cls)
            return func(instance, *args, **kwargs)
        return inner
    return decorator


def require_set(func):
    """
    Decorator to ensure that the instance value is set before proceeding.

    This decorator can only be applied to instances of `obj:Value` and
    `obj:Valued`.
    """
    @functools.wraps(func)
    def inner(instance, *args, **kwargs):
        from pickyoptions.core.configuration import Configuration
        from pickyoptions.core.options import Option

        assert isinstance(instance, (Configuration, Option))
        if not instance.set:
            instance.raise_not_set()
        return func(instance, *args, **kwargs)
    return inner


def require_set_property(func):
    """
    Decorator for instance properties to ensure that the instance value is
    set before accessing the property value.

    This decorator can only be applied to instances of `obj:Value` and
    `obj:Valued`.

    NOTE:
    ----
    Be careful applying this to properties with setters!
    """
    @property
    def inner(instance, *args, **kwargs):
        from pickyoptions.core.configuration import Configuration
        from pickyoptions.core.options import Option

        assert isinstance(instance, (Configuration, Option))
        if not instance.set:
            instance.raise_not_set()
        return func(instance, *args, **kwargs)
    return inner
