from copy import deepcopy


__all__ = (
    'flatten',
    'ensure_iterable',
    'merge_dicts',
)


def flatten(arrays, ignore_types=None, cast=list):
    """
    Flattens the arrays/iterables in an array to remove a level of nesting.
    """
    flattened = []
    ignore_types = ensure_iterable(ignore_types or [])
    for array in arrays:
        if hasattr(array, '__iter__') and type(array) not in ignore_types and type(array) is not str:
            flattened += list(array)
        else:
            flattened.append(array)
    return cast(flattened)


def ensure_iterable(value, cast=list):
    """
    Ensures that the value is an iterable.  If the provided value is not an iterable, it will return an iterable
    with the provided value as the first element.
    """
    if hasattr(value, '__iter__') and not isinstance(value, type):
        return value
    value = (value, )
    return cast(value)


def merge_dicts(dicts):
    """
    Merges an array of `obj:dict` instances together by copying the first `obj:dict` in the array and merging
    the subsequent ones.
    """
    if len(dicts) == 0:
        return {}
    elif len(dicts) == 1:
        return deepcopy(dicts[0])
    else:
        active_dict = deepcopy(dicts[0])
        for i in range(1, len(dicts)):
            active_dict.update(dicts[i])
        return active_dict
