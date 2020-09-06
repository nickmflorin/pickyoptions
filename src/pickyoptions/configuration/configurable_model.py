from abc import ABCMeta
import contextlib
import six
import sys

from .exceptions import ConfigurationDoesNotExist, NotConfiguredError


class ConfigurableModel(six.with_metaclass(ABCMeta, object)):
    configurations = ()

    def __init__(self, **kwargs):
        self._configured = False
        self._configuring = False

        # Right now, until we have a better system, the configuration mapping will be by
        # private key attributes.
        self._configuration = {}

        # Configure the model with the provided configuration values.
        self.configure(**kwargs)

    @property
    def configuration_fields(self):
        return [configuration.field for configuration in self.configurations]

    def has_configuration(self, field):
        return field in self.configuration_fields

    def configuration(self, field):
        try:
            return [
                configuration for configuration in self.configurations
                if configuration.field == field
            ][0]
        except IndexError:
            raise ConfigurationDoesNotExist(field=field)

    @property
    def configured(self):
        return self._configured

    @property
    def configuring(self):
        return self._configuring

    def configure(self, **kwargs):
        with self._configuring_context():
            # Set configurations that are supplied to the model.
            for k, v in kwargs.items():
                configuration = self.configuration(k)
                # If the value is None, the requirement check will be performed in the validate()
                # method.
                configuration.validate(v)
                self._configuration[configuration.field] = v

            # Make sure all required configurations are provided.
            for configuration in self.configurations:
                if configuration.field not in kwargs:
                    configuration.validate_not_provided()

    @contextlib.contextmanager
    def _configuring_context(self):
        self._configured = False
        self._configuring = True
        try:
            yield self
        except Exception:
            six.reraise(*sys.exc_info())
        else:
            self._configuring = False
            self._configured = True
            self.validate_configuration()

    def validate_configuration(self):
        if not self.configured:
            raise NotConfiguredError(
                "The %s instance must be configured." % self.__class__.__nane__
            )
