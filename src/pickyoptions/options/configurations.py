import six

from pickyoptions.lib.utils import check_num_function_arguments
from pickyoptions.configuration import Configuration


class PostProcessorConfiguration(Configuration):
    def __init__(self, field):
        super(PostProcessorConfiguration, self).__init__(field, required=False, default=None)

    def validate(self, value):
        super(PostProcessorConfiguration, self).validate(value)
        if value is not None:
            if not six.callable(value) or not check_num_function_arguments(value, 1):
                self.raise_invalid(
                    "Must be a callable that takes the options instance as it's first and "
                    "only argument."
                )


class ValidateConfiguration(Configuration):
    def __init__(self, field):
        super(ValidateConfiguration, self).__init__(field, required=False, default=None)

    def validate(self, value):
        super(ValidateConfiguration, self).validate(value)
        if value is not None:
            if not six.callable(value) or not check_num_function_arguments(value, 1):
                self.raise_invalid(
                    "Must be a callable that takes the options instance as it's first and "
                    "only argument."
                )
