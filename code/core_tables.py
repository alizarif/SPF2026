"""Recompute Tables 3–8 and B.13 from the supplied numerical data.

The supplied code's statistical choices are preserved, including its panel-size
weights, signed-error randomization statistics, positional pairing in Table 6,
and the different human/AI horizons needed for the published Table 7. These are
reproductions of the supplied calculations, not endorsements of those choices.
Table 11 and B.14 use the separately documented revised calculations.

No published numeric target enters these estimators. Source row and column order
are material: Table 3's ACF follows panel rows, and Table 6 pairs stored positions.
"""
import re
import warnings

import numpy as np
from scipy.stats import ttest_rel

from data import load_frame

SEED = 20261031
SIMULATIONS = 10_000
HORIZONS = ['0', '1', '4']


def calculate():
    """Return newly calculated cells as item/row/column/replicated dictionaries."""
    rng = np.random.default_rng(SEED)
    meta = load_frame('variables')
    variables = meta.variable.tolist()
    names = dict(zip(variables, meta.variable_longname))
    wide = load_frame('baseline_wide')
    baseline = load_frame('baseline_ts')
    oos = load_frame('oos_ts')
    cells = []

    def emit(item, row, column, value):
        cells.append({'item': item, 'row': row, 'column': column,
                      'replicated': float(value)})

    def pair(frame, variable, horizon):
        selected = frame[(frame.variable == variable) & (frame.id == str(horizon))]
        return selected.pivot(index='date_q', columns='type', values='forecast_error').reindex(columns=['AI', 'Human'])

    def weighted_mae(values, weights):
        valid = np.isfinite(values) & np.isfinite(weights) & (np.asarray(weights) > 0)
        return float(np.average(np.abs(np.asarray(values)[valid]), weights=np.asarray(weights)[valid])) if valid.any() else np.nan

    def swap_p(a, b, baseline_mean=None):
        a, b = np.array(a, float), np.array(b, float)
        mask = rng.random((SIMULATIONS, len(a))) < .5
        first, second = np.where(mask, a, b), np.where(mask, b, a)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', RuntimeWarning)
            if baseline_mean is None:
                observed = np.nanmean(a) - np.nanmean(b)
                simulated = np.nanmean(first, axis=1) - np.nanmean(second, axis=1)
            else:
                observed = np.nanmean(a) - baseline_mean
                simulated = np.nanmean(first, axis=1) - baseline_mean
        valid = np.isfinite(simulated)
        return float(np.mean(np.abs(simulated[valid]) >= abs(observed))) if valid.any() else np.nan

    def p_stars(p):
        # The source core tables use inclusive thresholds before display rounding.
        return int(p <= .1) + int(p <= .05) + int(p <= .01)

    # T3: realizations repeat once per AI-panel row. Do not collapse quarters.
    descriptive_columns = ['N', 'Mean', 'SD', 'Skewness', 'Kurtosis', 'Median', 'Min', 'Max', 'ACF(1)']
    for variable in variables:
        values = wide[f'{variable}_R0'].to_numpy(float)
        scaled = bool(np.any(values >= 1000))
        if scaled:
            values = values / 1000
        mean, sd = values.mean(), values.std(ddof=1)
        centered = values - mean
        result = [len(values), mean, sd, np.mean(centered ** 3) / sd ** 3,
                  np.mean(centered ** 4) / sd ** 4 - 3, np.median(values),
                  values.min(), values.max(),
                  np.dot(centered[:-1], centered[1:]) / np.dot(centered, centered)]
        label = names[variable] + (' (x1000)' if scaled else '')
        for column, value in zip(descriptive_columns, result):
            emit('T3', label, column, value)

    # T4/T5 draws are intentionally interleaved, as in the earlier verified run.
    for variable in variables:
        for horizon in HORIZONS:
            errors = pair(baseline, variable, horizon)
            weights = wide[wide[f'{variable}_H{horizon}'].notna()].groupby('date_q').size().reindex(errors.index).fillna(0).values
            p_value = swap_p(errors.AI, errors.Human)
            emit('T4', names[variable], f'h{horizon} AI', weighted_mae(errors.AI, weights))
            emit('T4', names[variable], f'h{horizon} Human', weighted_mae(errors.Human, weights))
            emit('T4', names[variable], f'h{horizon} p', p_value)
            emit('T4', names[variable], f'h{horizon} p stars', p_stars(p_value))

            paired = errors[weights > 0].dropna()
            ai, human = paired.AI.abs().values, paired.Human.abs().values
            wins = ai <= human
            ties, n = np.sum(ai == human), len(ai)
            observed = abs(wins.mean() - .5)
            successes = rng.binomial(n - ties, .5, SIMULATIONS)
            simulated = (successes + ties) / n
            p_value = float(np.mean(abs(simulated - .5) >= observed))
            emit('T5', names[variable], f'h{horizon} Share', wins.mean())
            emit('T5', names[variable], f'h{horizon} p', p_value)
            emit('T5', names[variable], f'h{horizon} p stars', p_stars(p_value))

    # T6 chooses one AI name per variable/horizon with duplicate-join weights.
    selected, estimates = {}, {}
    for variable in variables:
        for horizon in HORIZONS:
            columns = ['date_q', 'Name', f'{variable}_A{horizon}',
                       f'{variable}_H{horizon}', f'{variable}_R{horizon}']
            observations = wide[columns].copy()
            observations['error'] = observations[f'{variable}_A{horizon}'] - observations[f'{variable}_R{horizon}']
            weights = observations[observations[f'{variable}_H{horizon}'].notna()].groupby('date_q').size()
            observations['weight'] = observations.date_q.map(weights).fillna(0)
            ranks = observations.groupby('Name', sort=False).apply(
                lambda frame: weighted_mae(frame.error, frame.weight), include_groups=False)
            best = ranks.idxmin()
            selected[variable, horizon] = best
            selected_rows = observations[observations.Name == best]
            human = pair(baseline, variable, horizon).Human.reindex(selected_rows.date_q).values
            ai = selected_rows.error.values
            estimates[variable, horizon] = (np.nanmean(abs(ai)), np.nanmean(abs(human)))

    # Reproduce R pivot_longer row-major AI order and saved aggregate Human order.
    ai_records, human_records = [], []
    ai_columns = [column for column in wide if re.match(r'^.+_A[014]$', column)]
    for _, row in wide.iterrows():
        for column in ai_columns:
            variable, horizon = column.rsplit('_A', 1)
            if row.Name == selected[variable, horizon]:
                ai_records.append((variable, horizon, row.date_q, row[column] - row[f'{variable}_R{horizon}']))
    for _, row in baseline[(baseline.type == 'Human') & baseline.id.isin(HORIZONS)].iterrows():
        repeats = int(((wide.Name == selected[row.variable, row.id]) & (wide.date_q == row.date_q)).sum())
        human_records.extend([(row.variable, row.id, row.date_q, row.forecast_error)] * repeats)
    assert len(ai_records) == len(human_records)
    groups = [(variable, horizon) for variable in variables for horizon in HORIZONS]
    group_index = {key: i for i, key in enumerate(groups)}
    group = np.array([group_index[record[0], record[1]] for record in ai_records + human_records])
    errors = np.array([record[3] for record in ai_records + human_records])
    valid = np.isfinite(errors)
    finite_errors = np.nan_to_num(errors)
    n, group_count = len(ai_records), len(groups)

    def differences(is_ai):
        first_sum = np.bincount(group, weights=finite_errors * is_ai, minlength=group_count)
        first_n = np.bincount(group, weights=valid * is_ai, minlength=group_count)
        second_sum = np.bincount(group, weights=finite_errors * (~is_ai), minlength=group_count)
        second_n = np.bincount(group, weights=valid * (~is_ai), minlength=group_count)
        with np.errstate(invalid='ignore', divide='ignore'):
            return first_sum / first_n - second_sum / second_n

    observed = differences(np.r_[np.ones(n, bool), np.zeros(n, bool)])
    exceeds, valid_simulations = np.zeros(group_count), np.zeros(group_count)
    for _ in range(SIMULATIONS):
        mask = rng.random(n) < .5
        simulated = differences(np.r_[mask, ~mask])
        finite = np.isfinite(simulated)
        valid_simulations += finite
        exceeds += finite & (abs(simulated) >= abs(observed))
    for variable, horizon in groups:
        ai_mae, human_mae = estimates[variable, horizon]
        i = group_index[variable, horizon]
        p_value = exceeds[i] / valid_simulations[i]
        for suffix, value in [('AI', ai_mae), ('Human', human_mae), ('p', p_value), ('p stars', p_stars(p_value))]:
            emit('T6', names[variable], f'h{horizon} {suffix}', value)

    # T8 follows the supplied signed-mean test, not a baseline/ablation MAE test.
    ablations = {name: load_frame(name + '_ts') for name in ['generic', 'no_realtime', 'no_data', 'recall']}
    column_labels = {'generic': 'Generic', 'no_realtime': 'No realtime',
                     'no_data': 'No data', 'recall': 'Recall'}
    ratios = []
    ratio_columns = []
    for variable in variables:
        row_ratios = []
        for variant in ['generic', 'no_realtime', 'no_data', 'recall']:
            for horizon in (['0'] if variant == 'recall' else ['0', '4']):
                errors = pair(ablations[variant], variable, horizon)
                base = pair(baseline, variable, horizon).AI
                ratio = float(errors.AI.abs().mean() / base.abs().mean())
                p_value = swap_p(errors.AI, errors.Human, float(base.mean()))
                column = f'{column_labels[variant]} h{horizon}'
                emit('T8', names[variable], column, ratio)
                emit('T8', names[variable], column + ' stars', p_stars(p_value))
                row_ratios.append(ratio)
                if variable == variables[0]:
                    ratio_columns.append(column)
        ratios.append(row_ratios)
    for column, value in zip(ratio_columns, np.mean(ratios, axis=0)):
        emit('T8', 'Average', column, value)

    # B.13 keeps the archived 2023–2024 sample and actual horizons 0/1/4.
    # Its saved h4 errors differ from current preparation-code clipping.
    for variable in variables:
        for horizon in HORIZONS:
            errors = pair(oos, variable, horizon)
            p_value = swap_p(errors.AI, errors.Human)
            for suffix, value in [('AI', errors.AI.abs().mean()), ('Human', errors.Human.abs().mean()),
                                  ('p', p_value), ('p stars', p_stars(p_value))]:
                emit('TB13', names[variable], f'h{horizon} {suffix}', value)
            # The earlier verified run also calculated a 2024-only diagnostic.
            # Consume its draws to preserve subsequent reported Monte Carlo p's.
            diagnostic = errors[errors.index >= '2024-01-01']
            swap_p(diagnostic.AI, diagnostic.Human)

    # T7: positive paired quarterly sample SDs; Human h0/3 versus raw AI h1/4.
    # All 5,388 raw AI rows, including placeholder names, are intentionally used.
    human_microdata = load_frame('baseline_microdata')
    raw_ai = load_frame('baseline_raw_forecasts')
    for panel in ['Human', 'AI']:
        for variable in ['CPI', 'UNEMP', 'RGDP', 'TBILL']:
            short, long = ('0', '3') if panel == 'Human' else ('1', '4')
            if panel == 'Human':
                selected_rows = human_microdata[(human_microdata.variable == variable) & human_microdata.id.astype(str).isin([short, long])]
                sd = selected_rows.groupby(['date_q', 'id'], observed=True).value.std(ddof=1).unstack()
            else:
                sd = raw_ai.groupby('date_q', observed=True)[[f'{variable}_A{short}', f'{variable}_A{long}']].std(ddof=1)
                sd.columns = [short, long]
            complete = sd[[short, long]].dropna()
            positive = complete[(complete[short] > 0) & (complete[long] > 0)]
            test = ttest_rel(positive[long], positive[short])
            short_mean, long_mean = positive.mean()
            values = [('Short SD', short_mean), ('Long SD', long_mean),
                      ('Ratio', long_mean / short_mean), ('t-stat', test.statistic),
                      ('N', len(positive)), ('t-stat stars', 3 if test.pvalue < .01 else 0)]
            for column, value in values:
                emit('T7', panel + ' / ' + variable, column, value)

    return cells
