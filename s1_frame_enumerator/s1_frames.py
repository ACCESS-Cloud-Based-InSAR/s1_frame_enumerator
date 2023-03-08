from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import List, Optional
from warnings import warn

import geopandas as gpd
import pandas as pd
from rasterio.crs import CRS
from shapely.geometry import MultiPolygon, Polygon

FRAMES_DIR = Path(__file__).parent / 'data'
FRAMES_PATH = (FRAMES_DIR / 's1_frames_latitude_aligned.geojson.zip').resolve()
GUNW_EXTENTS_PATH = (FRAMES_DIR / 's1_gunw_frame_footprints.geojson.zip')
GUNW_EXTENTS_PATH = GUNW_EXTENTS_PATH.resolve()


@lru_cache
def get_natural_earth_land_mask() -> MultiPolygon:
    ne_land_path = gpd.datasets.get_path('naturalearth_lowres')
    return gpd.read_file(ne_land_path).geometry.unary_union


@lru_cache
def get_global_s1_frames() -> gpd.GeoDataFrame:
    df_frames = gpd.read_file(FRAMES_PATH)
    return df_frames.rename(columns={'relative_orbit_number_min': 'track_number_min',
                                     'relative_orbit_number_max': 'track_number_max'
                                     }
                            )


@lru_cache
def get_global_gunw_footprints() -> gpd.GeoDataFrame:
    return gpd.read_file(GUNW_EXTENTS_PATH)


def get_s1_frame_row_by_id(frame_id: int) -> gpd.GeoDataFrame:
    df_frames = get_global_s1_frames()
    df_frame = df_frames[df_frames.frame_id == frame_id].reset_index(drop=True)
    return df_frame


@dataclass
class S1Frame(object):
    frame_id: int
    track_numbers: Optional[List[int]] = None
    frame_geometry: Optional[Polygon] = None
    use_natural_earth_land_mask: Optional[bool] = True
    coverage_geometry: Optional[MultiPolygon | Polygon] = None

    def __post_init__(self):

        # look up other relevant metadata from table using frame_id
        tn_empty = (self.track_numbers is None)
        frame_geo_empty = (self.frame_geometry is None)

        if frame_geo_empty:
            df_frame = get_s1_frame_row_by_id(self.frame_id)
            self.frame_geometry = df_frame.geometry.iloc[0]

        if tn_empty:
            df_frame = get_s1_frame_row_by_id(self.frame_id)
            tn_min = df_frame.track_number_min.iloc[0]
            tn_max = df_frame.track_number_max.iloc[0]
            self.track_numbers = list({tn_min, tn_max})

        # Coverage Geometry
        user_specified_coverage_geometry = not (self.coverage_geometry is None)
        # Ensure Coverage Geometry contained in Frame Geometry
        if user_specified_coverage_geometry:
            if not self.frame_geometry.contains(self.coverage_geometry):
                raise ValueError('Coverage geometry must be contained in Frame Geometry')
        # Assign coverage geometry to be frame geometry if unassigned
        if not user_specified_coverage_geometry:
            self.coverage_geometry = self.frame_geometry
        if self.use_natural_earth_land_mask:
            # Ensure user is aware that land mask is not being used
            if user_specified_coverage_geometry:
                warn('Although a Natural Earth Land Mask was requested for '
                     'coverage geometry; we are using the user geometry supplied',
                     category=UserWarning)
            else:
                land_geo = get_natural_earth_land_mask()
                self.coverage_geometry = self.frame_geometry.intersection(land_geo)

    def update_coverage_geo_with_custom_land_mask(self, land_geo):
        self.coverage_geometry = self.frame_geometry.intersection(land_geo)


def get_overlapping_s1_frames(geometry: Polygon,
                              track_numbers: List[int] = None,
                              ) -> gpd.GeoDataFrame:
    df_s1_frames = get_global_s1_frames()
    ind = df_s1_frames.intersects(geometry)
    df_overlapping_frames = df_s1_frames[ind].reset_index(drop=True)
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
            msg_track = ", ".join(track_numbers_str)
            msg = msg.replace('.', f' and track number(s) {msg_track}.')
        raise ValueError(msg)

    frames = gdf2frames(df_overlapping_frames)
    return frames


def gdf2frames(df_frames: gpd.GeoDataFrame) -> List[S1Frame]:
    records = df_frames.to_dict('records')

    def combine_min_max_orbits(row):
        tracks = [row['track_number_min'],
                  row['track_number_max']]
        tracks = list(set(tracks))
        return tracks
    all_track_numbers = df_frames.apply(combine_min_max_orbits, axis=1).tolist()
    return [S1Frame(frame_geometry=r['geometry'],
                    frame_id=r['frame_id'],
                    track_numbers=track_numbers
                    ) for (r, track_numbers) in zip(records, all_track_numbers)]


def frames2gdf(s1frames: List[S1Frame],
               use_coverage_geometry=False) -> gpd.GeoDataFrame:
    records = [asdict(frame) for frame in s1frames]
    geometry = [r.pop('frame_geometry') for r in records]
    coverage_geometry = [r.pop('coverage_geometry') for r in records]
    track_numbers = [r.pop('track_numbers') for r in records]
    track_number_min = [min(tn) for tn in track_numbers]
    track_number_max = [max(tn) for tn in track_numbers]
    if use_coverage_geometry:
        geometry = coverage_geometry

    df = pd.DataFrame(records)
    df['track_number_min'] = track_number_min
    df['track_number_max'] = track_number_max
    df = df.drop(columns=['use_natural_earth_land_mask'])
    df = gpd.GeoDataFrame(df,
                          geometry=geometry,
                          crs=CRS.from_epsg(4326))
    return df
