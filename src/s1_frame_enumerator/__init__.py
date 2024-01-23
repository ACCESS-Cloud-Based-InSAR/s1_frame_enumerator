import warnings
from importlib.metadata import PackageNotFoundError, version

from .ifg_enum import enumerate_dates, enumerate_gunw_time_series
from .s1_frames import (
    S1Frame,
    frames2gdf,
    gdf2frames,
    get_global_gunw_footprints,
    get_global_s1_frames,
    get_overlapping_s1_frames,
)
from .s1_stack import filter_s1_stack_by_geometric_coverage_per_pass, get_s1_stack, query_slc_metadata_over_frame
from .s1_stack_formatter import format_results_for_sent1_stack

try:
    __version__ = version(__name__)
except PackageNotFoundError:
    __version__ = None
    warnings.warn(
        'package is not installed!\n'
        'Install in editable/develop mode via (from the top of this repo):\n'
        '   python -m pip install -e .\n',
        RuntimeWarning,
    )

__all__ = [
    'enumerate_dates',
    'enumerate_gunw_time_series',
    'filter_s1_stack_by_geometric_coverage_per_pass',
    'format_results_for_sent1_stack',
    'frames2gdf',
    'gdf2frames',
    'get_global_gunw_footprints',
    'get_global_s1_frames',
    'get_overlapping_s1_frames',
    'get_s1_stack',
    'query_slc_metadata_over_frame',
    'S1Frame',
]
