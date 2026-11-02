"""Recover Table 11 AI calculations from original inputs, without fitting targets.

The paper's printed numbers are comparison targets only. Candidate definitions
come from explicit horizon fields and the manuscript's error/consensus wording.
No original research input is modified.
"""
from pathlib import Path
import csv,hashlib,json,re
import numpy as np
import pandas as pd
from statsmodels.regression.linear_model import OLS
from statsmodels.tools.tools import add_constant

OUT=Path(__file__).resolve().parent;ROOT=OUT.parent;SRC=ROOT.parent
C=ROOT/'data_cache';V=['RGDP','CPI','UNEMP','TBILL']
meta=pd.read_csv(C/'baseline_variables.csv').set_index('variable')
labels={v:meta.loc[v,'variable_AI_output'] for v in V}
source=SRC/'Simulating_SPF_processing/data/merged_results_spf_format_2026_fixed.xlsx'
columns=['Name','Date_Q']+[labels[v]+'_t'+('' if h==0 else '+1') for v in V for h in [0,1]]
raw=pd.read_excel(source,usecols=columns)
raw['source_row']=np.arange(len(raw))+2
raw=raw.rename(columns={'Date_Q':'date_q',**{labels[v]+'_t'+('' if h==0 else '+1'):f'{v}_A{h}' for v in V for h in [0,1]}})
raw['date_q']=pd.to_datetime(raw.date_q)
for v in V:
    for h in [0,1]:raw[f'{v}_A{h}']=pd.to_numeric(raw[f'{v}_A{h}'],errors='coerce')
median_source=SRC/'Simulating_SPF_processing/data/median_and_realtime_formatted.csv'
median=pd.read_csv(median_source,usecols=['date_q']+[v+'2' for v in V])
median['date_q']=pd.PeriodIndex(median.date_q.str.replace(' ',''),freq='Q').to_timestamp()
median=median.set_index('date_q')
wide=pd.read_parquet(C/'baseline_wide.parquet').drop_duplicates('date_q').set_index('date_q')
cache=pd.read_parquet(C/'baseline_raw_forecasts.parquet')
assert len(cache)==len(raw)
cache_checks={}
for v in V:
    for h in [0,1]:
        name=f'{v}_A{h}';cache_checks[name]=bool(np.allclose(raw[name],cache[name],equal_nan=True))
    cache_checks[v+'_H0']=bool(np.allclose(median.loc[wide.index,v+'2'],wide[v+'_H0'],equal_nan=True))
assert all(cache_checks.values())

targets={x['row'].split(' ',1)[1]:{} for x in json.loads((ROOT/'extended_cell_audit.json').read_text()) if x['item']=='T11' and x['row'].startswith('AI ')}
for x in json.loads((ROOT/'extended_cell_audit.json').read_text()):
    if x['item']=='T11' and x['row'].startswith('AI '):targets[x['row'].split(' ',1)[1]][x['column']]=x['original']

def model(data,reg):
    x=data.dropna(subset=['revision',reg]);X=add_constant(x[[reg]],has_constant='add');m=OLS(x.revision,X).fit(cov_type='HC1')
    # Independent centered-sum OLS and HC1 sandwich verification, avoiding
    # shared least-squares code and making the one-regressor algebra explicit.
    z=x[reg].to_numpy();yy=x.revision.to_numpy();zc=z-z.mean();sxx=np.sum(zc*zc)
    slope=np.sum(zc*(yy-yy.mean()))/sxx;beta=np.array([yy.mean()-slope*z.mean(),slope]);resid=yy-beta[0]-slope*z
    n=len(x);slope_var=np.sum((zc*resid)**2)/sxx**2*n/(n-2)
    intercept_var=np.sum(((1/n-z.mean()*zc/sxx)*resid)**2)*n/(n-2)
    assert np.allclose(beta,m.params,rtol=1e-8,atol=1e-10)
    assert np.allclose(np.sqrt([intercept_var,slope_var]),m.bse,rtol=1e-7,atol=1e-10)
    return {'intercept':float(m.params.iloc[0]),'coefficient':float(m.params.iloc[1]),'se_HC1':float(m.bse.iloc[1]),'N':int(m.nobs),'R2':float(m.rsquared),'p':float(m.pvalues.iloc[1]),'stars':3 if m.pvalues.iloc[1]<.01 else 0,'finite_rows':x.source_row.astype(int).tolist(),
            'lag_quarter_gap_counts':{str(k):int(n) for k,n in x.lag_quarter_gap.value_counts().sort_index().items()},'placeholder_rows':int((x.Name=='No Name Provided').sum())}

