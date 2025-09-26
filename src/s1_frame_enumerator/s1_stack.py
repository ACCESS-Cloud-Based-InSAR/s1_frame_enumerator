import datetime
import warnings
from warnings import warn

import asf_search as asf
import geopandas as gpd
import pandas as pd
from asf_search import ASFSearchResults
from shapely.ops import unary_union
from tqdm import tqdm

from .exceptions import StackFormationError
from .s1_frames import S1Frame
from .s1_stack_formatter import format_results_for_sent1_stack


MINIMUM_PER_FRAME_RATIO = 0.20
MIN_S1C_DATE = pd.Timestamp(
    '2025-05-19', tz='UTC'
)  # https://sentinels.copernicus.eu/-/sentinel-1c-products-are-now-calibrated


def query_slc_metadata_over_frame(
    frame: S1Frame,
    max_results_per_frame: int = 100_000,
    allowable_polarizations: list[str] = ['VV', 'VV+VH'],
    start_time: datetime.datetime = None,
    stop_time: datetime.datetime = None,
) -> ASFSearchResults:
    results = asf.geo_search(
        platform=[asf.PLATFORM.SENTINEL1],
        intersectsWith=frame.frame_geometry.wkt,
        maxResults=max_results_per_frame,
        relativeOrbit=frame.track_numbers,
        polarization=allowable_polarizations,
        beamMode=[asf.BEAMMODE.IW],
        processingLevel=[asf.PRODUCT_TYPE.SLC],
        start=start_time,
        end=stop_time,
    )
    results = [r.geojson() for r in results]
    return results


def filter_s1_stack_by_geometric_coverage_per_pass(
    df_stack: gpd.GeoDataFrame, frames: list[S1Frame], minimum_coverage_per_pass_ratio: float = 0.80
) -> gpd.GeoDataFrame:
    """
    Ensure there is a minimum area coverage over the stack. Also ensures that SLCs within a given pass are connected.

    Parameters
    ----------
    df_stack : gpd.GeoDataFrame
    frames : List[S1Frame]
    minimum_coverage_per_pass_ratio : float, optional

    Returns
    -------
    gpd.GeoDataFrame
       Filtered stack
    """
    df_stack_one_pass = df_stack.dissolve(by='repeat_pass_timestamp', aggfunc={'start_time': 'min'}, as_index=False)

    frame_geometries = [f.footprint_geometry for f in frames]
    total_frame_geometry = unary_union(frame_geometries)
    total_frame_coverage_area = total_frame_geometry.area

    # warnings related to lon/lat area computation
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', category=UserWarning)
        intersection_area_for_one_pass = df_stack_one_pass.geometry.intersection(total_frame_geometry).area
        intersection_ratio_for_one_pass = intersection_area_for_one_pass / total_frame_coverage_area
    dissolved_ind_area = intersection_ratio_for_one_pass >= minimum_coverage_per_pass_ratio

    # need to check geometric type of SLCs in stack which could potentially be disconnected
    # even if frames together are connected component
    dissolved_ind_contig = df_stack_one_pass.geometry.map(lambda geo: geo.geom_type == 'Polygon')

    dissolved_ind = dissolved_ind_area & dissolved_ind_contig
    pass_dates_to_include = df_stack_one_pass[dissolved_ind].repeat_pass_timestamp
    stack_ind = df_stack.repeat_pass_timestamp.isin(pass_dates_to_include)

    return df_stack[stack_ind].reset_index(drop=True)


def filter_s1_stack_by_geometric_coverage_per_frame(
    df_stack: gpd.GeoDataFrame, frames: list[S1Frame], minimum_coverage_ratio_per_frame: float = 0.5
) -> gpd.GeoDataFrame:
    """Filter stack by geometric coverage per frame.

    Parameters
    ----------
    df_stack : gpd.GeoDataFrame
    frames : List[S1Frame]
    minimum_coverage_ratio_per_frame : float, optional

    Returns
    -------
    gpd.GeoDataFrame
        Filtered stack
    """
    df_stack_one_pass = df_stack.dissolve(by='repeat_pass_timestamp', aggfunc={'start_time': 'min'}, as_index=False)

    dates_with_not_enough_per_frame_coverage = []
    for k, one_pass_series in df_stack_one_pass.iterrows():
        for frame in frames:
            frame_geo = frame.footprint_geometry
            frame_intersection = frame_geo.intersection(one_pass_series['geometry'])
            frame_coverage_ratio = frame_intersection.area / frame_geo.area
            if frame_coverage_ratio < minimum_coverage_ratio_per_frame:
                pass_ts = one_pass_series['repeat_pass_timestamp']
                dates_with_not_enough_per_frame_coverage.append(pass_ts)
                warn(
                    f'Frame {frame.frame_id} did not have enough coverage '
                    f'on {pass_ts.date()} (ratio of coverage was {frame_coverage_ratio:1.2f})'
                )

    dates_with_not_enough_per_frame_coverage = list(set(dates_with_not_enough_per_frame_coverage))
    stack_ind = ~df_stack.repeat_pass_timestamp.isin(dates_with_not_enough_per_frame_coverage)

    return df_stack[stack_ind].reset_index(drop=True)


