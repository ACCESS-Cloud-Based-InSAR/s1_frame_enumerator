# S1-Frame-Enumerator

This library enumerates input single look complex (SLC) IDs for reference and secondary imagery to generate a time series of interferograms over an area of interest (AOI) using *fixed spatial frames*. Such SLC imagery can then be used to generate an interferometric time series. Our focus is generating ARIA S1 Geocoded Unwrapped Interferogram (ARIA-S1-GUNW), a standardized, sensor-neutral inteferometric product as described [here](https://github.com/ACCESS-Cloud-Based-InSAR/DockerizedTopsApp) using [ISCE2](https://github.com/isce-framework/isce2).

## Background

Sentinel-1 SLC enumeration for interferometric processing is notoriously challenging despite its simple description. This is partly because ESA frame definitions are not spatially fixed in time and it is hard to ensure complete spatial coverage across date pairs. Our fixed frame approach attempts to circumvent this challenge by ensuring SLC pairs are enunumerated across fixed spatial areas. We also ensure consistent overlap (at least 1 burst) across inteferometric products to ensure interferometric products can be stitched for downstream analysis.

This library relies on [`asf-search`](https://github.com/asfadmin/Discovery-asf_search) to enumerate Sentinel-1 A/B pairs from fixed frames derived from ESA's burst [map](https://sar-mpc.eu/test-data-sets/). We describe the generation of the "fixed-frames" in this [repository](https://github.com/ACCESS-Cloud-Based-InSAR/s1-frame-generation). Using this frame map (stored a zip file within this library), we enumerate SLCs that cover contiguous collection of frames. The frames Northern and Souther boundaries are aligned with latitude lines to ensure GUNW products and the frame definitions are consistent. We have two datasets the latitude-aligned [frames](https://github.com/ACCESS-Cloud-Based-InSAR/s1-frame-enumerator/blob/58f7e62a4efd0784766da21ab7f618073fe9f347/s1_frame_enumerator/data/s1_frames_latitude_aligned.geojson.zip) and the expected GUNW product [extents](https://github.com/ACCESS-Cloud-Based-InSAR/s1-frame-enumerator/blob/58f7e62a4efd0784766da21ab7f618073fe9f347/s1_frame_enumerator/data/s1_gunw_frame_footprints.geojson.zip).

## Usage

Here is a summary of the API:

```
from shapely.geometry import Point
from s1_frame_enumerator import (get_s1_stack,
                                 get_overlapping_s1_frames,
                                 enumerate_gunw_time_series
                                 )

# Southern California
aoi_geo = Point(-120, 35).buffer(1)

# Get Frames
track_numbers = [144]
frames = get_overlapping_s1_frames(aoi_geo,
                                   track_numbers=track_numbers)

# Get Stack
df_stack = get_s1_stack(frames)

# Get Pairs for IFGs over Frames
min_temporal_baseline = 30
neighbors = 3
ifg_data = enumerate_gunw_time_series(df_stack,
                                      min_temporal_baseline_days=min_temporal_baseline,
                                      n_secondary_scenes_per_ref=neighbors,
                                      frames=frames
                                      )
```

Then, `ifg_data` is a list of dictionaries, each corresponding to a inteferogram for a complete time series covering the specified frames covering the AOI. For example, `ifg_data[0]` returns the dictionary:
```
{'reference': ['S1A_IW_SLC__1SDV_20230302T140018_20230302T140045_047466_05B2DB_C2B5',
  'S1A_IW_SLC__1SDV_20230302T140043_20230302T140110_047466_05B2DB_F791'],
 'secondary': ['S1A_IW_SLC__1SDV_20230125T140019_20230125T140046_046941_05A132_82DF',
  'S1A_IW_SLC__1SDV_20230125T140044_20230125T140111_046941_05A132_59E7'],
 'reference_date': Timestamp('2023-03-02 00:00:00+0000', tz='UTC'),
 'secondary_date': Timestamp('2023-01-25 00:00:00+0000', tz='UTC'),
 'frame_id': 22439,
 'geometry': <POLYGON Z ((-121.034 34.871 0, -121.037 34.871 0, -120.807 36.008 0, -117.9...>}
```

## Demonstration

See the [Basic_Demo.ipynb](./notebooks/Basic_Demo.ipynb) for a more complete look at this library and using `GeoPandas` and `matplotlib` to visualize the coverage and time-series.

## Fixed Frames

Each fixed frame consists of approximately 8 bursts and at least 1 burst overlap between GUNW extents between frames along track. The frames themselves have only `.001` degree overlap. However, since ISCE2 process all bursts intersecting a given bounding box (dictated by our frames), the extents have at least 1 burst overlap and often 2 or 3 depending on the swath. The fixed frames are constratined to be within 1 degree of the high resolution land mask high resolution GSHHG land map [here](https://www.ngdc.noaa.gov/mgg/shorelines/data/gshhg/latest/). See the [repository](https://github.com/ACCESS-Cloud-Based-InSAR/s1-frame-generation) for a complete description of the methodology.

## Installation

1. Clone the repository and navigate to it
2. Install the environment: `mamba env update -f environment.yml`
3. Activate the environment: `conda activate s1-frame-enumerator`
4. Install with pip: `pip install .`

For development, use `pip install -e .` so updates are instantly seen in by the interpreter.

## Contributing

We welcome contributions to this open-source package. To do so:

1. Create an GitHub issue ticket desrcribing what changes you need (e.g. issue-1)
2. Fork this repo
3. Make your modifications in your own fork
4. Make a pull-request (PR) in this repo with the code in your fork and tag the repo owner or a relevant contributor.

We use `flake8` and associated linting packages to ensure some basic code quality (see the `environment.yml`). These will be checked for each commit in a PR.

## Support

1. Create an GitHub issue ticket desrcribing what changes you would like to see or to report a bug.
2. We will work on solving this issue (hopefully with you).