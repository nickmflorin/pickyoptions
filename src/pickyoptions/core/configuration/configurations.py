import logging

from pickyoptions import settings, constants

from pickyoptions.core.base import track_init
from pickyoptions.core.parent import Parent

from .configurable import SimpleConfigurable
from .configuration import Configuration
from .exceptions import ConfigurationDoesNotExist


logger = logging.getLogger(settings.PACKAGE_NAME)


# TODO: Implement child properties like _set, _default and _value.
# TODO: This acts a little funky as a Child, since the Child class wants to
# be able to access an identifier...
class Configurations(Parent, SimpleConfigurable):

    # Child Implementation Properties
    parent_cls = ('Options', 'Option')
    child_identifier = "field"
    child_cls = Configuration
    does_not_exist_error = ConfigurationDoesNotExist

    @track_init
    def __init__(self, *configurations, **kwargs):
        self._validate = kwargs.pop('validate', None)
        SimpleConfigurable.__init__(self)
        Parent.__init__(self, children=list(configurations))

    def __repr__(self):
        # TODO: Keep track of state as an attribute.
        if self.initialized:
            return "<{cls_name} {configurations}>".format(
                configurations=self.children,
                cls_name=self.__class__.__name__
            )
        return "<{cls_name} state={state}>".format(
            state=constants.NOT_INITIALIZED,
            cls_name=self.__class__.__name__
        )

    @property
    def __isabstractmethod__(self):
        # This is an annoying side effect of using ABCMeta, not sure exactly
        # why it is being triggered yet but it is messing with the __getattr__
        # method.
        return False

    def __getattr__(self, k):
        """
        Retrieves and returns the `obj:Configuration` in the set of
        `obj:Configurations` based on the `obj:str` `field` attribute of the
        `obj:Configuration`.

        If the `obj:Configuration` does not exist,
        `obj:ConfigurationDoesNotExist` will be raised.
        """
        # This is an annoying side effect of using ABCMeta
        # if self.has_child(k):
        #     configuration = super(Configurations, self).__getattr__(k)
        #
        #     # Keep these as sanity checks for the time being - although this logic
        #     # is likely duplicate and should be removed.
        #     if configuration.required:
        #         if configuration.value_instance.set:
        #             assert not configuration.value_instance.defaulted
        #         # This seems to be causing problems when we try to access the
        #         # field configuration from the configurations at times when the
        #         # field configuration is not configured.  We should change the field
        #         # to not be a configuration.
        #         # assert configuration.configured
        #     return configuration
        # try:
        #     assert self.configured
        # except AssertionError:
        #     import ipdb; ipdb.set_trace()
        # assert self.configured

        # TODO: Should part of this be moved to a parent configurable/simple
        # configurable class?
        configuration = super(Configurations, self).__getattr__(k)

        # Keep these as sanity checks for the time being - although this logic
        # is likely duplicate and should be removed.
        if configuration.required:
            if configuration.set:
                assert not configuration.defaulted
            # This seems to be causing problems when we try to access the
            # field configuration from the configurations at times when the
            # field configuration is not configured.  We should change the field
            # to not be a configuration.
            # assert configuration.configured
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
            self.validate()

    def validate_configuration(self):
        if self._validate_configuration is not None:
            self._validate_configuration()

    def _configure(self, **kwargs):
        """
        Configures the `obj:Configuration`(s) of the overall
        `obj:Configurations` instance with the provided mapping of key-value
        pairs.

        For each field in the key-value pairs, if the `obj:Configuration` does
        not exist for the field, `obj:ConfigurationDoesNotExist` will be raised.

        NOTE:
        ----
        The configuration validation is performed in the ConfigurationRoutine
        of the owner class.
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
