"""Read-only verification of exported comparison workbook and formula caches."""
from pathlib import Path
import hashlib
import json
import math

import openpyxl

RUN = Path(__file__).resolve().parents[1]
OUTPUT = RUN.parent / "outputs/replication/replication_comparison.xlsx"
summary = json.loads((RUN / "replication_comparison.json").read_text())
cells = json.loads((RUN / "cell_comparison.json").read_text())
values = openpyxl.load_workbook(OUTPUT, read_only=True, data_only=True)
formulas = openpyxl.load_workbook(OUTPUT, read_only=True, data_only=False)
assert values.sheetnames == ["Summary", "Cell audit"]
sr = list(values["Summary"].iter_rows(min_row=9, max_row=8 + len(summary), max_col=16, values_only=True))
assert [r[0] for r in sr] == [x["id"] for x in summary]
for row, item in zip(sr, summary):
    assert row[1] == item["title"]
    assert row[3] == item["status"]
    for col, key in enumerate(["point_match", "point_total", "p_rounded_match", "p_mc_compatible", "p_total", "stars_match", "stars_total"], 4):
        assert row[col] == item.get(key), (item["id"], key, row[col], item.get(key))
    for col, key in [(12, "evidence"), (13, "limitations"), (14, "reproduced_paths"), (15, "source_scripts")]:
        expected = item.get(key)
        if isinstance(expected, list):
            expected = "; ".join(str(x) for x in expected)
        assert (row[col] or "") == (expected or ""), (item["id"], key)

ar = list(values["Cell audit"].iter_rows(min_row=9, max_row=8 + len(cells), max_col=10, values_only=True))
fr = list(formulas["Cell audit"].iter_rows(min_row=9, max_row=8 + len(cells), max_col=10, values_only=True))
for row, formula, item in zip(ar, fr, cells):
    assert row[0:3] == (item["item"], item["row"], item["column"])
    assert row[3] == item["original"] and row[4] == item["replicated"]
    difference = abs(item["replicated"] - item["original"])
    assert math.isclose(row[5], difference, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(row[5], item["absolute_difference"], rel_tol=1e-12, abs_tol=1e-12)
    assert row[7] == item["rounded_match"]
    assert row[8] == item["tolerance"]
    assert row[9] == (difference <= item["tolerance"]) == item["within_tolerance"]
    assert formula[5].startswith("=IF(") and formula[9].startswith("=IF(")

errors = []
for sheet in values:
    for row in sheet.iter_rows():
        errors.extend(f"{sheet.title}!{c.coordinate}: {c.value}" for c in row if c.data_type == "e")
assert not errors, errors
def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
result = {
    "workbook": str(OUTPUT),
    "summary_rows_checked": len(sr),
    "audit_rows_checked": len(ar),
    "recalculated_formula_cells_checked": 2 * len(ar),
    "formula_errors": errors,
    "all_source_values_and_flags_match": True,
    "sha256": {str(p.relative_to(RUN.parent)): digest(p) for p in [OUTPUT, RUN / "replication_comparison.json", RUN / "cell_comparison.json"]},
}
(RUN / "workbook_qa/saved_workbook_validation.json").write_text(json.dumps(result, indent=2))
print(json.dumps({k: v for k, v in result.items() if k != "sha256"}, indent=2))
