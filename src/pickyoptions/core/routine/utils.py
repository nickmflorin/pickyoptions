import functools

from pickyoptions.lib.utils import optional_parameter_decorator


@optional_parameter_decorator
def require_not_in_progress(func, id=None):
    """
    Decorator to decorate routine related methods that require that the
    specified routine's state is not IN_PROGRESS.

    The decorator can be applied to a `obj:Routine` itself or a class that
    extends `obj:Routined`.  In the latter case, the `id` needs to be supplied
    so that the specific `obj:Routine` can be found.
    """
    @functools.wraps(func)
    def inner(instance, *args, **kwargs):
        from pickyoptions.core.routine import Routine

        if isinstance(instance, Routine):
            routine = instance
        else:
            routine = getattr(instance.routines, id)

        if routine.in_progress:
            routine.raise_in_progress()
        return func(instance, *args, **kwargs)
    return inner


@optional_parameter_decorator
def require_finished(func, id=None):
    """
    Decorator to decorate routine related methods that require that the
    specified routine's state is FINISHED.

    The decorator can be applied to a `obj:Routine` itself or a class that
    extends `obj:Routined`.  In the latter case, the `id` needs to be supplied
    so that the specific `obj:Routine` can be found.
    """
    @functools.wraps(func)
    def inner(instance, *args, **kwargs):
        from pickyoptions.core.routine import Routine

        if isinstance(instance, Routine):
            routine = instance
        else:
            routine = getattr(instance.routines, id)

        if not routine.finished:
            routine.raise_not_finished()
        return func(instance, *args, **kwargs)
    return inner
