#!/usr/bin/env python3
"""Rebuild the six distribution pages with the attached review's common scales.

Run from the repository root: python3 reproduce.py --distributions
Inputs: individual AI and human forecasts and realized values in main_data.zip.
Output: report/original_distributions.pdf (two ridge pages, four density pages).

Presentation follows the recovered original make_review.py: four survey dates,
horizons 1 and 4, common x limits and density-height conversion within variable.
The original R smoothing is reproduced from observations, without PDF tracing.
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.ticker import MaxNLocator
from matplotlib.lines import Line2D

from data import ROOT, load_frame


VARIABLES = ("CPI", "UNEMP", "TBILL", "RGDP")
HORIZONS = (1, 4)
SELECTED_DATES = pd.to_datetime(["1999-01-01", "2008-07-01", "2020-04-01", "2023-01-01"])


def build_error_samples():
    """Return variable, horizon, type, yearqtr, value (3,088 source rows).

    `value` is forecast minus realized value. Fifty-seven missing individual
    forecasts remain missing; the original R density estimator excludes them
    during estimation. The 3,031 finite errors retain the source units.
    """
    wide = load_frame("baseline_wide")
    micro = load_frame("baseline_microdata")
    for frame in (wide, micro):
        frame["date_q"] = pd.to_datetime(frame["date_q"])
    micro["id"] = micro["id"].astype(str)
    wide = wide.loc[wide["date_q"].isin(SELECTED_DATES)]
    micro = micro.loc[micro["date_q"].isin(SELECTED_DATES)]
    blocks = []
    for variable in VARIABLES:
        for horizon in HORIZONS:
            actual_column = f"{variable}_R{horizon}"
            actual = wide[["date_q", actual_column]].drop_duplicates()
            assert len(actual) == 4 and not actual["date_q"].duplicated().any()
            assert np.isfinite(actual[actual_column]).all()
            actual = actual.set_index("date_q")[actual_column]
            ai = wide[["date_q", f"{variable}_A{horizon}"]].rename(
                columns={f"{variable}_A{horizon}": "forecast"})
            human = micro.loc[micro["variable"].eq(variable)
                              & micro["id"].eq(str(horizon)), ["date_q", "value"]]
            human = human.rename(columns={"value": "forecast"})
            for survey, data in (("AI", ai), ("Human", human)):
                assert set(data["date_q"]) == set(SELECTED_DATES)
                block = pd.DataFrame({
                    "variable": variable,
                    "horizon": horizon,
                    "type": survey,
                    "yearqtr": (data["date_q"].dt.year.astype(str) + " Q"
                                + data["date_q"].dt.quarter.astype(str)),
                    "value": data["forecast"] - data["date_q"].map(actual),
                })
                blocks.append(block)
    samples = pd.concat(blocks, ignore_index=True)
    assert len(samples) == 3088
    assert samples["value"].isna().sum() == 57
    assert np.isfinite(samples["value"]).sum() == 3031
    groups = samples.groupby(["variable", "horizon", "type", "yearqtr"], observed=True)
    assert groups.ngroups == 64 and groups["value"].count().min() >= 2
    return samples


# Algorithm references (no R runtime is needed):
# https://github.com/wch/r-source/blob/R-4-4-branch/src/library/stats/R/density.R
# https://github.com/wch/r-source/blob/trunk/src/library/stats/src/massdist.c
# https://github.com/wilkelab/ggridges/blob/master/R/stats.R

def bw_nrd0(values):
    """R's normal-reference bandwidth, including its constant-sample fallback."""
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 2:
        raise ValueError('At least two finite values are required')
    if np.all(x == x[0]):
        sd = 0.0
    else:
        # R accumulates means/squared deviations in extended precision.
        xx = x.astype(np.longdouble)
        mean = np.mean(xx)
        mean += np.sum(xx-mean) / len(xx)
        sd = float(np.sqrt(np.sum((xx-mean)**2) / (len(xx)-1)))
    lo = min(sd, float(np.diff(np.quantile(x, [.25, .75]))[0])/1.34)
    if lo == 0:
        lo = sd or abs(x[0]) or 1.0
    return 0.9 * lo * len(x)**(-0.2)


