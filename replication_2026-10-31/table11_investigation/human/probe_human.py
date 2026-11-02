from pathlib import Path
import pandas as pd,numpy as np,itertools,json
R=Path(__file__).resolve().parents[2];C=R/'data_cache'
n=pd.read_parquet(C/'human_native_core.parquet').rename(columns={'SPF_human_id':'person'});n=n[n.YEAR.between(1999,2023)].copy();n['q']=n.YEAR*4+n.QUARTER;n=n.sort_values(['person','q'],kind='stable')
w=pd.read_parquet(C/'baseline_wide.parquet').groupby('date_q').first()
target={'RGDP':(.981,.941,3437,-.612,.015),'CPI':(.881,.636,3452,-.690,.140),'UNEMP':(.956,.911,3615,-.868,.072),'TBILL':(.975,.922,3309,-.296,.004)}
rows=[]
def fit(y,x):
 if len(y)<10:return np.nan,np.nan
 xc=x-x.mean();yc=y-y.mean();den=np.sum(xc*xc)
 if den==0:return np.nan,np.nan
 b=np.sum(xc*yc)/den;res=yc-b*xc
 return b,1-np.sum(res*res)/np.sum(yc*yc)
for v,t in target.items():
 for h in range(1,7):
  d=n[['person','date_q','q',v+'1',v+str(h)]].copy() if h!=1 else n[['person','date_q','q',v+'1']].copy()
  d['f']=n[v+str(h)];d['consensus']=d.groupby('q').f.transform('median');g=d.groupby('person');d['lf']=g.f.shift();d['gap']=d.q-g.q.shift();d['revision']=d.f-d.lf;d['distance']=d.lf-g.consensus.shift()
  for src in ['native1','R0','R1','R4','H0','H1']:
   s=n.groupby('date_q')[v+'1'].median() if src=='native1' else w[v+'_'+src]
   for offset in [-1,0,1]:
    ss=s.copy();ss.index=ss.index+pd.offsets.QuarterBegin(offset,startingMonth=1)
    d['realized']=d.date_q.map(ss);d['error']=d.realized-d.lf
    for gap in ['previous','consecutive']:
     x=d.dropna(subset=['revision','error','distance']);x=x if gap=='previous' else x[x.gap==1]
     for trim in [(),('revision',),('error',),('distance',),('revision','error'),('revision','distance'),('error','distance'),('revision','error','distance')]:
      mask=np.ones(len(x),bool)
      for col in trim:
       lo,hi=x[col].quantile([.01,.99]);mask&=x[col].between(lo,hi)
      z=x[mask];b,r2=fit(z.revision.to_numpy(),z.error.to_numpy());bc,rc=fit(z.revision.to_numpy(),z.distance.to_numpy())
      score=abs(b-t[0])+abs(r2-t[1])+abs(bc-t[3])+abs(rc-t[4])+abs(len(z)-t[2])/t[2]
      rows.append({'variable':v,'h':h,'realization':src,'date_offset':offset,'gap':gap,'trim':','.join(trim),'N':len(z),'error_beta':b,'error_R2':r2,'consensus_beta':bc,'consensus_R2':rc,'score':score,'N_match':len(z)==t[2]})
res=pd.DataFrame(rows);res.to_csv(Path(__file__).parent/'hypothesis_grid.csv',index=False)
for v in target:
 print(v);print(res[res.variable==v].sort_values('score').head(6).to_string(index=False));print('COUNT MATCHES');print(res[(res.variable==v)&res.N_match].sort_values('score').head(6).to_string(index=False))
