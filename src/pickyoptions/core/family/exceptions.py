from pickyoptions.core.exceptions import PickyOptionsError


class ParentHasChildError(PickyOptionsError):
    default_message = "The parent already has the child in it's children."
