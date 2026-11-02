"""Recompute core paper tables from the raw-reconciled numerical cache.
Target PDF cells are read only AFTER calculations and are used solely for audit.
Python port of supplied R; deterministic Monte Carlo seed, no external services.
"""
from pathlib import Path
import json,re,warnings,os
import numpy as np
import pandas as pd
import fitz
from scipy.stats import binom
from render_helpers import render_table
warnings.filterwarnings('ignore',category=RuntimeWarning)
ROOT=Path(__file__).resolve().parents[1]; SRC=ROOT.parent
CACHE=ROOT/'data_cache'; OUT=ROOT/'reproduced'/'tables'; OUT.mkdir(parents=True,exist_ok=True)
PDF=Path(os.environ.get('SPF_SOURCE_PDF', SRC/'paper/predictable_forecasters.pdf')).expanduser()
RNG=np.random.default_rng(20261031); NSIM=10000
META=pd.read_csv(CACHE/'baseline_variables.csv'); VS=META.variable.tolist(); NAMES=dict(zip(VS,META.variable_longname))
W=pd.read_parquet(CACHE/'baseline_wide.parquet'); TS=pd.read_parquet(CACHE/'baseline_ts.parquet')
OOS=pd.read_parquet(CACHE/'oos_ts.parquet'); OW=pd.read_parquet(CACHE/'oos_wide.parquet')
RESULTS={}; CELL_AUDIT=[]

def pair(ts,v,h,field='forecast_error'):
 d=ts[(ts.variable==v)&(ts.id==str(h))]
 return d.pivot(index='date_q',columns='type',values=field).reindex(columns=['AI','Human'])

def swap_p(a,b,baseline=None):
 a=np.array(a,float);b=np.array(b,float)
 mask=RNG.random((NSIM,len(a)))<.5
 sa=np.where(mask,a,b);sb=np.where(mask,b,a)
 if baseline is None:
  obs=np.nanmean(a)-np.nanmean(b); sim=np.nanmean(sa,axis=1)-np.nanmean(sb,axis=1)
 else:obs=np.nanmean(a)-baseline;sim=np.nanmean(sa,axis=1)-baseline
 valid=np.isfinite(sim)
 return float(np.mean(np.abs(sim[valid])>=abs(obs))) if valid.any() else np.nan

def weighted_mae(x,weights):
 m=np.isfinite(x)&np.isfinite(weights)&(np.asarray(weights)>0);return float(np.average(np.abs(np.asarray(x)[m]),weights=np.asarray(weights)[m])) if m.any() else np.nan

def target(i,n):
 doc=fitz.open(PDF);rows=[];stars=[]
 for b in doc[i-1].get_text('blocks'):
  s=re.findall(r'[-−]?\d+\.\d+|(?<![A-Za-z0-9])5308',b[4])
  if len(s)==n:
   rows.append([float(x.replace('−','-')) for x in s]);stars.append([len(x) for x in re.findall(r'\d+\.\d+(⋆*)',b[4])])
 return np.array(rows),stars

