from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import List, Optional
from warnings import warn

import geopandas as gpd
import pandas as pd
from rasterio.crs import CRS
from shapely.geometry import Polygon

FRAMES_DIR = Path(__file__).parent / 'data'
FRAMES_PATH = (FRAMES_DIR / 's1_frames_latitude_aligned.geojson.zip').resolve()
GUNW_EXTENTS_PATH = FRAMES_DIR / 's1_gunw_frame_footprints.geojson.zip'
GUNW_EXTENTS_PATH = GUNW_EXTENTS_PATH.resolve()


@lru_cache
def get_global_s1_frames() -> gpd.GeoDataFrame:
    df_frames = gpd.read_file(FRAMES_PATH)
    return df_frames.rename(
        columns={'relative_orbit_number_min': 'track_number_min', 'relative_orbit_number_max': 'track_number_max'}
    )


@lru_cache
def get_global_gunw_footprints() -> gpd.GeoDataFrame:
    return gpd.read_file(GUNW_EXTENTS_PATH)


def get_geometry_by_id(frame_id: int, geometry_type: str, hemisphere: str = None) -> gpd.GeoDataFrame:
    if geometry_type not in ['footprint', 'frame']:
        raise ValueError('geometry_type must be either "footprint" or "frame"')
    if (hemisphere is not None) and (hemisphere not in ['east', 'west']):
        raise ValueError('Only "east" or "west" for hemisphere is accepted.')
    df_frames = get_global_s1_frames() if geometry_type == 'frame' else get_global_gunw_footprints()
    df_frame = df_frames[df_frames.frame_id == frame_id].reset_index(drop=True)
    if hemisphere is not None:
        df_frame = df_frame.cx[-180:0, :] if (hemisphere == 'west') else df_frame.cx[0:180, :]
        df_frame = df_frame.reset_index(drop=True)
    if df_frame.shape[0] > 1:
        warn(
            'The frame you requested has multiple geometries associated to it.' 'This is due to the dateline',
            category=UserWarning,
        )
    if df_frame.shape[0] == 0:
        raise ValueError('The id requested is invalid')
    return df_frame


@dataclass
class S1Frame(object):
    frame_id: int
    hemisphere: Optional[str] = None
    track_numbers: List[int] = field(init=False)
    frame_geometry: Polygon = field(init=False)
    footprint_geometry: Polygon = field(init=False)

    def __post_init__(self):
        df_frame = get_geometry_by_id(self.frame_id, 'frame', hemisphere=self.hemisphere)
        # Frame Geometry lookup
        self.frame_geometry = df_frame.geometry.iloc[0]
        # Recompute hemisphere if necessary
        if self.hemisphere is None:
            c_x = self.frame_geometry.centroid.x
            self.hemisphere = 'west' if c_x < 0 else 'east'
        # Track number lookup
        tn_min = df_frame.track_number_min.iloc[0]
        tn_max = df_frame.track_number_max.iloc[0]
        self.track_numbers = list({tn_min, tn_max})
        # Footprint lookup
        df_footprint = get_geometry_by_id(self.frame_id, 'footprint', hemisphere=self.hemisphere)
        self.footprint_geometry = df_footprint.geometry.iloc[0]

    def to_gdf(self, use_footprint_geometry: bool = False):
        return frames2gdf([self], use_footprint_geometry=use_footprint_geometry)


def get_overlapping_s1_frames(
    geometry: Polygon,
    track_numbers: List[int] = None,
) -> gpd.GeoDataFrame:
    df_s1_frames = get_global_s1_frames()
    # Note that intersection across frames near dateline will be correct as geometries are separated
    ind = df_s1_frames.intersects(geometry)
    df_overlapping_frames = df_s1_frames[ind].reset_index(drop=True)

    xmin, _, xmax, _ = geometry.bounds
    if xmax - xmin > 180:
        raise ValueError('Your geometry needs to be less than 180 degrees in width')

    if track_numbers and not df_overlapping_frames.empty:
        ind_0 = df_overlapping_frames.track_number_min.isin(track_numbers)
        ind_1 = df_overlapping_frames.track_number_max.isin(track_numbers)
        ind = ind_0 | ind_1
        df_temp = df_overlapping_frames[ind]
        df_overlapping_frames = df_temp.reset_index(drop=True)

    if df_overlapping_frames.empty:
        msg = 'There are no overlapping frames with the AOI.'
        if track_numbers:
            track_numbers_str = list(map(str, track_numbers))
            msg_track = ', '.join(track_numbers_str)
            msg = msg.replace('.', f' and track number(s) {msg_track}.')
        raise ValueError(msg)

    frames = gdf2frames(df_overlapping_frames)
    return frames


def gdf2frames(df_frames: gpd.GeoDataFrame) -> List[S1Frame]:
    xmin, _, xmax, _ = df_frames.total_bounds
    hemisphere = None
    if xmax - xmin > 180:
        raise ValueError('The frames span more than 180 degrees; break apart your request')
    if xmin <= -180:
        hemisphere = 'west'
    if xmax >= 180:
        hemisphere = 'east'
    records = df_frames.to_dict('records')
    return [S1Frame(frame_id=r['frame_id'], hemisphere=hemisphere) for r in records]


def frames2gdf(s1frames: List[S1Frame], use_footprint_geometry=False) -> gpd.GeoDataFrame:
    records = [asdict(frame) for frame in s1frames]
    geometry = [r.pop('frame_geometry') for r in records]
    footprint_geometry = [r.pop('footprint_geometry') for r in records]
    track_numbers = [r.pop('track_numbers') for r in records]
    track_number_min = [min(tn) for tn in track_numbers]
    track_number_max = [max(tn) for tn in track_numbers]
    if use_footprint_geometry:
        geometry = footprint_geometry

    df = pd.DataFrame(records)
    df['track_number_min'] = track_number_min
    df['track_number_max'] = track_number_max
    df = gpd.GeoDataFrame(df, geometry=geometry, crs=CRS.from_epsg(4326))
    return df
