"""Rebuild the distribution-test file and AI/human correlation figures.

Run from the repository root: python reproduce.py --responses
See the first page of report/distribution_tests.pdf for methods and limitations.
"""
from __future__ import annotations
import os
from pathlib import Path
import sys

REPOSITORY = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
os.environ.setdefault('MPLCONFIGDIR', str(REPOSITORY / '.runtime' / 'matplotlib'))

"""Quarterly AI/human forecast comparisons for 1999Q1--2023Q4.

Raw official median series are kept for consistency with the median scatter.
Means and sample SDs (ddof=1) use the individual forecasts and retain duplicate
AI response rows. Human median and human individual-median differences are
recorded, not silently substituted. A zero cross-sectional SD is valid data.

Models include an intercept. HAC uses Bartlett weights, a finite-sample
correction, and normal/chi-square inference (use_t=False), at lags 4 and 8.
Holm corrections cover 24 joint intercept/slope tests and, separately, 36 paired
average-gap tests. These test calibration and average moment gaps, not equality
of the complete forecast distributions. Correlation is also not equality.

CPI, unemployment and Treasury-bill forecasts retain source percentage units;
their SDs are in percentage points. RGDP retains the source GDP level units and
survey-vintage base-year changes. It is not GDP growth or a uniformly rebased
series. Trends, vintage changes and influential quarters affect interpretation.

Caller must put the repository code directory on sys.path so `data` is importable.
No source data or output files are modified by compute_response_statistics().
"""

import numpy as np
import pandas as pd
from scipy.stats import chi2, norm, spearmanr
from statsmodels.regression.linear_model import OLS
from statsmodels.tools.tools import add_constant

from data import load_frame


VARIABLES = ("CPI", "UNEMP", "TBILL", "RGDP")
HORIZONS = (0, 1, 4)
DATES = pd.date_range("1999-01-01", "2023-10-01", freq="QS")
Z95 = norm.ppf(0.975)


def _hac(model, lag):
    return model.fit(
        cov_type="HAC",
        cov_kwds={"maxlags": lag, "kernel": "bartlett", "use_correction": True},
        use_t=False,
    )


def _holm(log_pvalues):
    """Holm adjustment in log space preserves very small p-values."""
    values = np.asarray(log_pvalues, dtype=float)
    assert np.isfinite(values).all()
    order = np.argsort(values, kind="stable")
    adjusted = np.maximum.accumulate(values[order] + np.log(len(values) - np.arange(len(values))))
    adjusted = np.minimum(adjusted, 0)
    output = np.empty_like(values)
    output[order] = adjusted
    return np.exp(output), output


def _joint_equality(fitted):
    difference = np.asarray(fitted.params, float) - np.array([0.0, 1.0])
    covariance = np.asarray(fitted.cov_params(), float)
    statistic = float(difference @ np.linalg.solve(covariance, difference))
    assert statistic >= 0 and np.linalg.eigvalsh(covariance).min() > 0
    # With two restrictions, chi-square(2) has the exact log tail -W/2.
    return statistic, float(chi2.sf(statistic, 2)), -statistic / 2


def _individual_summary(values, value_column):
    grouped = values.groupby("date_q", sort=True, observed=True)[value_column]
    return grouped.agg(mean="mean", sd="std", n="count", individual_median="median")


