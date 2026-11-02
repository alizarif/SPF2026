"""Table B.14: raw-data, caption-faithful recalculation and historical diagnostics.

No network calls and no writes outside this investigation folder. Published values
are used only for the final comparison, never to select a calculation rule.
The primary output uses the current driver-selected AI workbook, all 2024 forecast
origins, native SPF columns h+2, and actuals at origin+h. For each quarter, the best
available individual forecast is selected separately within each survey. The test
uses absolute errors, pairs by quarter, and enumerates all 2**n label swaps.
"""
from pathlib import Path
import copy,hashlib,itertools,json,re,warnings
from decimal import Decimal, ROUND_HALF_EVEN
import numpy as np
import pandas as pd
import fitz
warnings.filterwarnings('ignore')
OUT=Path(__file__).resolve().parent; RUN=OUT.parent; WORK=RUN.parent
SRC=WORK/'Simulating_SPF_processing/data'; FUN=WORK/'Simulating_SPF_processing/functions'; CACHE=RUN/'data_cache'
META=pd.read_csv(CACHE/'oos_variables.csv').set_index('variable')
VS=[v for v in META.index if v!='BAABOND']; HS=[0,1,2]
ORIGINS=pd.date_range('2024-01-01','2024-10-01',freq='QS')
ORIGINAL=json.loads((RUN/'tables_review/table_data.json').read_text())['TB14']
TARGET={(c['audit_row'],c['audit_column']):c for r in ORIGINAL['rows'] for c in r.get('cells',[]) if 'audit_column'in c}
source_paths=[SRC/'merged_results_spf_format_oos.xlsx',SRC/'merged_file_outofsample_2024_SPF6_cleaned.xlsx',SRC/'SPFmicrodata.xlsx',SRC/'SPF_full_ts.csv',SRC/'realized_post2023q4.csv',SRC/'realized_post2023q4.numbers',FUN/'prepare_data.R',FUN/'tab_forecast_accuracy_best_outofsample.R',FUN/'tab_forecast_accuracy_outofsample.R',FUN/'randomization_test.R',WORK/'Simulating_SPF_processing/tables_figures_all.R',WORK/'Simulating_SPF_processing/tables/forecast_accuracy_best_forecasters_oos.txt',WORK/'latest draft/tables/forecast_accuracy_best_forecasters_oos.txt']
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source_hashes={str(p.relative_to(WORK)):digest(p) for p in source_paths}

def quarter(value):return str(pd.Timestamp(value).to_period('Q'))
def field(v,h):return str(META.loc[v,'variable_AI_output'])+'_'+('t' if h==0 else f't+{h}')
def fmt(value):
 s=str(Decimal(str(value)).quantize(Decimal('0.01'),rounding=ROUND_HALF_EVEN))
 return '0.00' if s=='-0.00' else s

def read_ai(filename,current=False):
 raw=pd.read_excel(SRC/filename);raw=raw.copy();raw['date_q']=pd.to_datetime(raw.Date_Q)
 info={'file':filename,'raw_rows':len(raw),'names':int(raw.Name.nunique()),'date_counts':{quarter(k):int(v)for k,v in raw.groupby('date_q').size().items()},'raw_duplicate_name_dates':int(raw.duplicated(['Name','date_q']).sum())}
 excluded=[]
 if current:
  good=pd.to_numeric(raw['GDP Price Index_t'],errors='coerce')<10000
  excluded+=raw.loc[~good,['Name','date_q']].assign(reason='GDP price nowcast >=10000 or missing').to_dict('records');raw=raw[good].copy()
  rescaled=[]
  for h in ['t','t+1','t+2','t+3','t+4','y1','y2']:
   c='GDP Price Index_'+h;s=pd.to_numeric(raw[c],errors='coerce');mask=s<10
   rescaled.append({'column':c,'rows':int(mask.sum())});raw.loc[mask,c]=100*s[mask]
  info['gdp_price_scale_corrections']=rescaled
 named=raw.Name.ne('No Name Provided');excluded+=raw.loc[~named,['Name','date_q']].assign(reason='No Name Provided').to_dict('records');raw=raw[named].copy()
 data={'date_q':raw.date_q,'Name':raw.Name}
 for v in VS:
  for h in HS:data[f'{v}_A{h}']=pd.to_numeric(raw[field(v,h)],errors='coerce')
 d=pd.DataFrame(data).reset_index(drop=True)
 info.update(clean_rows=len(d),rows_2024=int(d.date_q.isin(ORIGINS).sum()),clean_date_counts={quarter(k):int(v)for k,v in d.groupby('date_q').size().items()},excluded_rows=[{**x,'date_q':quarter(x['date_q'])}for x in excluded])
 return d,info
