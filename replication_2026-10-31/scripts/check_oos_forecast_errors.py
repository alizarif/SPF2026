from pathlib import Path
import importlib.util,json
import numpy as np
import pandas as pd
P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('figures',P/'replicate_figures.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
saved=m.load('oos_ts');long=m.load('oos_long');new,check=m.rebuild_time_series(long,saved)
keys=['date_q','type','variable','id']
d=saved.merge(new,on=keys,suffixes=['_cached','_rebuilt'],validate='one_to_one')
d['error_difference']=d.forecast_error_rebuilt-d.forecast_error_cached
d['changed']=d.error_difference.abs()>1e-8
rows=[]
for (var,h,typ),g in d.groupby(['variable','id','type'],observed=True):
 if not g.changed.any():continue
 realized=g.realized_cached.dropna();mean=realized.mean();sd=realized.std(ddof=1)
 rows.append({'variable':var,'horizon':h,'type':typ,'quarter_count':len(g),'realized_n':len(realized),'changed_quarters':int(g.changed.sum()),'max_absolute_error_difference':float(g.error_difference.abs().max()),'cached_mae':float(g.forecast_error_cached.abs().mean()),'rebuilt_mae':float(g.forecast_error_rebuilt.abs().mean()),'realized_mean':float(mean),'realized_sample_sd':float(sd),'lower_bound':float(mean-3*sd),'upper_bound':float(mean+3*sd),'cached_equals_unclipped_error_count':int(np.isclose(g.forecast_error_cached,g['median_cached']-g.realized_cached,atol=1e-8,equal_nan=False).sum())})
summary=pd.DataFrame(rows);summary.to_csv(m.RUN/'oos_error_reconciliation.csv',index=False)
cols=keys+['median_cached','median__cached','median__rebuilt','realized_cached','forecast_error_cached','forecast_error_rebuilt','error_difference']
d.loc[d.changed,cols].to_csv(m.RUN/'oos_error_reconciliation_rows.csv',index=False)
result={'method':'Rebuild medians from oos_long and clip per type/id/variable to mean(realized) +/- 3 * sample SD(realized, ddof=1), excluding NA, exactly as current prepare_data.R remove_outliers specifies. Groups span cached OOS dates2023Q1–2024Q4; not historical baseline dates.','median_max_abs_difference':check['median_max_abs_difference_from_R_cache'],'forecast_error_max_abs_difference':check['forecast_error_max_abs_difference_from_R_cache'],'groups_changed':len(summary),'rows_changed':int(d.changed.sum()),'total_rows':len(d),'groups':rows,'implication':'Published/archived results can be reproduced from saved prepared OOS data, but current preprocessing code does not recover all saved clipped errors. Figure6 selected four variables at h1 is unaffected.'}
(m.RUN/'oos_error_reconciliation.json').write_text(json.dumps(result,indent=2))
print(summary[summary.horizon.isin(['0','1','2','4'])].to_string(index=False));print('TOTAL',len(summary),int(d.changed.sum()))
