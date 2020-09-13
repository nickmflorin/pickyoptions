from copy import deepcopy
import logging

from pickyoptions import settings
from pickyoptions.core.base import BaseModel

from .exceptions import NotConfiguredError, ConfiguringError
from .state import ConfigurationState

logger = logging.getLogger(settings.PACKAGE_NAME)


# TODO: Merge this with the other routines in a common class.
class ConfigurationRoutine(object):
    def __init__(self, instance):
        self._instance = instance

    def __enter__(self):
        logger.debug("Entering configuration routine context.")
        self._instance.pre_configuration()
        self._instance.assert_not_configuring()
        if self._instance.configured:
            logger.debug("Reconfiguring %s." % self.__class__.__name__)
        self._instance._state = ConfigurationState.CONFIGURING

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.debug("Exiting configuration routine context.")
        self._instance._state = ConfigurationState.CONFIGURED
        if exc_type:
            return False
        self._instance.post_configuration()
        return False


class SimpleConfigurable(BaseModel):
    not_configured_error = NotConfiguredError
    configuring_error = ConfiguringError

    abstract_methods = ('_configure', )

    def __init__(self, **kwargs):
        self._state = ConfigurationState.NOT_CONFIGURED
        configure_on_init = kwargs.pop('configure_on_init', False)
        if configure_on_init:
            self.configure(**kwargs)

    @property
    def state(self):
        return self._state

    @property
    def configured(self):
        return self.state == ConfigurationState.CONFIGURED

    @property
    def not_configured(self):
        return self.state in (
            ConfigurationState.CONFIGURING, ConfigurationState.NOT_CONFIGURED)

    @property
    def configuring(self):
        return self.state == ConfigurationState.CONFIGURING

    def pre_configuration(self):
        logger.debug("Performing pre-configuration.")

    def post_configuration(self):
        logger.debug("Performing post-configuration.")

    def assert_configured(self):
        if not self.configured:
            self.raise_not_configured()

    def assert_not_configuring(self):
        if self.configuring:
            self.raise_configuring()

    def raise_configuring(self, *args, **kwargs):
        assert self.configuring is True
        kwargs.setdefault('cls', self.configuring_error)
        return self.raise_with_self(*args, **kwargs)

    def raise_not_configured(self, *args, **kwargs):
        assert self.configured is False
        kwargs.setdefault('cls', self.not_configured_error)
        return self.raise_with_self(*args, **kwargs)

    def configure(self, *args, **kwargs):
        routine = ConfigurationRoutine(self)
        with routine:
            self._configure(*args, **kwargs)


class Configurable(SimpleConfigurable):
    abstract_properties = ('configurations', )
    # We don't need the _configure method for the Configurable class, only the
    # SimpleConfigurable class.
    abstract_methods = ('validate_configuration', )

    def __init__(self, **kwargs):
        super(Configurable, self).__init__()

        # The __setattr__ on models is sometimes overridden.
        configurations = deepcopy(self.configurations)
        # Set the validation routine of the `obj:Configurations`.
        # TODO: Should we maybe specify this on initialization?
        configurations._validate_configuration = self.validate_configuration
        object.__setattr__(self, 'configurations', configurations)

        self.configure(**kwargs)
        # This should already be happening with the post configuration.
        # self.validate_configuration()

    @property
    def configuring(self):
        assert self.configurations.configuring == super(Configurable, self).configuring  # noqa
        return super(Configurable, self).configuring

    def _configure(self, *args, **kwargs):
        self.configurations.configure(*args, **kwargs)
        assert self.configurations.configured

    def post_configuration(self):
        assert self.configured
        assert self.configurations.configured
        self.validate_configuration()
