"""Export only the two tables required from an externally supplied R workspace.

The full historical workspace is intentionally not distributed: it retained a
credential inside serialized code. This optional extractor neither executes R
code nor copies its functions or environment into the repository.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import sys

extra = os.environ.get('PYREADR_EXTRA_PATH')
if extra:
    sys.path.insert(0, str(Path(extra).expanduser()))
import pyreadr

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path, help='External generic_output.RData file')
parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'data_cache')
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
objects = pyreadr.read_r(args.source, use_objects=['tests', 'accuracy_generic_no_data'])
manifest = {
    'source': 'Simulating_SPF_processing/generic_output.RData',
    'original_sha256': hashlib.sha256(args.source.read_bytes()).hexdigest(),
    'selection_reason': 'Only these tabular objects are required for the T8 archival rounding audit. Full serialized workspace omitted because it retained a credential. Values unchanged; no source R code executed.',
    'objects': {},
}
for name, frame in objects.items():
    output = args.output / ('archived_generic_' + name + '.parquet')
    frame.to_parquet(output, compression='zstd', index=True)
    manifest['objects'][name] = {
        'path': 'data_cache/' + output.name,
        'rows': len(frame),
        'columns': list(frame.columns),
        'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
    }
(args.output / 'archived_generic_objects.json').write_text(json.dumps(manifest, indent=2) + '\n')
print('Exported two table objects; no serialized functions or environments copied.')
