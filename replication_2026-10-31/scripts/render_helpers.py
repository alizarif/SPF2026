"""Readable, deterministic PNG tables for the replication report."""
from pathlib import Path
import textwrap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def render_table(title, columns, rows, path, notes=None, groups=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ncols = len(columns)
    width = max(10.5, min(16, ncols * 1.0))
    wrap = 33 if ncols <= 3 else 24
    wrapped = [[textwrap.fill(str(v), width=(22 if j==0 else 105) if ncols==2 else (wrap if j == 0 else max(16,wrap))) for j,v in enumerate(row)] for row in rows]
    linecounts = [max(str(v).count('\n')+1 for v in row) for row in wrapped]
    note = '\n'.join(textwrap.wrap(' '.join(notes) if isinstance(notes,list) else str(notes or ''), width=int(width*12)))
    body_height = sum(max(.31, .20*l+.10) for l in linecounts) + .7
    note_height = .21 * (note.count('\n')+1) if note else 0
    height = 1.1 + body_height + note_height
    fig = plt.figure(figsize=(width,height),facecolor='white')
    ax = fig.add_axes([.025,(note_height+.18)/height,.95,body_height/height])
    ax.axis('off')
    fig.text(.027,1-.20/height,title,ha='left',va='top',fontsize=15,fontweight='bold',color='#123349')
    colwidths = [.23,.77] if ncols==2 else None
    if ncols >= 6:
        first = .24
        colwidths = [first]+[(1-first)/(ncols-1)]*(ncols-1)
    table = ax.table(cellText=wrapped,colLabels=[textwrap.fill(str(c),12 if ncols>=6 else 16) for c in columns],cellLoc='center',colWidths=colwidths,bbox=[0,0,1,1])
    table.auto_set_font_size(False)
    table.set_fontsize(10.3 if ncols>=9 else 10.5)
    totalunits = sum(max(1.25,l) for l in linecounts)+1.8
    for (i,j),cell in table.get_celld().items():
        cell.set_edgecolor('#dce3e8');cell.set_linewidth(.45)
        if i==0:
            cell.set_facecolor('#173b52');cell.set_text_props(color='white',weight='bold');cell.set_height(1.8/totalunits)
        else:
            cell.set_facecolor('#f1f5f7' if i%2==0 else 'white');cell.set_height(max(1.25,linecounts[i-1])/totalunits)
            if j==0: cell.set_text_props(ha='left')
    if note: fig.text(.027,.10/height,note,ha='left',va='bottom',fontsize=9,color='#45525e',linespacing=1.35)
    fig.savefig(path,dpi=180,facecolor='white')
    plt.close(fig)
    return str(path)
