"""Integrate independent recalculations and create the original/reproduction audit PDF."""
from pathlib import Path
import argparse,json,csv,math,html,collections
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4,landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph,Table,TableStyle
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
INV=json.loads((ROOT/'originals/inventory.json').read_text())
core=json.loads((ROOT/'core_tables_results.json').read_text());ext=json.loads((ROOT/'extended_tables_results.json').read_text());t7=json.loads((ROOT/'table7_results.json').read_text())
figs=json.loads((ROOT/'figures_results.json').read_text())
figmap={'Figure1':'F1','Figure2':'F2','Figure3':'F3','Figure4':'F4','Figure5':'F5','Figure6':'F6','FigureA.1':'FA1','FigureA.2':'FA2'}
F={figmap[x['id']]:x for x in figs};R={**core,**ext}
R['T7']={'status':t7['status'],'counts':{'point_total':40,'point_match':40},'paths':[str(ROOT/t7['reproduced_png'])],'notes':[t7['method']]}
notes={
'F1':('Source reproduced','Original acknowledgment image reused from manuscript asset.','Documentary image; not a newly calculated research result.'),
'F2':('Partial reproduction','Eight trait distributions recomputed for 100 quarters.','Available metadata differ from the final figure; stream smoothing also differs.'),
'F3':('Numerical match','All 16 plotted forecast series agree at PDF coordinate rounding.','Independent medians recomputed; typography and layout differ.'),
'F4':('Match with caveat','Histogram bars and visible means recovered from raw nowcasts.','Filtering before demeaning yields 121 forecasters; caption states 194. Generating code was absent.'),
'F5':('Close reproduction','All 64 density curves agree closely with original vector shapes.','Direct Gaussian KDE replaces R FFT density evaluation; peak-height residuals are reported.'),
'F6':('Numerical match','All 8 plotted error series agree at PDF coordinate rounding.','The figure uses the OOS file for 2023-2024, including its overlapping 2023 observations.'),
'FA1':('Numerical match','Both 100-quarter count series match at PDF coordinate rounding.','AI counts require the older baseline workbook, not the current baseline used by most tables.'),
'FA2':('Partial reproduction','189 of 193 membership patterns match; both have 5,208 unique tiles.','Current metadata contain 5,236 records versus 5,232 in the original plotted asset.'),
'T1':('Source reproduced','All 23 variable definitions rebuilt from manuscript source.','Definitions are documentary content, not estimated quantities.'),
'T2':('Source reproduced','All 12 characteristic definitions rebuilt from source text.','Definitions are documentary content, not estimated quantities.'),
'T3':('Numerical match','All 207 printed numeric cells match.','N=5,308 repeats realizations across forecasters; ACF uses stored row order rather than a unique quarterly series.'),
'T4':('Partial reproduction','Most MAEs match; many reported p-values do not.','Code weights quarters by panel size and tests signed mean errors, although the caption describes MAE differences.'),
'T5':('Partial reproduction','Most accuracy shares and randomization p-values match.','Two displayed shares differ. Code counts ties as AI wins and reports fractions rather than 0-100 percentages.'),
'T6':('Partial reproduction','All 138 MAEs match; one p-value exceeds the Monte Carlo comparison tolerance.','Code compares the best AI persona with the human MEDIAN on its quarters; the caption refers to the best human.'),
'T7':('Match with caveat','All 40 displayed numeric cells match.','Human horizons are actually 0/3; AI horizons are 1/4. Both panels are labeled 1/4 in the paper.'),
'T8':('Partial reproduction','All 168 ratios, including averages, match; significance patterns differ.','Code randomizes AI/Human within each ablation using signed means, not baseline/ablation MAE differences.'),
'T9':('Match with caveat','All 14 event Z-scores match.','Uses h0 for Flash Crash and h1 for other events, including the pre-deadline S&P downgrade; SD is of signed errors.'),
'T10':('Match with caveat','All 24 displayed coefficients, SEs, counts and R-squared values match.','The 108 observations include duplicate 2023 quarters; there are 104 distinct quarters.'),
'T11':('Not reproduced','Only AI observation counts match among the 64 numeric cells.','Original calculation code is missing. Several plausible lag/consensus definitions fail to reproduce the published estimates.'),
'T12':('Numerical match','All 28 counts and percentages match.','Requires all 5,388 raw responses, including 80 placeholder-name rows excluded from the main cleaned panel.'),
'TB13':('Match with caveat','All 138 MAEs match; all 69 p-values are compatible with Monte Carlo variation.','Uses 2023-2024 and h0/1/4, unlike printed labels. Saved h4 errors are unclipped where current preparation code clips; raw preprocessing is not fully reproduced.'),
'TB14':('Partial reproduction','Historical source reconstruction matches only part of the table.','Older AI data and 2024 target cutoff improve agreement; best AI is compared with human median. Current-data caption method also saved.'),
'TD15':('Match with caveat','All 138 ratios, 69 p-values and 69 star patterns match.','Reconstructed AR(1) begins with two lagged pairs; DM test uses absolute loss and test horizon 1 for every forecast horizon.')}

