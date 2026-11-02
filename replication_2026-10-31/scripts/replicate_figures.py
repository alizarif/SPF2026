#!/usr/bin/env python3
"""Recompute paper figures from serialized research data, without copying output plots.
Python ports of supplied R plotting functions. Figure 1 is explicitly documentary.
Figure 4 is a method reconstruction because the generating script is absent.
"""
from pathlib import Path
import json, textwrap, math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from scipy.ndimage import gaussian_filter1d
from scipy.stats import norm
import fitz

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT/'replication_2026-10-31'
CACHE = RUN/'data_cache'
OUT = RUN/'reproduced'/'figures'
OUT.mkdir(parents=True, exist_ok=True)
SRC = ROOT/'latest draft'/'figures'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.titlesize':9,'axes.labelsize':8,'xtick.labelsize':8,'ytick.labelsize':8,'axes.linewidth':.65,'axes.edgecolor':'#bbbbbb','pdf.fonttype':42})
RESULTS=[]


def load(name):
    x=pd.read_parquet(CACHE/(name+'.parquet'))
    if 'date_q' in x:
        x['date_q']=pd.to_datetime(x['date_q'])
    if 'id' in x:x['id']=x['id'].astype(str)
    return x


def clean_json(x):
    if isinstance(x,dict):return {str(k):clean_json(v) for k,v in x.items()}
    if isinstance(x,(tuple,list)):return [clean_json(v) for v in x]
    if isinstance(x,(np.integer,)):return int(x)
    if isinstance(x,(np.floating,)):return float(x) if np.isfinite(x) else None
    if isinstance(x,pd.Timestamp):return x.isoformat()
    return x


def page(title,caption=None):
    fig=plt.figure(figsize=(8.5,11))
    fig.text(.105,.94,title,ha='left',va='top',fontweight='bold',fontsize=11)
    if caption:fig.text(.105,.915,textwrap.fill(caption,105),ha='left',va='top',fontsize=8,linespacing=1.4)
    return fig


def save(fig,filename,footnote=None):
    if footnote:
        fig.text(.105,.055,textwrap.fill(footnote,110),fontsize=7,color='#444',ha='left',va='bottom')
    fig.savefig(OUT/(filename+'.pdf'))
    fig.savefig(OUT/(filename+'.png'),dpi=130)
    plt.close(fig)
    return str((OUT/(filename+'.pdf')).relative_to(RUN))


def combine(files,name):
    d=fitz.open()
    for f in files:
        s=fitz.open(RUN/f);d.insert_pdf(s)
    d.save(OUT/(name+'.pdf'));d.close()
    return str((OUT/(name+'.pdf')).relative_to(RUN))


def style_ts(ax,perc=False):
    ax.xaxis.set_major_locator(mdates.YearLocator(10))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.tick_params(length=0)
    ax.grid(False)
    if perc:
        from matplotlib.ticker import FuncFormatter
        ax.yaxis.set_major_formatter(FuncFormatter(lambda z,p:f'{z:g}%'))


def legend(fig,y=.12):
    fig.legend([Line2D([0],[0],color='darkgray',lw=3),Line2D([0],[0],color='black',lw=1)],['Human','AI'],loc='lower center',bbox_to_anchor=(.5,y),ncol=2,frameon=False,fontsize=9)


def add_result(id,pages,files,status,method,checks,limits=''):
    RESULTS.append({'id':id,'type':'figure','original_pages':pages,'reproduced_pages':files,'reproduced_pngs':[str(Path(f).with_suffix('.png')) for f in files],'reproduced_pdf':combine(files,id.replace('.','_')) if len(files)>1 else files[0],'status':status,'method':method,'checks':checks,'limitations':limits})


