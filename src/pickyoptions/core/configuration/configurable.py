from copy import deepcopy
import logging

from pickyoptions import settings
from pickyoptions.core.base import Base
from pickyoptions.core.decorators import raise_with_error
from pickyoptions.core.routine.routine import (
    require_not_in_progress, require_finished)
from pickyoptions.core.routine.constants import RoutineState

from .child import ChildMixin
from .exceptions import NotConfiguredError, ConfiguringError
from .parent import ParentMixin
from .utils import require_configured


logger = logging.getLogger(settings.PACKAGE_NAME)


class ConfigurableMixin(object):
    errors = {
        'not_configured_error': NotConfiguredError,
        'configuring_error': ConfiguringError,
    }

    def _init(self, **kwargs):
        self.save_initialization_state(**kwargs)

        # Allow validate_configuration to be passed in as an argument or specified
        # in the child class.
        # self._validate_configuration = validate_configuration
        # if self._validate_configuration is None:
        #     if not hasattr(self, 'validate_configuration'):
        #         raise Exception()
        #     self._validate_configuration = self.validate_configuration

        self.create_routine(
            id="configuration",
            pre_routine=self.pre_configuration,
            post_routine=self.post_configuration
        )

    def configure(self, *args, **kwargs):
        with self.routines.configuration:
            self._configure(*args, **kwargs)
        assert self.configured

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

    @require_not_in_progress(id="configuration")
    def pre_configuration(self):
        if self.configured:
            logger.debug("Reconfiguring %s." % self)
        else:
            logger.debug("Configuring %s." % self)

    @require_finished(id="configuration")
    @require_configured
    def post_configuration(self):
        logger.debug("Done configuring %s." % self)
        self.validate_configuration()

    def assert_configured(self):
        if not self.configured:
            self.raise_not_configured()

    def assert_not_configuring(self):
        if self.configuring:
            self.raise_configuring()

    @raise_with_error(error='configuring_error')
    def raise_configuring(self, *args, **kwargs):
        assert self.configuring is True
        return self.raise_with_self(*args, **kwargs)

    @raise_with_error(error='configuration_error')
    def raise_configuration_error(self, *args, **kwargs):
        assert self.configuring is True
        return self.raise_with_self(*args, **kwargs)

    @raise_with_error(error='not_configured_error')
    def raise_not_configured(self, *args, **kwargs):
        assert self.configured is False
        return self.raise_with_self(*args, **kwargs)


class Configurable(Base, ConfigurableMixin):
    __abstract__ = True
    # TODO: Start merging the abstract properties/methods with inheritance.
    abstract_methods = ('_configure', )

    def __init__(self, **kwargs):
        super(Configurable, self).__init__()
        ConfigurableMixin._init(self, **kwargs)


class ConfigurableChild(Configurable, ChildMixin):
    __abstract__ = True
    # TODO: Start merging the abstract properties/methods with inheritance.
    abstract_methods = ('_configure', )
    abstract_properties = ('parent_cls', )

    def __init__(self, field, parent=None, **kwargs):
        super(ConfigurableChild, self).__init__(**kwargs)
        ChildMixin._init(self, field, parent=parent)

    # TODO: Is this really where we want to put this?
    @raise_with_error(name='field')
    def raise_with_self(self, *args, **kwargs):
        return super(ConfigurableChild, self).raise_with_self(*args, **kwargs)


class ConfigurableParent(Configurable, ParentMixin):
    __abstract__ = True
    # TODO: Start merging the abstract properties/methods with inheritance.
    abstract_methods = ('_configure', 'child_cls', )

    def __init__(self, child_value=None, children=None, **kwargs):
        super(ConfigurableParent, self).__init__(**kwargs)
        ParentMixin._init(self, children=children, child_value=child_value)


class ConfigurationsConfigurableMixin(ConfigurableMixin):
    # TODO: Start merging the abstract properties/methods with inheritance.
    abstract_properties = ('configurations', )

    def _init(self, **kwargs):
        super(ConfigurationsConfigurableMixin, self)._init(**kwargs)

        configurations = deepcopy(self.configurations)
        # Set the validation routine of the `obj:Configurations`.
        # What is this accomplishing again?
        # configurations._validate_configuration = self.validate_configuration
        # The __setattr__ on models is sometimes overridden.
        object.__setattr__(self, 'configurations', configurations)

    # Do we really want to do this lazily?  It might hide bugs that are internal
    # due to internal configurations set on the Option...
    def lazy_init(self, **kwargs):
        # The provided kwargs are from the saved state in Configurable.
        self.configure(**kwargs)

    def _configure(self, *args, **kwargs):
        self.configurations.configure(*args, **kwargs)
        assert self.configurations.configured

    # @require_configured
    # def post_configuration(self):
    #     # TODO: Should we assign the post configuration (validation of the
    #     # configuration) to the Configurations object?  Would that be cleaner?
    #     # super(ConfigurationsConfigurable, self).post_configuration()
    #     assert self.configurations.configured
    #     self.validate_configuration()


class ConfigurationsConfigurable(Base, ConfigurationsConfigurableMixin):
    __abstract__ = True
    # TODO: Start merging the abstract properties/methods with inheritance.
    abstract_properties = ('configurations', )

    def __init__(self, **kwargs):
        super(ConfigurationsConfigurable, self).__init__()
        ConfigurationsConfigurableMixin._init(self, **kwargs)


class ConfigurationsConfigurableChild(ConfigurationsConfigurable, ChildMixin):
    __abstract__ = True
    # TODO: Start merging the abstract properties/methods with inheritance.
    abstract_properties = ('configurations', )
    abstract_properties = ('parent_cls', )

    def __init__(self, field, parent=None, **kwargs):
        super(ConfigurationsConfigurableChild, self).__init__(**kwargs)
        ChildMixin._init(self, field, parent=parent)


class ConfigurationsConfigurableParent(ConfigurationsConfigurable, ParentMixin):
    __abstract__ = True
    # TODO: Start merging the abstract properties/methods with inheritance.
    abstract_properties = ('configurations', 'child_cls', )

    def __init__(self, children=None, child_value=None, **kwargs):
        super(ConfigurationsConfigurableParent, self).__init__(**kwargs)
        ParentMixin._init(self, children=children, child_value=child_value)
