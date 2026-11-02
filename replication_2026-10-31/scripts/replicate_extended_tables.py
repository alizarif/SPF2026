"""Independent calculations for final-paper Tables 9, 10, 11, 12 and D.15.
Published values appear only in comparison targets; no target value enters an estimator.
Inputs are source-data caches created by extract_replication_data.py.
"""
from pathlib import Path
import sys,json,re,warnings
import pandas as pd,numpy as np
from scipy.stats import t as student_t
from statsmodels.regression.linear_model import OLS
from statsmodels.tools.tools import add_constant
from render_helpers import render_table
warnings.filterwarnings('ignore',category=FutureWarning)
ROOT=Path(__file__).resolve().parents[1]; C=ROOT/'data_cache'; OUT=ROOT/'reproduced/tables';OUT.mkdir(parents=True,exist_ok=True)
RESEARCH=ROOT.parent; TEX=RESEARCH/'latest draft/May 2026 version.tex'
b=pd.read_parquet(C/'baseline_ts.parquet');o=pd.read_parquet(C/'oos_ts.parquet');wide=pd.read_parquet(C/'baseline_wide.parquet')
variables=pd.read_csv(C/'baseline_variables.csv'); variable_names=dict(zip(variables.variable,variables.variable_longname))
AUDIT=[]; RESULTS={}

def py(x):
 if isinstance(x,(np.floating,np.integer)): return x.item()
 if isinstance(x,np.ndarray):return x.tolist()
 if isinstance(x,pd.Timestamp):return x.isoformat()
 raise TypeError(type(x))

def audit(item,row,column,original,replicated,decimals=2,kind='point'):
 original=float(original);replicated=float(replicated);tol=.5*10**(-decimals)+1e-9;diff=abs(original-replicated);ok=bool(np.isfinite(diff) and diff<=tol)
 d={'item':item,'row':row,'column':column,'original':original,'replicated':replicated,'absolute_difference':diff,'kind':kind,'rounded_match':ok,'tolerance':tol,'within_tolerance':ok};AUDIT.append(d);return ok

def stars(p,limits=(.01,.05,.10)):
 return '***' if p<limits[0] else '**' if p<limits[1] else '*' if p<limits[2] else ''

def render_event_table(title,cols,rows,path,notes):
 """Event names and variable lists need more width than the numeric columns."""
 import textwrap
 import matplotlib.pyplot as plt
 widths=[.28,.22,.24,.13,.13]
 wrapped=[[textwrap.fill(str(v),width=[24,21,26,16,16][j]) for j,v in enumerate(row)] for row in rows]
 linecounts=[max(v.count('\n')+1 for v in row) for row in wrapped]
 note='\n'.join(textwrap.wrap(' '.join(notes),126));note_height=.21*(note.count('\n')+1)
 body_height=sum(max(.31,.20*l+.10) for l in linecounts)+.7;height=1.1+body_height+note_height
 fig=plt.figure(figsize=(10.5,height),facecolor='white');ax=fig.add_axes([.025,(note_height+.18)/height,.95,body_height/height]);ax.axis('off')
 fig.text(.027,1-.20/height,title,ha='left',va='top',fontsize=15,fontweight='bold',color='#123349')
 table=ax.table(cellText=wrapped,colLabels=[textwrap.fill(str(c),16) for c in cols],cellLoc='center',colWidths=widths,bbox=[0,0,1,1]);table.auto_set_font_size(False);table.set_fontsize(10.5)
 totalunits=sum(max(1.25,l) for l in linecounts)+1.8
 for (i,j),cell in table.get_celld().items():
  cell.set_edgecolor('#dce3e8');cell.set_linewidth(.45)
  if i==0:cell.set_facecolor('#173b52');cell.set_text_props(color='white',weight='bold');cell.set_height(1.8/totalunits)
  else:
   cell.set_facecolor('#f1f5f7' if i%2==0 else 'white');cell.set_height(max(1.25,linecounts[i-1])/totalunits)
   if j==0:cell.set_text_props(ha='left')
 fig.text(.027,.10/height,note,ha='left',va='bottom',fontsize=9,color='#45525e',linespacing=1.35)
 fig.savefig(path,dpi=180,facecolor='white');plt.close(fig);return str(path)