def filter_s1c_data(df_stack: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Filter out S1C data from the stack."""
    s1c_filter = (df_stack['slc_id'].map(lambda id_: id_[:3] == 'S1C')) & (
        pd.to_datetime(df_stack['start_time'], utc=True) >= MIN_S1C_DATE
    )
    not_s1c_filter = df_stack['slc_id'].map(lambda id_: id_[:3] != 'S1C')
    df_stack = df_stack[s1c_filter | not_s1c_filter].reset_index(drop=True)
    return df_stack


def get_s1_stack(
    frames: list[S1Frame],
    allowable_months: list[int] = None,
    allowable_polarizations: list[str] = ['VV', 'VV+VH'],
    minimum_coverage_ratio_per_pass: float = 0.80,
    minimum_coverage_ratio_per_frame: float = 0.25,
    max_query_results_per_frame: int = 100_000,
    query_start_time: datetime.datetime = None,
    query_stop_time: datetime.datetime = None,
) -> gpd.GeoDataFrame:
    """
    Generate a stack of SLCs from a list of frames.

    A stack is defined to be all the SLCs that constitute a single pass along an ascending/descending
    *contiguous* flight path.

    Parameters
    ----------
    frames : List[S1Frame]
    allowable_months : List[int], optional
    allowable_polarizations : List[str], optional
    minimum_coverage_ratio_per_pass : float, optional
    minimum_coverage_ratio_per_frame : float, optional
    max_query_results_per_frame : int, optional
    query_start_time : datetime.datetime, optional
    query_stop_time : datetime.datetime, optional

    Returns
    -------
    gpd.GeoDataFrame

    Raises
    ------
    StackFormationError
        If the frames are (a) not connected, (b) multiple tracks (more than 2 or 2 non-sequential tracks)
    """
    track_numbers = [tn for f in frames for tn in f.track_numbers]
    unique_track_numbers = list(set(list(track_numbers)))
    n_tracks = len(unique_track_numbers)
    if n_tracks > 1:
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
        results += query_slc_metadata_over_frame(
            frame,
            max_results_per_frame=max_query_results_per_frame,
            allowable_polarizations=allowable_polarizations,
            start_time=query_start_time,
            stop_time=query_stop_time,
        )

    df = format_results_for_sent1_stack(results, allowable_months=allowable_months)
    df = filter_s1c_data(df)

    if df.empty:
        warn('There were no results returned', category=UserWarning)
        return df

    if minimum_coverage_ratio_per_pass:
        ratio = minimum_coverage_ratio_per_pass
        df = filter_s1_stack_by_geometric_coverage_per_pass(df, frames, minimum_coverage_per_pass_ratio=ratio)
        if df.empty:
            warn(f'Ensuring per pass coverage of {ratio} left no available images in the stack', category=UserWarning)

    if minimum_coverage_ratio_per_frame:
        ratio = minimum_coverage_ratio_per_frame
        df = filter_s1_stack_by_geometric_coverage_per_frame(df, frames, minimum_coverage_ratio_per_frame=ratio)
        if df.empty:
            warn(f'Ensuring per frame coverage of {ratio} left no available images in the stack', category=UserWarning)
        if minimum_coverage_ratio_per_frame < MINIMUM_PER_FRAME_RATIO:
            warn(
                f'Requesting per frame coverage below {MINIMUM_PER_FRAME_RATIO}%; '
                'ISCE2 requires minimum number of bursts',
                category=UserWarning,
            )
    else:
        warn('No per frame check was performed so enumeration should be done by date', category=UserWarning)

    return df
