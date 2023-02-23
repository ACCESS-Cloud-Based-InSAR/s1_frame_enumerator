# S1-Frame-Enumerator

## Background

This library enumerates input single look complex (SLC) IDs for reference and secondary imagery to generate a time series of interferograms over an area of interest (AOI). Such SLC imagery can then be used to generate an interforgric time series including those from an ARIA S1 Geocoded Unwrapped Interferogram (GUNW), a standardized, sensor-neutral inteferometric product as described [here](https://github.com/ACCESS-Cloud-Based-InSAR/DockerizedTopsApp).

Sentinel-1 SLC enumeration for interferometric processing is notoriously challenging despite its simple description. This is partly because ESA frame definitions are not spatially fixed in time and it is hard to ensure complete spatial coverage across date pairs. Our fixed frame approach attempts to circumvent this challenge by ensuring SLC pairs are enunumerated across fixed spatial areas. We also ensure consistent overlap (2 bursts) across inteferometric products to ensure interferometric products can be stitched for downstream analysis.

This library relies on [`asf-search`](https://github.com/asfadmin/Discovery-asf_search) to enumerate Sentinel-1 A/B pairs from fixed frames derived from ESA's burst [map](https://sar-mpc.eu/test-data-sets/). We describe the generation of the "fixed-frames" in this [repository](https://github.com/ACCESS-Cloud-Based-InSAR/s1-frame-generation). Using this frame map (stored a gzip file within this library), we enumerate SLCs that cover contiguous collection of frames.

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
ifg_data = enumerate_gunw_time_series(frames,
                                      df_stack,
                                      min_temporal_baseline,
                                      n_secondary_scenes_per_ref=neighbors,
                                      )
```

Then, `ifg_data` is a list of dictionaries, each corresponding to a inteferogram for a complete time series covering the specified frames covering the AOI. For example, `ifg_data[0]` returns the dictionary:
```
{'reference': ['S1A_IW_SLC__1SDV_20230218T140018_20230218T140045_047291_05ACF0_4503',
               'S1A_IW_SLC__1SDV_20230218T140043_20230218T140110_047291_05ACF0_2591'],
 'secondary': ['S1A_IW_SLC__1SDV_20230113T140019_20230113T140046_046766_059B44_A9C1',
               'S1A_IW_SLC__1SDV_20230113T140044_20230113T140111_046766_059B44_FBB8'],
 'reference_date': datetime.date(2023, 2, 18),
 'secondary_date': datetime.date(2023, 1, 13),
 'frame_id': 22439,
 'geometry': <POLYGON Z ((-121.034 34.871 0, -121.037 34.871 0, -120.807 36.008 0, -117.9...>}
```

## Demonstration

See the [Basic_Demo.ipynb](./notebooks/Basic_Demo.ipynb) for a more complete look at this library and using `GeoPandas` and `matplotlib` to visualize the coverage and time-series.

## Fixed Frames

Each fixed frame consists of 10 bursts and ensures a 2 burst overlap between frames along track. We only consider frames within 1 degree of the high resolution land mask high resolution GSHHG land map [here](https://www.ngdc.noaa.gov/mgg/shorelines/data/gshhg/latest/). See the [repository](https://github.com/ACCESS-Cloud-Based-InSAR/s1-frame-generation) for a complete description.

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