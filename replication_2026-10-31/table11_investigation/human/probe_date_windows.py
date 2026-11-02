from pathlib import Path
import pandas as pd,numpy as np
R=Path(__file__).resolve().parents[2]
d=pd.read_parquet(R/'data_cache/human_native_core.parquet');d['q']=d.YEAR*4+d.QUARTER
V=['RGDP','CPI','UNEMP','TBILL'];T=np.array([3437,3452,3615,3309]);rows=[]
for h in range(1,7):
 for qstart in range(1997*4+1,2002*4+1):
  for qend in range(2022*4+1,int(d.q.max())+1):
   z=d[d.q.between(qstart,qend)].sort_values(['SPF_human_id','q']);g=z.groupby('SPF_human_id');gap=z.q-g.q.shift()
   for mode in ['previous','consecutive']:
    mask=gap>0 if mode=='previous' else gap==1
    counts=np.array([int((mask&z[v+str(h)].notna()&g[v+str(h)].shift().notna()).sum()) for v in V]);diff=np.abs(T-counts).sum()
    if diff<110:rows.append([h,qstart,qend,mode,*counts,diff])
res=pd.DataFrame(rows,columns=['h','qstart','qend','mode',*V,'total_diff']);print(res.sort_values('total_diff').head(20).to_string(index=False));res.to_csv(R/'table11_investigation/human/date_window_variants.csv',index=False)
print(d.date_q.max())
