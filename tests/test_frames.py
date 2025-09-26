import warnings

import pandas as pd
import pytest
from shapely.geometry import Point

from s1_frame_enumerator import (
    S1Frame,
    frames2gdf,
    gdf2frames,
    get_global_gunw_footprints,
    get_global_s1_frames,
    get_overlapping_s1_frames,
)
from s1_frame_enumerator.s1_frames import get_geometry_by_id


def test_frame_initialized_by_id() -> None:
    frame = S1Frame(9849)
    assert frame.track_numbers == [64]


def test_get_overlapping_frames() -> None:
    # Southern California
    aoi_geo = Point(-120, 35).buffer(0.1)
    frames = get_overlapping_s1_frames(aoi_geo)

    tracks = sorted([tn for frame in frames for tn in frame.track_numbers])
    assert tracks == [137, 144]
    assert len(frames) == 2

    frames = get_overlapping_s1_frames(aoi_geo, track_numbers=[137])
    tracks = sorted([tn for frame in frames for tn in frame.track_numbers])
    assert tracks == [137]
    assert len(frames) == 1

    # Somalia - sequential track examples
    aoi_geo = Point(41, 1.5).buffer(1)
    frames = get_overlapping_s1_frames(aoi_geo, track_numbers=[87])
    tracks = [tn for frame in frames for tn in frame.track_numbers]
    tracks = sorted(list(set(tracks)))
    assert tracks == [86, 87]
    assert len(frames) == 2

    aoi_geo = Point(41, 1.5).buffer(1)
    frames = get_overlapping_s1_frames(aoi_geo, track_numbers=[86])
    tracks = sorted([tn for frame in frames for tn in frame.track_numbers])
    assert tracks == [86, 87]
    assert len(frames) == 1


def test_gdf2frames_consistency() -> None:
    """Ensure invertiblility of frames2gdf and gdf2frames."""
    # Hawaii
    aoi_geo = Point(-155.5, 19.5).buffer(1)
    frames_0 = get_overlapping_s1_frames(aoi_geo)
    df_frames_0 = frames2gdf(frames_0)

    frames_1 = gdf2frames(df_frames_0)
    df_frames_1 = frames2gdf(frames_1)

    assert frames_0 == frames_1
    assert df_frames_0.equals(df_frames_1)


def test_to_ensure_footprints_contain_frames() -> None:
    df_frames = get_global_s1_frames()
    df_extents = get_global_gunw_footprints()

    assert df_frames.shape[0] == df_extents.shape[0]

    # Avoid the datelines where we can have multiple geometries with same frame_id
    df_frames_subset = df_frames.cx[-150:150, :].sample(n=100)
    frame_ids_subset = df_frames_subset.frame_id.to_list()

    ind0 = df_extents.frame_id.isin(frame_ids_subset)
    df_extents_subset = df_extents[ind0].copy()

    df_frames_subset.sort_values(by='frame_id', inplace=True)
    df_extents_subset.sort_values(by='frame_id', inplace=True)

    assert df_frames_subset.shape[0] == df_extents_subset.shape[0]
    assert df_extents_subset.geometry.contains(df_frames_subset.geometry.buffer(-0.001)).all()


def test_frames_at_dateline() -> None:
    # Make sure no warnings are passed
    for frame_id in [22738, 4553]:
        # When no hemisphere is passed, raise a UserWarning
        with pytest.warns(UserWarning):
            S1Frame(frame_id)
        # When hemisphere is passed - no warning should be raised
        for hemisphere in ['east', 'west']:
            with warnings.catch_warnings():
                warnings.simplefilter('error', category=UserWarning)
                S1Frame(frame_id, hemisphere=hemisphere)


def test_large_frame_extent_error() -> None:
    df_frame_0 = get_geometry_by_id(4553, 'frame', hemisphere='west')
    df_frame_1 = get_geometry_by_id(4553, 'frame', hemisphere='east')
    df_frame_2 = get_geometry_by_id(4554, 'frame', hemisphere='east')

    with pytest.raises(ValueError):
        df = pd.concat([df_frame_0, df_frame_1], axis=0)
        gdf2frames(df)

    df = pd.concat([df_frame_1, df_frame_2], axis=0)
    assert len(gdf2frames(df)) == 2


def test_frame_construction_error() -> None:
    with pytest.raises(ValueError):
        # Frame does not exist
        S1Frame(-1)

    with pytest.raises(ValueError):
        S1Frame(100, hemisphere='wrong')

    with pytest.raises(ValueError):
        S1Frame(100, hemisphere='EAST')
