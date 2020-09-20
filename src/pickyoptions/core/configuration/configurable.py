from copy import deepcopy
import logging
import six

from pickyoptions import settings
from pickyoptions.core.base import Base, BaseMixin
from pickyoptions.core.decorators import raise_with_error
from pickyoptions.core.routine.routine import (
    require_not_in_progress, require_finished)
from pickyoptions.core.routine.constants import RoutineState

from .child import ChildMixin
from .exceptions import (
    NotConfiguredError,
    ConfiguringError,
    ConfigurationError,
    ConfigurationInvalidError,
    ConfigurationTypeError
)
from .parent import ParentMixin
from .utils import require_configured


logger = logging.getLogger(settings.PACKAGE_NAME)


class ConfigurableMixin(BaseMixin):
    errors = {
        'not_configured_error': NotConfiguredError,
        'configuring_error': ConfiguringError,
        'configuration_error': ConfigurationError,
        # While in many cases we will call the .raise_invalid() methods right
        # off of the `obj:Configuration` object, there are some cases where we
        # cannot do that, which is what these errors are for.
        # TODO: Make object specific counterparts?
        'configuration_invalid_error': ConfigurationInvalidError,
        'configuration_type_error': ConfigurationTypeError,
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
        """
        Configures the instance in the configuration context.

        During the configuration, the configuration state will be IN_PROGRESS
        until it finishes, at which point the configuration state will be
        FINISHED (assuming there is no error).
        """
        with self.routines.configuration:
            self._configure(*args, **kwargs)
        assert self.configured

    @property
    def configuration_state(self):
        """
        Returns the state of the instance's configuration.  This can either be
        NOT_STARTED, IN_PROGRESS, FINISHED or ERROR.
        """
        return self.routines.configuration.state

    @property
    def configured(self):
        """
        Returns whether or not the instance has been configured.

        NOTE:
        ----
        This is a little misleading.  In the case that the object is
        already configured but is being reconfigured, the state will be
        IN_PROGRESS but it was actually already configured.  We should find
        a better way to indicate that.
        """
        return self.configuration_state == RoutineState.FINISHED

    @property
    def not_configured(self):
        """
        Returns whether or not the instance has not yet been configured and
        is not in the process of being configured.
        """
        return self.configuration_state in (
            RoutineState.IN_PROGRESS,
            RoutineState.NOT_STARTED
        )

    @property
    def configuring(self):
        """
        Returns whether or not the instance is in the process of being
        configured.
        """
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
        """
        Asserts that the instance is configured, raising an exception
        if it is not configured.
        """
        if not self.configured:
            self.raise_not_configured()

    def assert_not_configuring(self):
        """
        Asserts that the instance is not configuring, raising an exception
        if it is configuring.
        """
        if self.configuring:
            self.raise_configuring()

    @raise_with_error(error='configuration_error')
    def raise_configuration_error(self, *args, **kwargs):
        """
        Raises an exception to indicate that there was an error configuring the
        instance.
        """
        return self.raise_with_self(*args, **kwargs)

    @raise_with_error(error='configuration_invalid_error')
    def raise_invalid_configuration(self, *args, **kwargs):
        """
        Raises an exception to indicate that the `obj:Child` instance has
        a configuration that is invalid.

        Usually, the `obj:Configuration`'s raise_invalid() method will be
        called instead, but in some cases this is needed.
        """
        return self.raise_configuration_error(*args, **kwargs)

    @raise_with_error(error='invalid_error')
    def raise_invalid_configuration_type(self, *args, **kwargs):
        """
        Raises an exception to indicate that the `obj:Child` instance has
        a configuration that is of invalid type.

        Usually, the `obj:Configuration`'s raise_invalid_type() method will be
        called instead, but in some cases this is needed.
        """
        assert 'types' in kwargs
        return self.raise_invalid_configuration(*args, **kwargs)

    @raise_with_error(error='configuring_error')
    def raise_configuring(self, *args, **kwargs):
        """
        Raises an exception to indicate that the instance is configuring when
        it is not expected to be doing so.
        """
        assert self.configuring is True
        return self.raise_configuration_error(*args, **kwargs)

    @raise_with_error(error='not_configured_error')
    def raise_not_configured(self, *args, **kwargs):
        """
        Raises an exception to indicate that the instance is not configured
        when it is expected to be so.
        """
        assert self.configured is False
        return self.raise_configuration_error(*args, **kwargs)


class Configurable(Base, ConfigurableMixin):
    __abstract__ = True
    abstract_methods = ('_configure', )

    def __init__(self, **kwargs):
        super(Configurable, self).__init__()
        ConfigurableMixin._init(self, **kwargs)


class ConfigurableChild(Configurable, ChildMixin):
    __abstract__ = True

    def __init__(self, field, parent=None, **kwargs):
        self._field = field
        super(ConfigurableChild, self).__init__(**kwargs)
        ChildMixin._init(self, parent=parent)

        self._field = field
        if not isinstance(self._field, six.string_types):
            # TODO: Make sure this doesn't put the exception in the context of
            # the option field, in the exception message.
            self.raise_invalid_configuration_type(
                value=self._field,
                types=six.string_types,
                name='field'
            )
        elif self._field.startswith('_'):
            # TODO: Make sure this doesn't put the exception in the context of
            # the option field, in the exception message.
            self.raise_invalid_configuration(
                name='field',
                value=self._field,
                detail="It cannot be scoped as a private attribute."
            )

    @property
    def field(self):
        return self._field

    # TODO: Is this really where we want to put this?
    @raise_with_error(name='field')
    def raise_with_self(self, *args, **kwargs):
        return super(ConfigurableChild, self).raise_with_self(*args, **kwargs)


class ConfigurableParent(Configurable, ParentMixin):
    __abstract__ = True

    def __init__(self, child_value=None, children=None, **kwargs):
        super(ConfigurableParent, self).__init__(**kwargs)
        ParentMixin._init(self, children=children, child_value=child_value)


class ConfigurationsConfigurableMixin(ConfigurableMixin):
    abstract_properties = ('configurations', )

    def _init(self, **kwargs):
        super(ConfigurationsConfigurableMixin, self)._init(**kwargs)

        configurations = deepcopy(self.configurations)
        # Set the validation routine of the `obj:Configurations`.
        # What is this accomplishing again?
        # configurations._validate_configuration = self.validate_configuration
        # The __setattr__ on models is sometimes overridden.
        object.__setattr__(self, 'configurations', configurations)

    def __lazyinit__(self, **kwargs):
        # Do we really want to do this lazily?  It might hide bugs that are
        # internal due to internal configurations set on the Option...
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

    def __init__(self, **kwargs):
        super(ConfigurationsConfigurable, self).__init__()
        ConfigurationsConfigurableMixin._init(self, **kwargs)


class ConfigurationsConfigurableChild(ConfigurationsConfigurable, ChildMixin):
    __abstract__ = True

    def __init__(self, field, parent=None, **kwargs):
        super(ConfigurationsConfigurableChild, self).__init__(**kwargs)
        ChildMixin._init(self, parent=parent)
        self._field = field
        if not isinstance(self._field, six.string_types):
            # TODO: Make sure this doesn't put the exception in the context of
            # the option field, in the exception message.
            self.raise_invalid_configuration_type(
                value=self._field,
                types=six.string_types,
                name='field'
            )
        elif self._field.startswith('_'):
            # TODO: Make sure this doesn't put the exception in the context of
            # the option field, in the exception message.
            self.raise_invalid_configuration(
                name='field',
                value=self._field,
                detail="It cannot be scoped as a private attribute."
            )

    @property
    def field(self):
        return self._field


class ConfigurationsConfigurableParent(ConfigurationsConfigurable, ParentMixin):
    __abstract__ = True

    def __init__(self, children=None, child_value=None, **kwargs):
        super(ConfigurationsConfigurableParent, self).__init__(**kwargs)
        ParentMixin._init(self, children=children, child_value=child_value)
