"""Clean tables-only review of published and independently recalculated values.
Red marks numeric/method/test differences; blue is reserved for verified rounding only.
Reuses audited calculations and investigation overrides; does not change source inputs.
"""
from pathlib import Path
import json,html,re,math,argparse
import matplotlib
from collections import Counter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A3,landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Flowable,Paragraph,Table,TableStyle
from reportlab.lib.styles import ParagraphStyle

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--data-only',action='store_true',help='Write verified table data without creating a PDF.')
args=parser.parse_args()

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/pdf';OUT.mkdir(exist_ok=True,parents=True)
SUP=ROOT/'tables_review';SUP.mkdir(exist_ok=True)
CORE=json.loads((ROOT/'core_tables_results.json').read_text())
EXT=json.loads((ROOT/'annotated_extended_table_data.json').read_text())
AUDIT=json.loads((ROOT/'cell_comparison.json').read_text())
INVENTORY={x['id']:x for x in json.loads((ROOT/'originals/inventory.json').read_text())['items']}
ORDER=['T1','T2','T3','T4','T5','T6','T7','T8','T9','T10','T11','T12','TB13','TB14','TD15']
LOOK={(x['item'],x['row'],x['column']):x for x in AUDIT}

FONTDIR=Path(matplotlib.get_data_path())/'fonts/ttf'
for name,file in [('Review','DejaVuSans.ttf'),('ReviewBold','DejaVuSans-Bold.ttf')]:pdfmetrics.registerFont(TTFont(name,str(FONTDIR/file)))
pdfmetrics.registerFontFamily('Review',normal='Review',bold='ReviewBold',italic='Review',boldItalic='ReviewBold')
RED=colors.HexColor('#c01823');BLUE=colors.HexColor('#1565c0');NAVY=colors.HexColor('#16384b');GRAY=colors.HexColor('#52616b');LIGHT=colors.HexColor('#e9f0f4');RULE=colors.HexColor('#b8c7d1')
W,H=landscape(A3);M=34;WIDTH=W-2*M
RENDERED=[]

