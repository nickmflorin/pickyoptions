import pathlib


def safe_convert_paths(*paths):
    conv = []
    for pt in paths:
        if not isinstance(pt, pathlib.Path):
            conv.append(pathlib.Path(pt))
        else:
            conv.append(pt)
    return conv


def paths_overlap(base_path, path):
    """
    Returns True if the the two paths overlap and False if they do not.
    Overlapping Paths:  Defined as paths that are not relative to one another
    but share a common path, up until a certain point, when moving from the
    lowest point of the path towards the top of the paths.

    Examples:
    --------
        (base_path, path)
        ('/Users/Desktop/Folder/Documents', 'Folder/Documents'),
        ('Users/John/Desktop/Private/settings', 'Private/settings/dev.py'),

    Methodology
    -----------
    We do this by walking backwards over the path and finding the first point
    in which overlapping with the base_path occurs, if any:

        >>> base_path = ['System', 'Users', 'John', 'Desktop', 'settings']
        >>> path = ['John', 'Desktop', 'settings', 'file.py']

    Walk over ['file.py', 'settings', ...]
    The value 'settings' is the first place where overlapping occurs, at
    `overlapping_index` = 1.

    Starting at the `overlapping_index`, everything in the path must have an equal
    counter part in the base_path, starting at index 0.
        >>> reversed_base_parts = ['settings', 'Desktop', 'John', 'Users',
                'System']
        >>> reversed_parts = ['settings', 'Desktop', 'John']

    Note that if both paths are absolute, this will fail, since the path parts
    cannot be the same length (otherwise they would be relative to each other)
    and '/' would not match with it's counterpart in the other path:

        >>> reversed_base_parts = ['file.py', 'dev', '/']
        >>> reversed_parts = ['file.py', 'dev', 'settings', 'Users', '/']

    [x] Note:
    --------
    This is different than two paths being relative.  In fact, the two paths
    cannot be relative to one another for this to work.
    """
    if not isinstance(base_path, pathlib.Path):
        base_path = pathlib.Path(base_path)

    if not isinstance(path, pathlib.Path):
        path = pathlib.Path(path)

    try:
        path.relative_to(base_path)
    except ValueError:
        pass
    else:
        raise ValueError('Paths cannot be relative to one another.')

    reversed_parts = list(path.parts)[:]
    reversed_parts.reverse()

    reversed_base_parts = list(base_path.parts)[:]
    reversed_base_parts.reverse()

    def find_starting_overlap_index():
        """
        Finds the first index (when looking at the reversed path) for which
        overlapping with the base path occurs.
        For instance, if we have:
            >>> base_path = ['Users', 'John', 'settings']
            >>> path = ['settings', 'file.py']
        The reverse index at which overlapping occurs is 1, or
            >>> ['file.py', 'settings'][1]
        """
        for i in range(len(reversed_parts)):
            if reversed_parts[i] == base_path.parts[-1]:
                return i

    overlapping_start_index = find_starting_overlap_index()
    if overlapping_start_index is None:
        return False

    reversed_parts = reversed_parts[overlapping_start_index + 1:]
    reversed_base_parts = reversed_base_parts[1:]

    # We really could starting at + 1 of each list index, since we already checked
    # the equality at the place where index would be 0.
    index = 0
    while index < len(reversed_parts):
        if reversed_base_parts[index] != reversed_parts[index]:
            return False
        index += 1
    return True
