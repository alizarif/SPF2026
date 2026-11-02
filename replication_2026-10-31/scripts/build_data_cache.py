#!/usr/bin/env python3
"""Extract reproducible numeric analysis caches without executing project R code.

Usage: python3 replication_2026-10-31/scripts/build_data_cache.py
Requires pandas, numpy, pyarrow, openpyxl, pyreadr >=0.5.8, and narwhals.
Optional PYREADR_EXTRA_PATH points to a temporary package directory.

Only selected objects are materialized from the R archives. The enormous saved
data_long object is skipped and reconstructed from data_wide after biography
strings have been removed. Cached values are preserved, not recalculated.
"""
from pathlib import Path
import os,sys,re,json,hashlib,argparse,time,gc
import numpy as np
import pandas as pd

extra=os.environ.get('PYREADR_EXTRA_PATH')
if extra:sys.path.insert(0,str(Path(extra).expanduser()))
import pyreadr

WORK=Path(__file__).resolve().parents[2]
SOURCE=WORK/'Simulating_SPF_processing/data'
OUT=WORK/'replication_2026-10-31/data_cache'
OUT.mkdir(parents=True,exist_ok=True)
TRAITS=['gender2','continent_origin','education_level','education_field','cohort','title2','affiliation_type2','social_media_status2']
FILES={
 'baseline':'baseline_data.rda', 'oos':'outofsample_data.rda',
 'generic':'generic_forecaster_data.rda', 'no_data':'generic_forecaster_no_data.rda',
 'no_realtime':'generic_forecaster_no_realtime_data.rda', 'recall':'recall_data.rda',
 'llama':'llama70b.rda','deepseek':'deepseek.rda','generic_n':'generic_N_forecaster_data.rda'}
RAW={
 'baseline':'merged_results_spf_format_2026_fixed.xlsx',
 'oos':'merged_results_spf_format_oos.xlsx',
 'generic':'generic_forecaster_results_fixed.xlsx',
 'no_data':'generic_forecaster_no_data_fixed.xlsx',
 'no_realtime':'generic_forecaster_no_realtime_fixed.xlsx',
 'recall':'merged_file_multivariable_recall_cleaned2.xlsx'}
def clean(df):
    df=df.copy()
    if 'date_q' in df:df['date_q']=pd.to_datetime(df['date_q'])
    for c in df.columns:
        if pd.api.types.is_object_dtype(df[c].dtype) or isinstance(df[c].dtype,pd.StringDtype):
            if df[c].map(lambda x:isinstance(x,str) or pd.isna(x)).all():df[c]=df[c].astype('category')
    return df
def write(df,name):
    df=clean(df);p=OUT/name;df.to_parquet(p,index=False,compression='zstd')
    return {'path':name,'rows':len(df),'columns':list(df.columns),'bytes':p.stat().st_size,
            'date_min':str(df.date_q.min().date()) if 'date_q' in df and len(df) else None,
            'date_max':str(df.date_q.max().date()) if 'date_q' in df and len(df) else None}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def source_info(p):return {'path':str(p.relative_to(WORK)),'bytes':p.stat().st_size,'sha256':digest(p)}
