from pickyoptions.lib.utils import classlookup
from .exceptions import PickyOptionsError


def validate_is_picky_options_error_class(error_cls):
    bases = classlookup(error_cls)
    if PickyOptionsError not in bases:
        raise ValueError(
            "The provided error must be an instance of PickyOptionsError."
        )
