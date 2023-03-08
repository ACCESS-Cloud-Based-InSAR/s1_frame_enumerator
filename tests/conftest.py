import json
from pathlib import Path

import pytest


@pytest.fixture(scope='session')
def test_data_dir():
    data_dir = Path(__file__).resolve().parent / 'data'
    return data_dir


@pytest.fixture(scope='session')
def asf_results_from_query_by_frame():
    data_dir = Path(__file__).resolve().parent / 'data'

    def query_asf_by_frame(frame_id):
        return json.load(open(data_dir / f'frame_{frame_id}_asf_results.json'))

    return query_asf_by_frame