def clean(x):
 if isinstance(x,float) and not math.isfinite(x):return None
 if isinstance(x,dict):return {k:clean(v) for k,v in x.items()}
 if isinstance(x,list):return [clean(v) for v in x]
 return x

rows=[]
for item in INV['items']:
 id=item['id'];status,evidence,limit=notes[id];d=F[id] if id in F else R[id];ct=d.get('counts',{})
 row={'id':id,'title':item['title'],'kind':item['kind'],'original_pages':', '.join(str(p['pdf_page']) for p in item['pages']),'status':status,'evidence':evidence,'limitations':limit}
 for k in ['point_match','point_total','p_rounded_match','p_mc_compatible','p_total','stars_match','stars_total']:
  row[k]=ct.get(k,d.get(k))
 row['stars_match']=ct.get('star_match',row['stars_match']);row['stars_total']=ct.get('star_total',row['stars_total'])
 if id=='T7':row['stars_match']=8;row['stars_total']=8
 paths=d.get('reproduced_pngs',d.get('paths',[]));row['reproduced_paths']=[str((ROOT/p).resolve()) if not Path(p).is_absolute() else p for p in paths]
 row['source_scripts']='; '.join(item.get('source_scripts',[]));row['method_notes']=d.get('notes',[d.get('method','')])+([d['limitations']] if d.get('limitations') else [])
 assert len(row['reproduced_paths'])==len(item['pages']),(id,row['reproduced_paths'])
 for p in row['reproduced_paths']:assert Path(p).is_file(),p
 rows.append(row)

cells=[]
for f in ['core_cell_comparison.json','extended_cell_audit.json','table7_cell_comparison.json']:
 cells.extend(json.loads((ROOT/f).read_text()))
for x in cells:
 x['kind']={'point':'point estimate','p':'p-value'}.get(x['kind'],x['kind'])