def build(name):
    p=SOURCE/FILES[name];t=time.time()
    use=['data_wide','data_ts','horizons','horizons_full','variables','survey_names','characteristics']
    if name in ['baseline','oos']:use+=['SPFmicrodata_long']
    o=pyreadr.read_r(p,use_objects=use)
    rec={'source':source_info(p),'r_header':pyreadr.read_metadata(p),'outputs':{},'checks':{}}
    wide=o['data_wide'];forecasts=[c for c in wide if re.fullmatch(r'[A-Z0-9]+_[AHR][0-4AB]',c)]
    keys=[c for c in ['date_q','Name']+TRAITS+['affiliation','is_first_time','interviews2'] if c in wide]
    wide=clean(wide[keys+forecasts])
    for c in forecasts:wide[c]=pd.to_numeric(wide[c],errors='coerce')
    rec['outputs']['wide']=write(wide,f'{name}_wide.parquet')
    rec['outputs']['ts']=write(o['data_ts'],f'{name}_ts.parquet')
    vars_=o['variables'].copy()
    names=dict(zip(vars_['variable'],vars_['variable_longname']))
    long=wide.melt(id_vars=[c for c in ['date_q','Name']+TRAITS if c in wide],value_vars=forecasts,var_name='id_forecast',value_name='value')
    parts=long.id_forecast.str.rsplit('_',n=1,expand=True)
    long['variable']=parts[0].astype('category');long['id']=parts[1].str[1:].astype('category')
    long['type']=parts[1].str[0].map({'A':'AI','H':'Human','R':'Realized'}).astype('category')
    long['type_ordered']=pd.Categorical(long['type'],categories=['Human','AI','Realized'],ordered=True)
    long['variable_name']=long['variable'].map(names)
    long['id_forecast']=long['id_forecast'].astype('category')
    rec['outputs']['long']=write(long,f'{name}_long.parquet')
    if 'SPFmicrodata_long' in o:rec['outputs']['microdata']=write(o['SPFmicrodata_long'],f'{name}_microdata.parquet')
    for obj in ['horizons','horizons_full','variables','survey_names','characteristics']:
        o[obj].to_csv(OUT/f'{name}_{obj}.csv',index=False)
    ts=clean(o['data_ts'])
    rec['checks']['wide_unique_name_quarter']=not wide.duplicated(['date_q','Name']).any()
    rec['checks']['wide_duplicated_name_quarter_rows']=int(wide.duplicated(['date_q','Name']).sum())
    rec['checks']['forecast_column_count']=len(forecasts)
    rec['checks']['ts_unique_keys']=not ts.duplicated(['date_q','type','id','variable']).any()
    rec['checks']['ts_variables']=sorted(ts.variable.astype(str).unique())
    rec['checks']['ts_horizons']=sorted(ts.id.astype(str).unique())
    rec['checks']['ts_winsorized_medians']=int((~np.isclose(ts['median'],ts['median_'],equal_nan=True)).sum())
    ai=long[long.type=='AI'].groupby(['date_q','variable','id'],observed=True)['value'].median().rename('reconstructed')
    chk=ts[ts.type=='AI'].merge(ai.reset_index(),on=['date_q','variable','id'],how='outer')
    diff=(chk['median']-chk['reconstructed']).abs()
    rec['checks']['ts_median_vs_wide_max_abs_difference']=float(diff.max())
    rec['checks']['ts_median_vs_wide_differences_gt_1e_8']=int((diff>1e-8).sum())
    rec['checks']['ts_median_missingness_differences']=int((chk['median'].isna()!=chk['reconstructed'].isna()).sum())
    rec['seconds']=round(time.time()-t,2)
    del o,wide,long,parts,ts,chk;gc.collect()
    return rec