def register(key,title,cols,rows,notes,numeric,status):
 renderer=render_event_table if key=='T9' else render_table
 path=renderer(title,cols,rows,OUT/f'{key}.png',notes=notes)
 numeric_path=OUT/f'{key}_numeric.json'; numeric_path.write_text(json.dumps(numeric,indent=2,ensure_ascii=False,default=py))
 cells=[c for c in AUDIT if c['item']==key];points=[c for c in cells if c['kind']=='point'];ps=[c for c in cells if c['kind']=='p'];ss=[c for c in cells if c['kind']=='stars']
 RESULTS[key]={'id':key,'paths':[path],'png_path':path,'numeric_json':str(numeric_path),'status':status,'notes':notes,'counts':{'point_total':len(points),'point_match':sum(c['rounded_match'] for c in points),'p_total':len(ps),'p_rounded_match':sum(c['rounded_match'] for c in ps),'p_mc_compatible':None,'star_total':len(ss),'star_match':sum(c['rounded_match'] for c in ss)},'method_script':str(Path(__file__).resolve()),'source_files':[str(C/'baseline_ts.parquet')],'cell_audit_path':str(ROOT/'extended_cell_audit.json')}

# T9: reconstruct the published implementation. Error scale is signed-error SD,
# while the numerator compares absolute errors. Flash Crash uses h0; others h1.
events=[
 ('9/11 Attacks','2001-09-11','2001-07-01','1',['RGDP','UNEMP','CPI','TBILL','TBOND'],(.28,.01)),
 ('Lehman Brothers Collapse','2008-09-15','2008-07-01','1',['RGDP','UNEMP','CPI','TBILL','TBOND','HOUSING'],(1.49,.49)),
 ('Flash Crash','2010-05-06','2010-04-01','0',['RGDP','CPI'],(.00,-.12)),
 ('S&P Downgrade of U.S. Debt','2011-08-05','2011-07-01','1',['TBILL','TBOND','RGDP'],(.26,-.06)),
 ('COVID-19 Pandemic Declaration','2020-03-11','2020-01-01','1',['RGDP','UNEMP','CPI','HOUSING','INDPROD'],(1.19,.77)),
 ('Russia-Ukraine War','2022-02-24','2022-01-01','1',['RGDP','CPI','TBILL','TBOND'],(.72,.29)),
 ('Silicon Valley Bank Collapse','2023-03-10','2023-01-01','1',['RGDP','UNEMP','TBILL','TBOND'],(-.20,-.09))]
# Documentary event metadata from manuscript Table 9. The supplied survey
# deadline cache identifies months, not exact days, so these offsets are not
# independently validated and do not enter the forecast-error calculations.
event_deadline_offsets={'9/11 Attacks':27,'Lehman Brothers Collapse':39,'Flash Crash':-5,'S&P Downgrade of U.S. Debt':-3,'COVID-19 Pandemic Declaration':29,'Russia-Ukraine War':17,'Silicon Valley Bank Collapse':31}
a=b[(b.type=='AI')&b.id.isin(['0','1'])].copy();a['absolute_error']=a.forecast_error.abs();g=a.groupby(['variable','id'],observed=True)
a['z']=(a.absolute_error-g.absolute_error.transform('mean'))/g.forecast_error.transform('std')
a['conventional_z']=(a.absolute_error-g.absolute_error.transform('mean'))/g.absolute_error.transform('std')
rows=[];numbers=[]
for name,date,q,h,vs,target in events:
 x=a[(a.date_q==q)&(a.id==h)];rel=x[x.variable.isin(vs)].z.mean();allz=x.z.mean()
 audit('T9',name,'Relevant variables Z',target[0],rel);audit('T9',name,'All variables Z',target[1],allz)
 numbers.append({'event':name,'event_date':date,'survey_quarter':q,'horizon':int(h),'days_after_survey_deadline':event_deadline_offsets[name],'deadline_offset_source':'Manuscript Table 9; documentary metadata, not independently validated','relevant_variables':vs,'relevant_z':rel,'all_z':allz,'conventional_abs_error_sd_relevant_z':x[x.variable.isin(vs)].conventional_z.mean(),'conventional_abs_error_sd_all_z':x.conventional_z.mean()})
 rows.append([name+' ('+str(pd.Period(q,freq='Q')).replace('Q',' Q')+'; h'+h+')',date+' ('+str(event_deadline_offsets[name])+' days)',', '.join(vs),f'{0 if abs(rel)<.005 else rel:.2f}',f'{allz:.2f}'])
