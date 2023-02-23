from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import List

import geopandas as gpd
import pandas as pd
from rasterio.crs import CRS
from shapely.geometry import MultiPolygon, Polygon

FRAMES_DIR = Path(__file__).parent / 'data'
FRAMES_PATH = (FRAMES_DIR / 's1_frames_latitude_aligned.geojson.zip').resolve()
GUNW_EXTENTS_PATH = (FRAMES_DIR / 'gunw_frame_footprints.geojson.zip').resolve()


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


@dataclass
class S1Frame(object):
    frame_geometry: Polygon
    frame_id: int
    track_numbers: List[int]
    use_natural_earth_land_mask: bool = True
    coverage_geometry: MultiPolygon | Polygon = field(init=False)

    def __post_init__(self):
        self.coverage_geometry = self.frame_geometry
        if self.use_natural_earth_land_mask:
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
