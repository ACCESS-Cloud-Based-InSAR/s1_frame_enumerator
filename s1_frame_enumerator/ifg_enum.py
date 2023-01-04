import datetime
import warnings
from typing import List

import geopandas as gpd
from shapely.ops import unary_union
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


def get_minimum_coverage_set(df_image: gpd.GeoDataFrame,
                             frame: S1Frame) -> List[int]:

    df_image_new = df_image.copy()
    df_image_new['remaining_coverage_ratio'] = df_image_new['coverage_ratio']

    coverage_images = []
    coverage_indices = []
    k = 0
    while k < df_image_new.shape[0]:
        # Sort by remaining coverage ratio and if there is a tie, use image
        # that has greater coverage over frame
        columns = ['remaining_coverage_ratio', 'coverage_ratio']
        i_max = df_image_new.sort_values(by=columns, ascending=False).index[0]
        coverage_indices.append(i_max)
        coverage_images.append(df_image_new.geometry.iloc[i_max])
        coverage_geo = unary_union(coverage_images)
        frame_coverage_geo = frame.coverage_geometry

        if coverage_geo.covers(frame_coverage_geo):
            break

        remaining_area = frame_coverage_geo.difference(coverage_geo)
        intersection_geo = df_image_new.geometry.intersection(remaining_area)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=UserWarning)
            remaining_coverage_ratio = intersection_geo.area / frame.coverage_geometry.area
        df_image_new['remaining_coverage_ratio'] = remaining_coverage_ratio
        k += 1

    coverage_indices = sorted(coverage_indices)
    return coverage_indices


def select_ifg_pair_from_stack(ref_date: datetime.datetime,
                               sec_date: datetime.datetime,
                               frame: S1Frame,
                               df_stack: gpd.GeoDataFrame,
                               obtain_minimal_covering: bool = True) -> dict:

    intersection_geo = df_stack.intersection(frame.coverage_geometry)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        coverage_ratio = intersection_geo.area / frame.coverage_geometry.area
    geo_ind = (coverage_ratio >= .01)
    df_stack_frame = df_stack[geo_ind].reset_index(drop=True)
    df_stack_frame['coverage_ratio'] = coverage_ratio[geo_ind].values

    ref_ind = (df_stack_frame.repeat_pass_date == ref_date)
    df_ref = df_stack_frame[ref_ind].reset_index(drop=True)
    sec_ind = (df_stack_frame.repeat_pass_date == sec_date)
    df_sec = df_stack_frame[sec_ind].reset_index(drop=True)

    # Get minimum covering set; requires "coverage_ratio" in column
    if obtain_minimal_covering:
        ref_indices = get_minimum_coverage_set(df_ref, frame)
        df_ref = df_ref.iloc[ref_indices].reset_index(drop=True)

        sec_indices = get_minimum_coverage_set(df_sec, frame)
        df_sec = df_sec.iloc[sec_indices].reset_index(drop=True)

    ref_slcs = df_ref.slc_id.tolist()
    sec_slcs = df_sec.slc_id.tolist()
    return {'reference': ref_slcs,
            'secondary': sec_slcs,
            'frame_id': frame.frame_id,
            'geometry': frame.frame_geometry}


def enumerate_gunw_time_series(frames: List[S1Frame],
                               df_stack: gpd.GeoDataFrame,
                               min_temporal_baseline_days: int,
                               n_secondary_scenes_per_ref: int = 3,
                               obtain_minimal_covering: bool = True,
                               ) -> List[dict]:
    dates = df_stack.repeat_pass_date.unique().tolist()
    neighbors = n_secondary_scenes_per_ref
    ifg_dates = enumerate_dates(dates,
                                min_temporal_baseline_days,
                                n_secondary_scenes_per_ref=neighbors)

    covering = obtain_minimal_covering
    ifg_data = [select_ifg_pair_from_stack(ref_date,
                                           sec_date,
                                           frame,
                                           df_stack,
                                           obtain_minimal_covering=covering)
                for frame in tqdm(frames, desc='Frames')
                for (ref_date, sec_date) in tqdm(ifg_dates, desc='Date Pairs')]
    return ifg_data
