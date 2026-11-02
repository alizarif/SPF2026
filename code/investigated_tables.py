"""Verified recalculations of Tables 11 and B.14 from source-level data.

These implement the documented methods, not a claim to recover every published
estimate. Published values are never inputs to estimation. Table 11 averages
duplicate named AI forecasts and retains the source GDP vintage units. Table
B.14 selects the best individual forecast separately in each survey and quarter.
"""

from decimal import Decimal
from itertools import product

import numpy as np
import pandas as pd
from statsmodels.regression.linear_model import OLS
from statsmodels.tools.tools import add_constant

from data import load_frame


CORE_VARIABLES = ("RGDP", "CPI", "UNEMP", "TBILL")
HORIZONS = (0, 1, 2)


def quarter_numbers(frame):
    """An integer quarter index makes exact t versus t-1 matching explicit."""
    frame = frame.copy()
    frame["q"] = pd.PeriodIndex(frame["quarter"], freq="Q").astype(int)
    return frame


def result(item, row, column, value):
    return {"item": item, "row": row, "column": column,
            "replicated": float(value)}


def revision_sample(forecasts, official, variable):
    """Construct consecutive-quarter revisions and the two stated regressors."""
    lagged = forecasts.rename(columns={"forecast": "lag_forecast"}).copy()
    lagged["q"] += 1
    paired = forecasts.merge(lagged, on=["person", "q"],
                             how="inner", validate="one_to_one")
    actual = paired["q"].map(official[variable + "1"])
    consensus = (paired["q"] - 1).map(official[variable + "2"])
    paired["revision"] = paired["forecast"] - paired["lag_forecast"]
    paired["Error"] = actual - paired["lag_forecast"]
    paired["Consensus"] = paired["lag_forecast"] - consensus
    # Both specifications use the same complete-case sample, as verified.
    return paired.dropna(subset=["revision", "Error", "Consensus"])


def table11():
    """Nowcasts, strict quarterly pairs, official prior actuals, OLS/HC1."""
    ai = quarter_numbers(load_frame("t11_ai"))
    human = quarter_numbers(load_frame("t11_human"))
    official = quarter_numbers(load_frame("t11_reference")).set_index("q")
    first = pd.Period("1999Q1", freq="Q").ordinal
    last = pd.Period("2023Q4", freq="Q").ordinal
    ai = ai[ai["q"].between(first, last)
            & ai["person"].notna() & ai["person"].ne("No Name Provided")]
    human = human[human["q"].between(first, last)]
    assert len(ai) == 5308
    assert not official.index.duplicated().any()

    cells = []
    for panel in ("Human", "AI"):
        for variable in CORE_VARIABLES:
            if panel == "AI":
                # This is a declared identity rule, not evidence that conflicting
                # forecasts were averaged by the original paper's authors.
                forecasts = ai.groupby(["person", "q"], as_index=False,
                                       sort=True)[variable].mean()
                forecasts = forecasts.rename(columns={variable: "forecast"})
            else:
                forecasts = human.loc[human["variable"].eq(variable),
                                      ["person", "q", "forecast"]].copy()
            assert not forecasts.duplicated(["person", "q"]).any()
            sample = revision_sample(forecasts, official, variable)
            sample = sample.sort_values(["person", "q"])
            row = panel + " " + variable
            for model in ("Error", "Consensus"):
                fitted = OLS(sample["revision"],
                             add_constant(sample[[model]], has_constant="add")
                             ).fit(cov_type="HC1")
                values = {"coefficient": fitted.params.iloc[1],
                          "SE": fitted.bse.iloc[1], "N": fitted.nobs,
                          "R2": fitted.rsquared}
                for name, value in values.items():
                    cells.append(result("T11", row, model + " " + name, value))
                # Table 11's displayed convention is *** for p < .01.
                stars = 3 if fitted.pvalues.iloc[1] < .01 else 0
                cells.append(result("T11", row,
                                    model + " coefficient stars", stars))
    return cells


def minimum_decimal_error(values, actual):
    """Use source-value decimals to avoid binary half-cent display artifacts."""
    if not np.isfinite(actual):
        return None
    outcome = Decimal(str(actual))
    errors = [abs(Decimal(str(value)) - outcome)
              for value in values.dropna()]
    return min(errors) if errors else None


def exact_paired_test(ai_errors, human_errors):
    """Enumerate all 2**N sign assignments of paired absolute-error gaps."""
    differences = np.asarray(ai_errors, float) - np.asarray(human_errors, float)
    observed = abs(differences.sum())
    tolerance = 1e-12 * max(1, float(np.abs(differences).sum()))
    simulated = [abs(sum(sign * error for sign, error in zip(signs, differences)))
                 for signs in product((-1, 1), repeat=len(differences))]
    return sum(value >= observed - tolerance for value in simulated) / len(simulated)


def table_b14():
    """2024 origins, h=0/1/2, per-quarter minima, exact paired MAE tests."""
    ai = quarter_numbers(load_frame("b14_ai"))
    human = quarter_numbers(load_frame("b14_human"))
    actuals = quarter_numbers(load_frame("b14_actuals"))
    variables = actuals["variable"].drop_duplicates().tolist()
    labels = actuals.drop_duplicates("variable").set_index("variable")["variable_name"]
    actuals = actuals.set_index(["variable", "q"])["actual"]
    origins = pd.period_range("2024Q1", "2024Q4", freq="Q").astype(int)
    ai = ai[ai["q"].isin(origins)].copy()
    human = human[human["q"].isin(origins)]

    # Preserve the supplied current-OOS cleaning rules before selecting winners.
    ai = ai[ai["PGDP_A0"].lt(10000) & ai["person"].ne("No Name Provided")].copy()
    for horizon in HORIZONS:
        column = f"PGDP_A{horizon}"
        small = ai[column].lt(10)
        ai.loc[small, column] *= 100
    assert len(ai) == 798
    assert not ai.duplicated(["person", "q"]).any()

    cells = []
    eligible_pairs = 0
    for variable in variables:
        row = labels.loc[variable]
        for horizon in HORIZONS:
            ai_errors, human_errors = [], []
            for origin in origins:
                actual = actuals.loc[(variable, origin + horizon)]
                a = ai.loc[ai["q"].eq(origin), f"{variable}_A{horizon}"]
                h = human.loc[human["q"].eq(origin)
                              & human["variable"].eq(variable)
                              & human["horizon"].eq(horizon), "forecast"]
                ai_error = minimum_decimal_error(a, actual)
                human_error = minimum_decimal_error(h, actual)
                if ai_error is not None and human_error is not None:
                    ai_errors.append(ai_error)
                    human_errors.append(human_error)
            assert ai_errors, (variable, horizon, "no matched quarters")
            count = len(ai_errors)
            eligible_pairs += count
            ai_mae = sum(ai_errors, Decimal(0)) / Decimal(count)
            human_mae = sum(human_errors, Decimal(0)) / Decimal(count)
            p_value = exact_paired_test(ai_errors, human_errors)
            prefix = f"h{horizon} "
            for name, value in (("AI", ai_mae), ("Human", human_mae), ("p", p_value)):
                cells.append(result("TB14", row, prefix + name, value))
            stars = sum(p_value <= cutoff for cutoff in (.1, .05, .01))
            cells.append(result("TB14", row, prefix + "p stars", stars))
    assert eligible_pairs == 261
    return cells


def calculate():
    """Return {item, row, column, replicated} for numeric cells and stars."""
    return table11() + table_b14()
