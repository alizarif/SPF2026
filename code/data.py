"""Read the selected analysis inputs directly from their single data archive."""
from functools import lru_cache
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=None)
def _read_frame(name):
    with ZipFile(ROOT / 'data' / 'main_data.zip') as archive:
        return pd.read_parquet(BytesIO(archive.read(name + '.parquet')))


def load_frame(name):
    """Return an independent frame; preserve source row order and dtypes."""
    return _read_frame(name).copy()


def reference():
    """Published values and table layout are comparison targets, not estimates."""
    return json.loads((ROOT / 'data' / 'published_tables.json').read_text())
