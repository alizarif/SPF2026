from pathlib import Path
import fitz, re, json, hashlib, os
from PIL import Image, ImageChops
R=Path(__file__).resolve().parents[2]
OUT=R/'replication_2026-10-31/originals'; OUT.mkdir(parents=True,exist_ok=True)
SRC=Path(os.environ.get('SPF_SOURCE_PDF', R/'paper/predictable_forecasters.pdf')).expanduser(); D=fitz.open(SRC)
TEX=R/'latest draft/May 2026 version.tex'; tex=TEX.read_text(); lines=tex.splitlines()
F=R/'latest draft/figures'; T=R/'latest draft/tables'; S=R/'Simulating_SPF_processing/functions'
# Identifier, kind, printed number, PDF pages, TeX environment starting lines, source script, manual reconstruction status.
spec=[
('F1','Figure','1',[36],[380],[], 'Documentary screenshot, not a calculated result'),
('F2','Figure','2',[37,38],[394,436],['fig_characteristics_over_time.R'],'Existing generation function'),
('F3','Figure','3',[39,40],[470,487],['fig_ts_median.R','fig_human_ai_lgd.R'],'Existing generation function'),
('F4','Figure','4',[41],[502],[],'Embedded PNG; no matching supplied computation script located'),
('F5','Figure','5',[42,43],[517,534],['fig_densities.R'],'Existing generation function'),
('F6','Figure','6',[44],[618],['fig_forecast_errors_outofsample.R','fig_human_ai_lgd.R'],'Existing generation function'),
('T1','Table','1',[45],[675],[],'Definitions written inline in TeX, not an estimated result'),
('T2','Table','2',[46],[725],[],'Definitions stored in source text table, not an estimated result'),
('T3','Table','3',[47],[741],['tab_descriptive_stats.R'],'Existing generation function'),
('T4','Table','4',[48],[785],['tab_forecast_accuracy.R','randomization_test.R'],'Existing generation function'),
('T5','Table','5',[49],[802],['tab_num_quarters_AI_more_accurate.R'],'Existing generation function'),
('T6','Table','6',[50],[819],['tab_forecast_accuracy_best_forecasters.R'],'Existing generation function'),
('T7','Table','7',[51],[851],[],'Numbers written inline; reconstruct from stated paired-horizon standard-deviation method'),
('T8','Table','8',[52],[917],['tab_forecast_accuracy_generic.R','tab_forecast_accuracy_recall.R'],'Existing generation function'),
('T9','Table','9',[53],[936],[],'Numbers written inline; reconstruct event standardized forecast errors'),
('T10','Table','10',[54],[962],[],'Numbers written inline; reconstruct OLS cutoff regression'),
('T11','Table','11',[54],[988],[],'Numbers written inline; reconstruct OLS revision regressions'),
('T12','Table','12',[55],[1059],[],'Numbers written inline; reconstruct keyword classification from Appendix C'),
('FA1','Figure','A.1',[61],[1321],['fig_num_forecasters_over_time.R','fig_human_ai_lgd.R'],'Existing generation function'),
('FA2','Figure','A.2',[62],[1334],['fig_participation_over_time.R'],'Existing generation function'),
('TB13','Table','B.13',[64],[1350],['tab_forecast_accuracy_outofsample.R'],'Existing generation function'),
('TB14','Table','B.14',[65],[1368],['tab_forecast_accuracy_best_outofsample.R'],'Existing generation function'),
('TD15','Table','D.15',[68],[1753],[],'Existing source table; no matching supplied AR(1) generation script located'),
]
labels={
'F1':'fig:forecaster_thanks','F2':'fig:SPF_characteristics_over_time','F3':'fig:ts_median_AI_SPF','F4':'fig:fixed_effects','F5':'fig:density_AI_SPF','F6':'fig:oos_forecast_errors',
'T1':'tab:spf_variables_definitions','T2':'tab:forecaster_characteristics_definitions','T3':'tab:descriptive_stats','T4':'tab:forecastaccuracy_AI_SPF','T5':'tab:forecastaccuracy_AI_SPF_numquarters','T6':'tab:forecastaccacy_AI_SPF_best','T7':'tab:horizon_dispersion','T8':'tab:MAEs_forecastaccuracy_generic','T9':'tab:unexpected_events','T10':'tab:cutoff_regressions','T11':'tab:revision_regressions','T12':'tab:reasoning_categories','TB13':'tab:MAEs_forecastaccuracy_oos','TB14':'tab:MAEs_forecastaccuracy_oos_best','TD15':'tab:MAEs_AR1'}
tab_files={'T2':'characteristics_definitions.txt','T3':'descriptive_stats.txt','T4':'forecast_accuracy_ai_spf.txt','T5':'forecast_accuracy_num_quarters_ai_spf.txt','T6':'forecast_accuracy_best_forecasters.txt','T8':'forecast_accuracy_generic.txt','TB13':'forecast_accuracy_oos.txt','TB14':'forecast_accuracy_best_forecasters_oos.txt','TD15':'forecast_accuracy_ar1_relative_comparison.txt'}
# Extract true environments rather than relying on rough manually noted line starts.
envs=[]
for m in re.finditer(r'\\begin\{(figure|table)\}([\s\S]*?)\\end\{\1\}',tex):
 envs.append({'start_line':tex[:m.start()].count('\n')+1,'end_line':tex[:m.end()].count('\n')+1,'text':m.group(0)})

