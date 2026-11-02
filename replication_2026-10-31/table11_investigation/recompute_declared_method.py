"""Table 11 recalculation using a declared, consistent nowcast specification.

No attempt is made to tune observations or estimators to published numbers.
Original values are used only after fitting, to populate comparison cells.
"""
from pathlib import Path
import copy,hashlib,json
import numpy as np
import pandas as pd
from scipy.stats import norm
from statsmodels.regression.linear_model import OLS
from statsmodels.tools.tools import add_constant

OUT=Path(__file__).resolve().parent;ROOT=OUT.parent;SRC=ROOT.parent;C=ROOT/'data_cache'
V=['RGDP','CPI','UNEMP','TBILL']
meta=pd.read_csv(C/'baseline_variables.csv').set_index('variable')
labels={v:meta.loc[v,'variable_AI_output'] for v in V}
ai_file=SRC/'Simulating_SPF_processing/data/merged_results_spf_format_2026_fixed.xlsx'
med_file=SRC/'Simulating_SPF_processing/data/median_and_realtime_formatted.csv'
ai=pd.read_excel(ai_file,usecols=['Name','Date_Q']+[labels[v]+'_t' for v in V])
ai=ai.rename(columns={'Name':'person','Date_Q':'date_q',**{labels[v]+'_t':v for v in V}})
ai['source_row']=np.arange(len(ai))+2;ai['date_q']=pd.to_datetime(ai.date_q)
for v in V:ai[v]=pd.to_numeric(ai[v],errors='coerce')
named=ai[ai.person.notna()&ai.person.ne('No Name Provided')].copy()
assert len(named)==5308
duplicates=[]
for (person,q),d in named[named.duplicated(['person','date_q'],False)].groupby(['person','date_q']):
    duplicates.append({'person':person,'date_q':q.isoformat(),'source_rows':d.source_row.tolist(),
                       'values':d[V].to_dict('records'),'conflicting_core_forecasts':bool(any(d[v].nunique(dropna=False)>1 for v in V))})
(OUT/'ai_duplicate_identity_audit.json').write_text(json.dumps(duplicates,indent=2))
med=pd.read_csv(med_file,usecols=['date_q']+[v+str(j) for v in V for j in [1,2]])
med['date_q']=pd.PeriodIndex(med.date_q.str.replace(' ',''),freq='Q').to_timestamp()
assert not med.date_q.duplicated().any()
median=med.set_index('date_q')
human_sources={v:SRC/f'Simulating_SPF_processing/data/SPFmicrodata/{v}-Table 1.csv' for v in V}
human={}
for v,p in human_sources.items():
    d=pd.read_csv(p,usecols=['YEAR','QUARTER','ID',v+'2'])
    d['date_q']=pd.to_datetime({'year':d.YEAR,'month':d.QUARTER*3-2,'day':1})
    d=d[d.date_q.between('1999-01-01','2023-10-01')].copy()
    d['forecast']=pd.to_numeric(d[v+'2'].astype(str).str.replace(',',''),errors='coerce')
    d['person']=d.ID.astype(str);d=d[['person','date_q','forecast']]
    assert not d.duplicated(['person','date_q']).any()
    human[v]=d

def ai_panel(v,rule):
    d=named[['person','date_q','source_row',v]].rename(columns={v:'forecast'})
    if rule=='mean':return d.groupby(['person','date_q'],as_index=False,sort=True).agg(forecast=('forecast','mean'))
    if rule in ['first','last']:return d.drop_duplicates(['person','date_q'],keep=rule)[['person','date_q','forecast']]
    if rule=='exclude_conflicting':
        ambiguous=[(x['person'],pd.Timestamp(x['date_q'])) for x in duplicates if x['conflicting_core_forecasts']]
        d=d[~pd.MultiIndex.from_frame(d[['person','date_q']]).isin(ambiguous)]
        return d.drop_duplicates(['person','date_q'])[['person','date_q','forecast']]
    raise ValueError(rule)

def inputs(d,v,panel):
    # Calendar join, rather than a generic shift, ensures exactly one-quarter
    # spacing and never bridges missing respondent observations.
    lag=d.rename(columns={'forecast':'lag_forecast'}).copy()
    lag['lag_date_q']=lag.date_q;lag['date_q']=lag.date_q+pd.DateOffset(months=3)
    x=d.merge(lag,on=['person','date_q'],how='inner',validate='one_to_one')
    x['prior_quarter_actual_current_vintage']=x.date_q.map(median[v+'1'])
    x['lag_human_nowcast_median']=x.lag_date_q.map(median[v+'2'])
    x['revision']=x.forecast-x.lag_forecast
    x['lagged_realized_error']=x.prior_quarter_actual_current_vintage-x.lag_forecast
    x['lagged_consensus_deviation']=x.lag_forecast-x.lag_human_nowcast_median
    x['panel']=panel;x['variable']=v
    x=x.dropna(subset=['revision','lagged_realized_error','lagged_consensus_deviation']).sort_values(['person','date_q'])
    assert (x.date_q.dt.to_period('Q').astype(int)-x.lag_date_q.dt.to_period('Q').astype(int)).eq(1).all()
    assert not x.duplicated(['person','date_q']).any()
    assert x.date_q.between('1999-01-01','2023-10-01').all()
    return x

