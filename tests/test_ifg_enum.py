import datetime

import geopandas as gpd
import pandas as pd
import pytest

from s1_frame_enumerator import S1Frame, enumerate_dates, enumerate_gunw_time_series
from s1_frame_enumerator.exceptions import InvalidStack
from s1_frame_enumerator.ifg_enum import select_ifg_pair_from_stack
from s1_frame_enumerator.s1_stack_formatter import S1_COLUMNS


def test_enum_dates_with_min_baseline() -> None:
    dates = sorted([datetime.datetime(2020 + i, j, 1) for i in range(2) for j in range(1, 13)])
    date_pairs = enumerate_dates(dates, min_temporal_baseline_days=0, n_secondary_scenes_per_ref=1)

    date_pairs_sorted = sorted(date_pairs)
    # Reference (later date) comes first
    date_pairs_expected = sorted([(d_1, d_0) for (d_0, d_1) in zip(dates[:-1], dates[1:])])
    assert date_pairs_expected == date_pairs_sorted


def test_enum_dates_with_31_day_baseline() -> None:
    n_dates = 100
    dates = sorted([datetime.datetime(2021, 1, 1) + datetime.timedelta(days=j) for j in range(n_dates)])

    temp_baseline = 31
    n_pairs_lower_seed = 0
    for n_seeds in range(1, 5):
        date_pairs = enumerate_dates(
            dates, min_temporal_baseline_days=temp_baseline, n_secondary_scenes_per_ref=1, n_init_seeds=n_seeds
        )

        date_pairs_sorted = sorted(date_pairs)
        # Reference (later date) comes first
        seeds = dates[-n_seeds:]
        delta = datetime.timedelta(days=temp_baseline)
        n_pairs = n_dates // temp_baseline
        date_pairs_expected = [(d0 - k * delta, d0 - (k + 1) * delta) for k in range(n_pairs) for d0 in seeds]
        date_pairs_expected = list(set(date_pairs_expected))
        date_pairs_expected = sorted(date_pairs_expected)
        assert date_pairs_expected == date_pairs_sorted
        n_pairs = len(date_pairs_sorted)
        assert n_pairs_lower_seed < n_pairs
        n_pairs_lower_seed = n_pairs


def test_enum_dates_with_3_neighbors() -> None:
    dates = [datetime.datetime(2021, 1, 1) + datetime.timedelta(days=j) for j in range(5)]

    for n_seeds in range(1, 5):
        date_pairs = enumerate_dates(
            dates, min_temporal_baseline_days=0, n_secondary_scenes_per_ref=3, n_init_seeds=n_seeds
        )

        jan_5 = dates[-1]
        day = datetime.timedelta(days=1)
        date_pairs_expected = [
            (jan_5, jan_5 - day),
            (jan_5, jan_5 - 2 * day),
            (jan_5, jan_5 - 3 * day),
            (jan_5 - day, jan_5 - 2 * day),
            (jan_5 - day, jan_5 - 3 * day),
            (jan_5 - day, jan_5 - 4 * day),
            (jan_5 - 2 * day, jan_5 - 3 * day),
            (jan_5 - 2 * day, jan_5 - 4 * day),
            (jan_5 - 3 * day, jan_5 - 4 * day),
        ]
        assert date_pairs_expected == date_pairs


def test_select_valid_ifg_pairs_using_frame_and_dates(sample_stack: gpd.GeoDataFrame) -> None:
    frames = [S1Frame(21248), S1Frame(21249)]

    ref_date = pd.Timestamp('2022-12-20', tz='UTC')
    sec_date = pd.Timestamp('2022-12-8', tz='UTC')

    # There are 3 images; 2 cover each frame
    data = select_ifg_pair_from_stack(ref_date, sec_date, sample_stack, frames[0])
    assert len(data['reference']) == 2

    data = select_ifg_pair_from_stack(ref_date, sec_date, sample_stack, frames[1])
    assert len(data['reference']) == 2

    # For none - we should get all 3 images in the stack
    data = select_ifg_pair_from_stack(ref_date, sec_date, sample_stack, None)
    assert len(data['reference']) == 3


def test_enum_by_track(sample_stack: gpd.GeoDataFrame) -> None:
    data = enumerate_gunw_time_series(
        sample_stack, min_temporal_baseline_days=0, n_secondary_scenes_per_ref=1, frames=None
    )
    unique_dates = sample_stack.repeat_pass_timestamp.unique().tolist()

    expected_num_of_ifgs = len(unique_dates) - 1
    assert len(data) == expected_num_of_ifgs


def test_enum_by_frames(sample_stack: gpd.GeoDataFrame) -> None:
    frames = [S1Frame(21248), S1Frame(21249)]
    data = enumerate_gunw_time_series(
        sample_stack, min_temporal_baseline_days=0, n_secondary_scenes_per_ref=1, frames=frames
    )
    unique_dates = sample_stack.repeat_pass_timestamp.unique().tolist()

    expected_num_of_ifgs = (len(unique_dates) - 1) * len(frames)
    assert len(data) == expected_num_of_ifgs


@pytest.mark.parametrize('df_stack', [pd.DataFrame({'dummy': list(range(10))}), pd.DataFrame(columns=S1_COLUMNS)])
def test_invalid_stack(df_stack: pd.DataFrame) -> None:
    with pytest.raises(InvalidStack):
        enumerate_gunw_time_series(df_stack, min_temporal_baseline_days=0, n_secondary_scenes_per_ref=1)


def test_geometry_filtering(df_nz_146_stack: gpd.GeoDataFrame) -> None:
    # See Issue #11: https://github.com/ACCESS-Cloud-Based-InSAR/s1_frame_enumerator/issues/11
    frame = S1Frame(22745)
    ifg_data = enumerate_gunw_time_series(
        df_nz_146_stack, n_init_seeds=3, min_temporal_baseline_days=365, frames=[frame]
    )
    ifg_prev_disconnected = [
        d for d in ifg_data if 'S1B_IW_SLC__1SSV_20161221T173720_20161221T173747_003497_005FA6_A1A2' in d['reference']
    ]

    expected_ifgs = [
        {
            'reference': [
                'S1B_IW_SLC__1SSV_20161221T173720_20161221T173747_003497_005FA6_A1A2',
                'S1B_IW_SLC__1SSV_20161221T173745_20161221T173812_003497_005FA6_48FF',
                'S1B_IW_SLC__1SSV_20161221T173810_20161221T173837_003497_005FA6_D292',
            ],
            'secondary': ['S1A_IW_SLC__1SSV_20151221T173830_20151221T173900_009143_00D27B_A55F'],
        },
        {
            'reference': [
                'S1B_IW_SLC__1SSV_20161221T173720_20161221T173747_003497_005FA6_A1A2',
                'S1B_IW_SLC__1SSV_20161221T173745_20161221T173812_003497_005FA6_48FF',
                'S1B_IW_SLC__1SSV_20161221T173810_20161221T173837_003497_005FA6_D292',
            ],
            'secondary': ['S1A_IW_SLC__1SSV_20151127T173831_20151127T173901_008793_00C8AE_14FB'],
        },
    ]

    assert len(ifg_prev_disconnected) == len(expected_ifgs)
    for ifg, expected_ifg in zip(ifg_prev_disconnected, expected_ifgs):
        assert ifg['reference'] == expected_ifg['reference']
        assert ifg['secondary'] == expected_ifg['secondary']
