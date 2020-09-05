from pickyoptions.configuration import ConfigurableModel
from pickyoptions.configuration.utils import configurable_property, configurable_property_setter

from .configurations import (
    PostProcessorConfiguration, ValidateConfiguration, OptionsConfiguration)


class OptionsConfiguration(ConfigurableModel):
    configurations = (
        PostProcessorConfiguration('post_processor'),
        ValidateConfiguration('validator'),
        OptionsConfiguration('strict', default=False, types=(bool, )),
    )

    @property
    def options(self):
        # Not stored as a separate configuration variable but still requires validation of the
        # configuration when set/changed.
        return self._options

    @options.setter
    def options(self, value):
        # Not stored as a separate configuration variable but still requires validation of the
        # configuration when set/changed.
        self._options = value
        self.validate_configuration()

    @configurable_property
    def post_processor(self):
        pass

    @configurable_property_setter(post_processor)
    def post_processor(self, value):
        pass

    @configurable_property
    def validator(self):
        pass

    @configurable_property_setter(validator)
    def validator(self, value):
        pass

    @configurable_property
    def strict(self):
        pass

    @configurable_property_setter(strict)
    def strict(self, value):
        pass