def _make_points():
    aggregate = load_frame("baseline_ts")
    ai = load_frame("baseline_wide")
    human = load_frame("baseline_microdata")
    for frame in (aggregate, ai, human):
        frame["date_q"] = pd.to_datetime(frame["date_q"])
    aggregate["id"] = aggregate["id"].astype(str)
    human["id"] = human["id"].astype(str)
    blocks = []
    for variable in VARIABLES:
        for horizon in HORIZONS:
            mask = aggregate["variable"].eq(variable) & aggregate["id"].eq(str(horizon))
            selected = aggregate.loc[mask & aggregate["type"].isin(["AI", "Human"])]
            assert not selected.duplicated(["date_q", "type"]).any()
            medians = selected.pivot(index="date_q", columns="type", values="median")
            medians = medians.reindex(DATES)
            human_rows = human.loc[human["variable"].eq(variable)
                                   & human["id"].eq(str(horizon))]
            summaries = {
                "AI": _individual_summary(ai, f"{variable}_A{horizon}"),
                "Human": _individual_summary(human_rows, "value"),
            }
            point = pd.DataFrame(index=DATES)
            for survey in ("AI", "Human"):
                point[survey + "_median"] = medians[survey]
                for field in ("mean", "sd", "n", "individual_median"):
                    point[survey + "_" + field] = summaries[survey][field].reindex(DATES)
                point[survey + "_n"] = point[survey + "_n"].astype(int)
            assert point.notna().all().all()
            assert np.isfinite(point.to_numpy()).all()
            assert point[["AI_n", "Human_n"]].min().min() >= 2
            assert point[["AI_sd", "Human_sd"]].min().min() >= 0
            np.testing.assert_allclose(point["AI_median"], point["AI_individual_median"],
                                       rtol=0, atol=1e-9)
            point["Human_median_minus_individual"] = (
                point["Human_median"] - point["Human_individual_median"]
            )
            point["variable"] = variable
            point["horizon"] = horizon
            point.index.name = "date_q"
            blocks.append(point.reset_index())
    result = pd.concat(blocks, ignore_index=True)
    assert len(result) == 1200
    assert not result.duplicated(["variable", "horizon", "date_q"]).any()
    for _, group in result.groupby(["variable", "horizon"], sort=False):
        assert pd.DatetimeIndex(group["date_q"]).equals(DATES)
        assert np.diff(group["date_q"].dt.to_period("Q").astype(int)).tolist() == [1] * 99
    return result