def env_at(n):
 candidates=[e for e in envs if e['start_line']<=n<=e['end_line']]
 return candidates[0] if candidates else min(envs,key=lambda e:abs(e['start_line']-n))

def page_crop(n,start,end,filename):
 p=D[n-1];sc=2.5; pix=p.get_pixmap(matrix=fitz.Matrix(sc,sc),clip=fitz.Rect(0,start,612,end),alpha=False)
 im=Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
 mask=im.convert('L').point(lambda z:255 if z<248 else 0)
 b=mask.getbbox(); pad=15
 b=(max(0,b[0]-pad),max(0,b[1]-pad),min(im.width,b[2]+pad),min(im.height,b[3]+pad))
 im.crop(b).save(OUT/filename)
 bbox=[round((pix.x+b[0])/sc,3),round((pix.y+b[1])/sc,3),round((pix.x+b[2])/sc,3),round((pix.y+b[3])/sc,3)]
 return bbox

items=[]
for key,kind,num,pages,linenos,scripts,status in spec:
 pat=re.compile(r'^'+kind+r'\s+'+re.escape(num)+r':')
 firstblocks=[b for b in D[pages[0]-1].get_text('blocks') if pat.match(b[4])]
 firsttitle=firstblocks[0][4].strip()
 firsttitle=re.split(r'\n(?:The (?:figure|table)|Mean cross-sectional|Percentage of forecaster)',firsttitle)[0].replace('\n',' ')
 title=re.sub(r'^'+kind+r'\s+'+re.escape(num)+r':\s*','',firsttitle)
 item={'id':key,'kind':kind.lower(),'number':num,'title':title,'pages':[],'caption':firsttitle,'notes':[],'subpanels':[],'source_tex':str(TEX),'source_tex_ranges':[],'source_files':[],'source_scripts':[str(S/s) for s in scripts],'mapping_confidence':'high for TeX/assets; computation linkage as noted','replication_source_status':status}
 for ii,n in enumerate(pages):
  p=D[n-1];bs=p.get_text('blocks');cb=[b for b in bs if pat.match(b[4])][0]
  start=max(0,cb[1]-6);end=780 if key=='T8' else (295 if key=='T10' else 730)
  crop=page_crop(n,start,end,f'{key}_part{ii+1}_original.png')
  cliptext=p.get_text(clip=fitz.Rect(*crop))
  (OUT/f'{key}_part{ii+1}_original.txt').write_text(cliptext)
  printed='52 (footer suppressed)' if n==52 else str(n) if n<60 else f'A{n-59}'
  item['pages'].append({'pdf_page':n,'printed_page':printed,'crop_bbox':crop,'png_path':str(OUT/f'{key}_part{ii+1}_original.png'),'text_path':str(OUT/f'{key}_part{ii+1}_original.txt')})
  for b in bs:
   if b[1]<start or b[3]>end: continue
   for starter in ['The figure','The table','Mean cross-sectional','Percentage of forecaster','Notes:']:
    ix=b[4].find(starter)
    if ix>=0:item['notes'].append(b[4][ix:].strip().replace('\n',' '));break
  e=env_at(linenos[ii] if ii<len(linenos) else linenos[0]);item['source_tex_ranges'].append({'start_line':e['start_line'],'end_line':e['end_line']})
  for src in re.findall(r'\\(?:input|includegraphics)(?:\[[^\]]*\])?\s*\{([^}]+)\}',e['text']):
   full=str(TEX.parent/src)
   if full not in item['source_files']:item['source_files'].append(full)
  item['subpanels']+=re.findall(r'\\subfloat\[([^\]]+)\]',e['text'])
 if key in tab_files: item['source_files']=[str(T/tab_files[key])]
 item['notes']=list(dict.fromkeys(item['notes']))
 if key=='F4':item['subpanels']=['RGDP fixed effects','CPI fixed effects','UNEMP fixed effects','NGDP fixed effects']
 if key=='T7':item['subpanels']=['Panel A: Human','Panel B: AI']
 if key=='T11':item['subpanels']=['Panel A: Human (Error Correction and Consensus Tracking)','Panel B: AI (Error Correction and Consensus Tracking)']
 if key=='T12':item['subpanels']=['Detailed Categories','ECB Aggregation']
 if key in ['T3','T4','T5','T6','T8','TB13','TB14','TD15']:item['subpanels']=['Section 1: U.S. Business Indicators','Section 2: Real GDP and Its Components','Section 3: CPI and PCE Inflation']
 items.append(item)