def r_density(values, bandwidth, start, end, n=512):
    """Return the n equally spaced x/y estimates used by the original plots."""
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if not len(x) or bandwidth <= 0 or end <= start:
        raise ValueError('Invalid density input')
    bins = max(512, 2**int(np.ceil(np.log2(n))))
    lower = start - 4*bandwidth
    upper = end + 4*bandwidth
    step = (upper-lower)/(bins-1)
    mass = np.zeros(2*bins)
    for value in x:
        position = (value-lower)/step
        left = int(np.floor(position))
        fraction = position-left
        if 0 <= left < bins-1:
            mass[left] += (1-fraction)/len(x)
            mass[left+1] += fraction/len(x)
        elif left == -1:
            mass[0] += fraction/len(x)
        elif left == bins-1:
            mass[left] += (1-fraction)/len(x)
    # Mirror positive lags around the periodic boundary. The midpoint's Gaussian
    # value is negligible; its positive sign matches the R construction.
    lags = np.arange(2*bins)*step
    lags[bins+1:] = -lags[bins-1:0:-1]
    kernel = np.exp(-0.5*(lags/bandwidth)**2)/(bandwidth*np.sqrt(2*np.pi))
    smooth = np.fft.ifft(np.fft.fft(mass)*np.conj(np.fft.fft(kernel))).real[:bins]
    smooth = np.maximum(0.0, smooth)
    grid = np.linspace(start, end, n)
    return grid, np.interp(grid, np.linspace(lower, upper, bins), smooth)


def ridgeline_curves(observations):
    """Recompute every variable/horizon panel using only raw exported values.

    Columns: variable, horizon, type, yearqtr, value. No exported curves or
    settings are read. Groups with missing values drop those rows before bw/KDE.
    """
    results = []
    settings = []
    for (variable, horizon), panel in observations.groupby(['variable','horizon'], sort=True):
        panel = panel[np.isfinite(panel.value)]
        groups = list(panel.groupby(['type', 'yearqtr'], sort=True))
        bandwidth = float(np.mean([bw_nrd0(group.value) for _, group in groups]))
        start = float(panel.value.min()-3*bandwidth)
        end = float(panel.value.max()+3*bandwidth)
        heights = []
        for (kind, quarter), group in groups:
            grid, height = r_density(group.value, bandwidth, start, end)
            heights.append(float(height.max()))
            results.append(pd.DataFrame(dict(variable=variable,horizon=horizon,
                type=kind,yearqtr=quarter,x=grid,density=height)))
        settings.append(dict(variable=variable,horizon=horizon,bandwidth=bandwidth,
                             min_x=start,max_x=end,max_density=max(heights)))
    return pd.concat(results,ignore_index=True), pd.DataFrame(settings)


def compute_density_curves(samples):
    """Return plotting-ready curves; consume observations, never oracle curves.

    Input columns: variable, horizon, type, yearqtr, value. Output columns:
    variable, horizon, type, yearqtr, x, density. Each group has 512 rows.
    The eight independently computed panel settings are available in
    returned_dataframe.attrs['settings'] as a list of records.
    """
    curves, settings = ridgeline_curves(samples)
    curves.attrs['settings'] = settings.to_dict('records')
    return curves


