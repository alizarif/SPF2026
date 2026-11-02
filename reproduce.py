#!/usr/bin/env python3
"""Reproduce or verify the archived research outputs without external APIs."""
from pathlib import Path
import argparse
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
RUN = ROOT / 'replication_2026-10-31'

def execute(relative_path, *arguments):
    script = RUN / relative_path
    environment = os.environ.copy()
    environment.setdefault('MPLCONFIGDIR', str(ROOT / '.runtime' / 'matplotlib'))
    environment.setdefault('PYTHONDONTWRITEBYTECODE', '1')
    print(f'Running {relative_path}', flush=True)
    subprocess.run([sys.executable, str(script), *arguments], cwd=ROOT,
                   env=environment, check=True)

def verify():
    execute('tables_review/verify_investigation_results.py')
    execute('tables_review/verify_clean_tables_pdf.py')

def tables():
    execute('table11_investigation/investigate_ai.py')
    execute('table11_investigation/recompute_declared_method.py')
    execute('tableB14_investigation/investigate_table_b14.py')
    execute('scripts/build_annotated_tables.py', '--data-only')
    execute('tables_review/audit_rounding.py')
    execute('scripts/build_annotated_tables.py')
    verify()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--verify', action='store_true', help='Check saved numeric results and the annotated PDF (default).')
    mode.add_argument('--tables', action='store_true', help='Recompute Tables 11/B.14 and rebuild the latest annotated PDF.')
    mode.add_argument('--legacy', action='store_true', help='Rebuild the earlier full figure/table comparison using the numerical caches.')
    mode.add_argument('--rebuild-cache', action='store_true', help='Rebuild and validate the numerical caches from the included source files.')
    arguments = parser.parse_args()
    if sys.version_info < (3, 11):
        parser.error('Python 3.11 or newer is required; Python 3.11 was used for the supplied results.')
    if arguments.tables:
        tables()
    elif arguments.legacy:
        execute('scripts/run_replication.py')
    elif arguments.rebuild_cache:
        execute('scripts/build_data_cache.py')
        execute('scripts/validate_data_cache.py')
    else:
        verify()
    print('Requested workflow completed. See README.md for interpretation and limitations.')

if __name__ == '__main__':
    main()
