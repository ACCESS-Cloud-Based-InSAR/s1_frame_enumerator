from typing import List

import geopandas as gpd
import pandas as pd
from rasterio.crs import CRS
from shapely.geometry import shape

S1_COLUMNS = ['slc_id',
              'start_time',
              'stop_time',
              'url',
              'track_number',
              'polarization',
              'orbit',
              'beam_mode',
              'size_gb',
              'stack_repeat_pass_id',
              'repeat_pass_date',
              'geometry',
              ]


def format_results_for_sent1(results: list,
                             allowable_months: List[int] = None) -> gpd.GeoDataFrame:
    geometry = [shape(r.geojson()['geometry']) for r in results]
    data = [r.properties for r in results]

    df_asf = pd.DataFrame(data)
    df_asf = gpd.GeoDataFrame(df_asf,
                              geometry=geometry,
                              crs=CRS.from_epsg(4326))

    df_formatted = gpd.GeoDataFrame(columns=S1_COLUMNS,
                                    geometry=[],
                                    crs=CRS.from_epsg(4326))
    if df_asf.empty:
        return df_formatted

    df_formatted['slc_id'] = df_asf['fileID'].map(lambda file_id: file_id.replace('-SLC', ''))
    df_formatted['start_time'] = pd.to_datetime(df_asf.startTime)
    df_formatted['stop_time'] = pd.to_datetime(df_asf.stopTime)
    df_formatted['url'] = df_asf['url']
    df_formatted['track_number'] = df_asf['pathNumber'].astype(int)
    df_formatted['orbit'] = df_asf['orbit'].astype(int)
    df_formatted['polarization'] = df_asf['polarization']
    df_formatted['beam_mode'] = df_asf['beamModeType']
    df_formatted['size_gb'] = df_asf['bytes'] / 1e9
    df_formatted['geometry'] = df_asf['geometry']

    # Drop duplicate rows and sort by acq time
    df_formatted.drop_duplicates(subset=['slc_id'], inplace=True)
    df_formatted = df_formatted.sort_values(by=['start_time', 'track_number']).reset_index(drop=True)

    if allowable_months:
        ind_month = df_formatted.start_time.dt.month.isin(allowable_months)
        df_formatted = df_formatted[ind_month].reset_index(drop=True)

    # Want to group S1 imagery by repeat pass date - technically this could be at midnight so we do some work.
    # First we get ids based on julian date, then we group by first date in group
    julian_dates = df_formatted.start_time.map(lambda dt: dt.to_julian_date())
    # Note this calculus depends on the repeat pass frequency of Sentinel-1 which is 6
    df_formatted['stack_repeat_pass_id'] = ((julian_dates - julian_dates[0]) // 5).astype(int)
    # Ensure sequential (see: https://stackoverflow.com/a/15074395)
    df_formatted['stack_repeat_pass_id'] = df_formatted.groupby(['stack_repeat_pass_id']).grouper.group_info[0]

    df_temp = pd.DataFrame(columns=['stack_repeat_pass_id', 'repeat_pass_date'])
    df_temp['stack_repeat_pass_id'] = df_formatted.stack_repeat_pass_id
    df_temp['repeat_pass_date'] = df_formatted.start_time.dt.date
    # Get the min date in group
    df_repeat_pass_date = df_temp.groupby('stack_repeat_pass_id').min()
    # look up min date based on group
    repeat_pass_dict = df_repeat_pass_date.to_dict()['repeat_pass_date']
    df_formatted['repeat_pass_date'] = df_formatted.stack_repeat_pass_id.map(lambda rp_id: repeat_pass_dict[rp_id])

    return df_formatted