(ROOT/'replication_comparison.json').write_text(json.dumps(clean(rows),indent=2))
(ROOT/'cell_comparison.json').write_text(json.dumps(clean(cells),indent=2))
for filename,data in [('replication_comparison.csv',rows),('cell_comparison.csv',cells)]:
 fields=list(dict.fromkeys(k for d in data for k in d))
 with open(ROOT/filename,'w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows([{k:json.dumps(v) if isinstance(v,(list,dict)) else v for k,v in d.items()} for d in data])
summary={'items':len(rows),'figures':sum(r['kind']=='figure' for r in rows),'tables':sum(r['kind']=='table' for r in rows),'statuses':dict(collections.Counter(r['status'] for r in rows)),'point_total':sum(r['point_total'] or 0 for r in rows),'point_match':sum(r['point_match'] or 0 for r in rows),'p_total':sum(r['p_total'] or 0 for r in rows),'p_rounded_match':sum(r['p_rounded_match'] or 0 for r in rows),'cells_in_audit':len(cells)}
(ROOT/'audit_summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
parser=argparse.ArgumentParser();parser.add_argument('--prepare-only',action='store_true');args=parser.parse_args()
if args.prepare_only:raise SystemExit

OUT=ROOT/'output/pdf';OUT.mkdir(parents=True,exist_ok=True);pdf=OUT/'original_vs_replicated.pdf'
c=canvas.Canvas(str(pdf),pagesize=A4);c.setTitle('Predictable Forecasters | Original and replicated figures and tables');c.setAuthor('Replication audit from supplied data and code')
NAVY=colors.HexColor('#14394e');INK=colors.HexColor('#202d35');GRAY=colors.HexColor('#5a6873');LINE=colors.HexColor('#d9e1e7')
styles={name:ParagraphStyle(name,fontName='Helvetica',fontSize=size,leading=lead,textColor=INK,spaceAfter=6) for name,size,lead in [('body',10.5,15),('small',8.7,12),('table',8.4,11.2),('tiny',7.5,10),('title',24,29)]}
styles['title'].fontName='Helvetica-Bold';styles['title'].textColor=NAVY
index=[]

def para(text,x,y,width,style='body'):
 p=Paragraph(text,styles[style]);_,h=p.wrap(width,10000);p.drawOn(c,x,y-h);return y-h

def start(title,size=A4,subtitle=None):
 c.setPageSize(size);w,h=size;c.setFillColor(NAVY);c.rect(0,h-10,w,10,fill=1,stroke=0)
 key=f'page_{c.getPageNumber()}';c.bookmarkPage(key);c.addOutlineEntry(title+(' | '+subtitle if title=='Additional check' and subtitle else ''),key,level=0)
 y=para(html.escape(title),36,h-32,w-72,'title' if len(title)<55 else 'body')
 if subtitle:y=para(html.escape(subtitle),36,y-9,w-72,'small')
 c.setStrokeColor(LINE);c.line(36,28,w-36,28);c.setFillColor(GRAY);c.setFont('Helvetica',7.5);c.drawString(36,16,'Predictable Forecasters | Replication audit | 31 October 2026');c.drawRightString(w-36,16,str(c.getPageNumber()))
 return w,h,y-20

def finish():c.showPage()
def image_fit(path,x,y_top,maxw,maxh):
 im=Image.open(path);iw,ih=im.size;s=min(maxw/iw,maxh/ih);w=iw*s;h=ih*s;c.drawImage(str(path),x+(maxw-w)/2,y_top-h,width=w,height=h,preserveAspectRatio=True,mask='auto');return h

def evidence_text(r):
 s=r['evidence']
 if r['point_total'] is not None:s+=f" Numeric cells: {r['point_match']}/{r['point_total']}."
 if r['p_total']:
  s+=f" P-values: {r['p_rounded_match']}/{r['p_total']} match rounding."
  if r['p_mc_compatible'] is not None:s+=f" {r['p_mc_compatible']}/{r['p_total']} within MC tolerance."
 if r['stars_total']:s+=f" Stars: {r['stars_match']}/{r['stars_total']}."
 return s

w,h,y=start('Original versus replicated','' if False else A4,'All numbered figures and tables in the supplied final PDF')
y=para('<b>Replication is partial.</b> Every numbered figure and table is included in this report, but the available data and code do not establish a complete numerical reproduction of the final paper.',36,y,w-72)
y=para(f"The audit covers <b>{summary['figures']} figures and {summary['tables']} tables</b>. Figures with continuations are retained as separate parts: 26 original/reproduction pairs in total. Each original screenshot is immediately followed by its independently rebuilt result. Documentary definitions and the acknowledgment image are identified as source reproductions.",36,y-12,w-72)
y=para('<b>What the comparison establishes</b>',36,y-18,w-72)
for t in [
'Exact numerical agreement is possible for many results, including descriptive statistics, event scores, cutoff regression estimates, reasoning categories and the AR(1) table.',
'Several numerical matches require a different sample or horizon than the printed description: the disagreement table uses different horizons across panels, and Table B.13 uses 2023-2024 and horizon 4 in its last column.',
'The revision regressions remain unreproduced. The best-forecaster out-of-sample table and several reported significance tests also contain unresolved differences.',
'Figures 2 and A.2 expose metadata-version differences. Figure 4 recovers the plotted histogram with 121 retained forecasters, although its caption states 194.'
]:y=para('• '+html.escape(t),42,y-9,w-84)
y=para('<b>How to read this report</b>',36,y-19,w-72)
y=para('The next three pages provide the comparison table. The method page explains tolerances and provenance. Original screenshots retain the paper’s wording; the following reproduced pages carry audit notes. Matching a number does not establish that the paper’s stated method or interpretation is correct.',36,y-6,w-72)
y=para('Reference: predictable_forecasters.pdf, 68 pages. Original PDF SHA-256: '+INV['source_sha256'],36,y-18,w-72,'tiny')
finish()

for chunk in range(0,len(rows),8):
 w,h,y=start(f'Comparison table | {chunk//8+1} of 3',landscape(A4),'Numerical and documentary agreement are assessed separately; all discrepancies are retained.')
 data=[[Paragraph('<b>'+x+'</b>',styles['table']) for x in ['Item / original page','Result','Evidence','Method or data limitation']]]
 for r in rows[chunk:chunk+8]:
  label=f"<b>{html.escape(r['id'])}</b> · p. {r['original_pages']}<br/>{html.escape(r['title'])}"
  data.append([Paragraph(label,styles['table']),Paragraph(html.escape(r['status']),styles['table']),Paragraph(html.escape(evidence_text(r)),styles['table']),Paragraph(html.escape(r['limitations']),styles['table'])])
 table=Table(data,colWidths=[147,112,218,w-72-147-112-218]);table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e3edf3')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f4f7f9')]),('BOX',(0,0),(-1,-1),.4,LINE),('INNERGRID',(0,0),(-1,-1),.3,LINE),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]));tw,th=table.wrap(w-72,h);assert th<y-42,(chunk,th,y);table.drawOn(c,36,y-th);finish()