register('T9','Table 9. AI forecast performance during unexpected events',['Event / quarter / horizon','Event date (days after deadline)','Relevant variables','Relevant Z','All-variable Z'],rows,[
 'Recomputed from supplied median AI forecast errors, 1999-2023. Z = (absolute event error - mean absolute error) / SD of signed error, separately by variable and horizon. Relevant-variable and all-variable scores are arithmetic means.',
 'Event dates and days after the survey deadline are documentary metadata from manuscript Table 9. Deadline offsets have not been independently validated: the supplied deadline cache identifies months, not exact days. Negative offsets indicate events before the deadline.',
 'The matching calculation uses h=0 for the Flash Crash and h=1 for every other event. The S&P downgrade therefore uses h=1 even though it preceded its survey deadline; applying the stated pre-deadline nowcast rule instead produces 0.38 for its relevant-variable score.'],numbers,'Reproduced with documented method clarification')

# T10: the supplied plotting function concatenates baseline and OOS samples;
# preserve the overlapping 2023 records to reproduce the published N=108.
target10={'RGDP':[366.06,65.43,715.56,340.01,108,.040],'UNEMP':[.714,.141,-.539,.732,108,.005],'CPI':[2.135,.210,-1.323,1.091,108,.014],'TBILL':[.652,.076,-.137,.397,108,.001]}
rows=[];numbers={};models={}
d=pd.concat([b,o],ignore_index=True)
for v in target10:
 x=d[(d.type=='AI')&(d.id=='1')&(d.variable==v)].dropna(subset=['forecast_error']).copy();x['post']=(x.date_q>'2023-10-31').astype(int);m=OLS(x.forecast_error.abs(),add_constant(x.post)).fit();models[v]=m
 values=[*list(np.r_[m.params.iloc[0],m.bse.iloc[0],m.params.iloc[1],m.bse.iloc[1]]),int(m.nobs),m.rsquared]
 numbers[v]={'intercept':m.params.iloc[0],'intercept_se':m.bse.iloc[0],'post_coefficient':m.params.iloc[1],'post_se':m.bse.iloc[1],'N':int(m.nobs),'R2':m.rsquared,'intercept_p':m.pvalues.iloc[0],'post_p':m.pvalues.iloc[1],'distinct_quarters':x.date_q.nunique(),'post_observations':int(x.post.sum())}
 for j,(name,dec) in enumerate([('Intercept',2 if v=='RGDP' else 3),('Intercept SE',2 if v=='RGDP' else 3),('Post cutoff',2 if v=='RGDP' else 3),('Post SE',2 if v=='RGDP' else 3),('N',0),('R2',3)]):audit('T10',v,name,target10[v][j],values[j],dec)
for v,m in models.items():
 audit('T10',v,'Intercept stars',3,len(stars(m.pvalues.iloc[0],(.001,.01,.05))),0,'stars');audit('T10',v,'Post cutoff stars',1 if v=='RGDP' else 0,len(stars(m.pvalues.iloc[1],(.001,.01,.05))),0,'stars')