NOTES={
'T1':'Definitions reproduced from the supplied manuscript source. These are documentary definitions, not statistical estimates.',
'T2':'Definitions reproduced from the supplied source text. Inferred personal characteristics are the manuscript’s classifications.',
'T3':'The supplied calculation repeats realizations across forecaster rows (N=5,308); ACF(1) follows stored row order. Series labeled x1000 are divided by 1,000. All displayed values match.',
'T4':'Recalculation follows supplied code: MAEs are weighted by panel size through a duplicate join; significance tests use signed mean errors, although the published description refers to MAE differences.',
'T5':'Values are shares, so 0.50 means 50%. The supplied calculation counts ties as AI wins. Two shares differ at printed precision.',
'T6':'All MAEs match. Supplied code selects the best AI persona across time and compares it with the human median on that persona’s quarters; it does not select the best human forecaster.',
'T7':'All numeric cells match, but the Human panel actually uses horizons 0 and 3, while the AI panel uses 1 and 4. Published column labels are retained. Quarters with zero dispersion at either horizon are excluded.',
'T8':'All ratios match. Red entries reflect different significance markers. The supplied test swaps AI/Human within each ablation and compares signed means, rather than testing baseline/ablation MAE differences.',
'T9':'All Z-scores match. Event dates and days from the survey deadline are manuscript metadata, not independently validated. The matching calculation uses h0 for Flash Crash and h1 for other events, including the pre-deadline S&P downgrade.',
'T10':'All estimates match. The calculation has 108 observations because it concatenates baseline and OOS files with overlapping 2023 quarters; there are 104 distinct quarters. Standard errors are conventional OLS errors.',
'T11':'UNRESOLVED ESTIMATOR: the red values are a qualified reconstruction, not proven corrections. The generating script is absent. Alternative lag/consensus definitions did not recover the published coefficients. Robust standard errors are in parentheses.',
'T12':'All counts and percentages match using all 5,388 raw responses, including 80 placeholder-name rows. Categories are nonexclusive. The caption’s separate claim that all crisis-versus-normal differences have p<0.001 was not independently validated.',
'TB13':'The red header [4] corrects the last block’s actual horizon. Matching saved data use 2023Q1–2024Q4, not the caption’s 2024-only sample. Saved h4 errors are unclipped where current preparation code would clip; raw preprocessing is not fully reproduced.',
'TB14':'UNRESOLVED DATA / METHOD: red values use the older AI workbook, best AI per quarter versus the human median, and realized targets through 2024Q4. This historical reconstruction differs from the best-human rule in the caption. Red entries are not proven corrections.',
'TD15':'All ratios, p-values and stars match. Reconstructed expanding AR(1) starts with two lagged pairs; DM tests use absolute loss and test horizon 1 for all three forecast horizons.'}
DESCRIPTIONS={
'T1':'Variables covered by the SPF point forecasts and their definitions.',
'T2':'Forecaster characteristics and their definitions in the supplied manuscript.',
'T3':'Number of observations, mean, standard deviation, skewness, kurtosis, median, minimum, maximum and first-order autocorrelation.',
'T4':'Mean absolute errors of median AI and human SPF forecasts. Horizons 0, 1 and 4 denote the nowcast, one quarter ahead and four quarters ahead.',
'T5':'Share of survey quarters in which the AI median forecast is at least as accurate as the human median. Values are fractions, not 0–100 percentages.',
'T6':'Published accuracy table for the best forecasters. MAE values are retained; recalculated p-values and stars appear beside them where different.',
'T7':'Mean cross-sectional standard deviations, their ratio, paired t-statistic and number of quarters. Sample: 1999–2023.',
'T8':'Mean absolute errors relative to the baseline AI forecast. Ratios above one indicate lower accuracy. Significance markers are compared separately from ratios.',
'T9':'AI forecast performance around unexpected events. Both reported event Z-scores are recalculated; event dates and deadline offsets are retained.',
'T10':'OLS regressions of absolute one-quarter-ahead AI forecast errors on an indicator for survey dates after October 2023. Standard errors in parentheses.',
'T11':'OLS forecast-revision regressions: error correction and consensus tracking, separately for human and AI panels. Published and reconstructed estimates are shown together.',
'T12':'Percentage of reasoning responses containing each category, by economic period. The same response can belong to multiple categories.',
'TB13':'Published out-of-sample MAE table. The original third horizon label is shown with its recalculated data horizon in red beside it.',
'TB14':'Published out-of-sample accuracy of the best human and AI forecasters. Red entries show the available historical reconstruction and remain qualified.',
'TD15':'MAEs of AI and AR(1) forecasts relative to human accuracy, with Diebold–Mariano test p-values.'}


def textcell(s):return {'kind':'text','original':s,'replicated':s,'original_display':s,'replicated_display':s,'mismatch':False}
def display(v,precision=2,stars=0):
 if not math.isfinite(v):return 'NA'
 if round(v,precision)==0:v=0
 return f'{v:.{precision}f}'+('*'*int(stars))

