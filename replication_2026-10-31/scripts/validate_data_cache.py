#!/usr/bin/env python3
"""Compare cached AI forecasts to the workbook inputs named by the R driver.
No source/cached values are altered. Writes explicit reconciliation evidence.
"""
from pathlib import Path
import json,hashlib,numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[2];S=ROOT/'Simulating_SPF_processing/data';O=ROOT/'replication_2026-10-31/data_cache'
sources={'baseline':'merged_results_spf_format_2026_fixed.xlsx','oos':'merged_results_spf_format_oos.xlsx','generic':'generic_forecaster_results_fixed.xlsx','no_data':'generic_forecaster_no_data_fixed.xlsx','no_realtime':'generic_forecaster_no_realtime_fixed.xlsx','recall':'merged_file_multivariable_recall_cleaned2.xlsx'}
hm={'0':'t','1':'t+1','2':'t+2','3':'t+3','4':'t+4','A':'y1','B':'y2'}
report={}
for n,f in sources.items():
    v=pd.read_csv(O/f'{n}_variables.csv');vm=dict(zip(v.variable,v.variable_AI_output))
    c=pd.read_parquet(O/f'{n}_wide.parquet');raw=pd.read_excel(S/f)
    r={'raw_rows':len(raw),'cached_rows':len(c),'excluded_No_Name_Provided':int(raw.Name.eq('No Name Provided').sum()),'source':f,'source_sha256':hashlib.sha256((S/f).read_bytes()).hexdigest()}
    raw=raw[raw.Name!='No Name Provided'].copy()
    if n=='oos':
        r['excluded_GDP_Price_Index_ge_10000_or_missing']=int((~raw['GDP Price Index_t'].lt(10000)).sum())
        raw=raw[raw['GDP Price Index_t'].lt(10000)].copy()
        for h in hm.values():
            col='GDP Price Index_'+h
            raw.loc[raw[col].lt(10),col]*=100
    raw['date_q']=pd.to_datetime(raw.Date_Q)
    raw['occ']=raw.groupby(['Name','date_q']).cumcount();c['occ']=c.groupby(['Name','date_q'],observed=True).cumcount()
    keys=['Name','date_q','occ'];rn={}
    missing=[]
    for col in c.columns:
        if '_A' not in col:continue
        var,hor=col.rsplit('_A',1)
        if var not in vm or hor not in hm:continue
        orig=vm[var]+'_'+hm[hor]
        if orig in raw:rn[orig]=col
        else:missing.append({'cache_column':col,'nonmissing':int(c[col].notna().sum()),'expected_workbook_column':orig})
    rr=raw[keys+list(rn)].rename(columns=rn)
    m=c[keys+list(rn.values())].merge(rr,on=keys,how='outer',suffixes=('_cache','_raw'),indicator=True)
    r['row_merge']=m['_merge'].value_counts().to_dict();r['cached_columns_absent_from_workbook']=missing
    mismatch=[]
    for col in rn.values():
        a=pd.to_numeric(m[col+'_cache'],errors='coerce');b=pd.to_numeric(m[col+'_raw'],errors='coerce')
        bad=~np.isclose(a,b,equal_nan=True,rtol=0,atol=1e-8)
        if bad.any():mismatch.append({'column':col,'count':int(bad.sum()),'max_abs_difference':float((a-b).abs().max()),'examples':m.loc[bad,keys+[col+'_cache',col+'_raw']].head(3).to_dict('records')})
    r['numeric_columns_compared']=len(rn);r['mismatching_columns']=mismatch
    ts=pd.read_parquet(O/f'{n}_ts.parquet');clip=ts.loc[~np.isclose(ts['median'],ts['median_'],equal_nan=True),['date_q','type','variable','id','median','median_']]
    clip.to_csv(O/f'{n}_clipped_medians.csv',index=False)
    r['clipped_medians']=len(clip);r['clipped_medians_reported_horizons']=int(clip.id.isin(['0','1','4']).sum())
    report[n]=r
    print(n,'rows',r['row_merge'],'columns',len(rn),'mismatches',len(mismatch),'missingcols',missing,flush=True)
w=pd.read_parquet(O/'recall_wide.parquet')[['date_q','BAABOND_A0']]
later=pd.read_excel(S/'generic_forecaster_recall_fixed.xlsx',usecols=['Date_Q','BAA Corp Bond Yield_t']).rename(columns={'Date_Q':'date_q','BAA Corp Bond Yield_t':'BAA_later'})
later.date_q=pd.to_datetime(later.date_q);m=w.merge(later,on='date_q',how='left')
report['recall']['BAA_later_recall_workbook_match']={'rows':len(m),'mismatches':int((~np.isclose(m.BAABOND_A0,m.BAA_later,equal_nan=True)).sum()),'source':'generic_forecaster_recall_fixed.xlsx','source_sha256':hashlib.sha256((S/'generic_forecaster_recall_fixed.xlsx').read_bytes()).hexdigest()}
(O/'raw_reconciliation.json').write_text(json.dumps(report,indent=2,default=str))