for key,name in [('intercept','Intercept'),('intercept_se','SE'),('post_coefficient','Post October 2023'),('post_se','SE'),('N','Observations'),('R2','R²')]:
 row=[name]
 for v in target10:
  val=numbers[v][key];dec=2 if v=='RGDP' and key not in ['R2','N'] else 3
  st=stars(numbers[v]['intercept_p' if key=='intercept' else 'post_p'],(.001,.01,.05)) if key in ['intercept','post_coefficient'] else ''
  row.append(str(int(val)) if key=='N' else f'{val:.{dec}f}'+st)
 rows.append(row)
register('T10','Table 10. Absolute forecast errors and the knowledge cutoff',['Statistic']+list(target10),rows,[
 'OLS with intercept and a dummy for survey dates after October 31, 2023; one-quarter-ahead absolute AI median errors. Conventional OLS standard errors. Significance: * p<.05; ** p<.01; *** p<.001.',
 'Exact reproduction requires concatenating the 100-quarter baseline and 8-quarter OOS files, including duplicate 2023 survey quarters: 108 observations but 104 distinct quarters. The four post-cutoff observations are 2024Q1-Q4.'],numbers,'Reproduced; overlapping sample documented')
RESULTS['T10']['source_files'] += [str(C/'oos_ts.parquet')]

# T12: verbatim Appendix C keyword rules, case-insensitive substring detection.
keywords={'Mechanical':['trend','historical','average','mean reversion','pattern','previous','past','typical','normal','baseline','extrapolat'],'Policy':['fed','federal reserve','monetary policy','fiscal','stimulus','rate hike','rate cut','tightening','easing','central bank','government','policy response','intervention'],'Model':['phillips curve','okun','gdp growth','economic model','structural','relationship between','economic theory','multiplier','elasticity','economic indicator','leading indicator'],'Event':['covid','pandemic','crisis','recession','shock','war','collapse','lockdown','unprecedented','disruption','financial crisis','lehman','subprime','outbreak','emergency']}
r=pd.read_parquet(C/'baseline_reasoning.parquet');text=r.reasoning.fillna('').str.lower()
for k,words in keywords.items():r[k]=text.str.contains('|'.join(map(re.escape,words)))
r['Model-based']=r.Mechanical|r.Model;r['Judgment-based']=r.Policy|r.Event;r['Period']='Normal'
r.loc[r.date_q.between('2008-07-01','2009-10-01'),'Period']='Financial Crisis';r.loc[r.date_q.between('2020-01-01','2020-10-01'),'Period']='COVID-19';r.loc[r.date_q.between('2022-01-01','2022-10-01'),'Period']='Inflation Shock'
target12={'Normal':[4626,98.6,55.2,86.7,19.7,99.6,63.3],'Financial Crisis':[346,84.7,34.4,37.6,82.4,88.4,87.6],'COVID-19':[204,72.1,59.8,26.5,77.0,72.5,79.9],'Inflation Shock':[212,85.4,87.3,97.2,30.2,98.1,87.7]}
cats=list(keywords)+['Model-based','Judgment-based'];rows=[];numbers={}
for period,target in target12.items():
 x=r[r.Period==period];values=[len(x)]+[100*x[c].mean() for c in cats];numbers[period]=dict(zip(['N']+cats,values));rows.append([period,str(len(x))]+[f'{z:.1f}%' for z in values[1:]])
 for j,col in enumerate(['N']+cats):audit('T12',period,col,target[j],values[j],0 if j==0 else 1)
r[['Name','date_q','Period']+cats].to_parquet(OUT/'T12_classified_responses.parquet',index=False)
register('T12','Table 12. Reasoning categories by economic period',['Period','N','Mechanical','Policy','Model','Event','Model-based','Judgment'],rows,[
 'Recomputed using all 5,388 source reasoning responses, including the 80 rows named "No Name Provided". Nonexclusive case-insensitive substring matches use the exact Appendix C keyword lists. Model-based = Mechanical OR Model; Judgment-based = Policy OR Event.',
 'Financial Crisis: 2008Q3-2009Q4; COVID-19: 2020Q1-Q4; Inflation Shock: 2022Q1-Q4; otherwise Normal. Counts and all percentages match the final paper at its printed precision.'],{'keywords':keywords,'statistics':numbers},'Reproduced')
