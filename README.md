# SPF2026

A compact replication of the **15 tables** in *Simulating the Survey of Professional Forecasters* by Hansen, Horton, Kazinnik, Puzzello, and Zarifhonarvar (June 2026 draft).

Start with the [tables report](report/tables.pdf) and [comparison summary](report/comparison.csv).

| Folder | Contents |
| --- | --- |
| `code/` | Three calculation scripts, a data reader, and the PDF builder. |
| `data/` | The main research inputs in one archive, plus published table values for comparison. |
| `report/` | The final PDF and a short table-by-table comparison. |

## Run

Use Python 3.11 and run these commands from the repository folder:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python reproduce.py
```

This recalculates every statistical table and rebuilds the report. Tables 1 and 2 contain definitions reproduced from the manuscript. No API calls or external data downloads are needed.

`main_data.zip` contains only the 17 data tables used by the calculations, stored as Parquet, and a `sources.json` file recording their origins and hashes. The code reads the archive directly. These are the selected analysis inputs, including source-level inputs for Tables 11 and B.14; the full original research archive remains available in the earlier version linked below. Published values are used only for comparison, never as estimated results.

## Reading the results

Red brackets show recalculated values that differ from the paper. Blue is reserved for verified rounding-only differences; none remain in this version. The PDF contains only table numbers, titles, and tables.

Table 11 uses consecutive-quarter nowcasts, official prior-quarter actuals, the prior human median, and HC1 standard errors; duplicate AI person-quarter forecasts are averaged. The published human panel remains unrecovered. Table B.14 uses the best individual forecast in each survey and quarter, the 2024 sample, and exact paired tests. These are verified recalculations under documented choices.

Other tables preserve the supplied calculations, including their sample, horizon, and test-definition limitations. The comparison summary explains these briefly. Matching a printed value does not validate the original method. Randomization uses 10,000 draws with seed `20261031`.

The simplified code reproduces all previously verified numerical results. The [full earlier archive](https://github.com/alizarif/SPF2026/tree/abfc19ae4404bb874ba88034d3df8bf7cd622512) retains the original files, figures, and detailed investigations. No new software or data license is added; original attribution remains applicable.