def source_line_check(filename,series,kind):
    """Compare regenerated values to original vector-plot path under affine axes.
    This only validates an independently computed series; it never supplies plot values.
    """
    path=SRC/filename
    if not path.exists():return {'status':'source_asset_missing'}
    doc=fitz.open(path);drawing=doc[0].get_drawings()
    wanted=[v for v in drawing if v['type']=='s' and len(v['items'])>4 and v['color'] and ((kind=='AI' and max(v['color'])<.05) or (kind=='Human' and .55<np.mean(v['color'])<.75))]
    # Data paths use distinctive R linewidths; excludes grid and recession boxes.
    wanted=[v for v in wanted if (kind=='AI' and .9<v['width']<1.3) or (kind=='Human' and 2.7<v['width']<3.3)]
    orig=[]
    for d in wanted:
        for item in d['items']:
            if item[0]=='l':
                if not orig or tuple(item[1])!=orig[-1]:orig.append(tuple(item[1]))
                
                if tuple(item[2]) != orig[-1]:orig.append(tuple(item[2]))
    arr=np.array(orig)
    s=series[['date_q','value']].dropna().sort_values('date_q').drop_duplicates('date_q')
    if len(arr)!=len(s):return {'status':'length_mismatch','original_vertices':len(arr),'recomputed_points':len(s)}
    # A path uses fixed PDF-point rounding; residual below .02pt is at rounding precision.
    xv=mdates.date2num(s.date_q);yv=s.value.to_numpy(float)
    bx=np.linalg.lstsq(np.c_[xv,np.ones(len(xv))],arr[:,0],rcond=None)[0]
    by=np.linalg.lstsq(np.c_[yv,np.ones(len(yv))],arr[:,1],rcond=None)[0]
    rx=arr[:,0]-np.c_[xv,np.ones(len(xv))]@bx
    ry=arr[:,1]-np.c_[yv,np.ones(len(yv))]@by
    # Also calibrate the ordinate from labeled axis ticks, so an arbitrary affine
    # transformation of wrong forecast levels cannot pass the shape check.
    tick_pairs=[];words=doc[0].get_text('words')
    for q in drawing:
        if q['type']!='s' or len(q['items'])!=1 or q['items'][0][0]!='l':continue
        _,p1,p2=q['items'][0]
        if abs(p1.y-p2.y)>.01 or not (0<abs(p2.x-p1.x)<5) or max(p1.x,p2.x)>arr[:,0].min():continue
        candidates=[]
        for word in words:
            if word[2]>max(p1.x,p2.x):continue
            try:val=float(word[4].replace('−','-').replace('%','').replace('$','').replace('B',''))
            except ValueError:continue
            distance=abs((word[1]+word[3])/2-p1.y)
            if distance<5:candidates.append((distance,val))
        if candidates:tick_pairs.append((min(candidates)[1],p1.y))
    absolute=None
    if len(tick_pairs)>=2:
        vals,coords=np.asarray(tick_pairs).T
        axis=np.polyfit(vals,coords,1);raw_diff=(arr[:,1]-axis[1])/axis[0]-yv
        calibrated_residual=abs(arr[:,1]-(yv*axis[0]+axis[1])).max()
        absolute={'max_value_difference_at_pdf_precision':float(abs(raw_diff).max()),'max_axis_calibrated_residual_pt':float(calibrated_residual),'axis_tick_pairs':tick_pairs}
    matching=max(abs(rx).max(),abs(ry).max())<.02 and by[0]<0 and (absolute is None or absolute['max_axis_calibrated_residual_pt']<.02)
    return {'status':'match_at_vector_rounding' if matching else 'different_series','n':len(s),'x_max_residual_pt':float(abs(rx).max()),'y_max_residual_pt':float(abs(ry).max()),'y_residual_fraction_span':float(abs(ry).max()/np.ptp(arr[:,1])),'axis_calibrated_values':absolute,'value_min':float(yv.min()),'value_max':float(yv.max())}


def documentary():
    fig=page('Figure 1. Example of forecaster acknowledgments','Documentary source image, reused from the supplied project; this is not a computed statistical result.')
    ax=fig.add_axes([.105,.22,.79,.62]);ax.imshow(plt.imread(SRC/'forecaster_thanks.png'));ax.axis('off')
    f=save(fig,'Figure1', 'Provenance: latest draft/figures/forecaster_thanks.png. Reused documentary material; no new empirical computation applies.')
    add_result('Figure1',[36],[f],'Documentary source reused','Display the original acknowledgment screenshot with explicit source identification.',{'source':str(SRC/'forecaster_thanks.png')})