RESULTS['T12']['source_files']=[str(C/'baseline_reasoning.parquet')]

# TD15: separate expanding-window AR(1) fit for each median human horizon.
# First prediction follows two lagged training pairs. Nonidentified slopes are skipped.
def expanding_ar1(series):
 y=series.to_numpy(dtype=float);pred=np.full(len(y),np.nan);train_n=np.zeros(len(y),dtype=int)
 for i in range(1,len(y)):
  yy=y[1:i];xx=y[:i-1];valid=np.isfinite(xx)&np.isfinite(yy);train_n[i]=valid.sum()
  if valid.sum()<2 or not np.isfinite(y[i-1]) or np.ptp(xx[valid])==0:continue
  X=np.c_[np.ones(valid.sum()),xx[valid]];beta=np.linalg.lstsq(X,yy[valid],rcond=None)[0];pred[i]=beta[0]+beta[1]*y[i-1]
 return pd.Series(pred,index=series.index),train_n

def dm_absolute_h1(e1,e2):
 ok=np.isfinite(e1)&np.isfinite(e2);loss=np.abs(e1[ok])-np.abs(e2[ok]);n=len(loss);center=loss-loss.mean();variance=np.dot(center,center)/n
 if variance<=0:return np.nan
 stat=loss.mean()/np.sqrt(variance/n);stat*=np.sqrt((n-1)/n)
 return float(2*student_t.sf(abs(stat),df=n-1))

def read_ar1_targets():
 targets=[]
 for line in (RESEARCH/'latest draft/tables/forecast_accuracy_ar1_relative_comparison.txt').read_text().splitlines():
  cells=[x for x in re.split(r'(?<!\\)&',line) if x.strip()]
  if len(cells)!=10:continue
  values=[];ns=[]
  for cell in cells[1:]:
   match=re.search(r'[-+]?\d+\.\d+',cell);values.append(float(match[0]) if match else np.nan);ns.append(cell.count('\\star'))
  if np.isfinite(values).all():targets.append({'label':cells[0].strip(),'values':values,'stars':ns})
 return targets
ar_targets=read_ar1_targets();rows=[];numbers=[];series_export=[]
for v,target in zip(variables.variable,ar_targets):
 row=[variable_names[v]]
 for j,h in enumerate(['0','1','4']):
  human=b[(b.variable==v)&(b.id==h)&(b.type=='Human')].set_index('date_q').sort_index();ai=b[(b.variable==v)&(b.id==h)&(b.type=='AI')].set_index('date_q').sort_index();pred,train=expanding_ar1(human['median'])
  x=human[['median','realized','forecast_error']].rename(columns={'median':'human_median','forecast_error':'human_error'}).join(ai.forecast_error.rename('ai_error')).join(pred.rename('ar1_prediction'));x['ar1_error']=x.ar1_prediction-x.realized
  denom=x.human_error.abs().mean();mae_ai=x.loc[x.human_error.notna(),'ai_error'].abs().mean();mae_ar=x.ar1_error.abs().mean();ratio_ai=mae_ai/denom;ratio_ar=mae_ar/denom;p=dm_absolute_h1(x.ai_error.to_numpy(),x.ar1_error.to_numpy())
  vals=[ratio_ai,ratio_ar,p];row += [f'{ratio_ai:.2f}',f'{ratio_ar:.2f}',f'{p:.2f}'+stars(p)]
  for k,col in enumerate(['AI/Human MAE','AR1/Human MAE','p-value']):audit('TD15',v,f'h{h}: {col}',target['values'][j*3+k],vals[k],2,'p' if k==2 else 'point')
  audit('TD15',v,f'h{h}: significance stars',target['stars'][j*3+2],len(stars(p)),0,'stars')
  numbers.append({'variable':v,'horizon':int(h),'human_mae':denom,'ai_mae':mae_ai,'ar1_mae':mae_ar,'ai_relative_mae':ratio_ai,'ar1_relative_mae':ratio_ar,'p':p,'human_N':int(x.human_error.notna().sum()),'ar1_N':int(x.ar1_error.notna().sum())})
  x=x.reset_index();x['variable']=v;x['horizon']=int(h);x['training_pairs']=train;series_export.append(x)
 rows.append(row)
