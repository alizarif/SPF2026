from pathlib import Path
import pandas as pd,numpy as np,json,re
from statsmodels.regression.linear_model import OLS
from statsmodels.tools.tools import add_constant
from types import SimpleNamespace
sm=SimpleNamespace(OLS=OLS,add_constant=add_constant)
C=Path(__file__).resolve().parents[1]/'data_cache'
b=pd.read_parquet(C/'baseline_ts.parquet');o=pd.read_parquet(C/'oos_ts.parquet')
print('T10')
for combine,d in [('concat108',pd.concat([b,o])),('dedup104',pd.concat([b[b.date_q<'2023-01-01'],o]))]:
 for v in ['RGDP','UNEMP','CPI','TBILL']:
  x=d[(d.type=='AI')&(d.id=='1')&(d.variable==v)].copy();x=x.dropna(subset=['forecast_error']);y=x.forecast_error.abs();z=(x.date_q>'2023-10-31').astype(int);m=sm.OLS(y,sm.add_constant(z)).fit();print(combine,v,len(x),np.round(m.params.values,4),np.round(m.bse.values,4),round(m.rsquared,4))
print('T12')
r=pd.read_parquet(C/'baseline_reasoning.parquet');t=r.reasoning.fillna('').str.lower()
kw={'Mechanical':['trend','historical','average','mean reversion','pattern','previous','past','typical','normal','baseline','extrapolat'],'Policy':['fed','federal reserve','monetary policy','fiscal','stimulus','rate hike','rate cut','tightening','easing','central bank','government','policy response','intervention'],'Model':['phillips curve','okun','gdp growth','economic model','structural','relationship between','economic theory','multiplier','elasticity','economic indicator','leading indicator'],'Event':['covid','pandemic','crisis','recession','shock','war','collapse','lockdown','unprecedented','disruption','financial crisis','lehman','subprime','outbreak','emergency']}
for k,w in kw.items():r[k]=t.str.contains('|'.join(map(re.escape,w)))
r['Model-based']=r.Mechanical|r.Model;r['Judgment-based']=r.Policy|r.Event
r['Period']='Normal';r.loc[r.date_q.between('2008-07-01','2009-10-01'),'Period']='Financial Crisis';r.loc[r.date_q.between('2020-01-01','2020-10-01'),'Period']='COVID-19';r.loc[r.date_q.between('2022-01-01','2022-10-01'),'Period']='Inflation Shock'
print(r.groupby('Period').agg(N=('Name','size'),**{c:(c,'mean') for c in list(kw)+['Model-based','Judgment-based']}))
print('T9')
events=[('911','2001-07-01','1',['RGDP','UNEMP','CPI','TBILL','TBOND']),('Lehman','2008-07-01','1',['RGDP','UNEMP','CPI','TBILL','TBOND','HOUSING']),('Flash','2010-04-01','0',['RGDP','CPI']),('Downgrade','2011-07-01','0',['TBILL','TBOND','RGDP']),('COVID','2020-01-01','1',['RGDP','UNEMP','CPI','HOUSING','INDPROD']),('Ukraine','2022-01-01','1',['RGDP','CPI','TBILL','TBOND']),('SVB','2023-01-01','1',['RGDP','UNEMP','TBILL','TBOND'])]
a=b[b.type=='AI'].copy();a['ae']=a.forecast_error.abs();a['z']=a.groupby(['variable','id'],observed=True).ae.transform(lambda x:(x-x.mean())/x.std())
for e,q,h,vs in events:
 x=a[(a.id==h)&(a.date_q==q)];print(e,'h',h,'rel',round(x[x.variable.isin(vs)].z.mean(),4),'all',round(x.z.mean(),4))
print('T11 AI')
w=pd.read_parquet(C/'baseline_wide.parquet');print('n names',w.Name.nunique(),'n',len(w))
for v in ['RGDP','CPI','UNEMP','TBILL']:
 d=w[['Name','date_q',f'{v}_A0',f'{v}_R0',f'{v}_H0']].copy();d.columns=['person','date_q','forecast','realized','human_consensus'];d=d.sort_values(['person','date_q'],kind='stable');d['consensus']=d.groupby('date_q').forecast.transform('median')
 g=d.groupby('person');d['lagforecast']=g.forecast.shift();d['lagrealized']=g.realized.shift();d['lagconsensus']=g.consensus.shift();d['lagdate']=g.date_q.shift();d['rev']=d.forecast-d.lagforecast;d['lagerr']=d.lagrealized-d.lagforecast;d['errcurrent']=d.realized-d.lagforecast;d['dev']=d.lagforecast-d.lagconsensus;d['devhuman']=d.lagforecast-g.human_consensus.shift()
 for valid in ['allprevious','consecutive']:
  x=d if valid=='allprevious' else d[(d.date_q.dt.to_period('Q').astype(int)-d.lagdate.dt.to_period('Q').astype(int))==1]
  for reg in ['lagerr','errcurrent','dev','devhuman']:
   xx=x.dropna(subset=['rev',reg]);m=sm.OLS(xx.rev,sm.add_constant(xx[reg])).fit(cov_type='HC1');print(v,valid,reg,len(xx),round(m.params.iloc[1],4),round(m.bse.iloc[1],4),round(m.rsquared,4))