def raw_auxiliary():
    p=SOURCE/RAW['baseline']
    df=pd.read_excel(p,usecols=['Name','Date_Q','Reasoning Response'])
    df=df.rename(columns={'Date_Q':'date_q','Reasoning Response':'reasoning'})
    rec={'reasoning_source':source_info(p),'reasoning':write(df,'baseline_reasoning.parquet')}
    raw=pd.read_excel(p)
    v=pd.read_csv(SOURCE/'data_overview.csv').dropna(subset=['SPF data name'])
    vm=dict(zip(v['AI output names'],v['SPF data name']))
    hm={'t':'0','t+1':'1','t+2':'2','t+3':'3','t+4':'4','y1':'A','y2':'B'}
    rename={}
    for col in raw.columns:
        if '_' not in col:continue
        var,hor=col.rsplit('_',1)
        if var in vm and hor in hm:rename[col]=vm[var]+'_A'+hm[hor]
    forecasts=raw[['Name','Date_Q']+list(rename)].rename(columns={'Date_Q':'date_q',**rename})
    for col in rename.values():forecasts[col]=pd.to_numeric(forecasts[col],errors='coerce')
    rec['raw_forecasts']=write(forecasts,'baseline_raw_forecasts.parquet')
    rec['raw_forecast_note']='All 5388 raw rows retained, including 80 No Name Provided records. Some final-paper analyses use this panel rather than the 5308-row cleaned panel.'
    old=pd.read_excel(SOURCE/'multivariable_SPF6.xlsx')
    old_rename={k:v for k,v in rename.items() if k in old}
    old_forecasts=old[['Name','Date_Q']+list(old_rename)].rename(columns={'Date_Q':'date_q',**old_rename})
    for col in old_rename.values():old_forecasts[col]=pd.to_numeric(old_forecasts[col],errors='coerce')
    rec['old_raw_source']=source_info(SOURCE/'multivariable_SPF6.xlsx')
    rec['old_raw_forecasts']=write(old_forecasts,'old_baseline_raw_forecasts.parquet')
    rec['old_participants']=write(old_forecasts[['Name','date_q']],'old_baseline_participants.parquet')
    frames=[]
    for var in ['CPI','UNEMP','RGDP','TBILL']:
        d=pd.read_excel(SOURCE/'SPFmicrodata.xlsx',sheet_name=var,usecols=['YEAR','QUARTER','ID','INDUSTRY']+[var+str(i) for i in range(1,7)])
        for c in d:d[c]=pd.to_numeric(d[c],errors='coerce')
        frames.append(d)
    native=frames[0]
    for d in frames[1:]:native=native.merge(d,on=['YEAR','QUARTER','ID','INDUSTRY'],validate='one_to_one')
    native['date_q']=pd.to_datetime(dict(year=native.YEAR,month=(native.QUARTER-1)*3+1,day=1))
    native=native.rename(columns={'ID':'SPF_human_id'})
    rec['human_native_source']=source_info(SOURCE/'SPFmicrodata.xlsx')
    rec['human_native_core']=write(native,'human_native_core.parquet')
    for f in ['data_overview.csv','realized_post2023q4.csv','macro_data_ts.csv','median_and_realtime_formatted.csv','SPF_full_ts.csv','merged_UR_LLM_all.csv']:
        d=pd.read_csv(SOURCE/f)
        # Preserve native source names/date representation in auxiliary files.
        d.to_parquet(OUT/('source_'+Path(f).stem+'.parquet'),index=False,compression='zstd')
    return rec
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--variants',nargs='+',default=['baseline','oos','generic','no_data','no_realtime','recall']);a=ap.parse_args()
    manifest_path=OUT/'provenance.json'
    manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else {'purpose':'Numerical replication caches, no source modifications, no API calls.','variants':{},'scope_notes':[
       'R cached numerical values are authoritative for reproducing the supplied pipeline; long panels are reconstructed from cached wide panels.',
       'No biography/prompt strings in wide/long caches. Eight standardized traits retained; reasoning is separately cached.',
       'Units are unchanged. Real GDP and other level/index forecasts are not converted to growth. CPI/PCE rates are already annualized percentage points.',
       'median is untrimmed cross-sectional median. median_ clips to realized MEAN +/-3 sample SD within each survey/variable/horizon, per source code. Paper prose says MEDIAN +/-3SD: discrepancy retained and flagged.',
       'OOS archive includes 2023 and 2024; final-paper OOS comparisons must restrict the evaluation sample to 2024. Preserve 2023 for transition plots.',
       'Realizations use next survey vintage (one-quarter shift of median_and_realtime_formatted.csv), PGDP from P24Q3, then manually entered realized_post2023q4.csv through2025Q3. Annual realized values are missing.',
       'Human median comes from SPF_full_ts, but human means/quantiles come from anonymous microdata, not named forecaster identities.',
       'Recall cache combines the older current-quarter-only recall workbook for22variables with BAA nowcasts from the later generic_forecaster_recall_fixed.xlsx, verified directly. Current source R driver does not fully express this hybrid.'
    ]}
    manifest['auxiliary']=raw_auxiliary()
    for name in a.variants:
        manifest['variants'][name]=build(name)
        manifest_path.write_text(json.dumps(manifest,indent=2,default=str))
        print(name,manifest['variants'][name]['seconds'],manifest['variants'][name]['checks'],flush=True)
    print('COMPLETE',flush=True)
