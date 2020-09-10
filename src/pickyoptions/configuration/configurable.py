# from abc import ABCMeta, abstractmethod
from copy import deepcopy
import contextlib
import functools
import logging
import six
import sys

from pickyoptions import settings
from pickyoptions.base import BaseModel

from .configurations import Configurations
from .exceptions import (
    NotConfiguredError,
    ConfigurationInvalidError,
    ConfigurationTypeError,
    ConfigurationRequiredError
)


logger = logging.getLogger(settings.PACKAGE_NAME)


def requires_configured(func):
    @functools.wraps(func)
    def inner(instance, *args, **kwargs):
        if not instance.configured:
            instance.raise_not_configured()
        return func(instance, *args, **kwargs)
    return inner


class Configurable(BaseModel):
    not_configured_error = NotConfiguredError
    invalid_configuration_error = ConfigurationInvalidError
    invalid_configuration_type_error = ConfigurationTypeError
    configuration_required_error = ConfigurationRequiredError

    _configured = False
    configurations = Configurations()

    def __init__(self, extra_configurations=None, reverse_assign_configurations=True, **kwargs):
        self._configuring = False

        # We cannot call the __setattr__ on the model itself because it is overridden.  This is
        # annoying, and we should find a better way of doing this.
        configurations = deepcopy(self.configurations)
        configurations.add_children(extra_configurations or [])
        object.__setattr__(self, 'configurations', configurations)

        # The configurations must be assigned a parent before continuing with the configuration.
        self.configurations.assign_parent(self)

        self.configure(**kwargs)

    # @abstractmethod
    # def validate_configuration(self):
    #     pass

    @property
    def configured(self):
        return self._configured

    @property
    def configuring(self):
        return self._configuring

    def raise_not_configured(self, *args, **kwargs):
        kwargs.setdefault('cls', self.not_configured_error)
        return self.conditional_raise(*args, **kwargs)

    def assert_configured(self):
        if not self.configured:
            self.raise_not_configured()

    # Move parts of this to the Configurations model.
    def configure(self, **kwargs):
        assert len(self.configurations) != 0
        if self.configured:
            logger.debug("Reconfiguring %s." % self.__class__.__name__)

        with self.configuration_cycle():
            assert self.configurations.assigned
            self.configurations.configure(**kwargs)

    # Move parts of this to the Configurations model.
    @contextlib.contextmanager
    def configuration_cycle(self):
        self._configuring = True
        try:
            yield self
        except Exception:
            six.reraise(*sys.exc_info())
        finally:
            self._configuring = False
            # Configured will only be False before the first configuration, afterwards it will
            # always be True.
            # TODO: Should there be a way to reset the configurations?
            self._configured = True
            self.validate_configuration()