def render_distributions(curves, destination):
    """Use the same limits, ridge scaling, page sizes and layout as the review."""
    LABELS={'CPI':'CPI inflation','UNEMP':'Unemployment rate','TBILL':'3-month Treasury bill yield','RGDP':'Real GDP'}
    VARIABLES=list(LABELS)
    QUARTERS=['1999 Q1','2008 Q3','2020 Q2','2023 Q1']
    COLORS={'AI':'#151515','Human':'#888888'}
    LIMITS={}
    for v in VARIABLES:
        c=curves[curves.variable.eq(v)]
        xlo,xhi=c.x.min(),c.x.max()
        LIMITS[v]={'x_min':float(xlo),'x_max':float(xhi),'density_max':float(c.density.max()*1.06)}
    plt.rcParams.update({'font.family':'serif','font.size':11,'axes.titlesize':13,
        'axes.labelsize':11,'xtick.labelsize':10,'ytick.labelsize':10,
        'pdf.fonttype':3,'ps.fonttype':42,'axes.linewidth':.65,
        'axes.unicode_minus':False})
    handles=[Line2D([],[],color=COLORS['AI'],lw=2,label='AI'),Line2D([],[],color=COLORS['Human'],lw=2,label='Human SPF')]

    def style(ax):
        ax.spines[['top','right']].set_visible(False)
        ax.grid(axis='x',color='#eeeeee',lw=.6)
        ax.set_axisbelow(True)
        ax.xaxis.set_major_locator(MaxNLocator(5))

    def unit(v):return 'Billions, as recorded' if v=='RGDP' else 'Percentage points'

    def distribution(c,v,h,q,panel):
        return c[(c.variable==v)&(c.horizon==h)&(c.yearqtr==q)&(c.type==panel)].sort_values('x')

    figs=[]
    for variables in [['CPI','UNEMP'],['TBILL','RGDP']]:
        fig,axs=plt.subplots(2,2,figsize=(10.8,9.4))
        for i,v in enumerate(variables):
            lim=LIMITS[v]
            for j,h in enumerate([1,4]):
                ax=axs[i,j]
                for qi,q in enumerate(QUARTERS):
                    for panel in ['Human','AI']:
                        z=distribution(curves,v,h,q,panel)
                        height=z.density.to_numpy()/lim['density_max']*.84
                        ax.fill_between(z.x,qi,qi+height,color=COLORS[panel],alpha=.34 if panel=='AI' else .28,linewidth=0)
                        # Suppress only visually zero line segments; retain the full
                        # density, its support, and every observation in the calculation.
                        visible=np.where(height>1e-5,qi+height,np.nan)
                        ax.plot(z.x,visible,color=COLORS[panel],lw=1.1)
                    ax.hlines(qi,lim['x_min'],lim['x_max'],color='#dddddd',lw=.45,zorder=0)
                ax.axvline(0,color='#999999',ls=':',lw=.7,zorder=0)
                ax.set_xlim(lim['x_min'],lim['x_max']);ax.set_ylim(-.18,4.05)
                ax.set_yticks(range(4),QUARTERS)
                ax.set_title(LABELS[v],loc='left',pad=10)
                ax.set_xlabel('Forecast minus realized value\n'+unit(v))
                style(ax);ax.spines['left'].set_visible(False);ax.tick_params(axis='y',length=0)
        fig.text(.32,.965,'One quarter ahead',ha='center',fontsize=14)
        fig.text(.78,.965,'Four quarters ahead',ha='center',fontsize=14)
        fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.045),ncol=2,frameon=False)
        fig.text(.10,.017,'Note: Original R density curves. Horizontal range and density-height conversion are identical\nwithin each variable across horizons and dates. No observations are trimmed.',fontsize=9,ha='left')
        fig.subplots_adjust(left=.11,right=.98,top=.91,bottom=.14,wspace=.28,hspace=.34)
        figs.append(fig)

    for v in VARIABLES:
        lim=LIMITS[v]
        fig,axs=plt.subplots(4,2,figsize=(10.8,10.8))
        for i,q in enumerate(QUARTERS):
            for j,h in enumerate([1,4]):
                ax=axs[i,j]
                for panel in ['Human','AI']:
                    z=distribution(curves,v,h,q,panel)
                    ax.fill_between(z.x,0,z.density,color=COLORS[panel],alpha=.26,linewidth=0)
                    ax.plot(z.x,z.density,color=COLORS[panel],lw=1.1)
                ax.set_xlim(lim['x_min'],lim['x_max']);ax.set_ylim(0,lim['density_max'])
                ax.set_title(q,loc='left',fontsize=11,pad=4)
                ax.set_ylabel('Density');style(ax)
                ax.yaxis.set_major_locator(MaxNLocator(3))
                if v=='RGDP':ax.ticklabel_format(axis='y',style='plain',useOffset=False)
                if i==3:ax.set_xlabel('Forecast minus realized value\n'+unit(v))
        fig.suptitle(LABELS[v],y=.988,fontsize=18)
        fig.text(.31,.951,'One quarter ahead',ha='center',fontsize=12)
        fig.text(.78,.951,'Four quarters ahead',ha='center',fontsize=12)
        fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.027),ncol=2,frameon=False)
        fig.text(.09,.009,'Note: All eight panels have identical x and y limits. Curves retain the original R smoothing.',fontsize=9)
        fig.subplots_adjust(left=.10,right=.98,top=.91,bottom=.11,wspace=.30,hspace=.38)
        figs.append(fig)

    with PdfPages(destination) as pdf:
        for fig in figs:pdf.savefig(fig)
    for fig in figs:plt.close(fig)


def run_distribution_plots():
    """Regenerate all 64 densities and the six-page review from main_data.zip."""
    samples = build_error_samples()
    curves = compute_density_curves(samples)
    destination = ROOT / 'report' / 'original_distributions.pdf'
    destination.parent.mkdir(exist_ok=True)
    render_distributions(curves, destination)
    print('Rebuilt 64 density curves from 3,031 finite individual forecast errors.')
    print('Output: report/original_distributions.pdf (6 pages; common scales).')
    return curves
