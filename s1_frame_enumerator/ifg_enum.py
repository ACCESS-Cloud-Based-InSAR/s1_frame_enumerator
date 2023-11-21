import datetime
import warnings
from typing import List

import geopandas as gpd
import pandas as pd
from shapely import STRtree
from tqdm import tqdm

from .exceptions import InvalidStack
from .s1_frames import S1Frame
from .s1_stack_formatter import S1_COLUMNS


def viable_secondary_date(secondary_date: datetime.datetime | pd.Timestamp,
                          reference_date: datetime.datetime | pd.Timestamp,
                          min_temporal_baseline_days: int) -> bool:
    timedelta = datetime.timedelta(days=min_temporal_baseline_days)
    cond_1 = (secondary_date <= reference_date - timedelta)
    cond_2 = (secondary_date != reference_date)
    return cond_1 and cond_2


def enumerate_dates(dates: List[pd.Timestamp],
                    min_temporal_baseline_days: int,
                    n_secondary_scenes_per_ref: int = 3,
                    n_init_seeds: int = 1) -> List[tuple]:
    """Enumerates date pairs

    Parameters
    ----------
    dates : List[datetime.date]
        List of dates for enumeration (can be unsorted). Should have timezone otherwise comparisons will be invalid.
    min_temporal_baseline_days : int
        Ensures ifg pairs must have at least this many days between them
    n_secondary_scenes_per_ref : int, optional
        When creating time series, selects at most 3 viable dates to include in subsequent pairs, by default 3
    n_init_seeds : int, optional
        How many initial dates to populate the queue with; most recent dates are seeds, by default 1. Must be >= 1.

    Returns
    -------
    List[tuple]
        (reference_date, secondary_date)
    """
    sorted_dates = sorted(dates, reverse=True)
    queue = sorted_dates[:n_init_seeds]
    dates_visited = [sorted_dates[0]]
    pairs = []

    neighbors = n_secondary_scenes_per_ref
    while queue:
        ref_date = queue.pop(0)
        available_dates = [date for date in sorted_dates
                           if viable_secondary_date(date,
                                                    ref_date,
                                                    min_temporal_baseline_days)]
        secondary_dates = [sec_date for sec_date in available_dates[:neighbors]]
        pairs_temp = [(ref_date, sec_date) for sec_date in secondary_dates]
        pairs += pairs_temp
        for sec_date in secondary_dates:
            if sec_date not in dates_visited:
                dates_visited.append(sec_date)
                queue.append(sec_date)

    # Have to de-duplicate pairs (i.e. ensure uniqueness of items) due to seeds.
    # There are situations when a visited date may be removed from the queue
    # And then added back with multiple initial date seeds.
    pairs = list(set(pairs))
    return sorted(pairs, reverse=True)


def select_ifg_pair_from_stack(ref_date: pd.Timestamp,
                               sec_date: pd.Timestamp,
                               df_stack: gpd.GeoDataFrame,
                               frame: S1Frame = None) -> dict:
    if (not isinstance(ref_date, pd.Timestamp)) or (not isinstance(ref_date, pd.Timestamp)):
        raise TypeError('ref and secondary dates must be pd.TimeStamp')

    # It appears the datetime timezone is not stable either because of DAAC API types
    # or pandas - converting to string should enusre consistency
    if (str(ref_date.tz).lower() != 'utc') or (str(sec_date.tz).lower() != 'utc'):
        raise TypeError('Timestamp must be in UTC timezone')

    df_stack_subset = df_stack
    if frame is not None:
        tree = STRtree(df_stack.geometry)
        ind_frame = tree.query(frame.frame_geometry, predicate="intersects")
        df_stack_frame_temp = df_stack.iloc[ind_frame].sort_values(by='slc_id')
        intersection_geo = df_stack_frame_temp.intersection(frame.frame_geometry)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=UserWarning)
            coverage_ratio = intersection_geo.area / frame.frame_geometry.area
        geo_ind = (coverage_ratio >= .01)
        df_stack_subset = df_stack_frame_temp[geo_ind].reset_index(drop=True)

    ref_ind = (df_stack_subset.repeat_pass_timestamp == ref_date)
    df_ref = df_stack_subset[ref_ind].reset_index(drop=True)
    sec_ind = (df_stack_subset.repeat_pass_timestamp == sec_date)
    df_sec = df_stack_subset[sec_ind].reset_index(drop=True)

    total_intersection_geometry = None
    if frame is None:
        ref_geo = df_ref.geometry.unary_union
        sec_geo = df_sec.geometry.unary_union
        total_intersection_geometry = ref_geo.intersection(sec_geo)

    ref_slcs = df_ref.slc_id.tolist()
    sec_slcs = df_sec.slc_id.tolist()

    if (not ref_slcs) or (not sec_slcs):
        raise ValueError('No IFG could be generated from dates and frames')

    return {'reference': ref_slcs,
            'secondary': sec_slcs,
            'reference_date': ref_date,
            'secondary_date': sec_date,
            'frame_id': frame.frame_id if frame else frame,
            'geometry': frame.frame_geometry if frame else total_intersection_geometry}


def enumerate_gunw_time_series(df_stack: gpd.GeoDataFrame,
                               min_temporal_baseline_days: int = 0,
                               n_secondary_scenes_per_ref: int = 3,
                               frames: List[S1Frame] = None,
                               n_init_seeds: int = 1,
                               ) -> List[dict]:

    if df_stack.columns.tolist() != S1_COLUMNS:
        raise InvalidStack('The stack dataframe must be generated using get_s1_stack')

    if df_stack.empty:
        raise InvalidStack('The stack dataframe must be non-empty')

    frames = frames or [None]
    dates = df_stack.repeat_pass_timestamp.unique().tolist()
    neighbors = n_secondary_scenes_per_ref
    ifg_dates = enumerate_dates(dates,
                                min_temporal_baseline_days,
                                n_secondary_scenes_per_ref=neighbors,
                                n_init_seeds=n_init_seeds)

    ifg_data = [select_ifg_pair_from_stack(ref_date,
                                           sec_date,
                                           df_stack,
                                           frame
                                           )
                # The order ensures we first fix dates and then iterate through
                # frames. Ensures the data is ordered by date.
                for (ref_date, sec_date) in tqdm(ifg_dates, desc='Date Pairs')
                for frame in frames
                ]
    return ifg_data
