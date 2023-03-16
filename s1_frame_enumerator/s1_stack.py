import datetime
import warnings
from typing import List
from warnings import warn

import asf_search as asf
import geopandas as gpd
from asf_search import ASFSearchResults
from shapely.ops import unary_union
from tqdm import tqdm

from .exceptions import StackFormationError
from .s1_frames import S1Frame
from .s1_stack_formatter import format_results_for_sent1_stack


def query_slc_metadata_over_frame(frame: S1Frame,
                                  max_results_per_frame: int = 100_000,
                                  allowable_polarizations: List[str] = ['VV', 'VV+VH'],
                                  start_time: datetime.datetime = None,
                                  stop_time: datetime.datetime = None) -> ASFSearchResults:
    results = asf.geo_search(platform=[asf.PLATFORM.SENTINEL1],
                             intersectsWith=frame.frame_geometry.wkt,
                             maxResults=max_results_per_frame,
                             relativeOrbit=frame.track_numbers,
                             polarization=allowable_polarizations,
                             beamMode=[asf.BEAMMODE.IW],
                             processingLevel=[asf.PRODUCT_TYPE.SLC],
                             start=start_time,
                             end=stop_time
                             )
    results = [r.geojson() for r in results]
    return results


def filter_s1_stack_by_geometric_coverage_per_pass(df_stack: gpd.GeoDataFrame,
                                                   frames: List[S1Frame],
                                                   minimum_coverage_per_pass_ratio: float = .80) -> gpd.GeoDataFrame:

    df_stack_one_pass = df_stack.dissolve(by='repeat_pass_timestamp',
                                          aggfunc={'start_time': 'min'},
                                          as_index=False)

    frame_coverage_geometries = [f.coverage_geometry for f in frames]
    total_frame_coverage_geometry = unary_union(frame_coverage_geometries)
    total_frame_coverage_area = total_frame_coverage_geometry.area

    # warnings related to lon/lat area computation
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        intersection_area_for_one_pass = df_stack_one_pass.geometry.intersection(total_frame_coverage_geometry).area
        intersection_ratio_for_one_pass = intersection_area_for_one_pass / total_frame_coverage_area
    dissolved_ind = (intersection_ratio_for_one_pass > minimum_coverage_per_pass_ratio)

    rounded_pass_date = df_stack_one_pass[dissolved_ind].repeat_pass_timestamp
    stack_ind = df_stack.repeat_pass_timestamp.isin(rounded_pass_date)

    return df_stack[stack_ind].reset_index(drop=True)


def get_s1_stack(frames: List[S1Frame],
                 allowable_months: List[int] = None,
                 allowable_polarizations: List[str] = ['VV', 'VV+VH'],
                 minimum_coverage_ratio_per_pass: float = .80,
                 max_results_per_frame: int = 100_000,
                 start_time: datetime.datetime = None,
                 stop_time: datetime.datetime = None
                 ) -> gpd.GeoDataFrame:

    track_numbers = [tn for f in frames
                     for tn in f.track_numbers]
    unique_track_numbers = list(set(list(track_numbers)))
    n_tracks = len(unique_track_numbers)
    if (n_tracks > 1):
        if n_tracks > 2:
            raise StackFormationError('There are more than 2 track numbers specified')
        if abs(unique_track_numbers[0] - unique_track_numbers[1]) > 1:
            raise StackFormationError('There is more than 1 track number specified and these are not sequential')

    frame_geometries = [f.frame_geometry for f in frames]
    total_frame_geometry = unary_union(frame_geometries)
    if total_frame_geometry.geom_type != 'Polygon':
        raise StackFormationError('Frames must be contiguous')

    n = len(frame_geometries)
    results = []
    # Breaking apart the frame geometries takes longer, but ensures we get all the results
    # since asf_search may not get all the images if the geometry is too large
    for frame in tqdm(frames, desc=f'Downloading stack from {n} frame geometries'):
        results += query_slc_metadata_over_frame(frame,
                                                 max_results_per_frame=max_results_per_frame,
                                                 allowable_polarizations=allowable_polarizations,
                                                 start_time=start_time,
                                                 stop_time=stop_time
                                                 )

    df = format_results_for_sent1_stack(results, allowable_months=allowable_months)

    if df.empty:
        warn('There were no results returned', category=UserWarning)
        return df

    if minimum_coverage_ratio_per_pass:
        df = filter_s1_stack_by_geometric_coverage_per_pass(df, frames,
                                                            minimum_coverage_per_pass_ratio=minimum_coverage_ratio_per_pass)
        if df.empty:
            warn('The geometric coverage using the frames coverage geometry filtered out remaining results')

    return df
