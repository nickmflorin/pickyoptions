from pickyoptions.exceptions import ObjectTypeError

from pickyoptions.configuration import ConfigurableModel, Configuration
from pickyoptions.configuration.utils import configurable_property, configurable_property_setter

from pickyoptions.option.base import Option

from .configurations import PostProcessConfiguration, ValidateConfiguration


class OptionsConfiguration(ConfigurableModel):
    configurations = (
        PostProcessConfiguration('post_process'),
        ValidateConfiguration('validator'),
        Configuration('strict', default=False, types=(bool, )),
    )

    def validate_configuration(self):
        """
        Validates the configuration for configuration variables that depend on one another,
        after they are set.

        Note that this doesn't involve validating the configurations for the invidual
        `obj:Option`(s), as those will be validated on their own initialization.
        """
        super(OptionsConfiguration, self).validate_configuration()

        # TODO: Maybe we should move this to just validate when the options are set.
        # This would be problematic, because we set the options privately as a configuration,
        # they need to be validated when the options are configured.
        for option in self.options:
            if not isinstance(option, Option):
                raise ObjectTypeError(
                    "The options must all be instances of {types}.",
                    types=Option
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
        for option in self._options:
            option._options = self

    # Will this public/private pairing work?
    @configurable_property
    def post_process(self):
        pass

    @configurable_property_setter(post_process)
    def post_process(self, value):
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
