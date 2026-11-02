"""Independent numerical verification of the two rebuilt tables."""
from pathlib import Path
import json,itertools,math
import pandas as pd
import numpy as np
from scipy.stats import norm
R=Path(__file__).resolve().parents[1]
# Re-estimate every Table11 regression from the exported observation-level data.
a=pd.read_parquet(R/'table11_investigation/verified_regression_inputs.parquet')
e=json.loads((R/'table11_investigation/verified_estimates.json').read_text())
assert ((a.date_q.dt.to_period('Q').astype(int)-a.lag_date_q.dt.to_period('Q').astype(int))==1).all()
assert not a.duplicated(['panel','variable','person','date_q']).any()
assert np.allclose(a.revision,a.forecast-a.lag_forecast)
assert np.allclose(a.lagged_realized_error,a.prior_quarter_actual_current_vintage-a.lag_forecast)
assert np.allclose(a.lagged_consensus_deviation,a.lag_forecast-a.lag_human_nowcast_median)
t11=[]
for model in e:
 d=a[(a.panel==model['panel'])&(a.variable==model['variable'])]
 for kind,col in [('error','lagged_realized_error'),('consensus','lagged_consensus_deviation')]:
  z=d.dropna(subset=['revision',col]);x=z[col].to_numpy();y=z.revision.to_numpy();n=len(x);xc=x-x.mean();yc=y-y.mean();sxx=np.sum(xc**2)
  beta=np.sum(xc*yc)/sxx;intercept=y.mean()-beta*x.mean();res=yc-beta*xc
  se=np.sqrt((n/(n-2))*np.sum(xc**2*res**2)/(sxx*sxx));rsq=1-np.sum(res**2)/np.sum(yc**2);p=2*norm.sf(abs(beta/se))
  actual={'coefficient':float(beta),'intercept':float(intercept),'se_HC1':float(se),'R2':float(rsq),'p':float(p),'N':n}
  for key,val in actual.items():assert np.isclose(val,model[kind][key],rtol=1e-10,atol=1e-11),(model['panel'],model['variable'],kind,key,val,model[kind][key])
  t11.append(dict(panel=model['panel'],variable=model['variable'],regression=kind,verified=True,**actual))
# Recompute every B14 MAE and p-value, independently enumerating swapped pairs.
b=R/'tableB14_investigation';q=pd.read_json(b/'verified_quarter_results.json');r=pd.read_json(b/'verified_results.json')
w=pd.read_parquet(R/'data_cache/oos_wide.parquet');h=pd.read_parquet(R/'data_cache/oos_microdata.parquet')
quarter_checks=0
for row in q.itertuples(index=False):
 assert pd.Period(row.forecast_origin,freq='Q')+row.horizon==pd.Period(row.target_quarter,freq='Q')
 if not row.eligible:continue
 dt=pd.Period(row.forecast_origin,freq='Q').start_time
 ai=w.loc[w.date_q.eq(dt),f'{row.variable}_A{row.horizon}'].dropna().to_numpy()
 hu=h.loc[h.date_q.eq(dt)&h.variable.eq(row.variable)&h.id.eq(str(row.horizon)),'value'].dropna().to_numpy()
 assert np.isclose(np.min(abs(ai-row.actual)),row.ai_absolute_error,rtol=1e-11,atol=1e-10)
 assert np.isclose(np.min(abs(hu-row.actual)),row.human_absolute_error,rtol=1e-11,atol=1e-10)
 quarter_checks+=1
tb14=[]
for row in r.itertuples(index=False):
 z=q[q.variable.eq(row.variable)&q.horizon.eq(row.horizon)&q.eligible];d=(z.ai_absolute_error-z.human_absolute_error).to_numpy();n=len(d);observed=abs(sum(d));eps=max(1,float(sum(abs(d))))*1e-12
 perm=[abs(sum(sign*value for sign,value in zip(signs,d)))for signs in itertools.product([-1,1],repeat=n)]
 p=sum(value>=observed-eps for value in perm)/len(perm)
 assert n==row.n and p==row.p_value
 assert np.isclose(z.ai_absolute_error.mean(),row.ai_mae,rtol=1e-11,atol=1e-10)
 assert np.isclose(z.human_absolute_error.mean(),row.human_mae,rtol=1e-11,atol=1e-10)
 tb14.append(dict(variable=row.variable,horizon=row.horizon,N=n,AI_MAE=float(z.ai_absolute_error.mean()),Human_MAE=float(z.human_absolute_error.mean()),exact_p=p,verified=True))
output={'table11_models':len(t11),'table11_all_estimates_and_HC1_SE_verified':True,'table11_unique_person_quarters_and_consecutive_lags_verified':True,'B14_quarter_minima_verified':quarter_checks,'B14_MAE_and_exact_test_groups_verified':len(tb14),'table11':t11,'B14':tb14}
(R/'tables_review/independent_investigation_audit.json').write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps({k:v for k,v in output.items()if k not in ['table11','B14']},indent=2))
