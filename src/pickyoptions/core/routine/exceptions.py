from pickyoptions.core.exceptions import PickyOptionsError, DoesNotExistError


class RoutineError(PickyOptionsError):
    identifier = "Routine Error"


class RoutineDoesNotExistError(DoesNotExistError, RoutineError):
    default_message = "The routine {id} does not exist."


class RoutineNotFinishedError(RoutineError):
    default_message = "The routine {id} is not finished."


class RoutineInProgressError(RoutineError):
    default_message = "The routine {id} is still in progress."


class RoutineNotInProgressError(RoutineError):
    default_message = "The routine {id} is not in progress."