def audit(id,values,page,pcols=(),note='',labels=None,columns=None,stars=None):
 vals=np.array(values,float); tar,tarstars=target(page,vals.shape[1]);assert tar.shape==vals.shape,(id,tar.shape,vals.shape)
 labels=labels or [NAMES[v] for v in VS]
 cols=columns or [str(i) for i in range(vals.shape[1])]
 counts={'point_total':0,'point_match':0,'p_total':0,'p_rounded_match':0,'p_mc_compatible':0}
 for r in range(len(vals)):
  for c in range(vals.shape[1]):
   value=vals[r,c]; expected=tar[r,c];err=abs(value-expected);rounded=bool(err<=.005000001)
   is_p=c in pcols;tol=max(.015,3*np.sqrt(2*expected*(1-expected)/NSIM)+.005) if is_p else .005000001
   match=bool(err<=tol)
   if is_p:counts['p_total']+=1;counts['p_rounded_match']+=int(rounded);counts['p_mc_compatible']+=int(match)
   else:counts['point_total']+=1;counts['point_match']+=int(rounded)
   CELL_AUDIT.append({'item':id,'row':labels[r],'column':cols[c],'original':expected,'replicated':float(value),'absolute_difference':float(err),'kind':'p-value' if is_p else 'point estimate','rounded_match':rounded,'tolerance':float(tol),'within_tolerance':match})
 extra={}
 if pcols:
  pst=np.array([[int(vals[i,j]<=.1)+int(vals[i,j]<=.05)+int(vals[i,j]<=.01) for j in pcols] for i in range(len(vals))])
  target_pst=np.array(tarstars)[:,list(pcols)]
  extra={'stars_total':int(pst.size),'stars_match':int(np.sum(pst==target_pst))}
  for i in range(len(vals)):
   for k,j in enumerate(pcols):
    CELL_AUDIT.append({'item':id,'row':labels[i],'column':cols[j]+' stars','original':int(target_pst[i,k]),'replicated':int(pst[i,k]),'absolute_difference':int(abs(pst[i,k]-target_pst[i,k])),'kind':'stars','rounded_match':bool(pst[i,k]==target_pst[i,k]),'tolerance':0,'within_tolerance':bool(pst[i,k]==target_pst[i,k])})
 if stars is not None:
  st=np.array(stars);st=st[:-1] if labels[-1]=='Average' else st;tt=np.array(tarstars)[:len(st)];extra={'stars_total':int(st.size),'stars_match':int(np.sum(st==tt))}
  for i in range(len(st)):
   for j in range(st.shape[1]):
    CELL_AUDIT.append({'item':id,'row':labels[i],'column':cols[j]+' stars','original':int(tt[i,j]),'replicated':int(st[i,j]),'absolute_difference':int(abs(st[i,j]-tt[i,j])),'kind':'stars','rounded_match':bool(st[i,j]==tt[i,j]),'tolerance':0,'within_tolerance':bool(st[i,j]==tt[i,j])})
 status='Numerical match' if counts['point_match']==counts['point_total'] else 'Partial numerical match'
 if counts['p_total'] and counts['p_mc_compatible']<counts['p_total']:status='Partial numerical match'
 rows=[]
 for i,row in enumerate(vals):
  cells=[]
  for j,x in enumerate(row):
   s=f'{0 if abs(x)<.005 else x:.2f}' if np.isfinite(x) else 'NA'
   if id=='T3' and j==0:s=str(int(x))
   if stars is not None and i<len(stars):s+='*'*int(stars[i][j])
   elif j in pcols:s+='*'*(int(x<=.1)+int(x<=.05)+int(x<=.01))
   cells.append(s)
  rows.append([labels[i]]+cells)
 path=render_table(f'{id} | Recomputed from supplied data',['Variable']+cols,rows,OUT/f'{id}_replicated.png',notes=note)
 RESULTS[id]={'id':id,'status':status,'counts':counts,**extra,'notes':[note],'paths':[path],'values':vals.tolist(),'rows':labels,'columns':cols}
 print(id,counts,extra,flush=True)
 return counts

# Descriptive tables use source definitions, not the target PDF.
def strip_tex(s):
 s=s.replace('\\&','&').replace('\\%','%').replace('\\_','_').replace('\\\\','').strip()
 return re.sub(r'\\textbf\{([^}]*)\}',r'\1',s)
for id,source,lo,hi in [('T1',SRC/'latest draft'/'May 2026 version.tex',688,717),('T2',SRC/'latest draft'/'tables'/'characteristics_definitions.txt',0,100)]:
 lines=source.read_text().splitlines()[lo:hi];rows=[]
 for l in lines:
  if ' & ' in l:
   row=[strip_tex(x) for x in l.split(' & ',1)]
   if row[0] not in ['Characteristic','Variable']:rows.append(row)
 path=render_table(f'{id} | Definitions rebuilt from manuscript source',['Variable' if id=='T1' else 'Characteristic','Definition'],rows,OUT/f'{id}_replicated.png',notes='Documentary source reproduction. Definitions are transcribed from the supplied manuscript source; no statistical estimation is involved.')
 RESULTS[id]={'id':id,'status':'Source text reproduced','paths':[path],'notes':['Definitions rebuilt from supplied TeX/text source, not independently estimated.'],'rows':rows,'source':str(source),'counts':{'definition_rows':len(rows)}}

