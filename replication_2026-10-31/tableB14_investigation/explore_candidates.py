from pathlib import Path
import pandas as pd,numpy as np,json,itertools,warnings
warnings.filterwarnings("ignore")
P=Path(__file__).resolve().parents[1];S=P.parent/'Simulating_SPF_processing/data';C=P/'data_cache';OUT=Path(__file__).resolve().parent
meta=pd.read_csv(C/'oos_variables.csv');vs=[x for x in meta.variable if x!='BAABOND'];labels=meta.set_index('variable').variable_AI_output.to_dict();names=meta.set_index('variable').variable_longname.to_dict()
W=pd.read_parquet(C/'oos_wide.parquet');TS=pd.read_parquet(C/'oos_ts.parquet');M=pd.read_parquet(C/'oos_microdata.parquet')
old=pd.read_excel(S/'merged_file_outofsample_2024_SPF6_cleaned.xlsx');old['date_q']=pd.to_datetime(old.Date_Q)
A={'old':old[['date_q','Name']].copy(),'current':W[['date_q','Name']].copy()}
for v in vs:
 for h in range(5):
  field=f'{labels[v]}_'+('t'if h==0 else f't+{h}')
  A['old'][f'{v}_A{h}']=pd.to_numeric(old[field],errors='coerce');A['current'][f'{v}_A{h}']=W[f'{v}_A{h}']
target=json.loads((P/'core_tables_results.json').read_text())['TB14'];audit=json.loads((P/'cell_comparison.json').read_text());orig={(x['row'],x['column']):x['original']for x in audit if x['item']=='TB14'and x['kind']!='stars'}
real=TS[TS.type=='Human'].set_index(['variable','id','date_q']).realized
results=[];allpoints=[]
for vintage,selection,hmeth,cut in itertools.product(['old','current'],['quarter_min','best_name'],['median','quarter_min'],['origins2024','targets2024']):
 cells=[]
 for v in vs:
  for h in range(3):
   r=real.loc[(v,str(h))];a=A[vintage][['date_q','Name',f'{v}_A{h}']].copy();a['error']=a[f'{v}_A{h}']-a.date_q.map(r)
   a=a[a.date_q.ge('2024-01-01')]
   if cut=='targets2024':a=a[a.date_q.le(pd.Timestamp('2024-10-01')-pd.DateOffset(months=3*h))]
   if selection=='quarter_min':aa=a.groupby('date_q').error.apply(lambda x:x.abs().min());selected='each quarter'
   else:
    selected=a.groupby('Name').error.apply(lambda x:x.abs().mean()).idxmin();aa=a[a.Name==selected].set_index('date_q').error.abs()
   if hmeth=='median':hh=TS[(TS.variable==v)&(TS.id==str(h))&(TS.type=='Human')].set_index('date_q');bb=(hh['median']-hh.realized).abs()
   else:
    hh=M[(M.variable==v)&(M.id==str(h))].copy();hh['error']=hh.value-hh.date_q.map(r);bb=hh.groupby('date_q').error.apply(lambda x:x.abs().min())
   q=pd.concat([aa.rename('AI'),bb.rename('Human')],axis=1).reindex(aa.index).dropna()
   for s in ['AI','Human']:
    value=q[s].mean();published=orig[(names[v],f'h{h} {s}')];match=abs(value-published)<=.005000001
    cells.append({'vintage':vintage,'selection':selection,'human_method':hmeth,'cut':cut,'variable':v,'h':h,'survey':s,'value':value,'published':published,'match':bool(match),'N':len(q),'selected':selected})
 key=f'{vintage} {selection} {hmeth} {cut}'
 results.append({'candidate':key,'point_matches':sum(x['match']for x in cells),'ai_matches':sum(x['match']for x in cells if x['survey']=='AI'),'human_matches':sum(x['match']for x in cells if x['survey']=='Human')})
 allpoints.extend(cells)
pd.DataFrame(allpoints).to_csv(OUT/'candidate_point_cells.csv',index=False);pd.DataFrame(results).to_csv(OUT/'candidate_overview.csv',index=False)
print(pd.DataFrame(results).sort_values('point_matches',ascending=False).to_string(index=False))
for v in ['NGDP','RGDP','UNEMP']:
 for h in [0,1,2]:
  r=real.loc[(v,str(h))];d=old[['date_q','Name']].copy();d['forecast']=A['old'][f'{v}_A{h}'];d['actual']=d.date_q.map(r);d['error']=(d.forecast-d.actual).abs();d=d[d.date_q.ge('2024-01-01')]
  print(v,h,'null',d.groupby('date_q').forecast.count().to_dict(),'min',d.groupby('date_q').error.min().to_dict(),'pub',orig[(names[v],f'h{h} AI')])
