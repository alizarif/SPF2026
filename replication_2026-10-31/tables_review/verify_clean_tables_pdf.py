"""Verify final table text, annotation colors, adjacency, and clean page geometry."""
from pathlib import Path
import collections, hashlib, json, re
import fitz

HERE = Path(__file__).resolve().parent
metadata = json.loads((HERE/'render_validation_verified.json').read_text())
tables = json.loads((HERE/'table_data_verified.json').read_text())
previous = json.loads((HERE/'table_data.json').read_text())
pdf_path = HERE.parent/'output/pdf'/Path(metadata['pdf']).name
doc = fitz.open(pdf_path)
assert len(doc) == 15

def canonical(table):
    return {(cell.get('audit_row', row.get('label','')), cell.get('audit_column', table['columns'][i])): cell
            for row in table['rows'] if row['type']=='data'
            for i,cell in enumerate(row['cells']) if cell['kind']=='numeric'}

for key,table in tables.items():
    old,new = canonical(previous[key]),canonical(table)
    assert set(old)==set(new), (key,'cell coverage changed')
    for cell_id,cell in old.items():
        assert cell['original_display']==new[cell_id]['original_display'],(key,cell_id,'published value changed')

def normalize(s):
    return re.sub(r'\s+','',s).replace('−','-')

def color_name(color):
    if color==0:return 'black'
    r,g,b=(color>>16)&255,(color>>8)&255,color&255
    if r>150 and g<70 and b<70:return 'red'
    if b>130 and b>r*1.5 and b>g*1.2:return 'blue'
    return 'other'

spans={i+1:[s for block in page.get_text('dict')['blocks']
            for line in block.get('lines',[]) for s in line['spans']]
       for i,page in enumerate(doc)}
checks=[];failures=[];rectangles=[];overflows=[]
for cell in metadata['rendered_cells']:
    page=doc[cell['page']-1]
    x,y,w,h=cell['bbox_pdf'];bottom=page.rect.height-y;top=bottom-h
    selected=sorted([s for s in spans[cell['page']]
                     if x-.1<=s['origin'][0]<=x+w+.1 and top-1<=s['origin'][1]<=bottom+1],key=lambda s:s['origin'][0])
    by_color={color:[s for s in selected if color_name(s['color'])==color] for color in ['black','red','blue','other']}
    texts={color:normalize(''.join(s['text'] for s in value)) for color,value in by_color.items()}
    expected={'black':normalize(('Horizon ' if cell['kind']=='header' else '')+cell['original']), 'red':'','blue':'','other':''}
    if cell['mismatch']:expected[cell['annotation_color']]='['+normalize(cell['replicated'])+']'
    good=texts==expected
    gap=baseline=None
    if cell['mismatch']:
        black=by_color['black'];colored=by_color[cell['annotation_color']]
        if black and colored:
            gap=min(s['bbox'][0] for s in colored)-max(s['bbox'][2] for s in black)
            baseline=abs(max(s['origin'][1] for s in black)-max(s['origin'][1] for s in colored))
            good=good and gap>=-.2 and baseline<.2
        else:good=False
    record={k:cell[k] for k in ['item','row','column','page','kind','annotation_color']}
    record.update(match=good,texts=texts,gap_pt=gap,baseline_delta_pt=baseline)
    checks.append(record)
    if not good:failures.append(dict(record,expected=expected))
    if selected:
        rect=[min(s['bbox'][0] for s in selected),min(s['bbox'][1] for s in selected),max(s['bbox'][2] for s in selected),max(s['bbox'][3] for s in selected)]
        rectangles.append({'page':cell['page'],'cell':(cell['item'],cell['row'],cell['column']),'bbox':rect})
        if rect[0]<x-.2 or rect[2]>x+w+.2:overflows.append(rectangles[-1])

overlaps=[]
for i,a in enumerate(rectangles):
    for b in rectangles[i+1:]:
        if a['page']!=b['page']:continue
        r,s=a['bbox'],b['bbox']
        if min(r[2],s[2])-max(r[0],s[0])>.05 and min(r[3],s[3])-max(r[1],s[1])>.05:overlaps.append([a,b])

removed_text=['Black = published value','Red in [brackets]','Matching entries appear once','Audit note:','Tables-only replication review','UNRESOLVED ESTIMATOR','UNRESOLVED DATA','1 November 2026']
for i,page in enumerate(doc):
    text=page.get_text()
    assert not any(x in text for x in removed_text),(i+1,'unwanted explanatory text')
    assert not [s for s in spans[i+1] if s['bbox'][3]>page.rect.height-30],(i+1,'footer-area text')
    assert text.startswith('Table '),(i+1,'missing title')

result={'pdf':str(pdf_path),'sha256':hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
        'pages':len(doc),'original_numeric_values_preserved':True,'clean_title_and_table_only':True,
        'body_cells_checked':sum(x['kind']=='numeric' for x in checks),
        'annotation_counts':dict(collections.Counter(x['annotation_color'] for x in checks if x['annotation_color'])),
        'per_table_annotations':dict(collections.Counter(x['item'] for x in checks if x['annotation_color'])),
        'failures':failures,'horizontal_overflows':overflows,'overlapping_numeric_cells':overlaps,'checks':checks}
(HERE/'verified_pdf_content_audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='checks'},indent=2))
assert not failures and not overflows and not overlaps
