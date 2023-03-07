import pytest
from shapely.ops import unary_union

from s1_frame_enumerator import S1Frame, get_s1_stack
from s1_frame_enumerator.exceptions import StackFormationError


def test_disconnected_frames_and_same_track():
    frame_0 = S1Frame(9846)
    frame_1 = S1Frame(9848)

    assert frame_0.track_numbers == frame_1.track_numbers

    with pytest.raises(StackFormationError):
        get_s1_stack([frame_0, frame_1])


def test_different_tracks_and_connected_geometry():
    frame_0 = S1Frame(21249)
    frame_1 = S1Frame(22439)

    frames = [frame_0, frame_1]
    total_geometry = unary_union([f.frame_geometry for f in frames])

    assert total_geometry.geom_type == 'Polygon'

    with pytest.raises(StackFormationError):
        get_s1_stack([frame_0, frame_1])