def fit(x,reg):
    X=add_constant(x[[reg]],has_constant='add');y=x.revision
    m=OLS(y,X).fit(cov_type='HC1')
    # Independent centered sums verify coefficient, sandwich SE, R² and p.
    z=x[reg].to_numpy();yy=y.to_numpy();n=len(x);zc=z-z.mean();yc=yy-yy.mean();sxx=np.sum(zc*zc)
    b=np.sum(zc*yc)/sxx;a=yy.mean()-b*z.mean();e=yy-a-b*z
    se=np.sqrt(np.sum((zc*e)**2)/(sxx*sxx)*n/(n-2));r2=1-np.sum(e*e)/np.sum(yc*yc);p=2*norm.sf(abs(b/se))
    assert np.allclose([a,b,se,r2,p],[m.params.iloc[0],m.params.iloc[1],m.bse.iloc[1],m.rsquared,m.pvalues.iloc[1]],rtol=1e-8,atol=1e-10)
    return {'intercept':float(m.params.iloc[0]),'coefficient':float(m.params.iloc[1]),'se_HC1':float(m.bse.iloc[1]),'N':int(m.nobs),'R2':float(m.rsquared),'p':float(m.pvalues.iloc[1]),'stars':3 if m.pvalues.iloc[1]<.01 else 0,'manual_verification':{'coefficient':float(b),'se_HC1':float(se),'N':n,'R2':float(r2),'p':float(p)}}

results=[];all_inputs=[];sensitivity=[]
for panel in ['Human','AI']:
    for v in V:
        data=human[v] if panel=='Human' else ai_panel(v,'mean')
        x=inputs(data,v,panel);all_inputs.append(x)
        entry={'panel':panel,'variable':v,'error':fit(x,'lagged_realized_error'),'consensus':fit(x,'lagged_consensus_deviation')}
        results.append(entry)
        if panel=='AI':
            for rule in ['mean','first','last','exclude_conflicting']:
                z=inputs(ai_panel(v,rule),v,panel)
                sensitivity.append({'variable':v,'duplicate_rule':rule,'error':fit(z,'lagged_realized_error'),'consensus':fit(z,'lagged_consensus_deviation')})
data=pd.concat(all_inputs,ignore_index=True)
data.to_parquet(OUT/'verified_regression_inputs.parquet',index=False)
data.to_csv(OUT/'verified_regression_inputs.csv',index=False)
(OUT/'verified_estimates.json').write_text(json.dumps(results,indent=2))
(OUT/'duplicate_rule_sensitivity.json').write_text(json.dumps(sensitivity,indent=2))

canonical=copy.deepcopy(json.loads((ROOT/'annotated_extended_table_data.json').read_text())['T11'])
lookup={(x['panel'],x['variable']):x for x in results}
for row in canonical['rows']:
    if row['type']!='data':continue
    for cell in row['cells']:
        if cell['kind']!='numeric':continue
        panel,v=cell['audit_row'].split(' ');prefix,suffix=cell['audit_column'].split(' ',1)
        block=lookup[panel,v]['error' if prefix=='Error' else 'consensus']
        field={'coefficient':'coefficient','SE':'se_HC1','N':'N','R2':'R2'}[suffix]
        val=block[field];dec=cell['precision'];st=block['stars'] if suffix=='coefficient' else 0
        if dec==0:s=f'{val:,}' if cell.get('thousands_separator') else str(val)
        else:s=f'{0 if abs(val)<.5*10**(-dec) else val:.{dec}f}'
        numeric_display=s;s+='*'*st
        if cell.get('parentheses'):s='('+s+')'
        cell.update(replicated=val,starsreplicated=st,replicated_display=s,mismatch=s!=cell['original_display'],stars_mismatch=st!=cell['starsoriginal'],
                    numeric_mismatch=round(val,dec)!=round(cell['original'],dec),verified_under_declared_method=True)