pd.concat(series_export,ignore_index=True).to_parquet(OUT/'TD15_predictions.parquet',index=False)
register('TD15','Table D.15. AI and AR(1) accuracy relative to human forecasts',['Variable','h0 AI','h0 AR(1)','h0 p','h1 AI','h1 AR(1)','h1 p','h4 AI','h4 AR(1)','h4 p'],rows,[
 'Reconstructed with expanding OLS AR(1) models fitted separately to median human forecasts at each horizon, using only past survey observations from the baseline. Minimum training sample: two lagged pairs; rank-deficient fits are omitted. Ratios use the human MAE over its available sample; AI is restricted to dates with a human forecast, while AR(1) has fewer initial observations.',
 'Diebold-Mariano tests use absolute losses (power=1), Harvey small-sample adjustment, two-sided t reference, and test horizon h=1 for all three forecast horizons. All 138 ratios and 69 p-values match to two decimals; significance stars are separately checked.'],numbers,'Reproduced')

# T11: no generation script supplied. Apply the stated lagged-error and within-panel
# SPF human median definitions directly; retain the mismatch rather than importing published coefficients.
raw=pd.read_parquet(C/'baseline_raw_forecasts.parquet');micro=pd.read_parquet(C/'baseline_microdata.parquet')
target11={
 'Human':{'RGDP':[.981,.008,3437,.941,-.612,.134,3437,.015],'CPI':[.881,.016,3452,.636,-.690,.035,3452,.140],'UNEMP':[.956,.007,3615,.911,-.868,.064,3615,.072],'TBILL':[.975,.008,3309,.922,-.296,.102,3309,.004]},
 'AI':{'RGDP':[.610,.028,5188,.568,-1.016,.004,5188,.776],'CPI':[.443,.018,5188,.354,-.693,.017,5188,.551],'UNEMP':[.647,.008,5188,.946,-.510,.049,5188,.086],'TBILL':[.594,.008,5188,.827,-1.143,.011,5188,.716]}}