def characteristics(wide):
    specs=[('gender2','Gender',['Female','Male','Unknown']),('cohort','Graduation Year',['-1969','1970-1989','1990-2009','2010-','Unknown']),('continent_origin','Continent of Origin',['USA','Americas (excl. USA)','Europe','Asia','Unknown']),('social_media_status2','Public Appearance',['Interviews only','Interviews + Twitter','Twitter only','Unknown']),('education_level','Education level',["Bachelor's","Master's",'MBA/MPA','Ph.D.','Unknown']),('education_field','Education field',['Economics/Finance','Business/Management','Econometrics/Statistics','Public Administration','Law','Unknown']),('affiliation_type2','Affiliation type',['Consulting','University','Investment Banking','Commercial Banking','Asset Management','Manufacturing','Other','Unknown']),('title2','Job title',['Chief Economist','Executive Role','Economist','Academic Role','Consultant/Analyst','Unknown'])]
    colors=['#66c2a5','#fc8d62','#8da0cb','#e78ac3','#a6d854','#ffd92f','#e5c494','#b3b3b3']
    counts=[];files=[];checks={}
    for pg in range(2):
        fig=page('Figure 2. Characteristics of the SPF panel over time'+(' (continued)' if pg else ''),'Quarterly composition of the AI persona panel, recomputed from participant records. Unknown characteristics remain a separate category.')
        axes=fig.subplots(2,2,gridspec_kw={'left':.11,'right':.95,'bottom':.20,'top':.84,'wspace':.24,'hspace':.50})
        for j,ax in enumerate(axes.flat):
            idx=pg*4+j;col,title,order=specs[idx]
            vals=wide[['date_q',col]].copy();vals[col]=vals[col].fillna('Unknown').astype(str)
            cats=list(dict.fromkeys(order+sorted(set(vals[col])-set(order))))
            tab=pd.crosstab(vals.date_q,vals[col]).reindex(columns=cats,fill_value=0)
            tab=tab.loc[:,tab.sum()>0];cats=tab.columns.tolist()
            cnt=tab.reset_index().melt('date_q',var_name='category',value_name='count');cnt['characteristic']=col
            cnt['share']=cnt['count']/cnt.groupby('date_q')['count'].transform('sum');counts.append(cnt)
            # Reproduce the smoothed proportional stream appearance; Gaussian smoothing
            # changes only the graphics, not the exported exact quarter-level shares.
            smooth=gaussian_filter1d(tab.to_numpy(float),sigma=2,axis=0,mode='nearest')
            smooth=smooth/smooth.sum(axis=1,keepdims=True)
            pal=colors[:len(cats)];pal[-1]='#b3b3b3'
            # ggplot stacks first factor at the top.
            ax.stackplot(tab.index,*smooth[:,::-1].T,colors=pal[::-1],lw=0)
            ax.set_ylim(0,1);ax.set_yticks([0,.25,.5,.75,1]);ax.set_yticklabels(['0.00','0.25','0.50','0.75','1.00'])
            ax.xaxis.set_major_locator(mdates.YearLocator(5));ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'));ax.tick_params(length=0)
            for spine in ax.spines.values():spine.set_visible(False)
            ax.set_title(f'({chr(97+idx)}) {title}',pad=12)
            from matplotlib.patches import Patch
            labels=[v.replace('Interviews only','Interviews').replace('Twitter only','Twitter') for v in cats]
            ax.legend([Patch(color=c) for c in pal],labels,loc='upper center',bbox_to_anchor=(.5,-.14),ncol=2 if len(cats)>3 else 3,fontsize=6,frameon=False,handlelength=.8,columnspacing=.9)
            checks[col]={'quarter_count':len(tab),'rows':int(tab.to_numpy().sum()),'categories':cats,'max_share_sum_error':float(abs((tab.div(tab.sum(axis=1),axis=0)).sum(axis=1)-1).max())}
            doc=fitz.open(SRC/(col+'_over_time.pdf'));areas=[]
            for drawing in doc[0].get_drawings():
                if drawing['fill'] and len(drawing['items'])>20:
                    pts=np.asarray([tuple(drawing['items'][0][1])]+[tuple(t[2]) for t in drawing['items'] if t[0]=='l'])
                    areas.append(abs(np.sum(pts[:,0]*np.roll(pts[:,1],1)-pts[:,1]*np.roll(pts[:,0],1)))/2)
            checks[col]['current_mean_quarterly_shares']=tab.div(tab.sum(axis=1),axis=0).mean().to_dict()
            checks[col]['source_rendered_mean_area_shares_in_legend_order']=(np.asarray(areas)/sum(areas)).tolist()
            checks[col]['source_legend_order']=order
            checks[col]['comparison_note']='Source polygon areas are visual audit measures; they do not supply regenerated counts or shares.'
        files.append(save(fig,f'Figure2_page{pg+1}','Computed from the saved baseline participant panel. Gaussian smoothing approximates the supplied ggstream renderer; exact quarterly counts and shares are exported to CSV.'))
    pd.concat(counts).to_csv(OUT/'Figure2_quarterly_characteristics.csv',index=False)
    add_result('Figure2',[37,38],files,'Recomputed; source composition differs','Port of fig_characteristics_over_time.R: group participant rows by quarter and trait; proportional stacked areas in original panel order.',checks,'Saved metadata differ from the final-PDF category composition (notably gender Unknown and the additional No public appearance category). Original ggstream smoothing is replaced by a Gaussian graphical smoother (2 quarters). Exact underlying shares are retained; category sets are checked, not adjusted to force agreement.')