AI,ai_info=read_ai('merged_results_spf_format_oos.xlsx',True)
OLD,old_info=read_ai('merged_file_outofsample_2024_SPF6_cleaned.xlsx')
actual_raw=pd.read_csv(SRC/'realized_post2023q4.csv').set_index('variable')
ACTUAL=actual_raw.T;ACTUAL.index=pd.PeriodIndex([str(s).upper()for s in ACTUAL.index],freq='Q').to_timestamp();ACTUAL=ACTUAL.apply(pd.to_numeric,errors='coerce')
HMED=pd.read_csv(SRC/'SPF_full_ts.csv');HMED['date_q']=pd.PeriodIndex(HMED.date_q.str.replace(' ',''),freq='Q').to_timestamp();HMED=HMED.set_index('date_q')
MICRO={};cache_micro=pd.read_parquet(CACHE/'oos_microdata.parquet');micro_checks=[]
with pd.ExcelFile(SRC/'SPFmicrodata.xlsx') as xf:
 for v in VS:
  d=pd.read_excel(xf,sheet_name=v);d=d[d.YEAR==2024].copy();d['date_q']=pd.to_datetime(dict(year=d.YEAR,month=(d.QUARTER-1)*3+1,day=1));MICRO[v]=d
  for h in HS:
   raw=d[['date_q','ID',v+str(h+2)]].rename(columns={'ID':'SPF_human_id',v+str(h+2):'raw'})
   cache=cache_micro[(cache_micro.variable==v)&(cache_micro.id==str(h))&cache_micro.date_q.isin(ORIGINS)][['date_q','SPF_human_id','value']]
   merged=raw.merge(cache,on=['date_q','SPF_human_id'],how='outer',validate='one_to_one',indicator=True)
   ok=merged._merge.eq('both').all() and np.allclose(pd.to_numeric(merged.raw,errors='coerce'),merged.value,equal_nan=True,atol=1e-10,rtol=0)
   assert ok,(v,h,'microdata/cache disagreement');micro_checks.append({'variable':v,'horizon':h,'raw_rows':len(raw),'cache_rows':len(cache),'exact_match':bool(ok)})
cache_w=pd.read_parquet(CACHE/'oos_wide.parquet')
joined=AI.merge(cache_w,on=['date_q','Name'],suffixes=('_raw','_cache'),validate='one_to_one')
assert len(joined)==len(AI)==len(cache_w)
for v in VS:
 for h in HS:assert np.allclose(joined[f'{v}_A{h}_raw'],joined[f'{v}_A{h}_cache'],equal_nan=True,rtol=0,atol=1e-10)
cache_t=pd.read_parquet(CACHE/'oos_ts.parquet');actual_checks=[]
for v in VS:
 for h in HS:
  for date in ORIGINS:
   target=date+pd.DateOffset(months=h*3);raw=ACTUAL.loc[target,v]
   z=cache_t[(cache_t.type=='Human')&(cache_t.variable==v)&(cache_t.id==str(h))&(cache_t.date_q==date)].iloc[0]
   assert np.isclose(raw,z.realized,equal_nan=True,rtol=0,atol=1e-10)
   median=float(HMED.loc[date,v+str(h+2)])
   assert np.isclose(median,z['median'],equal_nan=True,rtol=0,atol=1e-10)
   actual_checks.append(dict(variable=v,horizon=h,forecast_origin=quarter(date),target_quarter=quarter(target),actual=raw,human_median=median,actual_and_human_median_match_cache=True))

def exact_test(a,b):
 a=np.asarray(a,float);b=np.asarray(b,float);m=np.isfinite(a)&np.isfinite(b);d=a[m]-b[m];n=len(d)
 if not n:return dict(p_value=None,n=0,extreme=None,total=None)
 observed=abs(d.sum());signs=np.array(list(itertools.product([-1,1],repeat=n)),float);sim=np.abs(signs@d)
 # Small arithmetic tolerance includes the mathematically identical endpoint permutations.
 tol=1e-12*max(1,float(np.sum(np.abs(d))));extreme=int(np.sum(sim>=observed-tol));total=2**n
 mc=np.random.default_rng(20261101+n).choice([-1,1],size=(10000,n));mce=int(np.sum(abs(mc@d)>=observed-tol))
 return dict(p_value=extreme/total,n=n,extreme=extreme,total=total,observed_abs_sum=float(observed),tie_tolerance=tol,mc_draws=10000,mc_extreme=mce,mc_p=mce/10000)