rows=[];numbers=[];regression_data=[]
for panel in ['Human','AI']:
 for v in ['RGDP','CPI','UNEMP','TBILL']:
  if panel=='AI': d=raw[['Name','date_q',v+'_A0']].rename(columns={'Name':'person',v+'_A0':'forecast'}).copy()
  else:d=micro[(micro.variable==v)&(micro.id=='0')][['SPF_human_id','date_q','value']].rename(columns={'SPF_human_id':'person','value':'forecast'}).copy()
  realized=wide[['date_q',v+'_R0',v+'_H0']].drop_duplicates('date_q').rename(columns={v+'_R0':'realized',v+'_H0':'spf_consensus'})
  d=d.merge(realized,on='date_q',how='left');d=d.sort_values(['person','date_q'],kind='stable');d['consensus']=d.groupby('date_q').forecast.transform('median');g=d.groupby('person',sort=False)
  d['lag_forecast']=g.forecast.shift();d['lag_realized']=g.realized.shift();d['lag_consensus']=g.consensus.shift();d['lag_date']=g.date_q.shift();d['revision']=d.forecast-d.lag_forecast;d['lag_error']=d.lag_realized-d.lag_forecast;d['lag_deviation_within_panel']=d.lag_forecast-d.lag_consensus;d['lag_spf_consensus']=g.spf_consensus.shift();d['lag_deviation']=d.lag_forecast-d.lag_spf_consensus
  vals=[];entry={'panel':panel,'variable':v,'method':'chronologically sorted previous available observation; lagged human SPF median; current-horizon realization from supplied vintage cache'}
  for reg in ['lag_error','lag_deviation']:
   x=d.dropna(subset=['revision',reg]);m=OLS(x.revision,add_constant(x[reg])).fit(cov_type='HC1');gap=x.date_q.dt.to_period('Q').astype(int)-x.lag_date.dt.to_period('Q').astype(int)
   audit('T11',panel+' '+v,reg+' stars',3,3 if m.pvalues.iloc[1]<.01 else 0,0,'stars')
   vals += [m.params.iloc[1],m.bse.iloc[1],int(m.nobs),m.rsquared];entry[reg]={'coefficient':m.params.iloc[1],'se_HC1':m.bse.iloc[1],'N':int(m.nobs),'R2':m.rsquared,'p':m.pvalues.iloc[1],'nonconsecutive_or_duplicate_lags':int((gap!=1).sum())}
  for j,col in enumerate(['Error coefficient','Error SE','Error N','Error R2','Consensus coefficient','Consensus SE','Consensus N','Consensus R2']):audit('T11',panel+' '+v,col,target11[panel][v][j],vals[j],0 if j in [2,6] else 3)
  cells=[str(z) if j in [2,6] else f'{z:.3f}' for j,z in enumerate(vals)]
  for j,reg in [(0,'lag_error'),(4,'lag_deviation')]:cells[j]+='***' if entry[reg]['p']<.01 else ''
  rows.append([panel+' / '+v]+cells);numbers.append(entry)
  xa=d.dropna(subset=['revision','lag_deviation_within_panel']);ma=OLS(xa.revision,add_constant(xa.lag_deviation_within_panel)).fit(cov_type='HC1');entry['within_panel_consensus_alternative']={'coefficient':ma.params.iloc[1],'se_HC1':ma.bse.iloc[1],'N':int(ma.nobs),'R2':ma.rsquared}
  d['panel']=panel;d['variable']=v;d['person']=d.person.astype(str);regression_data.append(d)
pd.concat(regression_data,ignore_index=True).to_parquet(OUT/'T11_regression_inputs.parquet',index=False)
register('T11','Table 11. Reconstructed revision regressions (does not reproduce target)',['Panel / variable','Error coefficient','Robust SE','N','R²','Consensus coefficient','Robust SE','N','R²'],rows,[
 'The original computation script is absent. This reconstruction uses supplied nowcasts: revision = forecast(t) - previous available forecast; lagged error = previous realization - previous forecast; consensus deviation = previous forecast - previous human SPF median. OLS includes an intercept and HC1 standard errors. Recalculated significance: *** p<0.01, following the original table. AI uses all raw responses, including the placeholder name, while human IDs come from supplied SPF microdata.',
 'Published coefficients, standard errors, human observation counts and most R² values are not reproduced. AI N=5,188 is reproduced. Gaps and duplicate name-quarter observations are retained as supplied and counted in the numeric audit. The body says within-panel consensus whereas the caption says SPF consensus; the alternative within-panel estimates are also retained in the numeric file and do not reproduce the target. Alternate lag, realization-vintage and legacy-input checks did not identify the published estimator. This is an explicitly qualified reconstruction, not a confirmed replication.'],numbers,'Not reproduced; estimator/sample provenance unresolved')
RESULTS['T11']['source_files']=[str(C/'baseline_raw_forecasts.parquet'),str(C/'baseline_microdata.parquet'),str(C/'baseline_wide.parquet')]

(ROOT/'extended_cell_audit.json').write_text(json.dumps(AUDIT,indent=2,ensure_ascii=False,default=py))
(ROOT/'extended_tables_results.json').write_text(json.dumps(RESULTS,indent=2,ensure_ascii=False,default=py))
for k,r in RESULTS.items(): print(k,r['status'],r['counts'])