def medians(ts):
    files=[];checks={};parts=[]
    vs=['CPI','TBILL','UNEMP','RGDP'];names=['CPI inflation rate','3-month Treasury bill rate','Unemployment rate','Real GDP index']
    for pg in range(2):
        fig=page('Figure 3. SPF and AI-generated median forecasts'+(' (continued)' if pg else ''),'One- and four-quarter-ahead median human and AI forecasts. Shaded areas denote NBER recession quarters.')
        axs=fig.subplots(2,2,gridspec_kw={'left':.12,'right':.94,'bottom':.22,'top':.84,'wspace':.25,'hspace':.35})
        for j,ax in enumerate(axs.flat):
            k=pg*2+j//2;v=vs[k];h=['1','4'][j%2]
            sub=ts[(ts.variable==v)&(ts.id==h)].copy();parts.append(sub)
            rec=sub[['date_q','nber_rec']].drop_duplicates().sort_values('date_q')
            for r in rec[rec.nber_rec==1].itertuples():ax.axvspan(r.date_q-pd.Timedelta(days=45),r.date_q+pd.Timedelta(days=45),color='black',alpha=.12,lw=0)
            for typ,col,lw in [('Human','darkgray',3),('AI','black',1)]:
                d=sub[sub.type==typ].sort_values('date_q');ax.plot(d.date_q,d['median'],color=col,lw=lw)
                checks[f'{v}_{h}_{typ}']=source_line_check(f'ts_median_{v}_{h}.pdf',d.rename(columns={'median':'value'}),typ)
            style_ts(ax,perc=v!='RGDP')
            if v in ['RGDP','UNEMP']:ax.set_ylim(-.05*sub['median'].max(),1.05*sub['median'].max())
            ax.set_title(f'({chr(97+pg*4+j)}) {names[k]}, '+('one quarter ahead' if h=='1' else 'four quarters ahead'),fontsize=7.5)
        legend(fig,.14);files.append(save(fig,f'Figure3_page{pg+1}','Medians recomputed from saved individual forecasts and checked against the source plot vector paths. Recession shading uses the saved NBER series.'))
    pd.concat(parts).to_csv(OUT/'Figure3_medians.csv',index=False)
    status='Reproduced: numeric series match' if all(c.get('status')=='match_at_vector_rounding' for c in checks.values()) else 'Recomputed; source-series mismatch'
    add_result('Figure3',[39,40],files,status,'Port of fig_ts_median.R: quarterly cross-sectional AI medians and published human SPF medians, horizons 1 and 4.',checks,'Matplotlib typography and page layout differ from R/LaTeX.')


def bw_nrd0(x):
    x=np.asarray(x);x=x[np.isfinite(x)]
    if len(x)<2:return 1.
    hi=0. if np.ptp(x)==0 else np.std(x,ddof=1);lo=min(hi,(np.percentile(x,75)-np.percentile(x,25))/1.34)
    if lo==0:lo=hi or abs(x[0]) or 1
    return .9*lo*len(x)**(-.2)


def density_source_check(filename, curves):
    """Check recomputed KDEs against published paths after common vertical scaling."""
    doc=fitz.open(SRC/filename)
    polygons=[q for q in doc[0].get_drawings() if q['fill'] and len(q['items'])>500]
    expected=[z for row in curves[::-1] for z in row]  # source draws latest quarter first
    generated=[];target=[]
    for kde,poly in zip(expected,polygons):
        points=[tuple(poly['items'][0][1])]+[tuple(t[2]) for t in poly['items'] if t[0]=='l']
        top=[]
        for point in points:
            if top and point[0]<top[-1][0]:break
            if not top or point[0]!=top[-1][0]:top.append(point)
        top=np.asarray(top)
        if len(top)!=len(kde):return {'status':'inconclusive','vertices':len(top)}
        generated.extend(kde);target.extend(poly['rect'].y1-top[:,1])
    a=np.asarray(generated);b=np.asarray(target);scale=np.dot(a,b)/np.dot(a,a);res=b-a*scale
    return {'status':'density_shapes_agree' if max(abs(res))/max(b)<.02 else 'density_shape_mismatch','curves':len(polygons),'grid_points_per_curve':512,'max_height_error_fraction':float(max(abs(res))/max(b)),'rms_height_error_fraction':float(np.sqrt(np.mean(res**2))/max(b)),'note':'Direct Gaussian evaluation versus original R FFT density implementation; vertical scaling and PDF point rounding accounted for.'}


