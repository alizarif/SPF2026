from pathlib import Path
import pandas as pd, numpy as np
R=Path(__file__).resolve().parents[3]
rows=[]
target={'RGDP':3437,'CPI':3452,'UNEMP':3615,'TBILL':3309}
native=pd.read_parquet(R/'replication_2026-10-31/data_cache/human_native_core.parquet').rename(columns={'SPF_human_id':'ID'})
for v in target:
 csv=pd.read_csv(R/f'Simulating_SPF_processing/data/SPFmicrodata/{v}-Table 1.csv',low_memory=False)
 for source,raw in [('CSV',csv),('XLSX',native)]:
  for h in range(1,7):
   col=v+str(h)
   for drop in [False,True]:
    for lag_before in [False,True]:
     d=raw[['ID','YEAR','QUARTER',col]].copy();d['forecast']=pd.to_numeric(d[col],errors='coerce');d['q']=d.YEAR*4+d.QUARTER
     if not lag_before:d=d[d.YEAR.between(1999,2023)]
     if drop:d=d.dropna(subset=['forecast'])
     d=d.sort_values(['ID','q'],kind='stable');g=d.groupby('ID');d['lag']=g.forecast.shift();d['gap']=d.q-g.q.shift();d['rev']=d.forecast-d.lag
     if lag_before:d=d[d.YEAR.between(1999,2023)]
     for gap in ['any','consecutive']:
      x=d.dropna(subset=['rev']);x=x if gap=='any' else x[x.gap==1]
      rows.append(dict(variable=v,source=source,col=col,drop_before=drop,lag_before_sample=lag_before,gap=gap,N=len(x),distance=len(x)-target[v]))
res=pd.DataFrame(rows);res.to_csv(R/'replication_2026-10-31/table11_investigation/human/sample_count_variants.csv',index=False)
print(res[res.distance==0].to_string(index=False))
for v in target:print(res[res.variable==v].assign(absdiff=lambda x:x.distance.abs()).sort_values('absdiff').head(10).to_string(index=False))
