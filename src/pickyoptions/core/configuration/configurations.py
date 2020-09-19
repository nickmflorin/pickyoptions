import logging

from pickyoptions import settings, constants

from .configurable import ConfigurableParent
from .configuration import Configuration
from .exceptions import ConfigurationDoesNotExist


logger = logging.getLogger(settings.PACKAGE_NAME)


# TODO: Implement child properties like _set, _default and _value.
class Configurations(ConfigurableParent):
    __abstract__ = False

    # Parent Implementation Properties
    child_cls = Configuration

    errors = {
        'does_not_exist_error': ConfigurationDoesNotExist
    }

    def __init__(self, *configurations, **kwargs):
        validation_error = kwargs.pop('validation_error', None)
        configuration_error = kwargs.pop('validation_error', None)

        super(Configurations, self).__init__(
            children=list(configurations),
            *kwargs
        )

        # Pass overridden errors down through to the individual
        # `obj:Configuration` children.
        for configuration in self.children:
            configuration.override_errors(
                validation_error=validation_error,
                configuration_error=configuration_error
            )

    def __repr__(self):
        if self.initialized:
            return super(Configurations, self).__repr__(
                configurations=self.children,
            )
        return super(Configurations, self).__repr__(
            state=constants.NOT_INITIALIZED
        )

    def get_configuration(self, k):
        # Avoid use of super().__getattr__ because it can be buggy.  We should
        # only use the __getattr__ for public access.
        configuration = self.get_child(k)
        # Keep these as sanity checks for the time being - although this logic
        # is likely duplicate and should be removed.
        if configuration.required:
            if configuration.set:
                assert not configuration.defaulted
            assert configuration.configured
        return configuration

    def __getattr__(self, k):
        """
        Retrieves and returns the `obj:Configuration` in the set of
        `obj:Configurations` based on the `obj:str` `field` attribute of the
        `obj:Configuration`.

        If the `obj:Configuration` does not exist,
        `obj:ConfigurationDoesNotExist` will be raised.
        """
        if k.startswith('_'):
            raise AttributeError("The attribute %s does not exist." % k)
        return self.get_configuration(k)

    def __setattr__(self, k, v):
        """
        Updates the value of the `obj:Configuration` whose field is associated
        with the provided `obj:str` `field` attribute by configuring the
        `obj:Configuration` with the provided value.

        If the `obj:Configuration` does not exist,
        `obj:ConfigurationDoesNotExist` will be raised.

        If the `obj:Configuration` is already configured and cannot be
        reconfigured, `obj:ConfigurationCannotReconfigureError` will be
        raised.
        """
        # Note: This will cause issues if configurations are privately scoped.
        if not self.initialized or k.startswith('_'):
            object.__setattr__(self, k, v)
        else:
            configuration = self[k]

            # Make sure that the configuration can be reconfigured.
            # TODO: Use configuration.locked.
            if not configuration.updatable:
                configuration.raise_cannot_reconfigure()

            configuration.configure(v)

            # Validate the overall configuration after the configuration is set.
            self.validate()

    def subsection(self, fields):
        return self.__class__(*tuple([getattr(self, field) for field in self]))

    def validate_configuration(self):
        """
        Validates the individual `obj:Configuration` children in the overall
        `obj:Configurations`.
        """
        pass
        # Do we want to do this?  What is this accomplishing?  Is this double
        # validating?
        # self.parent.validate_configuration()
        # if self._validate_configuration is not None:
        #     self._validate_configuration()

    def _configure(self, **kwargs):
        """
        Configures the `obj:Configuration`(s) of the overall
        `obj:Configurations` instance with the provided mapping of key-value
        pairs.

        For each field in the key-value pairs, if the `obj:Configuration` does
        not exist for the field, `obj:ConfigurationDoesNotExist` will be raised.
        """
        # Make sure no invalid configurations provided.
        for k, _ in kwargs.items():
            # TODO: Change name to raise_if_unknown_child.
            self.raise_if_child_missing(k)

        # It is important here that we loop over all the `obj:Configurations`,
        # because configuring should replace all of the `obj:Configuration`
        # values.
        for field, configuration in self:
            if field in kwargs:
                configuration.value = kwargs[field]
            else:
                configuration.set_default()

    @property
    def explicitly_set_configurations(self):
        data = {}
        for field, configuration in self:
            if configuration.configured:
                data[field] = configuration
        return data

    @property
    def explicitly_set_configuration_values(self):
        """
        Returns the key-value pairs of explicitly set configuration values
        that were provided on configuration of the `obj:Configurations`.
        """
        data = {}
        for k, v in self.explicitly_set_configurations.items():
            data[k] = v.value
        return data