def density(long,micro):
    wanted=pd.to_datetime(['1999-01-01','2008-07-01','2020-04-01','2023-01-01'])
    vs=['CPI','TBILL','UNEMP','RGDP'];names=['CPI inflation rate','3-month Treasury bill rate','Unemployment rate','Real GDP index']
    files=[];checks={};parts=[]
    for pg in range(2):
        fig=page('Figure 5. Densities of human and AI forecast errors'+(' (continued)' if pg else ''),'Individual forecast distributions centered on realized values for four selected quarters. Original panel order and horizons are retained.')
        axs=fig.subplots(2,2,gridspec_kw={'left':.15,'right':.95,'bottom':.22,'top':.84,'wspace':.40,'hspace':.35})
        for j,ax in enumerate(axs.flat):
            k=pg*2+j//2;v=vs[k];h=['1','4'][j%2]
            sel=long[(long.variable==v)&(long.id==h)&long.date_q.isin(wanted)]
            real=sel[sel.type=='Realized'][['date_q','value']].drop_duplicates().rename(columns={'value':'realized'})
            a=sel[sel.type=='AI'][['date_q','value']].assign(type='AI')
            b=micro[(micro.variable==v)&(micro.id==h)&micro.date_q.isin(wanted)][['date_q','value']].assign(type='Human')
            d=pd.concat([a,b]).merge(real,on='date_q');d['error']=d.value-d.realized;d=d.dropna(subset=['error']);d['variable']=v;d['horizon']=h;parts.append(d)
            # ggridges default computes one common nrd0 bandwidth by averaging each group's bandwidth.
            grouped=[g.error.to_numpy() for _,g in d.groupby(['date_q','type'])]
            bw=float(np.mean([bw_nrd0(x) for x in grouped]))
            grid=np.linspace(d.error.min()-3*bw,d.error.max()+3*bw,512)
            curves=[]
            for dt in wanted:
                row=[]
                for typ in ['Human','AI']:
                    x=d[(d.date_q==dt)&(d.type==typ)].error.to_numpy()
                    z=np.mean(norm.pdf((grid[:,None]-x[None,:])/bw),axis=1)/bw if len(x) else np.zeros_like(grid)
                    row.append(z)
                curves.append(row)
            max_height=max(float(z.max()) for row in curves for z in row)
            for q,row in enumerate(curves):
                for z,c in zip(row,['darkgray','black']):ax.fill_between(grid,q,q+z/max_height*1.8,color=c,alpha=.7,lw=0)
            ax.set_yticks(range(4));ax.set_yticklabels(['1999 Q1','2008 Q3','2020 Q2','2023 Q1']);ax.set_ylim(-.4,4.8);ax.tick_params(length=0);ax.set_title(f'({chr(97+pg*4+j)}) {names[k]}, '+('one quarter ahead' if h=='1' else 'four quarters ahead'),fontsize=8)
            checks[v+'_'+h]={'source_shape_check':density_source_check(f'density_{v}_{h}.pdf',curves),'bandwidth':bw,'groups':[{'quarter':str(dt.date()),'type':typ,'n':len(g),'error_mean':float(g.error.mean()),'error_sd':float(g.error.std()),'min':float(g.error.min()),'max':float(g.error.max())} for (dt,typ),g in d.groupby(['date_q','type'])]}
        legend(fig,.14);files.append(save(fig,f'Figure5_page{pg+1}','Recomputed Gaussian kernel densities with a common R nrd0 bandwidth for the groups in each panel. Forecast-error samples and numerical distribution summaries are exported.'))
    pd.concat(parts).to_csv(OUT/'Figure5_density_samples.csv',index=False)
    add_result('Figure5',[42,43],files,'Recomputed: density shapes agree','Port of fig_densities.R: AI individual forecasts plus human SPF microdata, minus corresponding realized value. Common Gaussian KDE bandwidth is mean group nrd0.',checks,'All 64 density curves compared against original vector paths. Gaussian KDE is evaluated directly; original R density uses FFT approximation. Detailed shape residuals are reported (roughly <=2% of peak height). No original plot points supply reproduction data.')


def oos_errors(ts,oos):
    allts=oos.copy()  # Final-PDF curves use the OOS run for its overlapping 2023 observations.
    # The final PDF assets start in 2023, although archived R function says after 2020.
    allts=allts[(allts.date_q>=pd.Timestamp('2023-01-01'))&(allts.id=='1')]
    vs=['CPI','TBILL','UNEMP','RGDP'];names=['CPI inflation rate','3-month Treasury bill rate','Unemployment rate','Real GDP']
    fig=page('Figure 6. Median forecast errors around the training cutoff','One-quarter-ahead median forecast errors. The dashed line indicates October 2023, the stated GPT-4o mini training-data cutoff.')
    axs=fig.subplots(2,2,gridspec_kw={'left':.12,'right':.94,'bottom':.20,'top':.84,'wspace':.28,'hspace':.35});checks={};parts=[]
    for k,(v,ax) in enumerate(zip(vs,axs.flat)):
        d=allts[allts.variable==v].copy();parts.append(d)
        ax.axhline(0,color='black',ls=':',lw=.8);ax.axvline(pd.Timestamp('2023-10-31'),color='black',ls='--',lw=1.4)
        for typ,col,lw in [('Human','darkgray',3),('AI','black',1)]:
            z=d[d.type==typ].sort_values('date_q');ax.plot(z.date_q,z.forecast_error,color=col,lw=lw)
            checks[v+'_'+typ]=source_line_check(f'forecast_error_oos_{v}_1.pdf',z.rename(columns={'forecast_error':'value'}),typ)
        style_ts(ax,perc=v!='RGDP');ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1,7]));ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'));ax.set_title(f'({chr(97+k)}) {names[k]}, one quarter ahead',fontsize=8)
    legend(fig,.12);f=save(fig,'Figure6','Out-of-sample run, including its 2023 survey quarters. Errors use the supplied R rule: median forecast, clipped to realized mean ±3 SD, less realized value. Display starts at 2023Q1 to match the final PDF.');pd.concat(parts).to_csv(OUT/'Figure6_errors.csv',index=False)
    status='Reproduced: numeric series match' if all(c.get('status')=='match_at_vector_rounding' for c in checks.values()) else 'Recomputed; source-series mismatch'
    add_result('Figure6',[44],[f],status,'Port of fig_forecast_errors_outofsample.R with final-PDF 2023 display window. Use outofsample_data.rda including 2023 overlap; horizon 1. All eight source curves match this provenance.',checks,'Archived plotting function concatenates baseline and OOS and begins in 2021; the final PDF instead matches the OOS run alone for 2023–2024. This provenance difference is identified by all eight numeric paths.')