def compute_response_statistics():
    """Return points (1200 rows), correlations (24), and paired gap tests (36).

    alpha/beta model AI = alpha + beta * Human. cov_00/cov_01/cov_11
    are the corrected HAC4 coefficient covariance entries for normal pointwise
    fitted-mean confidence bands. Gap sign is AI minus Human. Holm families are
    the 24 joint tests and the 36 gap tests, not separate variable-by-variable
    families. Float p=0 means numerical underflow; the companion log p is finite.
    """
    points = _make_points()
    correlations, gaps = [], []
    for (variable, horizon), group in points.groupby(["variable", "horizon"], sort=False):
        group = group.sort_values("date_q")
        zero_counts = {
            survey + "_zero_sd_quarters": int(np.isclose(group[survey + "_sd"], 0,
                                                         atol=1e-12, rtol=0).sum())
            for survey in ("AI", "Human")
        }
        for statistic in ("median", "sd"):
            x = group["Human_" + statistic].to_numpy()
            y = group["AI_" + statistic].to_numpy()
            model = OLS(y, add_constant(x, has_constant="add"))
            hac4, hac8 = _hac(model, 4), _hac(model, 8)
            alpha, beta = hac4.params
            alpha_se, beta_se = hac4.bse
            covariance = np.asarray(hac4.cov_params())
            w4, p4, lp4 = _joint_equality(hac4)
            w8, p8, lp8 = _joint_equality(hac8)
            correlations.append({
                "variable": variable, "horizon": horizon, "statistic": statistic,
                "N": len(group), "pearson_r": np.corrcoef(x, y)[0, 1],
                "spearman_rho": spearmanr(x, y).statistic,
                "first_difference_r": np.corrcoef(np.diff(x), np.diff(y))[0, 1],
                "first_difference_N": len(group) - 1,
                "alpha": alpha, "beta": beta,
                "alpha_se_hac4": alpha_se, "beta_se_hac4": beta_se,
                "alpha_hac4_ci_low": alpha - Z95 * alpha_se,
                "alpha_hac4_ci_high": alpha + Z95 * alpha_se,
                "beta_hac4_ci_low": beta - Z95 * beta_se,
                "beta_hac4_ci_high": beta + Z95 * beta_se,
                "cov_00": covariance[0, 0], "cov_01": covariance[0, 1],
                "cov_11": covariance[1, 1],
                "joint_wald_hac4": w4, "joint_p_hac4": p4,
                "joint_log_p_hac4": lp4, "joint_wald_hac8": w8,
                "joint_p_hac8": p8, "joint_log_p_hac8": lp8,
                "covariance": "HAC Bartlett corrected", "use_t": False,
                **zero_counts,
            })

        for statistic in ("mean", "median", "sd"):
            x = group["Human_" + statistic].to_numpy()
            y = group["AI_" + statistic].to_numpy()
            difference = y - x
            model = OLS(difference, np.ones((len(group), 1)))
            hac4, hac8 = _hac(model, 4), _hac(model, 8)
            estimate, se4, se8 = hac4.params[0], hac4.bse[0], hac8.bse[0]
            z4, z8 = estimate / se4, estimate / se8
            logp4 = np.log(2) + norm.logsf(abs(z4))
            logp8 = np.log(2) + norm.logsf(abs(z8))
            gaps.append({
                "variable": variable, "horizon": horizon, "statistic": statistic,
                "N": len(group), "AI_average": y.mean(), "Human_average": x.mean(),
                "average_gap": estimate, "gap_se_hac4": se4,
                "gap_hac4_ci_low": estimate - Z95 * se4,
                "gap_hac4_ci_high": estimate + Z95 * se4,
                "gap_z_hac4": z4, "gap_p_hac4": float(np.exp(logp4)),
                "gap_log_p_hac4": logp4, "gap_se_hac8": se8,
                "gap_p_hac8": float(np.exp(logp8)), "gap_log_p_hac8": logp8,
                "covariance": "HAC Bartlett corrected", "use_t": False,
            })
    correlations = pd.DataFrame(correlations)
    gaps = pd.DataFrame(gaps)
    assert len(correlations) == 24 and len(gaps) == 36
    correlations["joint_p_holm24"], correlations["joint_log_p_holm24"] = _holm(
        correlations["joint_log_p_hac4"])
    gaps["gap_p_holm36"], gaps["gap_log_p_holm36"] = _holm(gaps["gap_log_p_hac4"])
    assert correlations["N"].eq(100).all() and gaps["N"].eq(100).all()
    points = points.rename(columns={
        "AI_median": "ai_median", "Human_median": "human_median",
        "AI_mean": "ai_mean", "Human_mean": "human_mean",
        "AI_sd": "ai_sd", "Human_sd": "human_sd",
        "AI_n": "n_ai", "Human_n": "n_human",
        "AI_individual_median": "ai_individual_median",
        "Human_individual_median": "human_individual_median",
        "Human_median_minus_individual": "human_median_minus_individual",
    })
    correlations = correlations.rename(columns={
        "N": "n_quarters", "alpha": "intercept", "beta": "slope",
        "alpha_se_hac4": "intercept_se_hac4", "beta_se_hac4": "slope_se_hac4",
        "alpha_hac4_ci_low": "intercept_hac4_ci_low",
        "alpha_hac4_ci_high": "intercept_hac4_ci_high",
        "beta_hac4_ci_low": "slope_hac4_ci_low",
        "beta_hac4_ci_high": "slope_hac4_ci_high",
        "joint_p_hac4": "hac4_joint_p", "joint_log_p_hac4": "hac4_joint_log_p",
        "joint_p_hac8": "hac8_joint_p", "joint_log_p_hac8": "hac8_joint_log_p",
        "joint_p_holm24": "hac4_joint_p_holm24",
        "joint_log_p_holm24": "hac4_joint_log_p_holm24",
        "AI_zero_sd_quarters": "ai_zero_sd_quarters",
        "Human_zero_sd_quarters": "human_zero_sd_quarters",
    })
    gaps = gaps.rename(columns={"N": "n_quarters", "AI_average": "ai_average",
                                "Human_average": "human_average"})
    return points, correlations, gaps


"""Render the copied historical moment tables, optionally beside fresh tests.

This module copies archived strings; it does not recompute historical estimates
or infer missing historical p-values. Importing it creates no output. The source strings are preserved for documentary comparison.
"""

