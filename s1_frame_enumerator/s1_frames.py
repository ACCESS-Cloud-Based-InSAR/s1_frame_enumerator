from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import List

import geopandas as gpd
import pandas as pd
from dem_stitcher.geojson_io import read_geojson_gzip
from rasterio.crs import CRS
from shapely.geometry import MultiPolygon, Polygon

FRAMES_DIR = Path(__file__).parent / 'data'
FRAMES_PATH = (FRAMES_DIR / 's1_frames.geojson.gzip').resolve()


@lru_cache
def get_natural_earth_land_mask() -> MultiPolygon:
    return gpd.read_file(gpd.datasets.get_path('naturalearth_lowres')).geometry.unary_union


@lru_cache
def get_global_s1_frames() -> gpd.GeoDataFrame:
    df_frames = read_geojson_gzip(FRAMES_PATH)
    return df_frames.rename(columns={'relative_orbit_number': 'track_numbers'})


@dataclass
class S1Frame(object):
    frame_geometry: Polygon
    frame_id: int
    track_numbers: List[int]
    use_land_mask: bool = True
    coverage_geometry: MultiPolygon | Polygon = field(init=False)

    def __post_init__(self):
        self.coverage_geometry = self.frame_geometry
        if self.use_land_mask:
            land_geo = get_natural_earth_land_mask()
            self.coverage_geometry = self.frame_geometry.intersection(land_geo)


def track_number_contained(relative_orbit_numbers_row: str,
                           track_numbers_subset: List[int]) -> bool:
    track_numbers_row = relative_orbit_numbers_row.split(',')
    track_numbers_row = list(map(int, track_numbers_row))
    intersection = [track_number for track_number in track_numbers_row if track_number in track_numbers_subset]
    if intersection:
        return True
    else:
        return False


def get_overlapping_s1_frames(geometry: Polygon,
                              track_numbers: List[int] = None,
                              ) -> gpd.GeoDataFrame:
    df_s1_frames = get_global_s1_frames()
    ind = df_s1_frames.intersects(geometry)
    df_overlapping_frames = df_s1_frames[ind].reset_index(drop=True)
    if track_numbers:
        def track_number_contained_p(relative_orbit_numbers):
            return track_number_contained(relative_orbit_numbers, track_numbers)

        ind = df_overlapping_frames.relative_orbit_numbers.map(track_number_contained_p)
        df_overlapping_frames = df_overlapping_frames[ind].reset_index(drop=True)

    frames = gdf2frames(df_overlapping_frames)

    return frames


def gdf2frames(df_frames: gpd.GeoDataFrame) -> List[S1Frame]:
    records = df_frames.to_dict('records')
    all_track_numbers = sorted([[int(tn) for tn in r['relative_orbit_numbers'].split(',')]
                                for r in records])
    return [S1Frame(frame_geometry=r['geometry'],
                    frame_id=r['frame_id'],
                    track_numbers=track_numbers
                    ) for (r, track_numbers) in zip(records, all_track_numbers)]


def frames2gdf(s1frames: List[S1Frame], use_coverage_geometry=False) -> gpd.GeoDataFrame:
    records = [asdict(frame) for frame in s1frames]
    geometry = [r.pop('frame_geometry') for r in records]
    coverage_geometry = [r.pop('coverage_geometry') for r in records]
    if use_coverage_geometry:
        geometry = coverage_geometry

    df = pd.DataFrame(records)
    df = gpd.GeoDataFrame(df,
                          geometry=geometry,
                          crs=CRS.from_epsg(4326))
    df['track_numbers'] = df['track_numbers'].map(lambda tns: ','.join([str(t) for t in tns]))
    return df