variants=[];recovered=[];regression_inputs=[]
for v in V:
    for h in [0,1]:
        d=raw[['Name','date_q','source_row',f'{v}_A{h}']].rename(columns={f'{v}_A{h}':'forecast'}).sort_values(['Name','date_q'],kind='stable').copy()
        d['human_nowcast_median']=d.date_q.map(median[v+'2']);d['actual_current']=d.date_q.map(wide[v+'_R0'])
        g=d.groupby('Name',sort=False)
        for src,dst in [('forecast','lag_forecast'),('human_nowcast_median','lag_human_nowcast_median'),('actual_current','lag_actual'),('date_q','lag_date')]:d[dst]=g[src].shift()
        d['revision']=d.forecast-d.lag_forecast
        d['lag_quarter_gap']=d.date_q.dt.to_period('Q').astype('int64')-d.lag_date.dt.to_period('Q').astype('int64')
        d['published_error_regressor']=d.human_nowcast_median-d.lag_forecast
        d['published_consensus_regressor']=d.lag_forecast-d.lag_human_nowcast_median
        d['actual_lagged_error']=d.lag_actual-d.lag_forecast
        d['actual_current_minus_lag_forecast']=d.actual_current-d.lag_forecast
        for sample in ['previous_available','consecutive_quarters']:
            x=d if sample=='previous_available' else d[d.lag_quarter_gap==1]
            for reg in ['published_error_regressor','published_consensus_regressor','actual_lagged_error','actual_current_minus_lag_forecast']:
                result=model(x,reg);variants.append({'variable':v,'forecast_horizon':h,'sample':sample,'regressor':reg,**result})
        if h==1:
            entry={'panel':'AI','variable':v,'forecast_horizon':1,'consensus_horizon':0,'sample':'previous available row within Name, preserving source order for duplicate quarters','error':model(d,'published_error_regressor'),'consensus':model(d,'published_consensus_regressor')}
            checks=[]
            for block,prefix in [('error','Error'),('consensus','Consensus')]:
                r=entry[block]
                for key,suffix,dec in [('coefficient','coefficient',3),('se_HC1','SE',3),('N','N',0),('R2','R2',3)]:
                    target=targets[v][prefix+' '+suffix];checks.append({'field':prefix+' '+suffix,'published':target,'computed':r[key],'precision':dec,'display_match':f'{target:.{dec}f}'==f'{r[key]:.{dec}f}'})
                checks.append({'field':prefix+' stars','published':3,'computed':r['stars'],'display_match':r['stars']==3})
            entry['published_comparisons']=checks;assert all(x['display_match'] for x in checks)
            recovered.append(entry);d['variable']=v;regression_inputs.append(d)

pd.concat(regression_inputs,ignore_index=True).to_parquet(OUT/'ai_recovered_regression_inputs.parquet',index=False)
(OUT/'ai_recovered_results.json').write_text(json.dumps(recovered,indent=2))
(OUT/'ai_justified_variants.json').write_text(json.dumps(variants,indent=2))

# Source-code provenance audit (not a claim that missing code never existed).
code_sources=list((SRC/'Simulating_SPF_processing').rglob('*.R'))
history_source=SRC/'Simulating_SPF_processing/.Rhistory'
if history_source.exists():code_sources.append(history_source)
hits=[]
pattern=re.compile(r'revision|lagged.?error|consensus|error.correction|lag_error',re.I)
for p in code_sources:
    for lineno,line in enumerate(p.read_text(errors='replace').splitlines(),1):
        if pattern.search(line):hits.append({'file':str(p),'line':lineno,'text':line})
source_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,median_source,*code_sources]}
evidence={
 'status':'All printed AI statistics numerically recovered from original data; original generating code was not supplied.',
 'recovered_numeric_cells':32,'recovered_star_cells':8,
 'formulas':{'outcome':'A1_i,t - A1_i,previous','error_regressor':'SPF2_t - A1_i,previous','consensus_regressor':'A1_i,previous - SPF2_previous'},
 'interpretation':{'A1':'AI one-quarter-ahead forecast, source field suffix _t+1','SPF2':'Official human current-quarter forecast median, source column VAR2','previous':'Previous row within Name after stable date sorting; may be same quarter or more than one quarter earlier'},
 'confirmed_by_data':['Every AI coefficient, robust HC1 standard error, count, R-squared and significance marker matches the published precision.','All recovered calculations use original workbook forecasts and original official SPF median CSV; cached inputs agree exactly.','OLS coefficients and HC1 covariance independently checked by centered-sum algebra.'],
 'not_confirmed':['The exact original script and intended method are absent. Numerical recovery is not proof of which implementation created the table.','The printed precision does not necessarily uniquely distinguish HC1 from other robust covariance corrections.'],
 'material_mislabeling':['The AI forecast is one-quarter-ahead, although the caption calls it a nowcast.','The so-called lagged forecast error uses the current human forecast median as its benchmark, not a realized outcome.','The consensus regressor compares a one-quarter-ahead AI forecast to a human nowcast median.','Within-person lags include duplicate-quarter observations and multi-quarter gaps, despite consecutive-quarter wording.'],
 'input_rows':len(raw),'unique_names':int(raw.Name.nunique()),'placeholder_rows':int((raw.Name=='No Name Provided').sum()),'duplicate_name_quarter_rows':int(raw.duplicated(['Name','date_q']).sum()),
 'cache_reconciliation':cache_checks,'r_files_searched':sum(p.suffix=='.R' for p in code_sources),'r_history_searched':history_source.exists(),'revision_related_code_hits':hits,'source_sha256':source_hashes,
 'manuscript_evidence':{'definitions':'May 2026 version.tex lines293-305','table':'May 2026 version.tex lines990-1020','commented_older_plot_note':'May 2026 version.tex lines643-648; says consecutive pairs and 1st/99th percentile trimming for visualization, not an active generating script.'}}
(OUT/'ai_evidence.json').write_text(json.dumps(evidence,indent=2))
print(json.dumps({v['variable']:{k:{a:v[k][a] for a in ['coefficient','se_HC1','N','R2','p']} for k in ['error','consensus']} for v in recovered},indent=2))
