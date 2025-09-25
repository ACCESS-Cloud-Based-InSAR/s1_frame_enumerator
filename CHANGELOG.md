# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [PEP 440](https://www.python.org/dev/peps/pep-0440/)
and uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [0.0.3]

### Changed
* Updated to ruff and removed flake8


### Added
* Sentinel-1C filtering based on Calibration Date: https://sentinels.copernicus.eu/-/sentinel-1c-products-are-now-calibrated

### Fixed
* Conda Environment.yml
* Natural earth world is no longer within geopandas so linked to github url.
* Unit tests to latest micromamba.

## [0.0.2]

### Added
* Adds `pandas` to `pyproject.toml` and `environment.yml`. 
* Ensures minimum `shapely` version in `pyproject.toml`.
* Linting of packaging files
* Docstrings in `stack.py`
* Updated readme with definitions

### Fixed
* Ensure SLCs are contiguous (in addition to frames)
* Future warning related to pandas `grouper`

### Removed
* Removes min version on asf_search. 

## [0.0.1]

Initial release of s1-frame-enumerator, a package for enumerating Sentinel-1 A/B pairs
for interferograms using burst-derived frames.

### Added
* All frame instances are initialized with hemisphere property depending whether centroid is smaller than 0 deg lat.
* Minimum frame coverage ratio (computed in epsg:4326) during enumeration is .2