import csv
import math
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

MOMENTS = ("Median", "P25", "P75", "Mean", "SD", "Skewness", "Kurtosis")
HORIZONS = (0, 1, 4)
PAGE = landscape(A4)
MARGIN = 32
WIDTH = PAGE[0] - 2 * MARGIN
INK = colors.HexColor("#172B3A")
GRAY = colors.HexColor("#53606B")
LINE = colors.HexColor("#D7DEE4")
METHOD_SOURCE = "Simulating_SPF_processing/functions/tab_rand_test_moments.R"
HORIZON_LABELS = {
    0: "Current quarter (h = 0)",
    1: "One quarter ahead (h = 1)",
    4: "Four quarters ahead (h = 4)",
}


def _paragraph(text, size=8.5, leading=11, color=INK):
    return Paragraph(text, ParagraphStyle(
        "archive", fontName="Helvetica", fontSize=size, leading=leading,
        textColor=color, alignment=TA_LEFT, spaceAfter=0,
    ))


def _draw_paragraph(pdf, text, y, size=8.5, leading=11, width=WIDTH):
    item = _paragraph(text, size, leading)
    _, height = item.wrap(width, PAGE[1])
    item.drawOn(pdf, MARGIN, y - height)
    return y - height


def _load_archive(path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 69:
        raise ValueError("Expected exactly 69 archived rows")
    seen = set()
    for row in rows:
        key = (row["variable"], int(row["horizon"]))
        if key in seen or key[1] not in HORIZONS:
            raise ValueError(f"Invalid or duplicate archived row: {key}")
        seen.add(key)
        for moment in MOMENTS:
            if not re.fullmatch(r"-?\d+\.\d{2}\*{0,3}", row[moment]):
                raise ValueError(f"Invalid printed string: {key} {moment}")
        if not re.fullmatch(r"[0-9a-f]{64}", row["source_sha256"]):
            raise ValueError("Missing source SHA-256")
    for horizon in HORIZONS:
        if sum(int(row["horizon"]) == horizon for row in rows) != 23:
            raise ValueError("Expected 23 variables per horizon")
    order = [r["variable"] for r in rows if int(r["horizon"]) == 0]
    if any([r["variable"] for r in rows if int(r["horizon"]) == h] != order
           for h in HORIZONS):
        raise ValueError("Archived variable order differs across horizons")
    return rows


def _base_table_style(font_size=9):
    return TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF0F4")),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, 0), 0.7, INK),
        ("LINEBELOW", (0, -1), (-1, -1), 0.7, INK),
    ])


def _archived_table(rows, horizon):
    selected = [row for row in rows if int(row["horizon"]) == horizon]
    data = [["Variable", *MOMENTS]]
    data.extend([[row["variable_name"], *[row[m] for m in MOMENTS]]
                 for row in selected])
    first_width = 217
    table = Table(data, colWidths=[first_width] + [(WIDTH-first_width)/7]*7,
                  rowHeights=[25] + [18]*23, repeatRows=1)
    style = _base_table_style(9)
    for index in (12, 20):
        style.add("LINEABOVE", (0, index), (-1, index), 0.6, LINE)
    table.setStyle(style)
    return table


def _fresh_rows(gap_tests):
    if isinstance(gap_tests, (str, Path)):
        with Path(gap_tests).open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    elif hasattr(gap_tests, "to_dict"):
        rows = gap_tests.to_dict("records")
    else:
        rows = list(gap_tests)
    lookup = {(r["variable"], int(r["horizon"]), r["statistic"]): r for r in rows}
    if len(lookup) != 36:
        raise ValueError("Expected 36 fresh mean/median/SD tests")
    data = [["Variable", "h", "Mean gap", "Adj. p", "Median gap", "Adj. p", "SD gap", "Adj. p"]]
    for variable in ("CPI", "UNEMP", "TBILL", "RGDP"):
        for horizon in HORIZONS:
            row = [variable, str(horizon)]
            for statistic in ("mean", "median", "sd"):
                value = lookup[(variable, horizon, statistic)]
                gap = float(value["average_gap"])
                p = float(value["gap_p_holm36"])
                if int(value["n_quarters"]) != 100 or not math.isfinite(gap) or not 0 <= p <= 1:
                    raise ValueError("Invalid fresh test result")
                row += [f"{gap:.3f}", "<0.001" if p < 0.001 else f"{p:.3f}"]
            data.append(row)
    return data


