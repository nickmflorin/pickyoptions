from abc import ABCMeta, abstractmethod
import contextlib
import six
import sys

from .exceptions import ConfigurationDoesNotExist


def configurable_property_setter(obj):
    def _decorator(func):
        @obj.setter
        def inner(instance, value):
            instance._configuration[func.__name__] = value

            # If we are not in the process of setting multiple different configurations values,
            # we should validate after it is set.
            if not instance.configuring:
                instance.validate_configuration()
        return inner
    return _decorator


def configurable_property(func):
    @property
    def inner(instance):
        # Get the actual configuration object.
        configuration = instance.configuration(func.__name__)

        # If the value associated with the configuration object was configured, return
        # it.  Otherwise, we need to return the default.
        if configuration.field in instance._configuration:
            return instance._configuration[configuration.field]

        assert not configuration.required
        return configuration.default
    return inner


class ConfigurableModel(six.with_metaclass(ABCMeta, object)):
    configurations = ()

    def __init__(self, **kwargs):
        self._configuration = {}
        self._configured = False
        self._configuring = False
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
        self._pre_configure()
        with self._configuring_context():

            # Set configurations that are supplied to the model.
            for k, v in kwargs.items():
                configuration = self.configuration(k)
                configuration.validate(v)
                self._configuration[configuration.field] = v

            # Make sure all required configurations are provided.
            for configuration in self.configurations:
                if configuration.required and configuration.field not in kwargs:
                    raise ValueError()  # Configuration Required

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
            self._post_configuration()

    def _post_configuration(self):
        self._configured = True
        self.validate_configuration()

    def _pre_configure(self):
        pass

    @abstractmethod
    def validate_configuration(self):
        pass
