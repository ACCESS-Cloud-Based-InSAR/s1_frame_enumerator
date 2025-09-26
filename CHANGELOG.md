# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [PEP 440](https://www.python.org/dev/peps/pep-0440/)
and uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [0.0.3] - 2025-09-26

### Added
* Filter for disconnected interferograms - we now take the largest connected component within a frame and utilize this to identify SLCs from reference/secondary passes
* Geometry for enumerated interferograms represent the intersection of the reference and secondary passes within the frame geometry.
* Dependency on parquet for testing

### Fixed
* Use of Natural earth within geopandas (deprecated useage) - now use contextily for plotting some background tiles for understanding location of interferograms.
* Remove ASF warnings related to geometric searches of frames - orient polygons with shapely using `orient_polygon`.
* Readme instructions for installation.

## [0.0.2]

### Added
* Adds `pandas` to `pyproject.toml` and `environment.yml`. 
* Ensures minimum `shapely` version in `pyproject.toml`.
* Linting of packaging files
* Docstrings in `stack.py`
* Updated readme with definitions
* Sentinel-1C filtering based on Calibration Date: https://sentinels.copernicus.eu/-/sentinel-1c-products-are-now-calibrated
* Python 3.13 support.

### Fixed
* Ensure SLCs are contiguous (in addition to frames)
* Future warning related to pandas `grouper`
* The syntax within Environment.yml (also added ruff)
* Natural earth world is no longer within geopandas so linked to github url.
* Unit tests now use the latest micromamba action (previous was not supported).

### Changed
* Ruff is now linter

### Removed
* Removes min version on asf_search. 
* Flake8 linting in favor of ruff


## [0.0.1]

Initial release of s1-frame-enumerator, a package for enumerating Sentinel-1 A/B pairs
for interferograms using burst-derived frames.

### Added
* All frame instances are initialized with hemisphere property depending whether centroid is smaller than 0 deg lat.
* Minimum frame coverage ratio (computed in epsg:4326) during enumeration is .2
