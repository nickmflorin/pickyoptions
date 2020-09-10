from pickyoptions.child import Child
from pickyoptions.parent import Parent

from .configuration import Configuration
from .exceptions import ConfigurationDoesNotExist


class EnforceTypesConfiguration(Configuration):
    def __init__(self, field):
        super(EnforceTypesConfiguration, self).__init__(field, default=None)

    def normalize(self, value):
        if hasattr(value, '__iter__') and len(value) == 0:
            return None
        return value

    def validate(self):
        super(EnforceTypesConfiguration, self).validate()
        if self.value is not None:
            if not hasattr(self.value, '__iter__'):
                self.raise_invalid(message="Must be an iterable of types.")
            for tp in self.value:
                if not isinstance(tp, type):
                    self.raise_invalid(message="Must be an iterable of types.")

    def conforms_to(self, value):
        """
        Checks whether or not the provided value conforms to the types specified by
        this configuration.
        """
        if self.value is not None:
            assert type(self.value) is tuple
            if value is None or not isinstance(value, self.value):
                return False
        return True


class Configurations(Parent, Child):
    parent_cls = ('Options', 'Option')
    child_identifier = "field"
    child_cls = Configuration

    unrecognized_child_error = ConfigurationDoesNotExist

    # These are required to get the ABCMeta to work, but I don't think they will ever be
    # used?
    invalid_child_error = None
    invalid_child_type_error = None
    child_required_error = None

    _configured = False

    # Note: This will cause issues with Python3/2 Compat - we need to use **kwargs.
    def __init__(self, *configurations, parent=None):
        self._configuring = False

        Parent.__init__(self, children=list(configurations))
        Child.__init__(self, parent=parent)

    def __repr__(self):
        return "<{cls_name} {configurations}>".format(
            configurations=self.children,
            cls_name=self.__class__.__name__
        )

    @property
    def configured(self):
        return self._configured

    @property
    def configuring(self):
        return self._configuring

    def __getattr__(self, k):
        # TODO: Do we need to check if it is configured here?
        # TODO: Should this part be moved to configurable?
        # WARNING: This might break if there is a configuration that is named the same as an
        # option - we should prevent that.
        # If the value is referring to a configuration, return the configuration value.
        # TODO: Configurations should probably have a configure value...
        # TODO: We should start merging Configurable with Configurations.
        configuration = super(Configurations, self).__getattr__(k)
        # Keep these as sanity checks for the time being - although this logic is likely
        # duplicate and should be removed.
        if configuration.required:
            assert not configuration.default_set
            assert configuration.configured
        return configuration

    # TODO: Maybe move the validate configuration methods to the Configurations level so that
    # when a configuration is set, the overall configurations can be validated.
    def __setattr__(self, k, v):
        if k.startswith('_'):
            super(Configurations, self).__setattr__(k, v)
        else:
            configuration = self[k]
            # Make sure that the configuration can be reconfigured.
            if not configuration.updatable:
                configuration.raise_cannot_reconfigure()

            configuration.configure(v)
            # Validate the overall configuration after the configuration is set.
            self.parent.validate_configuration()

    def configure(self, **kwargs):
        for field, configuration in self:
            if field in kwargs:
                # This will set the configuration as being configured - since the value
                # was explicitly provided.
                configuration.configure(kwargs[field])
            else:
                # This will validate that the configuration is not required before going
                # any further, but will not set the configuration as being configured.
                configuration.value = None

        # Make sure no invalid configurations provided.
        for k, _ in kwargs.items():
            self.raise_if_child_missing(k)

        self._configured = True

    @property
    def configured_configurations(self):
        data = {}
        for k, configuration in self:
            if configuration.configured:
                data[k] = configuration.value
        return data
