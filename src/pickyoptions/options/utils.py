import functools

from pickyoptions import settings

from .exceptions import OptionsNotPopulatedError


def requires_population(func):
    @functools.wraps(func)
    def inner(instance, *args, **kwargs):
        if not instance.populated:
            if settings.DEBUG:
                raise OptionsNotPopulatedError(
                    "Operation %s not permitted if the options are not "
                    "yet populated." % func.__name__,
                )
            raise OptionsNotPopulatedError()
        return func(instance, *args, **kwargs)
    return inner
