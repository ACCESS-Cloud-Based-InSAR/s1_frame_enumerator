import datetime
import warnings
from typing import List

import geopandas as gpd
from shapely import STRtree
from tqdm import tqdm

from .s1_frames import S1Frame


def viable_secondary_date(secondary_date: datetime.datetime,
                          reference_date: datetime.datetime,
                          min_temporal_baseline_days: int) -> bool:
    timedelta = datetime.timedelta(days=min_temporal_baseline_days)
    cond_1 = (secondary_date <= reference_date - timedelta)
    cond_2 = (secondary_date != reference_date)
    return cond_1 and cond_2


def enumerate_dates(dates: list,
                    min_temporal_baseline_days: int,
                    n_secondary_scenes_per_ref: int = 3) -> List[tuple]:
    sorted_dates = sorted(dates, reverse=True)
    queue = [sorted_dates[0]]
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

    return sorted(pairs, reverse=True)


def select_ifg_pair_from_stack(ref_date: datetime.datetime,
                               sec_date: datetime.datetime,
                               df_stack: gpd.GeoDataFrame,
                               frame: S1Frame = None) -> dict:
    df_stack_subset = df_stack
    if frame is not None:
        tree = STRtree(df_stack.geometry)
        ind_frame = tree.query(frame.coverage_geometry, predicate="intersects")
        df_stack_frame_temp = df_stack.iloc[ind_frame].sort_values(by='slc_id')
        intersection_geo = df_stack_frame_temp.intersection(frame.coverage_geometry)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=UserWarning)
            coverage_ratio = intersection_geo.area / frame.coverage_geometry.area
        geo_ind = (coverage_ratio >= .01)
        df_stack_subset = df_stack_frame_temp[geo_ind].reset_index(drop=True)

    ref_ind = (df_stack_subset.repeat_pass_date == ref_date)
    df_ref = df_stack_subset[ref_ind].reset_index(drop=True)
    sec_ind = (df_stack_subset.repeat_pass_date == sec_date)
    df_sec = df_stack_subset[sec_ind].reset_index(drop=True)

    ref_slcs = df_ref.slc_id.tolist()
    sec_slcs = df_sec.slc_id.tolist()
    return {'reference': ref_slcs,
            'secondary': sec_slcs,
            'reference_date': ref_date,
            'secondary_date': sec_date,
            'frame_id': frame.frame_id,
            'geometry': frame.frame_geometry}


def enumerate_gunw_time_series(df_stack: gpd.GeoDataFrame,
                               min_temporal_baseline_days: int = 0,
                               n_secondary_scenes_per_ref: int = 3,
                               frames: List[S1Frame] = None
                               ) -> List[dict]:
    frames = frames or [None]
    dates = df_stack.repeat_pass_date.unique().tolist()
    neighbors = n_secondary_scenes_per_ref
    ifg_dates = enumerate_dates(dates,
                                min_temporal_baseline_days,
                                n_secondary_scenes_per_ref=neighbors)

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