prompts=[]
for key,n,line in [('P1',56,1088),('P2',57,1145),('P3',58,1184),('P4',59,1223),('P5',59,1257)]:
 p=D[n-1];b=[b for b in p.get_text('blocks') if b[4].startswith(f'Prompt {key[1:]}:')][0];start=b[1]-6
 end=419 if key=='P4' else 730
 bbox=page_crop(n,start,end,f'{key}_original.png')
 prompts.append({'id':key,'kind':'prompt','number':key[1:],'title':b[4].splitlines()[0],'pdf_page':n,'png_path':str(OUT/f'{key}_original.png'),'crop_bbox':bbox,'source_tex':str(TEX),'source_tex_range':{k:v for k,v in env_at(line).items() if k!='text'},'included_in_figure_table_count':False})
inv={'source_pdf':str(SRC),'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'page_count':len(D),'figure_count':8,'table_count':15,'item_count':23,'item_page_crop_count':sum(len(x['pages']) for x in items),'items':items,'supplemental_prompts':prompts,'notes':['PDF is authoritative; excluded commented draft-only exhibits and newer oosnew figures not printed in the final PDF.','All pages portrait, including Table D.15.','Table 8 uses the page down through y765 and suppresses its footer.','Table 11 extends to x592; original screenshot preserves full table.','Caption/notes are retained verbatim in cropped images and per-item extracted text; notes field is paragraph extraction.']}
(OUT/'inventory.json').write_text(json.dumps(inv,ensure_ascii=False,indent=2))
source_map={x['id']:{k:x[k] for k in ['title','source_tex','source_tex_ranges','source_files','source_scripts','mapping_confidence','replication_source_status']} for x in items}
(OUT/'source_map.json').write_text(json.dumps(source_map,ensure_ascii=False,indent=2))
print('Saved',len(items),'items,',sum(len(x['pages']) for x in items),'crops and',len(prompts),'prompts')
for x in items:print(x['id'],[p['pdf_page'] for p in x['pages']],x['source_tex_ranges'],[Path(z).name for z in x['source_files']])
