from copy import deepcopy
import logging

from pickyoptions import settings
from pickyoptions.core.base import BaseModel
from pickyoptions.core.routine import Routine
from pickyoptions.core.routine.constants import RoutineState

from .exceptions import NotConfiguredError, ConfiguringError


logger = logging.getLogger(settings.PACKAGE_NAME)


class SimpleConfigurable(BaseModel):
    not_configured_error = NotConfiguredError
    configuring_error = ConfiguringError

    abstract_methods = ('_configure', )

    def __init__(self, **kwargs):
        self.configuration_routine = Routine(
            self,
            id='configuring',
            pre_routine=self.pre_configuration,
            post_routine=self.post_configuration
        )

        # TODO: Consider removing the ability to configure on init.
        configure_on_init = kwargs.pop('configure_on_init', False)
        if configure_on_init:
            self.configure(**kwargs)

    def configure(self, *args, **kwargs):
        with self.configuration_routine:
            self._configure(*args, **kwargs)

    @property
    def configuration_state(self):
        return self.configuration_routine.state

    @property
    def configured(self):
        if self.configuration_routine.finished:
            assert self.configuration_state == RoutineState.FINISHED
        return self.configuration_routine.finished

    @property
    def not_configured(self):
        return self.configuration_state in (
            RoutineState.IN_PROGRESS,
            RoutineState.NOT_STARTED
        )

    @property
    def configuring(self):
        if self.configuration_routine.in_progress:
            assert self.configuration_state == RoutineState.IN_PROGRESS
        return self.configuration_routine.in_progress

    @Routine.require_not_in_progress
    def pre_configuration(self):
        logger.debug("Performing pre-configuration.")
        if self.configured:
            logger.debug("Reconfiguring %s." % self.__class__.__name__)
        else:
            logger.debug("Configuring %s." % self.__class__.__name__)

    @Routine.require_finished
    def post_configuration(self):
        logger.debug("Done configuring %s." % self.__class__.__name__)

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

    def _configure(self, *args, **kwargs):
        self.configurations.configure(*args, **kwargs)
        assert self.configurations.configured

    def post_configuration(self):
        assert self.configured
        assert self.configurations.configured
        self.validate_configuration()
