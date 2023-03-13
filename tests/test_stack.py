import pytest
from shapely.ops import unary_union

import s1_frame_enumerator.s1_stack as s1_stack
from s1_frame_enumerator import S1Frame, get_s1_stack
from s1_frame_enumerator.exceptions import StackFormationError
from s1_frame_enumerator.s1_stack_formatter import S1_COLUMNS


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


def test_allowable_months(monkeypatch, asf_results_from_query_by_frame):
    def mock_response(*args, **kwargs):
        results_0 = asf_results_from_query_by_frame(9847)
        results_1 = asf_results_from_query_by_frame(9848)
        return results_0 + results_1

    monkeypatch.setattr(s1_stack, 'query_slc_metadata_over_frame', mock_response)
    frame_0 = S1Frame(9847)
    frame_1 = S1Frame(9848)

    month_num = 1
    df_stack = get_s1_stack([frame_0, frame_1], allowable_months=[month_num])
    assert not df_stack.empty
    stack_months = df_stack.repeat_pass_timestamp.dt.month
    assert stack_months.isin([month_num]).all()


def test_column_structure(monkeypatch, asf_results_from_query_by_frame):
    def mock_response(*args, **kwargs):
        return asf_results_from_query_by_frame(9847)

    monkeypatch.setattr(s1_stack, 'query_slc_metadata_over_frame', mock_response)
    frame = S1Frame(9847)
    df_stack = get_s1_stack([frame])
    assert df_stack.columns.tolist() == S1_COLUMNS


def test_sequential_tracks(monkeypatch, asf_results_from_query_by_frame):
    frame_0 = S1Frame(13403)
    frame_1 = S1Frame(13404)
    frames = [frame_0, frame_1]

    def mock_response(*args, **kwargs):
        results_0 = asf_results_from_query_by_frame(13403)
        results_1 = asf_results_from_query_by_frame(13404)
        return results_0 + results_1

    monkeypatch.setattr(s1_stack, 'query_slc_metadata_over_frame', mock_response)

    df_stack = get_s1_stack(frames)
    track_numbers = sorted(df_stack.track_number.unique().tolist())
    assert track_numbers == [86, 87]