vals=[]
for v in VS:
 x=W[f'{v}_R0'].to_numpy(float);x=x/1000 if np.any(x>=1000) else x;n=len(x);mu=x.mean();sd=x.std(ddof=1);z=x-mu
 vals.append([n,mu,sd,np.mean(z**3)/sd**3,np.mean(z**4)/sd**4-3,np.median(x),x.min(),x.max(),np.dot(z[:-1],z[1:])/np.dot(z,z)])
audit('T3',vals,47,labels=[NAMES[v]+(' (x1000)' if (W[f'{v}_R0']>=1000).any() else '') for v in VS],columns=['N','Mean','SD','Skewness','Kurtosis','Median','Min','Max','ACF(1)'],note='Faithful port of tab_descriptive_stats.R. Realizations repeat once per AI panel row (N=5,308), not once per quarter. ACF follows stored row order; e1071 type-3 moments are used. Series marked x1000 are divided by 1,000.')

# T4: preserve duplicate-row join, which weights MAEs by panel size.
vals=[];v5=[]
for v in VS:
 row=[];row5=[]
 for h in ['0','1','4']:
  p=pair(TS,v,h);weights=W[W[f'{v}_H{h}'].notna()].groupby('date_q').size().reindex(p.index).fillna(0).values
  row += [weighted_mae(p.AI,weights),weighted_mae(p.Human,weights),swap_p(p.AI,p.Human)]
  q=p[weights>0].dropna();a=q.AI.abs().values;b=q.Human.abs().values;wins=a<=b;ntie=np.sum(a==b);n=len(a);obs=abs(wins.mean()-.5)
  k=RNG.binomial(n-ntie,.5,NSIM);sim=(k+ntie)/n;pv=float(np.mean(abs(sim-.5)>=obs));row5 += [wins.mean(),pv]
 vals.append(row);v5.append(row5)
cols=[f'h{h} {s}' for h in [0,1,4] for s in ['AI','Human','p']]
audit('T4',vals,48,[2,5,8],columns=cols,note='Supplied code: MAEs weighted by AI panel row counts through a duplicate join; randomization tests use signed mean errors, although the paper describes MAE tests. 10,000 draws, seed 20261031.')
audit('T5',v5,49,[1,3,5],columns=[f'h{h} {s}' for h in [0,1,4] for s in ['Share','p']],note='Shares count ties as AI wins, following the supplied R code; fractions are displayed (0.50 = 50%). Tests use 10,000 label swaps, seed 20261031.')

# T6 select one AI persona per variable/horizon with original duplicate-join weights.
selected={};a_records=[];h_records=[];v6=[]
for v in VS:
 row=[]
 for h in ['0','1','4']:
  dat=W[['date_q','Name',f'{v}_A{h}',f'{v}_H{h}',f'{v}_R{h}']].copy();dat['error']=dat[f'{v}_A{h}']-dat[f'{v}_R{h}']
  weights=dat[dat[f'{v}_H{h}'].notna()].groupby('date_q').size();dat['weight']=dat.date_q.map(weights).fillna(0)
  ranks=dat.groupby('Name',sort=False).apply(lambda d:weighted_mae(d.error,d.weight),include_groups=False)
  best=ranks.idxmin(); selected[(v,h)]=best;sub=dat[dat.Name==best]
  human=pair(TS,v,h).Human.reindex(sub.date_q).values;ai=sub.error.values
  # Original R randomization pairs positions globally, not necessarily matching dates/groups.
  row += [np.nanmean(abs(ai)),np.nanmean(abs(human)),np.nan]
 v6.append(row)
# Reconstruct R pivot_longer row-major AI order and saved aggregate Human order.
ai_cols=[c for c in W if re.match(r'^.+_A[014]$',c)]
for rid,d in W.iterrows():
 for c in ai_cols:
  v,h=c.rsplit('_A',1)
  if d.Name==selected[(v,h)]:a_records.append((v,h,d.date_q,d[c]-d[f'{v}_R{h}']))
