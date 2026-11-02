"""Canonical display cells for extended annotated tables; no estimation runs.

Every numeric entry comes from the saved comparison audits. Original captions,
textual event metadata, precision and stars follow the authoritative paper.
"""
from pathlib import Path
import csv,json,re

ROOT=Path(__file__).resolve().parents[1]
inv={x['id']:x for x in json.loads((ROOT/'originals/inventory.json').read_text())['items']}
audits=json.loads((ROOT/'extended_cell_audit.json').read_text())+json.loads((ROOT/'table7_cell_comparison.json').read_text())
A={(x['item'],x['row'],x['column']):x for x in audits}
T={}

def fmt(value,precision,commas=False):
    if precision==0:return f'{int(round(value)):,}' if commas else str(int(round(value)))
    if abs(value)<.5*10**(-precision):value=0
    return f'{value:.{precision}f}'

def text(s):
    return {'kind':'text','original':s,'replicated':s,'original_display':s,'replicated_display':s,'mismatch':False}

def numeric(item,row,col,precision,star_col=None,parentheses=False,percent=False,commas=False):
    a=A[item,row,col];so=sr=0
    if star_col:
        s=A[item,row,star_col];so=int(s['original']);sr=int(s['replicated'])
    od=fmt(a['original'],precision,commas);rd=fmt(a['replicated'],precision,commas)
    if percent:od+='%';rd+='%'
    od+='*'*so;rd+='*'*sr
    if parentheses:od='('+od+')';rd='('+rd+')'
    return {'kind':'numeric','original':a['original'],'replicated':a['replicated'],
            'precision':precision,'starsoriginal':so,'starsreplicated':sr,
            'parentheses':parentheses,'percent':percent,'thousands_separator':commas,
            'original_display':od,'replicated_display':rd,'mismatch':od!=rd,
            'numeric_mismatch':fmt(a['original'],precision)!=fmt(a['replicated'],precision),
            'stars_mismatch':so!=sr,'audit_row':row,'audit_column':col}

def table(key,columns,rows,groups=None,notes=None):
    T[key]={'id':key,'title':inv[key]['caption'],'original_notes':inv[key]['notes'],
            'columns':columns,'rows':rows,'column_groups':groups or [],
            'replication_notes':notes or []}
    for row in rows:
        if row['type']=='data':assert len(row['cells'])==len(columns),(key,len(row['cells']),len(columns))

def row(label,cells):return {'type':'data','label':label,'cells':[text(label)]+cells}
def panel(label):return {'type':'section','label':label,'span_all_columns':True}
def blank():return {'kind':'blank','original_display':'','replicated_display':'','mismatch':False}

# Table 7: row-specific original SD precision is material (RGDP differs by panel).
t7=json.loads((ROOT/'table7_results.json').read_text());rows=[]
for p in ['Human','AI']:
    rows.append(panel('Panel A: Human' if p=='Human' else 'Panel B: AI'))
    for e in [x for x in t7['rows'] if x['panel']==p]:
        v=e['variable'];key=p+' / '+v;sd_precision=(2 if p=='Human' else 1) if v=='RGDP' else 3
        cells=[numeric('T7',key,c,d) for c,d in [('Short SD',sd_precision),('Long SD',sd_precision),('Ratio',2),('t-stat',2),('N',0)]]
        # T7's saved cell audit omitted separate star entries; both source and
        # computed stars are explicitly retained here (only AI CPI is unstarred).
        so=0 if p=='AI' and v=='CPI' else 3;sr=3 if e['p_value']<.01 else 0
        cells[3].update(starsoriginal=so,starsreplicated=sr,stars_mismatch=so!=sr)
        cells[3]['original_display']+='*'*so;cells[3]['replicated_display']+='*'*sr
        cells[3]['mismatch']=cells[3]['original_display']!=cells[3]['replicated_display']
        rows.append(row(v,cells))
table('T7',['Variable','σh+1','σh+4','Ratio','t-stat','N'],rows,notes=[t7['method']])

# Table 9: event metadata is documentary, and has no calculated mismatch status.
t9=json.loads((ROOT/'reproduced/tables/T9_numeric.json').read_text());rows=[]
for e in t9:
    cells=[text(e['event_date']+f" ({e['days_after_survey_deadline']} days)"),text(', '.join(e['relevant_variables']))]
    cells += [numeric('T9',e['event'],c,2) for c in ['Relevant variables Z','All variables Z']]
    r=row(e['event'],cells);r['metadata']={'survey_quarter':e['survey_quarter'],'horizon':e['horizon'],'deadline_offset_source':e['deadline_offset_source']};rows.append(r)
table('T9',['Event','Event date (days after survey deadline)','Relevant variables','Relevant variables Z-score','All variables Z-score'],rows,
      groups=[{'label':'Average Z-score','start_column':3,'end_column':4}],
      notes=['Event dates and offsets reproduce manuscript metadata. Exact deadline offsets were not independently validated. Forecast-error estimates are unchanged.'])

