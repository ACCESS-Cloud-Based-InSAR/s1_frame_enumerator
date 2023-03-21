import pytest
from shapely.ops import unary_union

import s1_frame_enumerator.s1_stack as s1_stack
from s1_frame_enumerator import S1Frame, get_s1_stack, frames2gdf
from s1_frame_enumerator.exceptions import StackFormationError
from s1_frame_enumerator.s1_stack import (filter_s1_stack_by_geometric_coverage_per_frame,
                                          filter_s1_stack_by_geometric_coverage_per_pass)
from s1_frame_enumerator.s1_stack_formatter import (
    S1_COLUMNS, format_results_for_sent1_stack)


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


def filter_per_pass(CA_20210915_resp):
    # The resp data for one date for the first 2 frames
    data_json = CA_20210915_resp
    df_resp = format_results_for_sent1_stack(data_json)

    frame_0 = S1Frame(9847)
    frame_1 = S1Frame(9848)
    frame_2 = S1Frame(9849)

    frames = [frame_0, frame_1, frame_2]
    df_frames = frames2gdf(frames)
    frame_union = df_frames.geometry.unary_union
    int_geo = (frame_union).intersection(df_resp.geometry.unary_union)
    pass_ratio = int_geo.area / frame_union.area

    r = pass_ratio - .01
    df_filter = filter_s1_stack_by_geometric_coverage_per_pass(df_resp,
                                                               frames,
                                                               minimum_coverage_per_pass_ratio=r)
    assert df_filter.empty

    r = pass_ratio + .01
    df_filter = filter_s1_stack_by_geometric_coverage_per_pass(df_resp,
                                                               frames,
                                                               minimum_coverage_per_pass_ratio=r)
    assert df_filter.shape[0] == df_resp.shape[0]


def filter_per_frame(CA_20210915_resp):
    # The resp data for one date for the first 2 frames
    data_json = CA_20210915_resp
    df_resp = format_results_for_sent1_stack(data_json)

    frame_0 = S1Frame(9847)
    frame_1 = S1Frame(9848)
    frame_2 = S1Frame(9849)
    frames = [frame_0, frame_1, frame_2]

    pass_geometry = df_resp.geometry.unary_union
    ratio_frame_int = [pass_geometry.intersection(f.footprint_geometry).area / f.footprint_geometry.area
                       for f in frames]
    min_frame_coverage = min(ratio_frame_int)

    r = min_frame_coverage - .01
    df_filter = filter_s1_stack_by_geometric_coverage_per_frame(df_resp,
                                                                frames,
                                                                minimum_coverage_ratio_per_frame=r)
    assert df_filter.empty

    r = min_frame_coverage + .01
    df_filter = filter_s1_stack_by_geometric_coverage_per_frame(df_resp,
                                                                frames,
                                                                minimum_coverage_ratio_per_frame=r)
    assert df_filter.shape[0] == df_resp.shape[0]
