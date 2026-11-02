"""Recalculate Tables 9, 10, 12 and D.15 from the main analysis data.

These retain the supplied research definitions, including overlapping 2023
observations in Table 10 and the horizon-1 DM test in every D.15 column.
"""
import re

import numpy as np
import pandas as pd
from scipy.stats import t as student_t
from statsmodels.regression.linear_model import OLS
from statsmodels.tools.tools import add_constant

from data import load_frame


def stars(p, cutoffs=(0.01, 0.05, 0.10)):
    return 3 if p < cutoffs[0] else 2 if p < cutoffs[1] else 1 if p < cutoffs[2] else 0


def expanding_ar1(series):
    """Predict from past observations, starting with two usable lagged pairs."""
    y = series.to_numpy(dtype=float)
    predictions = np.full(len(y), np.nan)
    for i in range(1, len(y)):
        yy, xx = y[1:i], y[:i - 1]
        valid = np.isfinite(xx) & np.isfinite(yy)
        if valid.sum() < 2 or not np.isfinite(y[i - 1]) or np.ptp(xx[valid]) == 0:
            continue
        design = np.c_[np.ones(valid.sum()), xx[valid]]
        beta = np.linalg.lstsq(design, yy[valid], rcond=None)[0]
        predictions[i] = beta[0] + beta[1] * y[i - 1]
    return pd.Series(predictions, index=series.index)


def dm_absolute_h1(e1, e2):
    """Two-sided absolute-loss DM test with the original h=1 adjustment."""
    valid = np.isfinite(e1) & np.isfinite(e2)
    loss = np.abs(e1[valid]) - np.abs(e2[valid])
    n = len(loss)
    centered = loss - loss.mean()
    variance = np.dot(centered, centered) / n
    if variance <= 0:
        return np.nan
    statistic = loss.mean() / np.sqrt(variance / n) * np.sqrt((n - 1) / n)
    return float(2 * student_t.sf(abs(statistic), df=n - 1))


