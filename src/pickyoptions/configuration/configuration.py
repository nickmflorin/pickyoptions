from abc import ABCMeta, abstractproperty
import six

from pickyoptions.lib.utils import ensure_iterable


class Configuration(six.with_metaclass(ABCMeta, object)):
    def __init__(self, field, types=None, required=None, default=None):
        self._field = field
        self._types = types
        self._required = required
        self._default = default

    @property
    def required(self):
        return self._required

    @property
    def field(self):
        return self._field

    @property
    def default(self):
        return self._default

    @property
    def types(self):
        if self._types is not None:
            return ensure_iterable(self._types, cast=tuple)
        return ()

    # TODO: Do we need to have specific exception classes for options vs. option?
    # Can't we just specify the model class or something like that on Configuration init?
    @abstractproperty
    def exception_cls(self):
        pass

    def validate(self, value):
        if value is not None:
            if self.types and not isinstance(value, self.types):
                self.raise_invalid("Must be an instance of %s." % self.types)
        else:
            if self._required:
                # TODO: If the default is specified, should we ignore the requirement?
                self.raise_invalid("The configuration is required.")

    def raise_invalid(self, message):
        raise self.exception_cls(field=self._field, message=message)