def core_table(id):
 d=CORE[id];inv=INVENTORY[id]
 clean_title=inv['title'].replace('fore- casters','forecasters')
 t={'id':id,'title':f"Table {inv['number']}: {clean_title}",'columns':[],'column_groups':[],'rows':[]}
 if id in ['T1','T2']:
  t['columns']=['Variable' if id=='T1' else 'Characteristic','Definition' if id=='T1' else 'Description']
  for i,row in enumerate(d['rows']):
   if id=='T1' and i in [0,11,19]:t['rows'].append({'type':'section','label':{0:'Section 1: U.S. Business Indicators',11:'Section 2: Real GDP and Its Components',19:'Section 3: CPI and PCE Inflation'}[i]})
   t['rows'].append({'type':'data','label':row[0],'cells':[textcell(x) for x in row]})
  return t
 cols=d['columns'];t['columns']=['Variable']+cols
 if id in ['T4','T6','TB13','TB14']:
  t['columns']=['Variable']+['AI','Human','P-val']*3
  hs=[0,1,2] if id in ['TB13','TB14'] else [0,1,4]
  t['column_groups']=[{'label':f'Horizon {h}','start_column':1+3*i,'end_column':3+3*i} for i,h in enumerate(hs)]
  if id=='TB13':t['column_groups'][-1]['correction']={'original_display':'2','replicated_display':'4','prefix':'Horizon ','kind':'header','mismatch':True,'starsoriginal':0,'starsreplicated':0}
 if id=='T5':
  t['columns']=['Variable']+['Share','P-val']*3;t['column_groups']=[{'label':f'Horizon {h}','start_column':1+2*i,'end_column':2+2*i} for i,h in enumerate([0,1,4])]
 if id=='T8':
  t['columns']=['Variable','h0','h4','h0','h4','h0','h4','h0'];t['column_groups']=[{'label':label,'start_column':a,'end_column':b} for label,a,b in [('Generic',1,2),('No real-time data',3,4),('No real-time or past SPF data',5,6),('Recall',7,7)]]
 if id=='T3':t['columns']=['Variable','N','Mean','SD','Skewness','Kurtosis','Median','Min','Max','ACF(1)']
 for i,label in enumerate(d['rows']):
  if i==0 or label.startswith('Real GDP') or label=='CPI Inflation Rate':
   section='Section 1: U.S. Business Indicators' if i==0 else ('Section 2: Real GDP and Its Components' if label.startswith('Real GDP') else 'Section 3: CPI and PCE Inflation')
   t['rows'].append({'type':'section','label':section})
  cells=[textcell(label)]
  for j,col in enumerate(cols):
   a=LOOK[(id,label,col)];star=LOOK.get((id,label,col+' stars'));so=int(star['original']) if star else 0;sr=int(star['replicated']) if star else 0;prec=0 if id=='T3' and col=='N' else 2
   orig=display(a['original'],prec,so);rep=display(a['replicated'],prec,sr)
   c={'kind':'numeric','original':a['original'],'replicated':a['replicated'],'precision':prec,'starsoriginal':so,'starsreplicated':sr,'original_display':orig,'replicated_display':rep,'mismatch':orig!=rep,'numeric_mismatch':not a['rounded_match'],'stars_mismatch':so!=sr,'audit_row':label,'audit_column':col}
   if id in ['T4','T6','TB13','TB14'] and j%3 in [0,1]:
    start=j-j%3;other=cols[start+1-j%3];c['bold_original']=a['original']<=LOOK[(id,label,other)]['original']
   if id=='T5' and j%2==0:c['bold_original']=a['original']>.5
   if id=='T8':c['bold_original']=a['original']>1
   cells.append(c)
  t['rows'].append({'type':'data','label':label,'cells':cells})
 return t

TABLES={k:(core_table(k) if k in CORE else EXT[k]) for k in ORDER}
for table_id,folder in [('T11','table11_investigation'),('TB14','tableB14_investigation')]:
 override_path=ROOT/folder/'verified_table.json'
 if not override_path.exists():raise FileNotFoundError(f'Investigation result required before authoring: {override_path}')
 override=json.loads(override_path.read_text())
 assert override['id']==table_id
 TABLES[table_id]=override

rounding=json.loads((SUP/'rounding_audit.json').read_text())
rounding_cells={(x['item'],x['row'],x['column']):x for x in rounding.get('classifications',[]) if x.get('classification')=='rounding_only'}
for k,t in TABLES.items():
 t['description']=DESCRIPTIONS[k];t['audit_note']=NOTES[k]
 for r in t['rows']:
  if r['type']!='data':continue
  for ci,cell in enumerate(r['cells']):
   if cell['kind']!='numeric':continue
   key=(k,cell.get('audit_row',r.get('label','')),cell.get('audit_column',t['columns'][ci]))
   evidence=rounding_cells.get(key)
   # Require the classification to refer to these exact numbers; investigations
   # may replace the earlier reconstruction, invalidating an earlier assessment.
   is_rounding=bool(evidence and evidence.get('original_display')==cell['original_display'] and evidence.get('replicated_display')==cell['replicated_display'] and not cell.get('stars_mismatch',False))
   cell['annotation_color']='blue' if cell['mismatch'] and is_rounding else ('red' if cell['mismatch'] else None)
 t['mismatch_count']=sum(c['mismatch'] for r in t['rows'] if r['type']=='data' for c in r['cells'] if c['kind']=='numeric')
expected={k:t['mismatch_count'] for k,t in TABLES.items()}
(SUP/'table_data_verified.json').write_text(json.dumps(TABLES,indent=2,ensure_ascii=False))
if args.data_only:
 print('Verified table data written; PDF generation skipped.')
 raise SystemExit(0)