w,h,y=start('Methods and scope')
method=[
('Independent calculation','New results are calculated from supplied raw files and numerical R data objects. Raw Excel forecasts reconcile with cached AI values; baseline medians and clipped errors were independently verified. B.13 uses saved OOS errors: its h4 values differ from current preparation-code clipping, so that preprocessing is not fully reproduced. Existing tables/images are comparison references; documentary images and definitions are labeled source reproductions.'),
('Execution environment','R and a LaTeX compiler were unavailable. Supplied R calculations were ported to Python; missing calculation scripts were reconstructed from the paper and archived data. The original R files were not changed. Existing LLM responses were analyzed; no new model responses or external API calls were generated.'),
('Numeric comparisons','Printed values are checked at their displayed precision (normally half of 0.01). Counts and significance-star patterns are checked separately. The workbook records originals, recomputed values, absolute differences and tolerances for each audited table cell.'),
('Randomized tests','Core randomization tests use 10,000 draws and seed 20261031. The original seed is absent. Exact displayed p-value matches and approximate compatibility are separate counts. Compatibility tolerance is max(0.015, 0.005 + 3 × sqrt(2p(1−p)/10000)); this is a diagnostic allowance, not proof of the same simulation. The AR(1) p-values are deterministic DM tests and are compared at printed precision.'),
('Figure comparisons','Line-series checks compare independently generated data with PDF vector coordinates. Histogram bars and density curves are checked against the rendered/vector reference. Styling, smoothing and density numerical approximations are distinguished from changes in data or sample membership.'),
('Files and scope','The companion workbook is the searchable comparison and cell audit. The replication folder contains scripts, numerical outputs, figure inputs, data provenance and source maps. The 5 numbered prompt exhibits are documentary prompt examples, not additional figures/tables, and are not included in the 23-item statistical inventory.')]
for head,body in method:
 y=para('<b>'+head+'</b>',36,y,w-72);y=para(html.escape(body),36,y-3,w-72,'small')-14
assert y>36,y
finish()

for item,r in zip(INV['items'],rows):
 for k,(orig,rep) in enumerate(zip(item['pages'],r['reproduced_paths']),1):
  label=f"{item['kind'].title()} {item['number']}"+(f' | part {k} of {len(item["pages"])}' if len(item['pages'])>1 else '')
  original_report_page=c.getPageNumber()
  w,h,y=start('Original | '+label,A4,f"Screenshot from original PDF page {orig['pdf_page']} · {item['title']}")
  image_fit(ROOT/'originals'/Path(orig['png_path']).name,28,y,w-56,y-43);finish()
  reproduced_report_page=c.getPageNumber()
  w,h,y=start('Reproduced | '+label,A4,r['status'])
  note=html.escape(r['limitations']);np=Paragraph(note,styles['small']);_,nh=np.wrap(w-72,1000)
  nh=max(nh,25)+14
  image_fit(rep,24,y,w-48,y-45-nh)
  np.drawOn(c,36,42);finish()
  index.append({'id':r['id'],'part':k,'source_page':orig['pdf_page'],'original_report_page':original_report_page,'reproduced_report_page':reproduced_report_page})

# Supplementary recalculations clarify the major sample/horizon alternatives.
for title,path,note in [
 ('T7 | Consistent horizons for both panels',ROOT/'reproduced/tables/Table_7_consistent_horizons.png','Diagnostic using one- and four-quarter-ahead forecasts for both human and AI panels; this is a correction of the horizon discrepancy, not a reproduction of the published table.'),
 ('B.13 | 2024-only sample',ROOT/'reproduced/tables/TB13_2024_only.png','Diagnostic restricted to the caption’s 2024 sample. The supplied code’s actual horizons 0/1/4 are retained and correctly labeled.'),
 ('B.14 | Current data and caption method',ROOT/'reproduced/tables/TB14_current_caption_method.png','Diagnostic using the current data, 2024 survey quarters, and best individual forecasts in each quarter for both panels. Current realized-data availability extends into 2025.')]:
 if path.exists():
  w,h,y=start('Additional check',A4,title);image_fit(path,24,y,w-48,y-105);para(html.escape(note),36,85,w-72,'small');finish()
c.save()
(ROOT/'report_page_index.json').write_text(json.dumps(index,indent=2))
print(str(pdf))
