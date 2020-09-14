class RoutineState(object):
    """
    Represents the state of a `obj:Routine` instance.

    The `obj:Routine`'s state is only NOT_STARTED once, before the first time
    the routine as run.  After that, all subsequent states will be IN_PROGRESS
    or FINISHED.
    """
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    FINISHED = "FINISHED"