class NumberPair(Flowable):
 def __init__(self,cell,id,row,col,size=11):
  super().__init__();self.cell=cell;self.id=id;self.row=row;self.col=col;self.base_size=size;self.size=size
 def parts(self):
  c=self.cell;o=c['original_display'];r=c['replicated_display'];prefix=c.get('prefix','');bold=c.get('bold_original',c.get('bold',False));font='ReviewBold' if bold else 'Review'
  result=[(prefix,'ReviewBold',1,0,colors.black)] if prefix else []
  def val(s,font,color):
   m=re.match(r'^(.*?)(\*+)?$',s);result.append((m.group(1),font,1,0,color))
   if m.group(2):result.append((m.group(2),font,.69,.40,color))
  val(o,font,colors.black)
  if c['mismatch']:
   color=BLUE if c.get('annotation_color')=='blue' else RED
   result.append(('  [','Review',1,0,color));val(r,'Review',color);result.append((']','Review',1,0,color))
  return result
 def wrap(self,availWidth,availHeight):
  self.width=availWidth;unscaled=sum(pdfmetrics.stringWidth(s,f,self.base_size*scale) for s,f,scale,raise_,co in self.parts())
  self.size=min(self.base_size,self.base_size*availWidth/max(unscaled,1));assert self.size>=8.8,(self.id,self.row,self.col,self.size)
  self.height=max(15,self.size*1.35);return availWidth,self.height
 def draw(self):
  parts=self.parts();total=sum(pdfmetrics.stringWidth(s,f,self.size*sc) for s,f,sc,ra,co in parts);x=(self.width-total)/2;y=2.2
  for s,f,sc,ra,color in parts:
   self.canv.setFont(f,self.size*sc);self.canv.setFillColor(color);self.canv.drawString(x,y+self.size*ra,s);x+=pdfmetrics.stringWidth(s,f,self.size*sc)
  gx,gy=self.canv.absolutePosition(0,0)
  color=self.cell.get('annotation_color') or ('red' if self.cell['mismatch'] else None)
  RENDERED.append({'item':self.id,'row':self.row,'column':self.col,'kind':self.cell['kind'],'page':self.canv.getPageNumber(),'original':self.cell['original_display'],'replicated':self.cell['replicated_display'],'red':color=='red','blue':color=='blue','annotation_color':color,'mismatch':bool(self.cell['mismatch']),'font_size':self.size,'bbox_pdf':[gx,gy,self.width,self.height]})

STYLES={name:ParagraphStyle(name,fontName='Review',fontSize=size,leading=leading,textColor=colors.black,spaceAfter=0) for name,size,leading in [('body',10.8,14.5),('small',9.8,13.2),('cell',10.8,14),('header',10.5,14),('section',10.5,14)]}
STYLES['header'].fontName='ReviewBold';STYLES['section'].fontName='ReviewBold';STYLES['section'].textColor=NAVY

def para(s,style='cell',bold=False):
 if bold:s='<b>'+html.escape(s)+'</b>'
 else:s=html.escape(s)
 return Paragraph(s,STYLES[style])

def pdraw(c,text,x,y,width,style='small'):
 p=Paragraph(text,STYLES[style]);_,hh=p.wrap(width,5000);p.drawOn(c,x,y-hh);return y-hh

