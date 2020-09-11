import logging

from pickyoptions import settings, constants

from pickyoptions.core.base import track_init
from pickyoptions.core.child import Child
from pickyoptions.core.configuration import Configuration
from pickyoptions.core.configurable import SimpleConfigurable
from pickyoptions.core.parent import Parent

from .exceptions import ConfigurationDoesNotExist


logger = logging.getLogger(settings.PACKAGE_NAME)


# TODO: Implement child properties like _set, _default and _value.
class Configurations(Parent, Child, SimpleConfigurable):

    # Child Implementation Properties
    parent_cls = ('Options', 'Option')
    child_identifier = "field"
    child_cls = Configuration
    unrecognized_child_error = ConfigurationDoesNotExist

    @track_init
    def __init__(self, *configurations, **kwargs):
        SimpleConfigurable.__init__(self)
        Parent.__init__(self, children=list(configurations))
        Child.__init__(self, parent=kwargs.get('parent'))

    def __repr__(self):
        if self.initialized:
            return "<{cls_name} {configurations}>".format(
                configurations=self.children,
                cls_name=self.__class__.__name__
            )
        return "<{state} {cls_name}>".format(
            state=constants.NOT_INITIALIZED,
            cls_name=self.__class__.__name__
        )

    def __getattr__(self, k):
        """
        Retrieves and returns the `obj:Configuration` in the set of
        `obj:Configurations` based on the `obj:str` `field` attribute of the
        `obj:Configuration`.

        If the `obj:Configuration` does not exist,
        `obj:ConfigurationDoesNotExist` will be raised.
        """
        # This is an annoying side effect of using ABCMeta
        if k == '__isabstractmethod__':
            return super(Configurations, self).__getattr__(k)

        assert self.configured

        # TODO: Should part of this be moved to a parent configurable/simple
        # configurable class?
        configuration = super(Configurations, self).__getattr__(k)

        # Keep these as sanity checks for the time being - although this logic
        # is likely duplicate and should be removed.
        if configuration.required:
            assert not configuration.defaulted
            assert configuration.configured
        return configuration

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
            if not configuration.updatable:
                configuration.raise_cannot_reconfigure()

            configuration.configure(v)

            # Validate the overall configuration after the configuration is set.
            self.parent.validate_configuration()

    def configure(self, **kwargs):
        """
        Configures the `obj:Configuration`(s) of the overall
        `obj:Configurations` instance with the provided mapping of key-value
        pairs.

        For each field in the key-value pairs, if the `obj:Configuration` does
        not exist for the field, `obj:ConfigurationDoesNotExist` will be raised.
        """
        # Make sure no invalid configurations provided.
        for k, _ in kwargs.items():
            self.raise_if_child_missing(k)

        # It is important here that we loop over all the `obj:Configurations`,
        # because configuring should replace all of the `obj:Configuration`
        # values.
        with self.configuration_routine():
            for field, configuration in self:
                if field in kwargs:
                    # This will set the configuration as being configured - since
                    # the value was explicitly provided.
                    configuration.configure(kwargs[field])
                else:
                    # This will not set teh configuration as being configured,
                    # since the value was not explicitly provided.  It will
                    # however validate that the configuration is not required
                    # before proceeding.
                    configuration.value = None

    @property
    def explicitly_set_configurations(self):
        """
        Returns the key-value pairs of explicitly set configuration values
        that were provided on configuration of the `obj:Configurations`.
        """
        data = {}
        for field, configuration in self:
            if configuration.configured:
                data[field] = configuration.value
        return data
