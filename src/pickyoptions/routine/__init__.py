from __future__ import absolute_import

import contextlib
import functools
import logging
import six
import sys

from pickyoptions import settings
from pickyoptions.lib.utils import optional_parameter_decorator
from pickyoptions.base import BaseModel

from .constants import RoutineState
from .exceptions import (
    RoutineStartedError, RoutineNotFinishedError, RoutineInProgressError,
    RoutineNotInProgressError)
from .routines import Routines  # noqa


logger = logging.getLogger(settings.PACKAGE_NAME)


class Routine(BaseModel):
    def __init__(self, id, pre_routine=None, post_routine=None):
        self._id = id
        self._state = RoutineState.NOT_STARTED
        self._queue = []
        self._history = []
        self._pre_routine = pre_routine
        self._post_routine = post_routine

    @contextlib.contextmanager
    def __call__(self, instance):
        assert len(self.queue) == 0
        self.pre_routine(instance)
        self._state = RoutineState.IN_PROGRESS
        try:
            logger.debug("Entering routine context.")
            yield self
        except Exception:
            six.reraise(*sys.exc_info())
        else:
            self._state = RoutineState.FINISHED
            # Populated will only be False before the first population,
            # afterwards it will always be True, until the options are reset.
            # self._populated = True
            # self._populated_value = constants.NOTSET

            self.post_routine(instance)
            logger.debug("Exiting population routine context.")

    @property
    def id(self):
        return self._id

    @property
    def state(self):
        return self._state

    @property
    def queue(self):
        return self._queue

    @property
    def history(self):
        return self._history

    @property
    def finished(self):
        return self.state == RoutineState.FINISHED

    @property
    def not_finished(self):
        return not self.finished

    @property
    def in_progress(self):
        return self.state == RoutineState.IN_PROGRESS

    @property
    def not_started(self):
        return self.state == RoutineState.NOT_STARTED

    @property
    def started(self):
        return not self.not_started

    def post_routine(self, instance):
        if not self.finished:
            self.raise_not_finished()
        logger.debug('Performing post-routine %s on %s.' % (
            self.__class__.__name__, instance.__class__.__name__))
        if self._post_routine:
            self._post_routine(self._instance)
        self.clear_queue()

    def pre_routine(self, instance):
        logger.debug('Performing pre-routine %s on %s.' % (
            self.__class__.__name__, instance.__class__.__name__))
        assert len(self.queue) == 0
        if self._pre_routine:
            self._pre_routine(instance)

    def raise_started(self, *args, **kwargs):
        kwargs.update(
            cls=RoutineStartedError,
            id=self.id
        )
        self.raise_with_self(*args, **kwargs)

    def raise_in_progress(self, *args, **kwargs):
        kwargs.update(
            cls=RoutineInProgressError,
            id=self.id
        )
        self.raise_with_self(*args, **kwargs)

    def raise_not_in_progress(self, *args, **kwargs):
        kwargs.update(
            cls=RoutineNotInProgressError,
            id=self.id
        )
        self.raise_with_self(*args, **kwargs)

    def raise_not_finished(self, *args, **kwargs):
        kwargs.update(
            cls=RoutineNotFinishedError,
            id=self.id
        )
        self.raise_with_self(*args, **kwargs)

    def add_to_queue(self, obj):
        self._queue.append(obj)

    def clear_queue(self):
        if self.in_progress:
            self.raise_in_progress()
        logger.debug("Clearing queue")
        self._queue = []

    def clear_history(self):
        if self.in_progress:
            self.raise_in_progress()
        logger.debug("Clearing history")
        self._history = []

    def reset(self):
        assert len(self.queue) == 0
        self.clear_history()
        self._state = RoutineState.NOT_STARTED

    def store(self, value):
        assert value not in self._history
        self._history.append(value)

    @staticmethod
    @optional_parameter_decorator
    def require_not_in_progress(func, routine=None):
        @functools.wraps(func)
        def inner(instance, *args, **kwargs):
            if routine:
                routine_instance = getattr(instance.routines, routine)
            else:
                routine_instance = instance
            assert isinstance(routine_instance, Routine)
            if routine_instance.in_progress:
                routine_instance.raise_in_progress()
            return func(instance, *args, **kwargs)
        return inner

    @staticmethod
    @optional_parameter_decorator
    def require_not_started(func, routine=None):
        @functools.wraps(func)
        def inner(instance, *args, **kwargs):
            if routine:
                routine_instance = getattr(instance.routines, routine)
            else:
                routine_instance = instance
            assert isinstance(routine_instance, Routine)
            if routine_instance.started:
                routine_instance.raise_started()
            return func(instance, *args, **kwargs)
        return inner

    @staticmethod
    @optional_parameter_decorator
    def require_finished(func, routine=None):
        @functools.wraps(func)
        def inner(instance, *args, **kwargs):
            if routine:
                routine_instance = getattr(instance.routines, routine)
            else:
                routine_instance = instance
            assert isinstance(routine_instance, Routine)
            if not routine_instance.finished:
                routine_instance.raise_not_finished()
            return func(instance, *args, **kwargs)
        return inner
