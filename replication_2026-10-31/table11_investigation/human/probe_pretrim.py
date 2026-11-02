from pathlib import Path
import pandas as pd,numpy as np,itertools
R=Path(__file__).resolve().parents[2];n=pd.read_parquet(R/'data_cache/human_native_core.parquet').rename(columns={'SPF_human_id':'person'});n=n[n.YEAR.between(1999,2023)].copy();n['q']=n.YEAR*4+n.QUARTER;n=n.sort_values(['person','q']);w=pd.read_parquet(R/'data_cache/baseline_wide.parquet').groupby('date_q').first();T={'RGDP':(.981,.941,3437,-.612,.015),'CPI':(.881,.636,3452,-.690,.140),'UNEMP':(.956,.911,3615,-.868,.072),'TBILL':(.975,.922,3309,-.296,.004)};rows=[]
def fit(y,x):
 x=x-x.mean();y=y-y.mean();d=(x*x).sum();b=(x*y).sum()/d if d else np.nan
 return b,1-((y-b*x)**2).sum()/(y*y).sum()
for v,t in T.items():
 for h in [2,3]:
  base=n[['person','date_q','q',v+str(h)]].copy();base['f']=n[v+str(h)];base['consensus']=base.date_q.map(w[v+'_H0']);base['dev']=base.f-base.consensus
  for complete in ['none','all_six','all_four_variables']:
   raw=base.copy()
   if complete=='all_six':raw=raw[n[[v+str(j) for j in range(1,7)]].notna().all(axis=1)]
   if complete=='all_four_variables':raw=raw[n[[vv+str(h) for vv in T]].notna().all(axis=1)]
   for pretrim in [(),('f',),('dev',),('f','dev')]:
    d=raw.copy();mask=np.ones(len(d),bool)
    for col in pretrim:
     lo,hi=d[col].quantile([.01,.99]);mask&=d[col].between(lo,hi)
    d=d[mask];g=d.groupby('person');d['lf']=g.f.shift();d['revision']=d.f-d.lf;d['error']=d.consensus-d.lf;d['distance']=d.lf-g.consensus.shift();d['gap']=d.q-g.q.shift()
    for gap in ['previous','consecutive']:
     x=d.dropna(subset=['revision','error','distance']);x=x if gap=='previous' else x[x.gap==1]
     for posttrim in [(),('revision',),('error',),('distance',),('revision','error'),('revision','distance'),('error','distance'),('revision','error','distance')]:
      mask=np.ones(len(x),bool)
      for col in posttrim:
       lo,hi=x[col].quantile([.01,.99]);mask&=x[col].between(lo,hi)
      z=x[mask];b,r=fit(z.revision.to_numpy(),z.error.to_numpy());bc,rc=fit(z.revision.to_numpy(),z.distance.to_numpy());score=abs(b-t[0])+abs(r-t[1])+abs(bc-t[3])+abs(rc-t[4])+abs(len(z)-t[2])/t[2]
      rows.append([v,h,complete,str(pretrim),str(posttrim),gap,len(z),b,r,bc,rc,score])
res=pd.DataFrame(rows,columns=['v','h','complete','pretrim','posttrim','gap','N','b','r2','bc','rc','score']);res.to_csv(R/'table11_investigation/human/pretrim_grid.csv',index=False)
for v in T:print(res[res.v==v].sort_values('score').head(4).to_string(index=False))