def _fresh_table(gap_tests):
    data = _fresh_rows(gap_tests)
    table = Table(data, colWidths=[81, 30]+[(WIDTH-111)/6]*6,
                  rowHeights=[21]+[15.5]*12)
    style = _base_table_style(8.5)
    for index in (4, 7, 10):
        style.add("LINEABOVE", (0, index), (-1, index), 0.5, LINE)
    table.setStyle(style)
    return table


def render_archived_tests(csv_path, output_path, gap_tests=None):
    """Write four pages: methods/current tests, then h=0/1/4 archive tables.

    gap_tests may be a CSV path, a DataFrame, or a list of 36 dictionaries with
    variable, horizon, statistic, n_quarters, average_gap, and gap_p_holm36.
    It is only displayed; this function performs no statistical estimation.
    """
    rows = _load_archive(csv_path)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(output), pagesize=PAGE, invariant=1)
    pdf.setTitle("AI and human response comparisons: current tests and archived results")
    pdf.setAuthor("SPF replication")
    y = PAGE[1]-MARGIN
    heading = "Quarterly AI-human comparisons" if gap_tests is not None else "ARCHIVED ORIGINAL RESULTS"
    y = _draw_paragraph(pdf, f"<b>{heading}</b>", y, 19, 23)-8
    if gap_tests is not None:
        y = _draw_paragraph(pdf, "<b>Fresh tests of the average quarterly gap, AI minus human</b> | 100 quarters, 1999Q1-2023Q4", y, 9, 12)-6
        table = _fresh_table(gap_tests)
        _, height = table.wrap(WIDTH, PAGE[1])
        table.drawOn(pdf, MARGIN, y-height)
        y -= height+8
        y = _draw_paragraph(pdf,
            "Each gap averages the 100 differences between the AI and human quarterly mean, median, or sample SD. "
            "Adjusted p-values use a two-sided normal HAC test (Bartlett weights, 4 lags, finite-sample correction), "
            "with Holm adjustment across all 36 tests. These test average moment gaps, not equality of entire distributions. "
            "Gaps use each variable's native units: percentage points for CPI, UNEMP and TBILL; billions of chained dollars for RGDP.",
            y, 8, 10)-10
    else:
        y = _draw_paragraph(pdf, "AI minus human pooled distributional moments | 23 variables | horizons 0, 1 and 4", y, 11, 14)-22
    y = _draw_paragraph(pdf, "<b>ARCHIVED ORIGINAL RESULTS: pages 2-4</b>", y, 11, 14)-5
    y = _draw_paragraph(pdf,
        "The following tables reproduce all 483 saved moment differences and significance markers exactly as printed. "
        "<b>The historical input version is unresolved; these are not fresh validated tests.</b> "
        "The supplied original code pools rows across quarters. Its many-to-many availability join duplicates AI rows, "
        "altering their weights. In each of 1,000 simulations it independently assigns every pooled row an AI or human label "
        "with replacement; group sizes can change and quarter/person dependence is not preserved.", y, 8, 10)-6
    y = _draw_paragraph(pdf,
        "Archived stars: *** p &lt;= 0.01; ** p &lt;= 0.05; * p &lt;= 0.10. Exact p-values are unavailable in the saved tables. "
        "No stars means the reported historical test was not significant at 10%. Printed negative zeros and rounded zeros "
        "with stars are preserved. Median, percentile, mean and SD differences use native variable units; skewness and "
        "excess-kurtosis differences are dimensionless. Source method: "+escape(METHOD_SOURCE)+".", y, 8, 10)-8
    y = _draw_paragraph(pdf,
        "<b>How to read the correlation plots and files</b><br/>"
        "Medians use the untrimmed source series (the official human SPF median); SDs are recomputed from individual "
        "responses with the sample denominator n-1. Zero SD quarters and duplicate AI response rows are retained. "
        "The solid line is OLS AI on human; the band is a pointwise 95% HAC(4) interval. The equality p-value tests "
        "intercept = 0 and slope = 1 jointly, using a chi-square reference. Correlations are descriptive, not equality tests. "
        "The CSVs include HAC(8) sensitivity, Holm adjustments, and first-difference correlations. Numerical p=0 in the "
        "correlation CSV denotes underflow; the finite log-p column retains its magnitude. RGDP uses changing survey-vintage "
        "base years; shared trends, vintage differences and influential observations affect interpretation. "
        "Current-data GDP slopes differ from the supplied example image. Source filenames and hashes are in the archival CSV.",
        y, 8, 10)
    if y < MARGIN:
        raise ValueError(f"First-page content exceeds the page: bottom={y}")
    pdf.showPage()
    for page, horizon in enumerate(HORIZONS, start=2):
        y = PAGE[1]-MARGIN
        y = _draw_paragraph(pdf, "<b>ARCHIVED ORIGINAL RESULTS</b>", y, 15, 19)-5
        y = _draw_paragraph(pdf, HORIZON_LABELS[horizon]+" | AI minus human pooled moment differences", y, 10, 13)-13
        table = _archived_table(rows, horizon)
        _, height = table.wrap(WIDTH, PAGE[1])
        table.drawOn(pdf, MARGIN, y-height)
        y -= height+12
        y = _draw_paragraph(pdf,
            "*** p &lt;= 0.01; ** p &lt;= 0.05; * p &lt;= 0.10. Exact p-values unavailable. "
            "Historical input version unresolved; copied original results, not newly validated tests.", y, 7.7, 10)
        if y < MARGIN:
            raise ValueError(f"Archived table exceeds page {page}: bottom={y}")
        pdf.showPage()
    pdf.save()
    return {"path": str(output), "pages": 4, "archived_rows": 69,
            "archived_printed_values": 483, "fresh_tests": 36 if gap_tests is not None else 0}