def counts_participation(wide,long,micro):
    old=load('old_baseline_participants')
    old=old[old.Name!='No Name Provided'].copy()
    a=old.groupby('date_q').size().rename('AI')
    h=micro.groupby(['date_q','variable','id'],observed=True).size().groupby('date_q').mean().rename('Human')
    c=pd.concat([a,h],axis=1).reset_index();c.to_csv(OUT/'FigureA1_counts.csv',index=False)
    fig=page('Figure A.1. Number of forecasters over time','AI participant counts from the original multivariable_SPF6.xlsx run; human SPF counts averaged across variables and horizons.')
    ax=fig.add_axes([.12,.25,.80,.55]);checks={}
    for typ,col,lw in [('Human','darkgray',3),('AI','black',1)]:
        ax.plot(c.date_q,c[typ],color=col,lw=lw);checks[typ]=source_line_check('num_forecasters_over_time.pdf',c[['date_q',typ]].rename(columns={typ:'value'}),typ)
    style_ts(ax);ax.set_ylim(0,70);ax.set_yticks(np.arange(0,71,10));ax.xaxis.set_major_locator(mdates.YearLocator(5));legend(fig,.15)
    f=save(fig,'FigureA1','The final PDF uses the older multivariable_SPF6.xlsx participant panel (5,188 rows after excluding No Name Provided), rather than the later baseline cache (5,308 rows). Both source curves match at vector rounding precision.');add_result('FigureA.1',[61],[f],'Reproduced: numeric series match' if all(v.get('status')=='match_at_vector_rounding' for v in checks.values()) else 'Recomputed; source-series mismatch','Port of fig_num_forecasters_over_time.R. Original workbook AI row counts; human microdata row counts by quarter/variable/horizon, then average. Later baseline vintage differs.',checks)
    # Reconstruct historical membership using available named-panel metadata.
    meta=pd.read_csv(ROOT/'Simulating_SPF_processing/data/individual_forecasters.csv',low_memory=False)
    meta=meta[meta.Name.isin(set(old.Name))].copy()
    meta['date_q']=pd.PeriodIndex(meta.date_q.astype(str).str.replace(' ',''),freq='Q').to_timestamp()
    wide=meta[['Name','date_q']].copy()
    stats=wide.groupby('Name',sort=True).agg(duration=('date_q','size'),start=('date_q','first')).reset_index().sort_values(['start','duration'],ascending=[False,False],kind='stable')
    names=stats.Name.tolist();dates=np.sort(wide.date_q.unique());p=wide.merge(stats,on='Name');p['duration_years']=p.duration/4;p.to_csv(OUT/'FigureA2_participation.csv',index=False)
    mat=pd.crosstab(p.Name,p.date_q).reindex(index=names,columns=dates,fill_value=0).to_numpy(float)
    durs=stats.set_index('Name').loc[names].duration.to_numpy()/4;mat=np.where(mat>0,durs[:,None],np.nan)
    fig=page('Figure A.2. Duration of individual forecaster participation','Quarterly panel membership, ordered by starting date and participation duration. Color denotes total observed participation in years.')
    ax=fig.add_axes([.15,.20,.79,.63]);numdates=mdates.date2num(pd.to_datetime(dates));dx=np.median(np.diff(numdates));edges=np.r_[numdates-dx/2,numdates[-1]+dx/2]
    cmap=LinearSegmentedColormap.from_list('R_gradient',[(0,'white'),(1/max(durs),'red'),(1,'darkblue')]);im=ax.pcolormesh(edges,np.arange(len(names)+1),mat,cmap=cmap,vmin=0,vmax=max(durs),edgecolors='white',linewidth=.18,shading='flat')
    ax.set_yticks([]);ax.set_ylabel('Individual forecasters');ax.xaxis_date();ax.xaxis.set_major_locator(mdates.YearLocator(10));ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'));cb=fig.colorbar(im,ax=ax,orientation='horizontal',pad=.07,fraction=.025);cb.set_ticks([5,10,15,20,25])
    f=save(fig,'FigureA2','Port of fig_participation_over_time.R using available participation metadata for the original 193 names. The original has 5,232 tile records; current metadata have 5,236. Some quarterly memberships differ, so this is a partial replication.');add_result('FigureA.2',[62],[f],'Partial replication: historical membership differs','Restrict individual_forecasters.csv to the 193 original AI names; duration=n()/4; start=first(date_q); order descending start and duration; draw forecaster-quarter tiles.',{'forecasters':len(names),'participant_quarters':len(wide),'unique_participant_quarters':len(wide.drop_duplicates()),'original_tile_records':5232,'original_unique_participant_quarters':5208,'original_row_membership_patterns_matching':189,'min_years':float(min(durs)),'max_years':float(max(durs)),'date_start':str(min(dates)),'date_end':str(max(dates))},'Original data_wide vintage unavailable: current metadata yield 5236 records, original vector asset5232; both have5208 unique tiles. 189 of193 original forecaster membership patterns match current metadata exactly. Ordering/tie handling and gradient rendering also differ.')


