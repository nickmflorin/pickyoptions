import functools

from pickyoptions import settings
from pickyoptions.exceptions import PickyOptionsError


def requires_population(func):
    @functools.wraps(func)
    def inner(instance, *args, **kwargs):
        if not instance.populated:
            if settings.DEBUG:
                raise PickyOptionsError(
                    "Operation %s not permitted if the options are not "
                    "yet populated." % func.__name__,
                )
            raise PickyOptionsError(
                "Operation not permitted if the options are not yet populated."
            )
        return func(instance, *args, **kwargs)
    return inner
