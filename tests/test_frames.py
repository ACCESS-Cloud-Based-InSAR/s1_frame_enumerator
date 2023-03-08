import warnings

import pytest
from shapely.geometry import Point

from s1_frame_enumerator import (S1Frame, frames2gdf, gdf2frames,
                                 get_overlapping_s1_frames)


def test_frame_initialized_by_id():
    frame = S1Frame(9849)
    assert frame.track_numbers == [64]


def test_frame_with_custom_coverage_geometry():
    frame = S1Frame(9849)
    custom_geo_good = frame.frame_geometry.buffer(-.1)
    custom_geo_bad = frame.frame_geometry.buffer(.1)

    # Ensure no warning is raised
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        frame_custom_good = S1Frame(9849,
                                    coverage_geometry=custom_geo_good,
                                    use_natural_earth_land_mask=False
                                    )
    assert frame_custom_good.coverage_geometry == custom_geo_good

    # Warns that Frame is not using land mask
    with pytest.warns(UserWarning):
        S1Frame(9849,
                coverage_geometry=custom_geo_good,
                use_natural_earth_land_mask=True
                )

    # Should raise error because geometry goes beyond frame
    with pytest.raises(ValueError):
        S1Frame(9849,
                coverage_geometry=custom_geo_bad,
                )


def test_get_overlapping_frames():
    # Southern California
    aoi_geo = Point(-120, 35).buffer(.1)
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
    tracks = sorted([tn for frame in frames for tn in frame.track_numbers])
    assert tracks == [86, 87]
    assert len(frames) == 2

    aoi_geo = Point(41, 1.5).buffer(1)
    frames = get_overlapping_s1_frames(aoi_geo, track_numbers=[86])
    tracks = sorted([tn for frame in frames for tn in frame.track_numbers])
    assert tracks == [86]
    assert len(frames) == 1


def test_gdf2frames_consistency():
    """Ensure invertiblility of frames2gdf and gdf2frames"""

    # Hawaii
    aoi_geo = Point(-155.5, 19.5).buffer(1)
    frames_0 = get_overlapping_s1_frames(aoi_geo)
    df_frames_0 = frames2gdf(frames_0)

    frames_1 = gdf2frames(df_frames_0)
    df_frames_1 = frames2gdf(frames_1)

    assert frames_0 == frames_1
    assert df_frames_0.equals(df_frames_1)
