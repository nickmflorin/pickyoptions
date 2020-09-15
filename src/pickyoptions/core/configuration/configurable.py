from copy import deepcopy
import logging

from pickyoptions import settings
from pickyoptions.core.routine import Routine, Routined
from pickyoptions.core.routine.constants import RoutineState

from .exceptions import NotConfiguredError, ConfiguringError


logger = logging.getLogger(settings.PACKAGE_NAME)


class SimpleConfigurable(Routined):
    not_configured_error = NotConfiguredError
    configuring_error = ConfiguringError

    abstract_methods = ('_configure', 'validate_configuration')

    def __init__(self):
        Routined.__init__(self)
        self.create_routine(
            id="configuration",
            pre_routine=self.pre_configuration,
            post_routine=self.post_configuration
        )

    def configure(self, *args, **kwargs):
        with self.routines.configuration:
            self._configure(*args, **kwargs)

    @property
    def configuration_state(self):
        return self.routines.configuration.state

    @property
    def configured(self):
        # NOTE: This is a little misleading.  In the case that the object is
        # already configured but is being reconfigured, the state will be
        # IN_PROGRESS but it was actually already configured.  We should find
        # a better way to indicate that.
        return self.configuration_state == RoutineState.FINISHED

    @property
    def not_configured(self):
        return self.configuration_state in (
            RoutineState.IN_PROGRESS,
            RoutineState.NOT_STARTED
        )

    @property
    def configuring(self):
        if self.routines.configuration.in_progress:
            assert self.configuration_state == RoutineState.IN_PROGRESS
        return self.routines.configuration.in_progress

    @Routine.require_not_in_progress(id="configuration")
    def pre_configuration(self):
        if self.configured:
            logger.debug("Reconfiguring %s." % self)
        else:
            logger.debug("Configuring %s." % self)

    @Routine.require_finished(id="configuration")
    def post_configuration(self):
        assert self.configured is True
        logger.debug("Done configuring %s." % self)
        self.validate_configuration()

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
        super(Configurable, self).post_configuration()
        assert self.configured
        assert self.configurations.configured
        self.validate_configuration()