canonical['status']='Independently verified recalculation under an explicitly declared nowcast method; not a recovery of the original Human estimator.'
canonical['replication_notes']=['Both panels use nowcasts, strictly consecutive quarterly observations, a prior-quarter historical realization available in the current survey, the previous quarter’s official human nowcast median, OLS with an intercept, and HC1 robust SEs. Named AI forecast duplicates are averaged within person-quarter; placeholder names are excluded.']
canonical['methodology']={'sample':'1999Q1–2023Q4, with both forecast quarters inside the sample','human_forecast':'Native SPF VAR2','AI_forecast':'Raw workbook field *_t','realized_error':'Official SPF VAR1 at survey t minus same person nowcast from t−1','consensus':'Same person nowcast from t−1 minus official SPF VAR2 median at t−1','AI_identity_rule':'Exclude No Name Provided; mean of duplicate named person-quarter forecasts','human_identity_rule':'Native anonymous ID; unique ID-quarter observations','OLS':'Intercept plus one regressor; HC1 standard errors and normal-reference p-values','significance':'*** p<0.01, matching the original Table 11 convention'}
cells=[c for r in canonical['rows'] if r['type']=='data' for c in r['cells'] if c['kind']=='numeric']
canonical['qa']={'numeric_cells':len(cells),'display_mismatch_cells':sum(c['mismatch'] for c in cells),'numeric_mismatch_cells':sum(c['numeric_mismatch'] for c in cells),'star_mismatch_cells':sum(c['stars_mismatch'] for c in cells),'independent_model_checks':16}
(OUT/'verified_table.json').write_text(json.dumps(canonical,indent=2,ensure_ascii=False))

rt=pd.read_csv(med_file,usecols=['date_q','qof_last_real_gdp','gdp','mof_last_real_cpi','cpi_pct','mof_last_real_uer','uer'])
alignment=[]
for i in range(min(4,len(rt)-1)):
    alignment.append({'cache_R0_assigned_survey_quarter':rt.iloc[i].date_q,'actual_input_survey_row':rt.iloc[i+1].date_q,'RGDP_actual_observation_quarter':rt.iloc[i+1].qof_last_real_gdp,'RGDP_value':float(rt.iloc[i+1].gdp),'UNEMP_observation_month':rt.iloc[i+1].mof_last_real_uer,'UNEMP_value':float(rt.iloc[i+1].uer)})
docs='https://www.philadelphiafed.org/-/media/frbp/assets/surveys-and-data/survey-of-professional-forecasters/spf-documentation.pdf'
evidence={'status':canonical['status'],'methodology':canonical['methodology'],
 'independent_verification':'All 16 models checked using separate centered-sum OLS, HC1 covariance, R-squared and p-value calculations.',
 'source_files':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ai_file,med_file,*human_sources.values()]},
 'realization_timing':{'chosen':'Official SPF VAR1 at current survey t is the historical value for target quarter t−1 known at that survey. This is a real-time vintage, not a latest-revised outcome.','documentation':{'url':docs,'pages':[22,26,39,53],'summary':'The official documentation maps suffix1 to the prior-quarter historical observation and suffix2 to the current-quarter nowcast. Historical observations are the values available when questionnaires were sent. Real GDP levels can use different base years across survey vintages.'},'cached_R0_problem':'prepare_data.R lines173–175 shifts real-time prompt data forward one survey row. Its explicit qof_last_real_gdp metadata then dates RGDP one quarter earlier than the R0 target. Unemployment uses a monthly observation rather than the target quarter average. R0 is therefore not used here.','examples':alignment},
 'identity_decisions':{'raw_AI_rows':len(ai),'named_AI_rows':len(named),'duplicate_name_quarter_groups':len(duplicates),'conflicting_core_groups':sum(x['conflicting_core_forecasts'] for x in duplicates),'primary_rule':'Average duplicate named forecasts within each quarter, exclude No Name Provided','sensitivity_file':'duplicate_rule_sensitivity.json'},
 'limitations':['The original Human calculation remains unidentified; this is a transparent recalculation, not a claim that the missing source script has been found.','Averaging conflicting AI duplicates is an explicit analysis choice; first, last and exclusion alternatives are supplied.','Real GDP is a level in the base-year dollars of each survey vintage. Cross-vintage level revisions can include rebasing effects; no unsupported rescaling was applied.','Nowcast-to-nowcast changes refer to different target quarters, as the caption states; they are not fixed-target forecast revisions.'],
 'cell_ready_table':'verified_table.json','estimates':'verified_estimates.json','inputs':'verified_regression_inputs.parquet'}
(OUT/'verified_evidence.json').write_text(json.dumps(evidence,indent=2,ensure_ascii=False))
print(json.dumps({x['panel']+' '+x['variable']:{k:{a:x[k][a] for a in ['coefficient','se_HC1','N','R2']} for k in ['error','consensus']} for x in results},indent=2))
