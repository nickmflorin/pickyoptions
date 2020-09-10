import six

from pickyoptions.lib.utils import check_num_function_arguments
from pickyoptions.configuration import Configuration


class PostProcessConfiguration(Configuration):
    def __init__(self, field):
        super(PostProcessConfiguration, self).__init__(field, required=False, default=None)

    def validate(self):
        super(PostProcessConfiguration, self).validate()
        if self.value is not None:
            if not six.callable(self.value) or not check_num_function_arguments(self.value, 1):
                self.raise_invalid(
                    "Must be a callable that takes the options instance as it's first and "
                    "only argument."
                )


class ValidateConfiguration(Configuration):
    def __init__(self, field):
        super(ValidateConfiguration, self).__init__(field, required=False, default=None)

    def validate(self):
        super(ValidateConfiguration, self).validate()
        if self.value is not None:
            if not six.callable(self.value) or not check_num_function_arguments(self.value, 1):
                self.raise_invalid(
                    "Must be a callable that takes the options instance as it's first and "
                    "only argument."
                )