def quarter_best(vintage,forecast):
 records=[];results=[]
 for v in VS:
  for h in HS:
   q=[]
   for date in ORIGINS:
    target=date+pd.DateOffset(months=h*3);actual=ACTUAL.loc[target,v]
    a=forecast[forecast.date_q==date][['Name',f'{v}_A{h}']].copy();a['error']=(a[f'{v}_A{h}']-actual).abs()
    u=MICRO[v][MICRO[v].date_q==date][['ID',v+str(h+2)]].copy();u['error']=(pd.to_numeric(u[v+str(h+2)],errors='coerce')-actual).abs()
    av=a.error.min();uv=u.error.min();aiwin=a[np.isclose(a.error,av,rtol=0,atol=1e-10)];hu=u[np.isclose(u.error,uv,rtol=0,atol=1e-10)]
    # Recompute the minimum with decimal source values. Float subtraction of
    # large levels otherwise moves exact half-cent means to either side of a tie.
    adec=min((abs(Decimal(str(f))-Decimal(str(actual))) for f in a[f'{v}_A{h}'].dropna()),default=None) if np.isfinite(actual) else None
    udec=min((abs(Decimal(str(f))-Decimal(str(actual))) for f in pd.to_numeric(u[v+str(h+2)],errors='coerce').dropna()),default=None) if np.isfinite(actual) else None
    rec={'vintage':vintage,'variable':v,'variable_name':META.loc[v,'variable_longname'],'horizon':h,'forecast_origin':quarter(date),'target_quarter':quarter(target),'actual':actual,'ai_candidates':int(a[f'{v}_A{h}'].notna().sum()),'human_candidates':int(u[v+str(h+2)].notna().sum()),'ai_absolute_error':av,'human_absolute_error':uv,'ai_winning_names':aiwin.Name.tolist(),'ai_winning_forecasts':aiwin[f'{v}_A{h}'].tolist(),'human_winning_ids':hu.ID.astype(int).tolist(),'human_winning_forecasts':pd.to_numeric(hu[v+str(h+2)]).tolist(),'eligible':bool(np.isfinite(av)and np.isfinite(uv))}
    rec.update(ai_absolute_error_float=av,human_absolute_error_float=uv,ai_absolute_error_decimal=str(adec)if adec is not None else None,human_absolute_error_decimal=str(udec)if udec is not None else None)
    if adec is not None:rec['ai_absolute_error']=float(adec)
    if udec is not None:rec['human_absolute_error']=float(udec)
    records.append(rec)
    if rec['eligible']:q.append(rec)
   aa=[x['ai_absolute_error']for x in q];bb=[x['human_absolute_error']for x in q]
   amean=sum((Decimal(r['ai_absolute_error_decimal'])for r in q),Decimal(0))/Decimal(len(q))
   hmean=sum((Decimal(r['human_absolute_error_decimal'])for r in q),Decimal(0))/Decimal(len(q))
   test=exact_test(aa,bb);results.append(dict(vintage=vintage,variable=v,variable_name=META.loc[v,'variable_longname'],horizon=h,ai_mae=float(amean),human_mae=float(hmean),ai_mae_decimal=str(amean),human_mae_decimal=str(hmean),ai_mae_float_original=float(np.mean([r['ai_absolute_error_float']for r in q])),human_mae_float_original=float(np.mean([r['human_absolute_error_float']for r in q])),**test))
 return records,results
quarter_records,verified=quarter_best('current',AI);old_quarters,old_caption=quarter_best('historical',OLD)
# Independent scalar check: minimum over explicit lists, then arithmetic sum / N.
for z in verified:
 q=[r for r in quarter_records if r['variable']==z['variable']and r['horizon']==z['horizon']and r['eligible']]
 assert np.isclose(sum(r['ai_absolute_error']for r in q)/len(q),z['ai_mae'],rtol=0,atol=1e-12)
 assert np.isclose(sum(r['human_absolute_error']for r in q)/len(q),z['human_mae'],rtol=0,atol=1e-12)
 assert z['extreme']/z['total']==z['p_value']

