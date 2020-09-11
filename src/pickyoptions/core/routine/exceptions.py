from pickyoptions.core.exceptions import PickyOptionsError


class RoutineError(PickyOptionsError):
    pass


class RoutineStartedError(RoutineError):
    default_message = "The routine {id} has already started."


class RoutineNotFinishedError(RoutineError):
    default_message = "The routine {id} is not finished."


class RoutineInProgressError(RoutineError):
    default_message = "The routine {id} is still in progress."


class RoutineNotInProgressError(RoutineError):
    default_message = "The routine {id} is not in progress."