def render_correlation_plots(points, correlations, destination):
    """Two 4-by-3 scatter grids with equal axes, HAC bands and equality tests."""
    from pathlib import Path
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.ticker import MaxNLocator
    import numpy as np

    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    labels = {'CPI': 'CPI inflation', 'UNEMP': 'Unemployment',
              'TBILL': '3-month Treasury bill', 'RGDP': 'Real GDP level'}
    horizons = {0: 'nowcast', 1: 't+1', 4: 't+4'}
    style = {'font.family': 'DejaVu Serif', 'font.size': 11,
             'axes.titlesize': 13, 'axes.labelsize': 11,
             'axes.spines.right': False, 'axes.spines.top': False,
             'axes.linewidth': .9, 'pdf.fonttype': 3, 'ps.fonttype': 42,
             'axes.axisbelow': True, 'savefig.facecolor': 'white'}

    def probability(value):
        return '<0.001' if value < .001 else f'= {value:.3f}'

    pdf_path = destination / 'ai_human_correlations.pdf'
    with plt.rc_context(style), PdfPages(pdf_path) as pdf:
        for statistic, display_name in [('median', 'median'), ('sd', 'standard deviation')]:
            figure, axes = plt.subplots(4, 3, figsize=(15, 19.5))
            figure.subplots_adjust(left=.065, right=.985, bottom=.04, top=.928,
                                   wspace=.29, hspace=.38)
            figure.suptitle(f'AI {display_name} versus human {display_name}',
                           y=.985, fontsize=23)
            figure.text(.5, .964, '1999Q1-2023Q4 | 100 matched quarters per panel',
                        ha='center', fontsize=11, color='#52616b')
            figure.text(.5, .950,
                        'OLS fit and 95% HAC(4) band | Dashed: equality | Equality p: joint intercept = 0, slope = 1',
                        ha='center', fontsize=9.5, color='#52616b')
            for row, variable in enumerate(['CPI', 'UNEMP', 'TBILL', 'RGDP']):
                for column, horizon in enumerate([0, 1, 4]):
                    axis = axes[row, column]
                    sample = points[(points.variable == variable) & (points.horizon == horizon)]
                    result = correlations[(correlations.variable == variable)
                                          & (correlations.horizon == horizon)
                                          & (correlations.statistic == statistic)].iloc[0]
                    x = sample[f'human_{statistic}'].to_numpy(float)
                    y = sample[f'ai_{statistic}'].to_numpy(float)
                    lower, upper = min(x.min(), y.min()), max(x.max(), y.max())
                    padding = .06 * max(upper - lower, 1e-8)
                    limits = (lower - padding, upper + padding)
                    grid = np.linspace(x.min(), x.max(), 160)
                    fitted = result['intercept'] + result['slope'] * grid
                    variance = result['cov_00'] + 2 * grid * result['cov_01'] + grid ** 2 * result['cov_11']
                    half_width = 1.959963984540054 * np.sqrt(np.maximum(variance, 0))
                    axis.grid(color='#e7e9ec', linewidth=.7)
                    axis.plot(limits, limits, '--', color='#919ba3', linewidth=1.4, zorder=1)
                    axis.fill_between(grid, fitted - half_width, fitted + half_width,
                                      color='#507e99', alpha=.17, linewidth=0, zorder=2)
                    axis.scatter(x, y, s=24, color='#44748d', alpha=.73,
                                 edgecolors='white', linewidths=.2, zorder=3)
                    axis.plot(grid, fitted, color='#153f59', linewidth=2.0, zorder=4)
                    axis.set(xlim=limits, ylim=limits, xlabel=f'Human {display_name}',
                             ylabel=f'AI {display_name}',
                             title=f'{labels[variable]} · {horizons[horizon]}')
                    axis.set_aspect('equal', adjustable='box')
                    axis.xaxis.set_major_locator(MaxNLocator(nbins=5))
                    axis.yaxis.set_major_locator(MaxNLocator(nbins=5))
                    axis.tick_params(labelsize=10)
                    annotation = (f"r = {result['pearson_r']:.2f}   ρ = {result['spearman_rho']:.2f}\n"
                                  f"β = {result['slope']:.2f}   N = {int(result['n_quarters'])}\n"
                                  f"Equality p {probability(result['hac4_joint_p'])}")
                    # GDP SD has a genuine upper-left outlier; keep the label clear of it.
                    right = statistic == 'sd' and variable == 'RGDP'
                    axis.text(.97 if right else .035, .96, annotation,
                              transform=axis.transAxes, ha='right' if right else 'left',
                              va='top', fontsize=9.5, linespacing=1.25,
                              bbox=dict(facecolor='white', edgecolor='none', alpha=.88, pad=3))
            pdf.savefig(figure)
            figure.savefig(destination / f'ai_human_{statistic}.png', dpi=170)
            plt.close(figure)
    return pdf_path


def run_response_analysis():
    """Recalculate current tests and render current plots plus archived tables."""
    output = REPOSITORY / 'report'
    output.mkdir(exist_ok=True)
    points, correlations, gap_tests = compute_response_statistics()
    correlations.to_csv(output / 'correlation_statistics.csv', index=False, lineterminator='\n')
    gap_tests.to_csv(output / 'quarterly_distribution_tests.csv', index=False, lineterminator='\n')
    render_correlation_plots(points, correlations, output)
    archive = render_archived_tests(REPOSITORY / 'data' / 'original_distribution_tests.csv',
                                    output / 'distribution_tests.pdf', gap_tests)
    print('Created median and SD plots: 4 variables x 3 horizons, 100 quarters per panel.')
    print('Calculated 24 correlation/equality results and 36 quarterly moment-gap tests.')
    print('Included 483 archived moment differences, clearly labeled as historical results.')
    return points, correlations, gap_tests, archive


if __name__ == '__main__':
    run_response_analysis()
