from abc import ABCMeta, abstractmethod, abstractproperty
from copy import deepcopy
import contextlib
import logging
import six
import sys

from pickyoptions import settings
from pickyoptions.base import BaseModel

from .constants import ConfigurationState
from .exceptions import (
    NotConfiguredError, CannotReconfigureError, ConfiguringError)


logger = logging.getLogger(settings.PACKAGE_NAME)


class SimpleConfigurable(six.with_metaclass(ABCMeta, BaseModel)):
    not_configured_error = NotConfiguredError
    cannot_reconfigure_error = CannotReconfigureError
    configuring_error = ConfiguringError

    def __init__(self):
        self._state = ConfigurationState.NOT_CONFIGURED

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

    @abstractmethod
    def configure(self):
        pass

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

    def raise_cannot_reconfigure(self, *args, **kwargs):
        assert self.configured is True
        kwargs['cls'] = self.cannot_reconfigure_error
        return self.raise_with_self(*args, **kwargs)

    @contextlib.contextmanager
    def configuration_routine(self):
        logger.debug("Entering configuration routine context.")
        self.pre_configuration()
        self.assert_not_configuring()
        if self.configured:
            logger.debug("Reconfiguring %s." % self.__class__.__name__)
        self._state = ConfigurationState.CONFIGURING
        try:
            yield self
        except Exception:
            six.reraise(*sys.exc_info())
        finally:
            # Configured will only be False before the first configuration,
            # afterwards it will always be True.
            # TODO: Should there be a way to reset the configurations?
            self._state = ConfigurationState.CONFIGURED
            self.post_configuration()
            logger.debug("Exiting configuration routine context.")


class Configurable(six.with_metaclass(ABCMeta, SimpleConfigurable)):

    def __init__(self, extra_configurations=None, **kwargs):
        super(Configurable, self).__init__()

        configurations = deepcopy(self.configurations)
        configurations.add_children(extra_configurations or [])

        # The __setattr__ on models is sometimes overridden.
        object.__setattr__(self, 'configurations', configurations)

        # The configurations must be assigned a parent before continuing with
        # the configuration.
        self.configurations.assign_parent(self)
        self.configure(**kwargs)
        self.validate_configuration()

    @abstractproperty
    def configurations(self):
        pass

    @abstractmethod
    def validate_configuration(self):
        pass

    @property
    def configured(self):
        assert self.configurations.configured == super(Configurable, self).configured  # noqa
        return super(Configurable, self).configured

    @property
    def configuring(self):
        assert self.configurations.configuring == super(Configurable, self).configuring  # noqa
        return super(Configurable, self).configuring

    def configure(self, *args, **kwargs):
        with self.configuration_routine():
            self.configurations.configure(*args, **kwargs)

    def post_configuration(self):
        assert self.configured
        self.validate_configuration()