# Historical cutoffs are inferred from archived figures, not optimized for table fit.
figure_evidence=[]
for v in VS:
 path=WORK/'Simulating_SPF_processing/figures'/f'forecast_error_oos_{v}_2.pdf'
 D=fitz.open(path);p=D[0];spans=[s for b in p.get_text('dict')['blocks']for l in b.get('lines',[])for s in l['spans']]
 years=[s for s in spans if re.fullmatch(r'20\d\d',s['text'])]
 x=np.array([(s['bbox'][0]+s['bbox'][2])/2 for s in years]);day=np.array([pd.Timestamp(s['text']+'-01-01').toordinal()for s in years]);slope,intercept=np.polyfit(x,day,1)
 paths=[g for g in p.get_drawings()if len(g['items'])>=8 and g['items'][0][0]=='l']
 for g in paths:
  last=g['items'][-1][-1].x;ordinal=round(slope*last+intercept);date=pd.Timestamp.fromordinal(ordinal)
  nearest=min(pd.date_range('2023-01-01','2024-10-01',freq='QS'),key=lambda d:abs((date-d).days))
  figure_evidence.append(dict(variable=v,path=str(path.relative_to(WORK)),survey='Human'if g['width']>2 else'AI',last_forecast_origin=quarter(nearest),last_target_quarter=quarter(nearest+pd.DateOffset(months=6)),date_reconstruction_error_days=abs((date-nearest).days)))
cutoffs={v:pd.Period(next(x['last_target_quarter']for x in figure_evidence if x['variable']==v and x['survey']=='Human'),freq='Q').to_timestamp()for v in VS}
# Historical R code selects a single best name over time, but compares Human medians
# even on rows where that name's AI forecast is NA. Its tests use median errors.
history=[];historical_quarters=[]
for v in VS:
 for h in HS:
  dates=ORIGINS;targets=dates+pd.DateOffset(months=h*3);actual=pd.Series([ACTUAL.loc[t,v]if t<=cutoffs[v]else np.nan for t in targets],index=dates)
  d=OLD[OLD.date_q.isin(dates)].copy();d['error']=d[f'{v}_A{h}']-d.date_q.map(actual)
  weights=d.groupby('date_q').size();rank=d.groupby('Name',sort=True).apply(lambda g:np.average(g.error.dropna().abs(),weights=g.loc[g.error.notna(),'date_q'].map(weights))if g.error.notna().any()else np.nan)
  best=rank.idxmin();selected=d[d.Name==best].set_index('date_q').reindex(dates)
  ai=selected.error;human=pd.to_numeric(HMED.loc[dates,v+str(h+2)],errors='coerce');raw_human_error=human-actual
  sd=actual.std();mu=actual.mean();clipped=human.clip(mu-3*sd,mu+3*sd)if np.isfinite(sd)else human
  median_ai=d.groupby('date_q')[f'{v}_A{h}'].median().reindex(dates);clipped_ai=median_ai.clip(mu-3*sd,mu+3*sd)if np.isfinite(sd)else median_ai
  median_signed_test=exact_test((clipped_ai-actual).values,(clipped-actual).values)
  best_loss_test=exact_test(ai.abs().values,raw_human_error.abs().values)
  z=dict(variable=v,variable_name=META.loc[v,'variable_longname'],horizon=h,selected_name=best,ai_mae=float(ai.abs().mean()),human_median_mae=float(raw_human_error.abs().mean()),human_clipped_median_mae=float((clipped-actual).abs().mean()),ai_N=int(ai.count()),human_N=int(actual.count()),actual_cutoff=quarter(cutoffs[v]),source_code_test_median_signed=median_signed_test,corrected_test_best_ai_vs_median_mae=best_loss_test)
  history.append(z)
  for date in dates:historical_quarters.append(dict(variable=v,horizon=h,forecast_origin=quarter(date),target_quarter=quarter(date+pd.DateOffset(months=h*3)),selected_name=best,actual=actual.loc[date],selected_ai_error=ai.loc[date],human_median_error=raw_human_error.loc[date],human_clipped_error=(clipped-actual).loc[date],median_ai_error=(clipped_ai-actual).loc[date]))

def output_json(name,value):
 # JSON standard: unavailable actuals are null, not NaN.
 text=json.dumps(value,indent=2,default=lambda x:int(x)if isinstance(x,np.integer)else float(x)if isinstance(x,np.floating)else str(x))
 text=re.sub(r'\bNaN\b','null',text);(OUT/name).write_text(text)