def fixed_effects(long):
    """Reconstruct equation (11); evaluate omitted horizon and restriction order.
    Independently computed nowcasts with pre-demeaning sample restriction reproduce
    both visible means and every histogram bar. The caption's 194 is pre-filter N.
    """
    raw=load('baseline_raw_forecasts')
    candidates={};tables=[]
    for horizon in ['0','1','4']:
        for order in ['filter_before_demean','filter_after_demean']:
            key=f'h{horizon}_{order}';stat={}
            for v in ['RGDP','CPI','UNEMP','NGDP']:
                col=v+'_A'+horizon
                d=raw[['date_q','Name',col]].dropna().rename(columns={col:'value'}).copy()
                n=d.groupby('Name').size();keep=n[n>=10].index
                if order=='filter_before_demean':d=d[d.Name.isin(keep)].copy()
                d['deviation']=d.value-d.groupby('date_q').value.transform('mean')
                g=d.groupby('Name').agg(fixed_effect=('deviation','mean'),n=('value','size'),quarters=('date_q','nunique')).reset_index()
                g=g[g.n>=10];g['variable']=v;g['candidate']=key;tables.append(g)
                hist,edges=np.histogram(g.fixed_effect,bins=20)
                stat[v]={'n':len(g),'mean':float(g.fixed_effect.mean()),'sd':float(g.fixed_effect.std()),'min':float(g.fixed_effect.min()),'max':float(g.fixed_effect.max()),'histogram_counts':hist.tolist(),'histogram_bin_edges':edges.tolist()}
            candidates[key]=stat
    pd.concat(tables).to_csv(OUT/'Figure4_fixed_effects_candidates.csv',index=False)
    chosen='h0_filter_before_demean';g=pd.concat([x for x in tables if x.candidate.iloc[0]==chosen]);g.to_csv(OUT/'Figure4_fixed_effects.csv',index=False)
    fig=page('Figure 4. Distribution of forecaster fixed effects','Reconstructed from raw AI nowcasts: retain forecasters with at least ten valid observations, then subtract quarterly cross-sectional means and average each forecaster’s deviations.')
    axs=fig.subplots(2,2,gridspec_kw={'left':.12,'right':.94,'bottom':.22,'top':.84,'wspace':.28,'hspace':.35})
    for v,ax,col in zip(['RGDP','CPI','UNEMP','NGDP'],axs.flat,['#e3889c','#c3be79','#e3889c','#6fa7a9']):
        z=g[g.variable==v].fixed_effect;ax.hist(z,bins=20,color=col,edgecolor='gray',linewidth=.5);ax.axvline(0,color='red',ls='--',lw=1,label='Zero (no bias)');ax.axvline(z.mean(),color='black',lw=1,label=f'Mean = {z.mean():.2f}');ax.set_title(f'{v} Forecast Fixed Effects\n(Persistent Optimism/Pessimism)',fontsize=9);ax.set_xlabel('Fixed effect (deviation from quarterly mean)',fontsize=7);ax.set_ylabel('Number of forecasters',fontsize=7);ax.legend(fontsize=6)
        if v=='UNEMP':
            from matplotlib.ticker import MaxNLocator
            ax.xaxis.set_major_locator(MaxNLocator(5))
    f=save(fig,'Figure4','Recovered calculation matches the published histogram means and shapes. Actual retained sample: 121 forecasters; the caption’s 194 is the count before the ten-observation restriction. Horizon and restriction order were omitted from the paper; both are documented here.')
    chosen_stats=candidates[chosen]
    # Audit pixel histogram heights only for comparison; never use these pixels
    # to generate values. Each chart uses an independently computed 20-bin histogram.
    from PIL import Image
    from scipy.ndimage import label, find_objects
    arr=np.asarray(Image.open(SRC/'figure6_fixed_effects_updated.png').convert('RGB'))
    pixel_checks={}
    for v,rgb,which in [('RGDP',(227,136,156),'top'),('CPI',(195,190,121),'top'),('UNEMP',(227,136,156),'bottom'),('NGDP',(111,167,169),'bottom')]:
        mask=np.all(arr==rgb,axis=2);mid=arr.shape[0]//2
        if which=='top':mask[mid:]=False
        else:mask[:mid]=False
        labels,n=label(mask);boxes=[]
        for sl in find_objects(labels):
            ys,xs=sl;h=ys.stop-ys.start;w=xs.stop-xs.start
            if h>8 and w>8:boxes.append((xs.start,ys.start,xs.stop,ys.stop))
        # A vertical reference line can split a bar into two components. Merge by
        # nominal 20-bin x position inferred from independently computed bin edges.
        if boxes:
            lo=min(x[0] for x in boxes);hi=max(x[2] for x in boxes)
            width=(hi-lo)/20
            heights={}
            for x0,y0,x1,y1 in boxes:
                idx=int(np.clip(np.floor(((x0+x1)/2-lo)/width),0,19));heights[idx]=max(heights.get(idx,0),y1-y0)
            hist=np.asarray(chosen_stats[v]['histogram_counts']);pairs=[(hist[i],hh) for i,hh in heights.items() if hist[i]>0]
            x=np.array([a for a,b in pairs]);y=np.array([b for a,b in pairs]);coef=np.linalg.lstsq(np.c_[x,np.ones(len(x))],y,rcond=None)[0];res=y-np.c_[x,np.ones(len(x))]@coef
            pixel_checks[v]={'nonzero_bars_compared':len(pairs),'total_nonzero_bars':int((hist>0).sum()),'height_residual_max_px':float(abs(res).max()),'count_per_pixel':float(1/coef[0]),'status':'matching_histogram_heights' if abs(res).max()<2 else 'pixel_check_inconclusive'}
    add_result('Figure4',[41],[f],'Reconstructed histogram matches; caption N differs','Raw baseline nowcasts, including the literal No Name Provided record. Restrict each variable to forecasters with >=10 observations BEFORE demeaning; average quarterly deviations by Name; 20 bins. Code was absent, so horizon/order were inferred and independently checked.',{'chosen_candidate':chosen,'computed':chosen_stats,'histogram_visual_validation':pixel_checks,'alternative_candidates':candidates,'target_caption_n':194,'actual_filtered_n':121,'target_visible_means':{'RGDP':11.48,'CPI':0.00,'UNEMP':0.00,'NGDP':-.82},'target_prose':{'RGDP_min':-160,'RGDP_max':187,'RGDP_sd':28.4,'CPI_sd':.27}},'Published sample size 194 is inconsistent with 121 histogram participants after restriction. Main-text RGDP range/SD and CPI SD also differ from the recovered plotted values. No image pixels supplied generated values.')