# Table 10: preserve original coefficient rows with parenthesized SE rows below.
rows=[];variables=['RGDP','UNEMP','CPI','TBILL']
for label,col,star,se in [('Intercept','Intercept','Intercept stars',False),('','Intercept SE',None,True),('I(t > Oct 2023)','Post cutoff','Post cutoff stars',False),('','Post SE',None,True),('Observations','N',None,False),('R²','R2',None,False)]:
    cells=[]
    for v in variables:
        d=0 if col=='N' else 3 if col=='R2' or v!='RGDP' else 2
        cells.append(numeric('T10',v,col,d,star,parentheses=se))
    rows.append(row(label,cells))
table('T10',['']+variables,rows)

# Table 11: retain both original panels, both four-variable model blocks,
# coefficient/SE rows and all repeated counts and R-squared entries.
rows=[];variables11=['RGDP','CPI','UNEMP','TBILL']
for p in ['Human','AI']:
    rows.append(panel('Panel A: Human' if p=='Human' else 'Panel B: AI'))
    for label,col,star,se,side in [('Lagged Error(i,t−1)','Error coefficient','lag_error stars',False,0),('','Error SE',None,True,0),('Distance from Consensus(i,t−1)','Consensus coefficient','lag_deviation stars',False,1),('','Consensus SE',None,True,1)]:
        cells=[numeric('T11',p+' '+v,col,3,star,parentheses=se) for v in variables11]
        cells=cells+[blank() for _ in range(4)] if side==0 else [blank() for _ in range(4)]+cells
        rows.append(row(label,cells))
    for label,suffix,d in [('Observations','N',0),('R²','R2',3)]:
        cells=[numeric('T11',p+' '+v,prefix+' '+suffix,d,commas=suffix=='N') for prefix in ['Error','Consensus'] for v in variables11]
        rows.append(row(label,cells))
table('T11',['']+variables11+variables11,rows,
      groups=[{'label':'Error Correction','start_column':1,'end_column':4},{'label':'Consensus Tracking','start_column':5,'end_column':8}],
      notes=['Recomputed values are the existing qualified reconstruction, which did not recover the published estimator. Stars use the original table’s *** p<0.01 rule.'])

# Table 12: original values are percentages, not fractions; N uses commas.
rows=[];columns12=['N','Mechanical','Policy','Model','Event','Model-based','Judgment-based']
for p in ['Normal','Financial Crisis','COVID-19','Inflation Shock']:
    rows.append(row(p,[numeric('T12',p,c,0 if c=='N' else 1,percent=c!='N',commas=c=='N') for c in columns12]))
table('T12',['Period','N','Mechanical','Policy','Model','Event','Model-Based','Judgment-Based'],rows,
      groups=[{'label':'Detailed Categories','start_column':2,'end_column':5},{'label':'ECB Aggregation','start_column':6,'end_column':7}],
      notes=['The original caption’s claim that all crisis-versus-normal differences have p<0.001 is documentary text; those separate tests were not part of the saved replication audit.'])

# Table D.15: read original boldface cells from its supplied TeX table, and
# attach the already audited stars rather than deriving stars from rounded p.
meta=list(csv.DictReader((ROOT/'data_cache/baseline_variables.csv').open()))
bold={};sections={};section=None
for line in (ROOT.parent/'latest draft/tables/forecast_accuracy_ar1_relative_comparison.txt').read_text().splitlines():
    if 'Section ' in line:section=re.search(r'(Section [^}]+)',line)[1]
    if ' & ' not in line:continue
    parts=line.split(' & ');vals=[c for c in parts[1:] if re.search(r'[-−]?\d+\.\d+',c)]
    if len(vals)==9:
        label=parts[0].replace(r'\&','&');bold[label]=['{B{' in c for c in vals];sections[label]=section
rows=[];previous=None
for e in meta:
    v=e['variable'];name=e['variable_longname'];sec=sections[name]
    if sec!=previous:rows.append(panel(sec));previous=sec
    cells=[]
    for h in [0,1,4]:
        for suffix in ['AI/Human MAE','AR1/Human MAE','p-value']:
            cells.append(numeric('TD15',v,f'h{h}: {suffix}',2,f'h{h}: significance stars' if suffix=='p-value' else None))
    for c,isbold in zip(cells,bold[name]):c['bold_original']=isbold
    rows.append(row(name,cells))
table('TD15',['Variable']+[s for _ in [0,1,4] for s in ['AI','AR(1)','P-val']],rows,
      groups=[{'label':f'Horizon {h}','start_column':1+3*j,'end_column':3+3*j} for j,h in enumerate([0,1,4])])

for key,t in T.items():
    cells=[c for r in t['rows'] if r['type']=='data' for c in r['cells'] if c['kind']=='numeric']
    t['qa']={'numeric_cells':len(cells),'display_mismatch_cells':sum(c['mismatch'] for c in cells),'numeric_mismatch_cells':sum(c['numeric_mismatch'] for c in cells),'star_mismatch_cells':sum(c['stars_mismatch'] for c in cells)}
out=ROOT/'annotated_extended_table_data.json';out.write_text(json.dumps(T,indent=2,ensure_ascii=False))
print(json.dumps({k:t['qa'] for k,t in T.items()},indent=2))
print(out)