for _,d in TS[(TS.type=='Human')&TS.id.isin(['0','1','4'])].iterrows():
 n=int(((W.Name==selected[(d.variable,d.id)])&(W.date_q==d.date_q)).sum())
 h_records.extend([(d.variable,d.id,d.date_q,d.forecast_error)]*n)
assert len(a_records)==len(h_records)
groups=[(v,h) for v in VS for h in ['0','1','4']];gidx={k:i for i,k in enumerate(groups)}
g=np.array([gidx[(r[0],r[1])] for r in a_records+h_records]);e=np.array([r[3] for r in a_records+h_records]);valid=np.isfinite(e);ef=np.nan_to_num(e);n=len(a_records);ng=len(groups)
def diffs(isai):
 sa=np.bincount(g,weights=ef*isai,minlength=ng);na=np.bincount(g,weights=valid*isai,minlength=ng)
 sb=np.bincount(g,weights=ef*(~isai),minlength=ng);nb=np.bincount(g,weights=valid*(~isai),minlength=ng)
 return sa/na-sb/nb
obs=diffs(np.r_[np.ones(n,bool),np.zeros(n,bool)]);exceed=np.zeros(ng);valid_sim=np.zeros(ng)
for _ in range(NSIM):
 mask=RNG.random(n)<.5;sim=diffs(np.r_[mask,~mask]);valid_draw=np.isfinite(sim);valid_sim+=valid_draw;exceed+=valid_draw&(abs(sim)>=abs(obs))
for i,v in enumerate(VS):
 for j,h in enumerate(['0','1','4']):v6[i][j*3+2]=exceed[gidx[(v,h)]]/valid_sim[gidx[(v,h)]]
audit('T6',v6,50,[2,5,8],columns=cols,note='Supplied code selects best AI persona across time, then compares the human MEDIAN on that persona’s quarters; it does not select the best human. Selection uses duplicate-join weights. Positional randomization is ported from R.')
(OUT/'T6_selected_personas.json').write_text(json.dumps({f'{v}_h{h}':name for (v,h),name in selected.items()},indent=2))

# T8 ablation ratios and code-defined significance stars.
v8=[];s8=[]
ablations={k:pd.read_parquet(CACHE/f'{k}_ts.parquet') for k in ['generic','no_realtime','no_data','recall']}
for v in VS:
 row=[];star=[]
 for name in ['generic','no_realtime','no_data','recall']:
  for h in (['0'] if name=='recall' else ['0','4']):
   p=pair(ablations[name],v,h);base=pair(TS,v,h).AI
   row.append(float(p.AI.abs().mean()/base.abs().mean()));pv=swap_p(p.AI,p.Human,float(base.mean()));star.append(int(pv<=.10)+int(pv<=.05)+int(pv<=.01))
 v8.append(row);s8.append(star)
v8.append(np.mean(v8,axis=0).tolist());s8.append([0]*7)
audit('T8',v8,52,columns=['Generic h0','Generic h4','No realtime h0','No realtime h4','No data h0','No data h4','Recall h0'],labels=[NAMES[v] for v in VS]+['Average'],stars=s8,note='Ratios follow supplied code (unweighted quarterly MAEs). Stars use its signed-mean test and swap AI/Human within each ablation, not baseline/ablation labels. Recall cache combines older recall data with later BAA values.')

# B13 supplied-code sample includes eight quarters, unlike its caption.
oosrows=[];oos2024=[]
for v in VS:
 row=[];r24=[]
 for h in ['0','1','4']:
  p=pair(OOS,v,h);q=p[p.index>=pd.Timestamp('2024-01-01')]
  row += [p.AI.abs().mean(),p.Human.abs().mean(),swap_p(p.AI,p.Human)]
  r24 += [q.AI.abs().mean(),q.Human.abs().mean(),swap_p(q.AI,q.Human)]
 oosrows.append(row);oos2024.append(r24)