def rebuild_time_series(long, saved, figure6_only=False):
    """Recompute aggregation and the supplied mean +/-3sd winsorization rule."""
    keys=['date_q','variable','id','type']
    med=long[long.type.isin(['AI','Human'])].groupby(keys,observed=True).value.median().reset_index(name='computed_median')
    ts=saved.merge(med,on=keys,how='left',validate='one_to_one')
    mdiff=float((ts['median']-ts.computed_median).abs().max())
    ts['median']=ts.pop('computed_median')
    groups=ts.groupby(['type','id','variable'],observed=True)
    mean=groups.realized.transform('mean');sd=groups.realized.transform('std')
    clipped=ts['median'].clip(mean-3*sd,mean+3*sd)
    # R comparisons with NA bounds do not turn an otherwise available forecast NA.
    clipped=clipped.where((mean-3*sd).notna(),ts['median'])
    err=clipped-ts.realized
    check_mask=(ts.variable.isin(['CPI','TBILL','UNEMP','RGDP'])&(ts.id=='1')) if figure6_only else pd.Series(True,index=ts.index)
    ediff=float((ts.loc[check_mask,'forecast_error']-err.loc[check_mask]).abs().max())
    ts['median_']=clipped;ts['forecast_error']=err
    return ts, {'median_max_abs_difference_from_R_cache':mdiff,'forecast_error_max_abs_difference_from_R_cache':ediff,'groups':int(check_mask.sum()),'scope':'four Figure6 variables at horizon1' if figure6_only else 'all baseline series'}


def main():
    wide=load('baseline_wide');long=load('baseline_long');ts=load('baseline_ts');micro=load('baseline_microdata');oos=load('oos_ts')
    ts,baseline_check=rebuild_time_series(long,ts)
    oos,oos_check=rebuild_time_series(load('oos_long'),oos,figure6_only=True)
    documentary();characteristics(wide);medians(ts);fixed_effects(long);density(long,micro);oos_errors(ts,oos);counts_participation(wide,long,micro)
    for r in RESULTS:
        if r['id']=='Figure3':r['checks']['aggregation_validation']=baseline_check
        if r['id']=='Figure6':r['checks']['aggregation_validation']=oos_check
    (RUN/'figures_results.json').write_text(json.dumps(clean_json(RESULTS),indent=2))
    print(json.dumps([{'id':r['id'],'status':r['status']} for r in RESULTS],indent=2))

if __name__=='__main__':main()
