#!/usr/bin/env python3
"""Rebuild tables, response comparisons, or the distribution review plots."""
import argparse
import csv
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'code'))
sys.dont_write_bytecode = True
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.runtime' / 'matplotlib'))

from additional_tables import calculate as additional_tables
from core_tables import calculate as core_tables
from investigated_tables import calculate as investigated_tables
from report import build_tables, render


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--responses', action='store_true',
                      help='Build distribution tests and AI/human median and SD plots.')
    mode.add_argument('--distributions', action='store_true',
                      help='Build the six original distribution pages with common scales.')
    args = parser.parse_args()
    if args.distributions:
        from distribution_plots import run_distribution_plots
        return run_distribution_plots()
    if args.responses:
        from response_analysis import run_response_analysis
        return run_response_analysis()
    print('Calculating all statistical tables from the main data...', flush=True)
    cells = core_tables() + additional_tables() + investigated_tables()
    keys = [(cell['item'], cell['row'], cell['column']) for cell in cells]
    if len(set(keys)) != len(keys):
        raise ValueError('Duplicate calculated cells')
    destination = ROOT / 'report'
    destination.mkdir(exist_ok=True)
    tables = build_tables(cells)
    summary = render(tables, destination / 'tables.pdf')
    fields = ['table', 'title', 'numeric_cells', 'matching_cells', 'different_cells',
              'rounding_only', 'header_corrections', 'interpretation']
    with (destination / 'comparison.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for item, table in tables.items():
            numeric = [cell for row in table['rows'] for cell in row.get('cells', [])
                       if cell['kind'] == 'numeric']
            differences = sum(cell['mismatch'] for cell in numeric)
            writer.writerow(dict(table=item, title=table['title'], numeric_cells=len(numeric),
                matching_cells=len(numeric) - differences, different_cells=differences,
                rounding_only=sum(cell['annotation_color'] == 'blue' for cell in numeric),
                header_corrections=sum(bool(group.get('correction')) for group in table['column_groups']),
                interpretation=table['calculation_note']))
    print(f"Rebuilt {summary['pages']} tables and checked {summary['numeric_cells_rendered']:,} numeric cells.")
    print('Outputs: report/tables.pdf and report/comparison.csv', flush=True)
    return summary


if __name__ == '__main__':
    main()