pdf=OUT/'tables_verified_results.pdf';c=canvas.Canvas(str(pdf),pagesize=(W,H));c.setTitle('Tables: verified recalculations');c.setAuthor('Replication review from supplied data and code')
page_qa=[]
for page,id in enumerate(ORDER,1):
 t=TABLES[id];ncol=len(t['columns'])
 c.bookmarkPage(id);c.addOutlineEntry(t['title'],id,0)
 title=Paragraph(html.escape(t['title']),ParagraphStyle('Title',fontName='ReviewBold',fontSize=19,leading=24,textColor=NAVY));_,th=title.wrap(WIDTH,1000);title.drawOn(c,M,H-31-th);y=H-31-th-9
 y-=10
 data=[];commands=[];hdr=0
 if t['column_groups']:
  group=['']*ncol
  for g in t['column_groups']:
   a,b=g['start_column'],g['end_column'];group[a]=NumberPair(g['correction'],id,'header',g['label'],size=11) if g.get('correction') else para(g['label'],'header')
   if a!=b:commands.append(('SPAN',(a,0),(b,0)))
  data.append(group);hdr+=1
 data.append([para(x,'header') for x in t['columns']]);hdr+=1
 for r in t['rows']:
  ri=len(data)
  if r['type']=='section':
   data.append([para(r['label'],'section')]+['']*(ncol-1));commands += [('SPAN',(0,ri),(-1,ri)),('BACKGROUND',(0,ri),(-1,ri),LIGHT),('LINEABOVE',(0,ri),(-1,ri),.65,RULE)]
  else:
   rr=[]
   for j,cell in enumerate(r['cells']):
    if cell['kind']=='numeric':rr.append(NumberPair(cell,id,cell.get('audit_row',r.get('label','')),cell.get('audit_column',t['columns'][j])))
    else:rr.append(para(cell['original_display']))
   data.append(rr)
   if ri%2==0:commands.append(('BACKGROUND',(0,ri),(-1,ri),colors.HexColor('#f7f9fa')))
 if id in ['T1','T2']:widths=[195,WIDTH-195]
 elif id=='T9':widths=[240,225,265,(WIDTH-730)/2,(WIDTH-730)/2]
 elif id=='T11':widths=[208]+[(WIDTH-208)/8]*8
 elif id=='T12':widths=[195,90]+[(WIDTH-285)/6]*6
 elif ncol<=6:widths=[230]+[(WIDTH-230)/(ncol-1)]*(ncol-1)
 else:widths=[190]+[(WIDTH-190)/(ncol-1)]*(ncol-1)
 table=Table(data,colWidths=widths,repeatRows=hdr,hAlign='LEFT')
 commands += [('VALIGN',(0,0),(-1,-1),'MIDDLE'),('ALIGN',(1,0),(-1,-1),'CENTER'),('BACKGROUND',(0,0),(-1,hdr-1),colors.HexColor('#dbe7ef')),('LINEBELOW',(0,hdr-1),(-1,hdr-1),.8,NAVY),('BOX',(0,0),(-1,-1),.45,RULE),('INNERGRID',(0,0),(-1,-1),.25,colors.HexColor('#dce3e8')),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]
 table.setStyle(TableStyle(commands));tw,hh=table.wrap(WIDTH,H)
 min_bottom=M
 if y-hh<min_bottom:
  # Tighten vertical padding, never shrink the printed numbers or break red pairs.
  table=Table(data,colWidths=widths,repeatRows=hdr,hAlign='LEFT')
  table.setStyle(TableStyle(commands+[('TOPPADDING',(0,0),(-1,-1),2.8),('BOTTOMPADDING',(0,0),(-1,-1),2.8)]));tw,hh=table.wrap(WIDTH,H)
 assert y-hh>=min_bottom,(id,hh,y,min_bottom)
 table.drawOn(c,M,y-hh)
 page_qa.append({'id':id,'page':page,'table_bottom_pt':y-hh,'annotated_body_entries':t['mismatch_count'],'original_pdf_page':INVENTORY[id]['pages'][0]['pdf_page']})
 c.showPage()
c.save()
counts=Counter(x['item'] for x in RENDERED if x['mismatch'] and x['kind']=='numeric')
assert all(counts[k]==v for k,v in expected.items())
qa={'pdf':str(pdf),'pages':15,'red_body_entries':sum(x['red'] and x['kind']=='numeric' for x in RENDERED),'blue_body_entries':sum(x['blue'] and x['kind']=='numeric' for x in RENDERED),'header_corrections':sum(x['mismatch'] and x['kind']=='header' for x in RENDERED),'numeric_cells_rendered':sum(x['kind']=='numeric' for x in RENDERED),'expected_counts':expected,'minimum_numeric_font_size':min(x['font_size'] for x in RENDERED),'page_checks':page_qa,'rendered_cells':RENDERED}
(SUP/'render_validation_verified.json').write_text(json.dumps(qa,indent=2,ensure_ascii=False))
print(json.dumps({k:v for k,v in qa.items() if k not in ['rendered_cells','page_checks']},indent=2))