ooscols=[f'h{h} {s}' for h in [0,1,4] for s in ['AI','Human','p']]
audit('TB13',oosrows,64,[2,5,8],columns=ooscols,note='Saved OOS errors use 2023Q1–2024Q4 and horizons 0/1/4; printed labels say 2024 and 0/1/2. Saved h4 errors are unclipped where current prepare_data.R would clip, so raw preprocessing is not fully reproduced. A 2024-only diagnostic is saved.')
(OUT/'TB13_2024_only.json').write_text(json.dumps(oos2024,indent=2))
render_table('B.13 | Diagnostic: caption sample 2024 only',['Variable']+ooscols,[[NAMES[v]]+[f'{x:.2f}' for x in r] for v,r in zip(VS,oos2024)],OUT/'TB13_2024_only.png')

# B14 follow paper's explicit best-per-quarter rule for both human and AI.
micro=pd.read_parquet(CACHE/'oos_microdata.parquet');v14=[];vs14=[v for v in VS if v!='BAABOND']
for v in vs14:
 row=[]
 for h in ['0','1','2']:
  p=pair(OOS,v,h,'realized');real=p.Human
  ai=OW[['date_q',f'{v}_A{h}']].copy();ai['err']=(ai[f'{v}_A{h}']-ai.date_q.map(real)).abs();a=ai.groupby('date_q').err.min()
  hu=micro[(micro.variable==v)&(micro.id==h)].copy();hu['err']=(hu.value-hu.date_q.map(real)).abs();b=hu.groupby('date_q').err.min()
  q=pd.concat([a.rename('AI'),b.rename('Human')],axis=1);q=q[q.index>=pd.Timestamp('2024-01-01')].dropna()
  row += [q.AI.mean(),q.Human.mean(),swap_p(q.AI,q.Human)]
 v14.append(row)
ooscols=[f'h{h} {s}' for h in [0,1,2] for s in ['AI','Human','p']]
(OUT/'TB14_current_caption_method.json').write_text(json.dumps(v14,indent=2))
render_table('B.14 | Diagnostic: current data and caption method',['Variable']+ooscols,[[NAMES[v]]+[f'{x:.2f}' for x in r] for v,r in zip(vs14,v14)],OUT/'TB14_current_caption_method.png')
# Archived earlier AI run and evaluation cutoff recover the provenance of this older table.
old=pd.read_excel(SRC/'Simulating_SPF_processing/data/merged_file_outofsample_2024_SPF6_cleaned.xlsx')
old['date_q']=pd.to_datetime(old.Date_Q);v14legacy=[]
for v in vs14:
 row=[];label=META.set_index('variable').loc[v,'variable_AI_output']
 for h in ['0','1','2']:
  dates=pair(OOS,v,h);end=pd.Timestamp('2024-10-01')-pd.DateOffset(months=3*int(h));dates=dates[(dates.index>='2024-01-01')&(dates.index<=end)]
  real=pair(OOS,v,h,'realized').Human;field=f'{label}_'+('t' if h=='0' else 't+'+h)
  d=old[['date_q',field]].copy();d['err']=(pd.to_numeric(d[field],errors='coerce')-d.date_q.map(real)).abs();a=d.groupby('date_q').err.min().reindex(dates.index)
  # Existing source family compares selected AI forecasts to median human SPF forecasts.
  b=dates.Human.abs();row += [a.mean(),b.mean(),swap_p(a,b)]
 v14legacy.append(row)
audit('TB14',v14legacy,65,[2,5,8],columns=ooscols,labels=[NAMES[v] for v in vs14],note='Historical reconstruction: older 492-row AI workbook, best AI per quarter versus HUMAN MEDIAN, evaluation targets through 2024Q4 (4/3/2 quarters). This differs from the caption’s best-human rule. The current-data/caption-method diagnostic is also saved; remaining mismatches are retained.')

( ROOT/'core_tables_results.json').write_text(json.dumps(RESULTS,indent=2,allow_nan=True))
(ROOT/'core_cell_comparison.json').write_text(json.dumps(CELL_AUDIT,indent=2,allow_nan=True))
pd.DataFrame(CELL_AUDIT).to_csv(ROOT/'core_cell_comparison.csv',index=False)
print('Core tables completed',flush=True)
