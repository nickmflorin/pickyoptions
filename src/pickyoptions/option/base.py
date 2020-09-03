import contextlib
import six
import sys

from src.lib.utils import check_num_function_arguments

from pickyoptions.exceptions import (
    OptionInvalidError, OptionConfigurationInstanceOfError, OptionConfigurationError,
    OptionRequiredError, OptionInstanceOfError)


class Option(object):
    def __init__(
        self,
        field,
        default=None,
        validate=None,
        required=False,
        enforce_type=None,
        normalize=None,
        post_process=None,
        display=None,
        merge_on_update=False,
        help_text=""
    ):
        self._configuring_the_option = False
        self._initialized = False

        # TODO: Maybe add a derive method that allows an option to be derived from the others.
        with self._configuring_option():
            self.field = field
            self.default = default
            self.required = required
            self.type = type
            self.help_text = help_text
            self.merge_on_update = merge_on_update

            self._validate = validate
            self._normalize = normalize
            self._post_process = post_process
            self._display = display

        # TODO: Do we need this property?
        self._initialized = True

    def _post_configuration(self):
        self._validate_configuration()

    @contextlib.contextmanager
    def _configuring_option(self):
        self._configuring_the_option = True
        try:
            yield self
        finally:
            self._configuring_the_option = False
            self._post_configuration()

    def _validate_configuration(self):
        if not isinstance(self.field, six.string_types):
            raise OptionConfigurationInstanceOfError(param="field", types=str)

        if self.default is not None and self.type is not None:
            if not isinstance(self.default, self.type):
                raise OptionConfigurationError(
                    param='normalize',
                    message=(
                        "If enforcing that the option be of a certain type, the default value "
                        "must also be of that type."
                    )
                )

        if self._normalize is not None:
            if (not six.callable(self._normalize)
                    or not check_num_function_arguments(self._normalize, 3)):
                raise OptionConfigurationError(
                    param='normalize',
                    message=(
                        "Must be a callable that takes the option value as it's first "
                        "argument, the option as it's second argument and the set options as "
                        "it's third argument."
                    )
                )

        if self._post_process is not None:
            if (not six.callable(self._post_process)
                    or not check_num_function_arguments(self._post_process, 3)):
                raise OptionConfigurationError(
                    param='post_process',
                    message=(
                        "Must be a callable that takes the option value as it's first "
                        "argument, the option as it's second argument and the set options as "
                        "it's third argument."
                    )
                )

        if self._validate is not None:
            if (not six.callable(self._validate)
                    or not check_num_function_arguments(self._validate, 2)):
                raise OptionConfigurationError(
                    param='validate',
                    message=(
                        "Must be a callable that takes the option value as it's first "
                        "argument and the option instance as it's second argument."
                    )
                )

        if self._display is not None:
            if (not six.callable(self._display)
                    or not check_num_function_arguments(self._display, 1)):
                raise OptionConfigurationError(
                    param='display',
                    message=(
                        "Must be a callable that takes the option instance as it's first "
                        "and only argument."
                    )
                )

    def __setattr__(self, k, v):
        try:
            super(Option, self).__setattr__(k, v)
        except AttributeError:
            raise AttributeError("Cannot configure Option with attribute %s." % k)
        else:
            if not self._configuring_the_option:
                self._post_configuration()

    def __repr__(self):
        return "<{cls_name} field={field} help={help}>".format(
            cls_name=self.__class__.__name__,
            field=self.field,
            help=self.help_text
        )

    def raise_invalid(self, *args, **kwargs):
        cls = kwargs.pop('cls', OptionInvalidError)
        kwargs['param'] = self.field
        raise cls(*args, **kwargs)

    @property
    def display(self):
        if self._display:
            return self._display(self)
        return "%s: %s" % (self.field, self.help_text)

    def normalize(self, value, options):
        if self._normalize:
            return self._normalize(value, self, options)
        return value

    def post_process(self, value, options):
        if self._post_process:
            self._post_process(value, self, options)
        return value

    def validate(self, value):
        if value is None:
            if self.required and not self.default:
                self.raise_invalid(cls=OptionRequiredError)
        else:
            if self.type is not None:
                if not isinstance(value, self.type):
                    self.raise_invalid(cls=OptionInstanceOfError, types=self.type)
            if self._validate is not None:
                # In the case that the option is invalid, validation method either returns a
                # string method or raises an OptionInvalidError (or an extension).
                try:
                    result = self._validate(value, self)
                except Exception as e:
                    if isinstance(e, OptionInvalidError):
                        six.reraise(*sys.exc_info())
                    else:
                        raise OptionConfigurationError(
                            param='validate',
                            message=(
                                "If raising an exception to indicate that the option is invalid, "
                                "the exception must be an instance of OptionInvalidError.  It is "
                                "recommended to use the `raise_invalid` "
                            )
                        )
                else:
                    if result is not None:
                        if not isinstance(result, six.string_types):
                            raise OptionConfigurationError(
                                param='validate',
                                message=(
                                    "The option validate method must return a string error "
                                    "message or raise an instance of OptionInvalidError in the "
                                    "case that the value is invalid.  If the value is valid, it "
                                    "must return None."
                                )
                            )
                        self.raise_invalid(value=value, message=result)