verified_by={(z['variable_name'],z['horizon']):z for z in verified}
canonical=copy.deepcopy(ORIGINAL);cell_audit=[];boundaries=[]
for row in canonical['rows']:
 for cell in row.get('cells',[]):
  if 'audit_column'not in cell:continue
  m=re.fullmatch(r'h(\d) (AI|Human|p)',cell['audit_column']);h=int(m[1]);survey=m[2];z=verified_by[(cell['audit_row'],h)]
  val=z[{'AI':'ai_mae','Human':'human_mae','p':'p_value'}[survey]]
  stars=int(val<=.1)+int(val<=.05)+int(val<=.01)if survey=='p'else 0
  cell.update(replicated=val,precision=2,starsreplicated=stars,replicated_display=fmt(val)+'*'*stars,numeric_mismatch=fmt(cell['original'])!=fmt(val),stars_mismatch=cell.get('starsoriginal',0)!=stars)
  cell['mismatch']=cell['numeric_mismatch']or cell['stars_mismatch'];cell['verification_method']='caption: best individual forecast per survey, quarter, variable and horizon; exact paired MAE test'
  cell_audit.append({'item':'TB14','row':cell['audit_row'],'column':cell['audit_column'],'original':cell['original'],'replicated':val,'original_display':cell['original_display'],'replicated_display':cell['replicated_display'],'mismatch':cell['mismatch'],'N':z['n'],'exact_test_extreme':z['extreme']if survey=='p'else None,'exact_test_total':z['total']if survey=='p'else None})
  if abs(abs(val*100)%1-.5)<1e-7:boundaries.append({'row':cell['audit_row'],'column':cell['audit_column'],'value':val,'repr':repr(val),'display':fmt(val),'published':cell['original_display']})
canonical['notes']=[];canonical['method_evidence']={'method':'caption_accurate_current_raw_exact_p','forecast_origins':'2024Q1-2024Q4','horizons':[0,1,2],'target_alignment':'origin + h quarters','selection':'minimum individual absolute error separately in each survey and quarter','test':'two-sided exact paired sign-flip of absolute-error differences; all 2^N assignments','input_vintage':'current driver-selected OOS workbook; source cleaning rules applied','display_rounding':'MAEs recomputed from Decimal(str(source forecast)) and Decimal(str(actual)), then decimal half-even to two places; original float calculations retained separately','not_a_recovery_of_published_pipeline':True}
# Evaluate historical fit only after the candidate methods were computed.
hist_audit=[]
for z in history:
 for kind,key in [('AI','ai_mae'),('Human raw median','human_median_mae'),('Human clipped median','human_clipped_median_mae')]:
  survey='AI'if kind=='AI'else'Human';orig=TARGET[(z['variable_name'],f"h{z['horizon']} {survey}")]['original'];val=z[key]
  hist_audit.append(dict(variable=z['variable'],horizon=z['horizon'],kind=kind,published=orig,computed=val,within_half_display_unit=bool(abs(orig-val)<=.005000001),published_display=fmt(orig),computed_display=fmt(val)))
fit={kind:sum(x['within_half_display_unit']for x in hist_audit if x['kind']==kind)for kind in ['AI','Human raw median','Human clipped median']}
output_json('verified_table.json',canonical);output_json('verified_results.json',verified);output_json('verified_quarter_results.json',quarter_records);output_json('verified_cell_audit.json',cell_audit);output_json('historical_code_results.json',history);output_json('historical_quarter_results.json',historical_quarters);output_json('historical_fit.json',hist_audit);output_json('old_workbook_caption_results.json',old_caption);output_json('old_workbook_caption_quarters.json',old_quarters);output_json('rounding_boundaries.json',boundaries);output_json('archived_figure_cutoff_evidence.json',figure_evidence)
pd.DataFrame(verified).to_csv(OUT/'verified_results.csv',index=False);pd.DataFrame(quarter_records).to_csv(OUT/'verified_quarter_results.csv',index=False);pd.DataFrame(cell_audit).to_csv(OUT/'verified_cell_audit.csv',index=False)
output_json('raw_validation.json',dict(current_ai=ai_info,historical_ai=old_info,ai_clean_rows_all66_columns_match_saved_cache=True,human_microdata_checks=micro_checks,actual_and_median_checks=actual_checks))
unchanged=all(digest(WORK/k)==h for k,h in source_hashes.items());assert unchanged
output_json('source_provenance.json',{'sha256':source_hashes,'all_source_files_unchanged':unchanged})
summary={'primary_method':'Caption-accurate recalculation using current raw data and exact paired MAE tests','table':'B.14','horizons':[0,1,2],'quarter_records':len(quarter_records),'eligible_quarter_records':sum(x['eligible']for x in quarter_records),'tests':len(verified),'sample_sizes':dict(pd.Series([x['n']for x in verified]).value_counts().sort_index().items()),'minimum_exact_p':min(x['p_value']for x in verified),'mismatching_printed_cells':sum(x['mismatch']for x in cell_audit),'numeric_cells':len(cell_audit),'historical_ai_mae_matches_out_of66':fit['AI'],'historical_human_raw_mae_matches_out_of66':fit['Human raw median'],'historical_human_clipped_mae_matches_out_of66':fit['Human clipped median'],'all_source_files_unchanged':unchanged}
output_json('investigation_summary.json',summary);print(json.dumps(summary,indent=2,default=int))