def calculate():
    cells = []

    def add(table, row, column, value):
        cells.append(dict(item=table, row=row, column=column, replicated=float(value)))

    baseline = load_frame('baseline_ts')
    oos = load_frame('oos_ts')

    # Table 9: scale absolute errors by the standard deviation of signed errors.
    # The matching specification uses nowcasts for Flash Crash and h1 otherwise.
    events = [
        ('9/11 Attacks', '2001-07-01', '1', ['RGDP', 'UNEMP', 'CPI', 'TBILL', 'TBOND']),
        ('Lehman Brothers Collapse', '2008-07-01', '1', ['RGDP', 'UNEMP', 'CPI', 'TBILL', 'TBOND', 'HOUSING']),
        ('Flash Crash', '2010-04-01', '0', ['RGDP', 'CPI']),
        ('S&P Downgrade of U.S. Debt', '2011-07-01', '1', ['TBILL', 'TBOND', 'RGDP']),
        ('COVID-19 Pandemic Declaration', '2020-01-01', '1', ['RGDP', 'UNEMP', 'CPI', 'HOUSING', 'INDPROD']),
        ('Russia-Ukraine War', '2022-01-01', '1', ['RGDP', 'CPI', 'TBILL', 'TBOND']),
        ('Silicon Valley Bank Collapse', '2023-01-01', '1', ['RGDP', 'UNEMP', 'TBILL', 'TBOND']),
    ]
    errors = baseline[(baseline.type == 'AI') & baseline.id.isin(['0', '1'])].copy()
    errors['absolute_error'] = errors.forecast_error.abs()
    groups = errors.groupby(['variable', 'id'], observed=True)
    errors['z'] = ((errors.absolute_error - groups.absolute_error.transform('mean'))
                   / groups.forecast_error.transform('std'))
    for name, quarter, horizon, variables in events:
        sample = errors[(errors.date_q == quarter) & (errors.id == horizon)]
        add('T9', name, 'Relevant variables Z', sample[sample.variable.isin(variables)].z.mean())
        add('T9', name, 'All variables Z', sample.z.mean())

    # Table 10: intentionally preserve the overlapping baseline/OOS quarters.
    combined = pd.concat([baseline, oos], ignore_index=True)
    for variable in ['RGDP', 'UNEMP', 'CPI', 'TBILL']:
        sample = combined[(combined.type == 'AI') & (combined.id == '1')
                          & (combined.variable == variable)].dropna(subset=['forecast_error']).copy()
        sample['post'] = (sample.date_q > '2023-10-31').astype(int)
        model = OLS(sample.forecast_error.abs(), add_constant(sample.post)).fit()
        values = {'Intercept': model.params.iloc[0], 'Intercept SE': model.bse.iloc[0],
                  'Post cutoff': model.params.iloc[1], 'Post SE': model.bse.iloc[1],
                  'N': int(model.nobs), 'R2': model.rsquared,
                  'Intercept stars': stars(model.pvalues.iloc[0], (0.001, 0.01, 0.05)),
                  'Post cutoff stars': stars(model.pvalues.iloc[1], (0.001, 0.01, 0.05))}
        for column, value in values.items():
            add('T10', variable, column, value)

    # Table 12: exact Appendix C substring rules; categories are nonexclusive.
    keywords = {
        'Mechanical': ['trend', 'historical', 'average', 'mean reversion', 'pattern', 'previous', 'past', 'typical', 'normal', 'baseline', 'extrapolat'],
        'Policy': ['fed', 'federal reserve', 'monetary policy', 'fiscal', 'stimulus', 'rate hike', 'rate cut', 'tightening', 'easing', 'central bank', 'government', 'policy response', 'intervention'],
        'Model': ['phillips curve', 'okun', 'gdp growth', 'economic model', 'structural', 'relationship between', 'economic theory', 'multiplier', 'elasticity', 'economic indicator', 'leading indicator'],
        'Event': ['covid', 'pandemic', 'crisis', 'recession', 'shock', 'war', 'collapse', 'lockdown', 'unprecedented', 'disruption', 'financial crisis', 'lehman', 'subprime', 'outbreak', 'emergency'],
    }
    reasoning = load_frame('baseline_reasoning')
    text = reasoning.reasoning.fillna('').str.lower()
    for category, words in keywords.items():
        reasoning[category] = text.str.contains('|'.join(map(re.escape, words)))
    reasoning['Model-based'] = reasoning.Mechanical | reasoning.Model
    reasoning['Judgment-based'] = reasoning.Policy | reasoning.Event
    reasoning['Period'] = 'Normal'
    for start, end, name in [('2008-07-01', '2009-10-01', 'Financial Crisis'),
                             ('2020-01-01', '2020-10-01', 'COVID-19'),
                             ('2022-01-01', '2022-10-01', 'Inflation Shock')]:
        reasoning.loc[reasoning.date_q.between(start, end), 'Period'] = name
    for period in ['Normal', 'Financial Crisis', 'COVID-19', 'Inflation Shock']:
        sample = reasoning[reasoning.Period == period]
        add('T12', period, 'N', len(sample))
        for category in list(keywords) + ['Model-based', 'Judgment-based']:
            add('T12', period, category, 100 * sample[category].mean())

    # D.15: the expanding AR(1) is estimated separately for each human horizon.
    for variable in load_frame('variables').variable:
        for horizon in ['0', '1', '4']:
            sample = baseline[(baseline.variable == variable) & (baseline.id == horizon)]
            human = sample[sample.type == 'Human'].set_index('date_q').sort_index()
            ai = sample[sample.type == 'AI'].set_index('date_q').sort_index()
            prediction = expanding_ar1(human['median'])
            values = human[['median', 'realized', 'forecast_error']].rename(
                columns={'median': 'human_median', 'forecast_error': 'human_error'})
            values = values.join(ai.forecast_error.rename('ai_error')).join(prediction.rename('prediction'))
            values['ar1_error'] = values.prediction - values.realized
            denominator = values.human_error.abs().mean()
            ai_mae = values.loc[values.human_error.notna(), 'ai_error'].abs().mean()
            ar1_mae = values.ar1_error.abs().mean()
            p = dm_absolute_h1(values.ai_error.to_numpy(), values.ar1_error.to_numpy())
            add('TD15', variable, f'h{horizon}: AI/Human MAE', ai_mae / denominator)
            add('TD15', variable, f'h{horizon}: AR1/Human MAE', ar1_mae / denominator)
            add('TD15', variable, f'h{horizon}: p-value', p)
            add('TD15', variable, f'h{horizon}: p-value stars', stars(p))
    return cells
