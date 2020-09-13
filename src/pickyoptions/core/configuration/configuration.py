import logging

from pickyoptions import settings, constants

from pickyoptions.core.base import track_init
from pickyoptions.core.child import Child

from .configurable import SimpleConfigurable
from .exceptions import (
    ConfigurationInvalidError,
    ConfigurationRequiredError,
    ConfigurationTypeError,
    ConfigurationNotSetError,
    ConfigurationLockedError,
    ConfigurationNotConfiguredError,
    ConfigurationConfiguringError
)


logger = logging.getLogger(settings.PACKAGE_NAME)


class Configuration(Child, SimpleConfigurable):
    """
    Represents a single configurable value in a set of `obj:Configurations`
    for either a `obj:Option` or the set of `obj:Options`.

    Parameters:
    ----------
    field: `obj:str` (required)
        A string identifier for the `obj:Configuration`.  This property will
        be used to access the `obj:Configuration` from the grouped
        `obj:Configurations` instance.

    default: `obj:object` (optional)
        The default value for the `obj:Configuration` if the `obj:Configuration`
        is not required and a value is not provided.

        Default: NOTSET (or None publically)

    types: `obj:tuple` or `obj:list` (optional)
        The types that the value of the `obj:Configuration` should be forced to
        comply with.  If provided and the value provided for the
        `obj:Configuration` is not of those types, an exception will be raised.

        Default: ()

    required: `obj:bool` (optional)
        Whether or not the `obj:Configuration` is required.  If True and the
        value is not provided for the `obj:Configuration`, an exception will be
        raised.

        Default: False

    validate: `obj:func` (optional)
        A validation method that determines whether or not the value provided
        for the `obj:Configuration` is valid.  The provided method must take the
        `obj:Configuration` value as it's first and only argument.

        It is important to note that the validate method will be applied to
        both the provided configuration value and it's default - so both must
        comply.

        Default: None

    normalize: `obj:func` (optional)
        A normalization method that normalizes the provided value to the
        `obj:Configuration`.

        It is important to note that the normalization method will be applied
        to the default value as well.

        Default: None

    locked: `obj:bool` (optional)
        Whether or not the `obj:Configuration` is allowed to be reconfigured
        after it was initially configured.

        Default: True

    TODO:
    ----
    - Eventually, we should consider trying to use Configuration recursively and
      give the Configuration configurations.
    - Parameter for whether or not the normalization method should be applied
      to the default.
    - Parameter for whether or not the validation method should be applied to
      the default.
    """
    # Child Implementation Properties
    invalid_error = ConfigurationInvalidError
    invalid_type_error = ConfigurationTypeError
    required_error = ConfigurationRequiredError
    not_set_error = ConfigurationNotSetError
    parent_cls = 'Configurations'
    child_identifier = 'field'

    # SimpleConfigurable Implementation Properties
    not_configured_error = ConfigurationNotConfiguredError
    configuring_error = ConfigurationConfiguringError

    @track_init
    def __init__(
        self,
        field,
        default=constants.NOTSET,
        required=False,
        normalize=None,
        validate=None,
        locked=False,
        types=None,
        parent=None,
    ):
        from pickyoptions.core.valued import Value

        self._field = field
        Child.__init__(self, parent=parent)
        SimpleConfigurable.__init__(self)
        # NOTE: We cannot set the `obj:Value` instance in a configuration method
        # because the configuration of a `obj:Configuration` involves setting the
        # value of the `obj:Value` instance.
        self.value_instance = Value(
            # Only needed for referencing the exceptions... Maybe there is a
            # better way to do reference what is going on in the exceptions..
            field,
            self,
            default=default,
            not_set_error=ConfigurationNotSetError,
            locked_error=ConfigurationLockedError,
            required_error=ConfigurationRequiredError,
            configuration_error=ConfigurationConfiguringError,
            validate=validate,
            normalize=normalize,
            required=required,
            types=types,
            # allow_null=allow_null
        )

    def _configure(self, value):
        self.value = value

    def __repr__(self):
        if self.configured:
            return (
                "<{cls_name} state={state} field={field} value={value}>".format(
                    cls_name=self.__class__.__name__,
                    field=self.field,
                    value=self.value,
                    state=self.state,
                )
            )
        # The field attribute won't be available until the `obj:Configuration`
        # is configured - not anymore, the field is set as the first line of the
        # init.
        return "<{cls_name} state={state} field={field}>".format(
            cls_name=self.__class__.__name__,
            state=self.state,
            field=self.field,
        )

    # @property
    # def set(self):
    #     return self._set
    #
    # def assert_set(self, *args, **kwargs):
    #     if not self.set:
    #         raise ValueError()

    @property
    def field(self):
        return self._field

    @property
    def required(self):
        return self.value_instance.required

    # WHY ARE WE NOT USING THE DEFAULT HERE?
    @property
    def value(self):
        # NOTE: The `obj:Configuration` may or may not be configured at this
        # point, because if the configuration is not present in the provided data
        # it is not technically considered configured.
        return self.value_instance.value
        # value = super(Configuration, self).value
        # if value is None:
        #     assert not self.required
        #     # assert self.allow_null
        #     return self.normalize(self.default)
        # return self.normalize(self._value)

    @value.setter
    def value(self, value):
        self.value_instance.value = value
        # self._value = value
        # self._set = True
        # self.validate()  # TODO: Should we also validate the default values?
