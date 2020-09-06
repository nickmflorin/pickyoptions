import functools

from pickyoptions import settings

from .exceptions import OptionNotPopulatedError


def requires_population(func):
    @functools.wraps(func)
    def inner(instance, *args, **kwargs):
        if not instance.populated:
            if settings.DEBUG:
                raise OptionNotPopulatedError(
                    "Operation %s not permitted if the option is not "
                    "yet populated." % func.__name__,
                )
            raise OptionNotPopulatedError()
        return func(instance, *args, **kwargs)
    return inner
