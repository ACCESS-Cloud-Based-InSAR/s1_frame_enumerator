# S1_Frame_Enumerator

[![PyPI license](https://img.shields.io/pypi/l/s1_frame_enumerator.svg)](https://pypi.python.org/pypi/s1_frame_enumerator/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/s1_frame_enumerator.svg)](https://pypi.python.org/pypi/s1_frame_enumerator/)
[![PyPI version](https://img.shields.io/pypi/v/s1_frame_enumerator.svg)](https://pypi.python.org/pypi/s1_frame_enumerator/)
[![Conda version](https://img.shields.io/conda/vn/conda-forge/s1_frame_enumerator)](https://anaconda.org/conda-forge/s1_frame_enumerator)
[![Conda platforms](https://img.shields.io/conda/pn/conda-forge/s1_frame_enumerator)](https://anaconda.org/conda-forge/s1_frame_enumerator)

This library enumerates input single look complex (SLC) IDs for reference and secondary imagery to generate a time series of interferograms over an area of interest (AOI) using *fixed spatial frames*. Such SLC imagery can then be used to generate an interferometric time series. Our focus is generating ARIA S1 Geocoded Unwrapped Interferogram (ARIA-S1-GUNW), a standardized, sensor-neutral inteferometric product as described [here](https://github.com/ACCESS-Cloud-Based-InSAR/DockerizedTopsApp) using [ISCE2](https://github.com/isce-framework/isce2).

## Installation

In order to easily manage dependencies, we recommend using dedicated project environments
via [Anaconda/Miniconda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html).
or [Python virtual environments](https://docs.python.org/3/tutorial/venv.html).

`s1_frame_enumerator` can be installed into a conda environment with

```
conda install -c conda-forge s1_frame_enumerator
```

or into a virtual environment with

```
python -m pip install s1_frame_enumerator
```

Currently, python 3.11+ is supported. See development installation below.

## Background and Usage

Sentinel-1 SLC enumeration for interferometric processing is notoriously challenging despite its simple description. This is partly because ESA frame definitions are not spatially fixed in time and it is hard to ensure complete spatial coverage across date pairs. Our fixed frame approach attempts to circumvent this challenge by ensuring SLC pairs are enunumerated across fixed spatial areas. We also ensure consistent overlap (at least 1 burst) across inteferometric products to ensure interferometric products can be stitched for downstream analysis.

This library relies on [`asf-search`](https://github.com/asfadmin/Discovery-asf_search) to enumerate Sentinel-1 A/B pairs from fixed frames derived from ESA's burst [map](https://sar-mpc.eu/test-data-sets/). We describe the generation of the "fixed-frames" in this [repository](https://github.com/ACCESS-Cloud-Based-InSAR/s1-frame-generation). Using this frame map (stored a zip file within this library), we enumerate SLCs that cover contiguous collection of frames. The frames Northern and Souther boundaries are aligned with latitude lines to ensure GUNW products and the frame definitions are consistent. We have two datasets the latitude-aligned [frames](https://github.com/ACCESS-Cloud-Based-InSAR/s1-frame-enumerator/blob/58f7e62a4efd0784766da21ab7f618073fe9f347/s1_frame_enumerator/data/s1_frames_latitude_aligned.geojson.zip) and the expected GUNW product [extents](https://github.com/ACCESS-Cloud-Based-InSAR/s1-frame-enumerator/blob/58f7e62a4efd0784766da21ab7f618073fe9f347/s1_frame_enumerator/data/s1_gunw_frame_footprints.geojson.zip).

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

# Subtlties of Creating an Image Stack

This library is aimed at a very specific type of enumeration of SLCs for Geocoded Interferograms derived from *Level-1 IW SLCs with VV polarization*. However, Sentinel-1 distributes a wide variety of products not all of which are available consistently globally. As such, there are situations when using this enumeration you will have to compare the imagery retrieved against [ASFSearch](https://search.asf.alaska.edu/). That said, we are using the following search parameters found [here](https://github.com/ACCESS-Cloud-Based-InSAR/s1-frame-enumerator/blob/c3a62f1b5b28cb9237c6c4e7ec64f24f2c7de74c/s1_frame_enumerator/s1_stack.py#L17). When comparing against ASFSearch or [`asf-search`](https://github.com/asfadmin/Discovery-asf_search), make sure to use these parameters. [Here](https://search.asf.alaska.edu/#/?zoom=6.120&center=-114.036,30.084&polygon=POLYGON((-119.4707%2031.6544,-114.0643%2031.6544,-114.0643%2034.1501,-119.4707%2034.1501,-119.4707%2031.6544))&productTypes=SLC&polarizations=VV%2BVH,VV&path=64-64&resultsLoaded=true&start=2023-02-23T08:00:00Z&end=2023-02-27T07:59:59Z&granule=S1A_IW_SLC__1SDV_20230225T015011_20230225T015041_047386_05B025_10E3-SLC) is an example of some suprising behavior: there is no `VV` or `VV+VH` on this pass when S1 images Mexico, but they exist within the US continental boundaries.

Generally speaking there are two competing considerations:

1. Spatial coverage - the spatial interesection of all dates in the stack
2. Temporal coverage - the number of dates included within a time series stack

Increasing one, decreases the other and vice versa. In the `get_s1_stack` utilizing the ASF metadata, there is control over spatial coverage via coverage ratios (per pass coverage and per frame coverage) which invariably will lead to smaller spatial coverage because when a given pass covers less area, its intersection across dates will go down. When excluding given frames (e.g. because a frame is mostly over ocean say), this decreases spatial coverage but since Sentinel-1 data that we care about does not exist over the ocean, this may likely increase our temporal coverage.

Let's be more explicit about the possible/anticipated scenarios for modifying stacks in these situtations. We hope to provide more detailed notebooks or instructions later.

1. An AOI has significant water making a pass disconnected (say an AOI spanning Africa and Europe over the Mediteranean) - separate into two different AOIs over each contiguous land areas
2. A specific frame has low coverage at numerous dates being at the boundary of a product distribution boundary (e.g. US and Mexico where Sentinel-1 might switch modes) or near a coastline - remove frame at the boundary or lower per frame or per pass coverage ratios
3. To ensure higher number of dates in the stack: trouble shoot with per frame and per pass coverage ratios in `get_s1_stack`. Lowering the per frame and pass ratios permits more dates to be included, but the total time series may have a lower spatial coverage. ISCE2 requires a minimum number of bursts to do processing. We recommend that every frame have at least 25% coverage to be safe.
4. Enumerating (temporally dense) interferograms over island chains will likely just be hard particulary because Sentinel-1 will turn off and on over the ocean.

## Development Installation

1. Clone the repository and navigate to it
2. Install the environment: `mamba env update -f environment.yml`
3. Activate the environment: `conda activate s1-frame-enumerator`
4. Install with pip: `pip install -e .`

To use the notebooks, please install the kernel associated with this environment as:

```
python -m ipykernel install --user --name s1-frame-enumerator
```


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
