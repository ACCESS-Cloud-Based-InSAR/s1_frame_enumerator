import datetime
import warnings
from typing import List

from tqdm import tqdm


def viable_secondary_date(secondary_date, reference_date, min_temporal_baseline_days):
    timedelta = datetime.timedelta(days=min_temporal_baseline_days)
    cond_1 = (secondary_date <= reference_date - timedelta)
    cond_2 = (secondary_date != reference_date)
    return cond_1 and cond_2


def enumerate_dates(dates: list,
                    min_temporal_baseline_days: int,
                    n_secondary_scenes_per_ref: int = 3) -> List[tuple]:
    sorted_dates = sorted(dates, reverse=True)
    queue = [sorted_dates[0]]
    pairs = []

    while queue:
        ref_date = queue.pop(0)
        available_dates = [date for date in sorted_dates if viable_secondary_date(date,
                                                                                  ref_date,
                                                                                  min_temporal_baseline_days)]
        secondary_dates = [sec_date for sec_date in available_dates[:n_secondary_scenes_per_ref]]
        pairs_temp = [(ref_date, sec_date) for sec_date in secondary_dates]
        pairs += pairs_temp
        for sec_date in secondary_dates:
            if sec_date not in queue:
                queue.append(sec_date)

    # although the queue nodes never repeat, pairs can easily repeat, only need to do this once
    pairs = list(set(pairs))
    return sorted(pairs, reverse=True)


def select_ifg_pair_from_stack(ref_date, sec_date, frame, df_stack) -> dict:

    intersection_geo = df_stack.intersection(frame.coverage_geometry)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        coverage_ratio = intersection_geo.area / frame.coverage_geometry.area
    geo_ind = coverage_ratio >= .01
    df_stack_frame = df_stack[geo_ind].reset_index(drop=True)

    df_ref = df_stack_frame[df_stack_frame.repeat_pass_date == ref_date].reset_index(drop=True)
    df_sec = df_stack_frame[df_stack_frame.repeat_pass_date == sec_date].reset_index(drop=True)

    return {'reference': df_ref.slc_id.tolist(),
            'secondary': df_sec.slc_id.tolist(),
            'frame_id': frame.frame_id,
            'geometry': frame.coverage_geometry}


def enumerate_gunw_time_series(frames,
                               df_stack,
                               min_temporal_baseline_days,
                               n_secondary_scenes_per_ref=3,
                               ) -> List[dict]:
    dates = df_stack.repeat_pass_date.unique().tolist()
    ifg_dates = enumerate_dates(dates,
                                min_temporal_baseline_days,
                                n_secondary_scenes_per_ref=n_secondary_scenes_per_ref)

    ifg_data = [select_ifg_pair_from_stack(ref_date, sec_date, frame, df_stack)
                for frame in tqdm(frames, desc='Frames')
                for (ref_date, sec_date) in tqdm(ifg_dates, desc='Date Pairs')]
    return ifg_data
