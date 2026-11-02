"""Read-only check of PDF numbers, colors, adjacency, and cell text geometry.

The 279 core correction pairs come from an independently prepared audit list.
All 1,709 numeric cells are additionally checked against their render metadata.
"""
from pathlib import Path
import collections,json,re,fitz,hashlib
RUN=Path(__file__).resolve().parents[1]
ROOT=RUN.parent
e=json.loads((RUN/'tables_review/independent_core_expected.json').read_text())
v=json.loads((RUN/'tables_review/render_validation.json').read_text())
t=json.loads((RUN/'tables_review/table_data.json').read_text())
pdf_path=RUN/'output/pdf'/Path(v['pdf']).name
doc=fitz.open(pdf_path)
expected={(x['item'],x['row'],x['column']):x for x in e['cells']}
rendered={(x['item'],x['row'],x['column']):x for x in v['rendered_cells'] if x['kind']!='header'}
core=set(e['tables'])
actual={k:x for k,x in rendered.items() if k[0] in core and x['red']}
assert set(actual)==set(expected),{'missing':list(set(expected)-set(actual)),'extra':list(set(actual)-set(expected))}
for k,x in expected.items():
 assert actual[k]['original']==x['published'],(k,'original')
 assert actual[k]['replicated']==x['recalculated'],(k,'replicated')
canon={}
for item,z in t.items():
 for row in z['rows']:
  for cell in row.get('cells',[]):
   if 'audit_column' in cell:
    canon[(item,cell.get('audit_row',row['label']),cell['audit_column'])]=cell
for k,x in expected.items():
 assert canon[k]['mismatch']
 assert canon[k]['original_display']==x['published']
 assert canon[k]['replicated_display']==x['recalculated']
spans={}
for i,p in enumerate(doc):
 spans[i+1]=[s for b in p.get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans']]
def red(color):
 r,g,b=(color>>16)&255,(color>>8)&255,color&255
 return r>150 and g<70 and b<70

def normalize(s):return re.sub(r'\s+','',s).replace('−','-')
checks=[];fail=[];cell_rectangles=[];horizontal_overflows=[]
for cell in v['rendered_cells']:
 if cell['kind']=='header':continue
 p=doc[cell['page']-1]
 x,y,w,h=cell['bbox_pdf']; bottom=p.rect.height-y;top=bottom-h
 selected=[s for s in spans[cell['page']] if x-.1<=s['origin'][0]<=x+w+.1 and top-1<=s['origin'][1]<=bottom+1]
 selected.sort(key=lambda s:s['origin'][0])
 black=[s for s in selected if s['color']==0];reds=[s for s in selected if red(s['color'])]
 orig=normalize(''.join(s['text'] for s in black));rep=normalize(''.join(s['text'] for s in reds))
 exorig=normalize(cell['original']);exrep='['+normalize(cell['replicated'])+']' if cell['red'] else ''
 good=orig==exorig and rep==exrep
 spacing=None;vertical=None
 if cell['red'] and black and reds:
  spacing=min(s['bbox'][0]for s in reds)-max(s['bbox'][2]for s in black)
  vertical=abs(max(s['origin'][1] for s in black)-max(s['origin'][1] for s in reds))
  good=good and spacing>=-.2 and vertical<.2
 record={'item':cell['item'],'row':cell['row'],'column':cell['column'],'page':cell['page'],'red':cell['red'],'black_text':orig,'red_text':rep,'match':good,'horizontal_gap_pt':spacing,'baseline_difference_pt':vertical}
 checks.append(record)
 if selected:
  rectangle=[min(s['bbox'][0] for s in selected),min(s['bbox'][1] for s in selected),max(s['bbox'][2] for s in selected),max(s['bbox'][3] for s in selected)]
  cell_rectangles.append({'page':cell['page'],'item':cell['item'],'row':cell['row'],'column':cell['column'],'bbox':rectangle})
  if rectangle[0]<x-.2 or rectangle[2]>x+w+.2:
   horizontal_overflows.append({'cell':record,'text_bbox':rectangle,'available_x':[x,x+w]})
 if not good:fail.append(dict(record,expected_black=exorig,expected_red=exrep,bbox_pdf=cell['bbox_pdf'],spans=selected))
headers=[]
for cell in v['rendered_cells']:
 if cell['kind']!='header':continue
 p=doc[cell['page']-1];x,y,w,h=cell['bbox_pdf'];bottom=p.rect.height-y;top=bottom-h
 selected=[s for s in spans[cell['page']] if x-.1<=s['origin'][0]<=x+w+.1 and top-1<=s['origin'][1]<=bottom+1];selected.sort(key=lambda s:s['origin'][0])
 headers.append({'cell':cell,'texts':[(s['text'],s['color'],s['origin'])for s in selected]})
 assert normalize(''.join(s['text'] for s in selected if s['color']==0))=='Horizon2'
 assert normalize(''.join(s['text'] for s in selected if red(s['color'])))=='[4]'
overlaps=[]
for i,a in enumerate(cell_rectangles):
 for b in cell_rectangles[i+1:]:
  if a['page']!=b['page']:continue
  r,s=a['bbox'],b['bbox']
  if min(r[2],s[2])-max(r[0],s[0])>.05 and min(r[3],s[3])-max(r[1],s[1])>.05:
   overlaps.append([a,b])
result={'pdf':str(pdf_path),'sha256':hashlib.sha256(pdf_path.read_bytes()).hexdigest(),'pages':len(doc),'independent_core_expected_pairs':len(expected),'independent_core_manifest_exact':True,'body_cells_checked_from_pdf':len(checks),'red_body_pairs_checked_from_pdf':sum(x['red']for x in checks),'all_pdf_cell_text_and_adjacency_pass':not fail,'failures':fail,'header_checks':headers,'per_table_red_pairs':dict(collections.Counter(x['item']for x in checks if x['red'])),'checks':checks}
result.update(horizontal_cell_overflows=horizontal_overflows,overlapping_numeric_text_boxes=overlaps,all_numeric_cell_geometry_pass=not(horizontal_overflows or overlaps))
(RUN/'tables_review/independent_pdf_audit.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items()if k not in ['checks','failures']},indent=2))
print('FAILURE COUNT',len(fail))
for x in fail[:6]:print(json.dumps(x,indent=2))
assert not fail and not horizontal_overflows and not overlaps
