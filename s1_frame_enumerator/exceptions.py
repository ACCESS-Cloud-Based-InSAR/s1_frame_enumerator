class StackFormationError(Exception):
    """If Generation of a Stack from S1Frames is not well-posed e.g. not in the same
    track (aka relative orbit number) or S1Frames are not contiguous"""
