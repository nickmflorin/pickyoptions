import six
import sys

from .configuration import OptionConfiguration
from .exceptions import (OptionInvalidError, OptionConfigurationError, OptionRequiredError,
    OptionInstanceOfError)


class Option(OptionConfiguration):
    def __init__(self, field, **kwargs):
        self._field = field
        if not isinstance(self.field, six.string_types):
            raise ValueError()
        if self.field.startswith('_'):
            raise ValueError()
        super(Option, self).__init__(**kwargs)

    def __repr__(self):
        return "<{cls_name} field={field}>".format(
            cls_name=self.__class__.__name__,
            field=self.field,
        )

    def raise_invalid(self, *args, **kwargs):
        cls = kwargs.pop('cls', OptionInvalidError)
        kwargs['field'] = self.field
        raise cls(*args, **kwargs)

    def raise_required(self, *args, **kwargs):
        self.raise_invalid(cls=OptionRequiredError, *args, **kwargs)

    @property
    def field(self):
        return self._field

    @property
    def display(self):
        if self.displayer is not None:
            return self.displayer(self)
        return "%s: %s" % (self.field, self.help_text)

    def normalize(self, value):
        if self.normalizer:
            return self.normalizer(value, self)
        return value

    def post_process(self, value, options):
        if self.post_processor is not None:
            self.post_processor(value, self, options)
        return value

    def validate_with_others(self, value, options):
        """
        Validates the `obj:Option` instance after all options have been set on the overall
        combined `obj:Options` instance.
        """
        if self.validator_with_others is not None:
            try:
                result = self.validator_with_others(value, self, options)
            except Exception as e:
                if isinstance(e, OptionInvalidError):
                    six.reraise(*sys.exc_info())
                else:
                    raise OptionConfigurationError(
                        field='validate',
                        message=(
                            "If raising an exception to indicate that the option is invalid, "
                            "the exception must be an instance of OptionInvalidError.  It is "
                            "recommended to use the `raise_invalid` method of the option instance."
                        )
                    )
            else:
                if result is not None:
                    if not isinstance(result, six.string_types):
                        raise OptionConfigurationError(
                            field='validate',
                            message=(
                                "The option validate method must return a string error "
                                "message or raise an instance of OptionInvalidError in the "
                                "case that the value is invalid.  If the value is valid, it "
                                "must return None."
                            )
                        )
                    self.raise_invalid(value=value, message=result)

    def validate(self, value, options):
        """
        Validates the `obj:Option` instance when it's corresponding value is being set on the
        `obj:Options`.
        """
        # TODO: Cleanup this required logic - there is also a required check in the parent options
        # that checks if the value was explicitly provided.
        # TODO: We have to account for the allow null property.  Whether or not the option is set
        # will be determined in the parent options class.
        if value is None:
            if self.required and not self.default:
                self.raise_invalid(cls=OptionRequiredError)
        else:
            if self.enforce_type is not None:
                if not isinstance(value, self.enforce_type):
                    self.raise_invalid(cls=OptionInstanceOfError, types=self.enforce_type)
            if self.validator is not None:
                # In the case that the option is invalid, validation method either returns a
                # string method or raises an OptionInvalidError (or an extension).
                try:
                    result = self.validator(value, self, options)
                except Exception as e:
                    if isinstance(e, OptionInvalidError):
                        six.reraise(*sys.exc_info())
                    else:
                        raise OptionConfigurationError(
                            field='validate',
                            message=(
                                "If raising an exception to indicate that the option is invalid, "
                                "the exception must be an instance of OptionInvalidError.  It is "
                                "recommended to use the `raise_invalid` method of the option "
                                "instance. "
                            )
                        )
                else:
                    if isinstance(result, six.string_types):
                        self.raise_invalid(value=value, message=result)
                    elif result is not None:
                        raise OptionConfigurationError(
                            field='validate',
                            message=(
                                "The option validate method must return a string error "
                                "message or raise an instance of OptionInvalidError in the "
                                "case that the value is invalid.  If the value is valid, it "
                                "must return None."
                            )
                        )
