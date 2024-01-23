class StackFormationError(Exception):
    """If Generation of a Stack from S1Frames is not well-posed e.g. not in the same
    track (aka relative orbit number) or S1Frames are not contiguous"""


class InvalidStack(Exception):
    """When a dataframe is submitted to enumerate and is not in the requisite form"""
