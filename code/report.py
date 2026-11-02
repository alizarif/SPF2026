"""Render the published tables beside fresh calculations.

The static reference contains only published entries and display metadata.
Every numeric estimate and significance marker must be supplied by the caller.
No saved calculation, historical audit, manuscript, or old PDF is read here.
"""
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
import html
import math
from pathlib import Path
import re

from data import reference

ORDER = ('T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9',
         'T10', 'T11', 'T12', 'TB13', 'TB14', 'TD15')


def required_keys():
    """Return the 1,709 estimate and 604 significance keys required to render."""
    keys = set()
    for item, table in reference().items():
        for row in table['rows']:
            for cell in row.get('cells', []):
                if cell['kind'] != 'numeric':
                    continue
                keys.add((item, cell['audit_row'], cell['audit_column']))
                if cell.get('star_column'):
                    keys.add((item, cell['audit_row'], cell['star_column']))
    return keys


def _format(value, cell, stars=0):
    """Half-even rounding of the quantity actually used in the calculation.

    Existing statistical calculations use IEEE binary floats, so their exact
    float values are rounded. B.14 uses decimal source arithmetic; its decimal
    quantity is preserved. These two rules intentionally differ at binary ties
    such as T6's 8.025 (8.03), versus B.14's decimal 0.075 (0.08).
    """
    if not math.isfinite(float(value)):
        raise ValueError('Non-finite estimate cannot be rendered')
    precision = cell['precision']
    if cell.get('rounding') == 'decimal':
        number = value if isinstance(value, Decimal) else Decimal(str(value))
    else:
        number = Decimal.from_float(float(value))
    with localcontext() as context:
        context.prec = 50
        number = number.quantize(Decimal(1).scaleb(-precision), rounding=ROUND_HALF_EVEN)
    if not number:
        number = abs(number)  # Do not print negative zero.
    spec = f',.{precision}f' if cell.get('thousands_separator') else f'.{precision}f'
    text = format(number, spec)
    if cell.get('percent'):
        text += '%'
    text += '*' * stars
    return '(' + text + ')' if cell.get('parentheses') else text


def build_tables(cells, *, verified_rounding=None):
    """Join fresh calculations to the published reference, failing on gaps.

    ``cells`` is a list of {item, row, column, replicated}. Significance entries
    use the numeric column name plus ' stars' and contain an integer from 0–3.
    Optional verified_rounding maps a cell key to {original_display,
    replicated_display, evidence}. It must document the same underlying
    estimate with a formatting-only discrepancy; size or Monte Carlo variation
    alone is not evidence. There are no such exceptions in the current report.
    """
    calculated = {}
    for entry in cells:
        key = (entry['item'], entry['row'], entry['column'])
        if key in calculated:
            raise ValueError(f'Duplicate calculated cell: {key}')
        calculated[key] = entry['replicated']
    expected = required_keys()
    missing, extra = expected - calculated.keys(), calculated.keys() - expected
    if missing or extra:
        raise ValueError(f'Calculation keys differ: missing={sorted(missing)}, extra={sorted(extra)}')
    proofs = verified_rounding or {}
    tables = deepcopy(reference())
    if set(tables) != set(ORDER):
        raise ValueError('The published reference must contain all 15 tables')
    for item in ORDER:
        table = tables[item]
        count = 0
        for row in table['rows']:
            for cell in row.get('cells', []):
                if cell['kind'] != 'numeric':
                    continue
                key = (item, cell['audit_row'], cell['audit_column'])
                value, stars = calculated[key], 0
                if cell.get('star_column'):
                    raw = calculated[(item, cell['audit_row'], cell['star_column'])]
                    if not math.isfinite(float(raw)) or float(raw) != int(raw) or not 0 <= int(raw) <= 3:
                        raise ValueError(f'Invalid significance count for {key}: expected integer 0–3')
                    stars = int(raw)
                display = _format(value, cell, stars)
                mismatch = display != cell['original_display']
                star_change = stars != cell['starsoriginal']
                proof = proofs.get(key)
                rounding_only = bool(proof and proof.get('evidence')
                                     and proof.get('original_display') == cell['original_display']
                                     and proof.get('replicated_display') == display
                                     and not star_change)
                cell.update(replicated=float(value), starsreplicated=stars,
                            replicated_display=display, mismatch=mismatch,
                            numeric_mismatch=display.replace('*', '') != cell['original_display'].replace('*', ''),
                            stars_mismatch=star_change,
                            annotation_color=('blue' if rounding_only else 'red') if mismatch else None)
                count += int(mismatch)
        table['mismatch_count'] = count
        # Derive horizon corrections from the actual calculation column keys.
        # B.13's published 'Horizon 2' covers h4 calculations, so it shows [4].
        for group in table['column_groups']:
            label = re.fullmatch(r'Horizon (\d+)', group['label'])
            if not label:
                continue
            horizons = set()
            for row in table['rows']:
                if row['type'] != 'data':
                    continue
                for cell in row['cells'][group['start_column']:group['end_column'] + 1]:
                    match = re.match(r'h(\d+)(?:\s|:)', cell.get('audit_column', ''))
                    if match:
                        horizons.add(match[1])
            if len(horizons) != 1:
                raise ValueError(f'Ambiguous horizon columns: {item}, {group["label"]}')
            horizon = next(iter(horizons))
            if horizon != label[1]:
                group['correction'] = dict(kind='header', prefix='Horizon ',
                    original_display=label[1], replicated_display=horizon,
                    mismatch=True, annotation_color='red')
    return tables


def render(tables, output_path):
    """Write one title-and-table-only A3 landscape page for each table."""
    import matplotlib
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A3, landscape
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Flowable, Paragraph, Table, TableStyle
    from reportlab.lib.styles import ParagraphStyle

    fonts = Path(matplotlib.get_data_path()) / 'fonts/ttf'
    for name, filename in [('Review', 'DejaVuSans.ttf'), ('ReviewBold', 'DejaVuSans-Bold.ttf')]:
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(fonts / filename)))
    pdfmetrics.registerFontFamily('Review', normal='Review', bold='ReviewBold',
                                  italic='Review', boldItalic='ReviewBold')
    red, blue = colors.HexColor('#c01823'), colors.HexColor('#1565c0')
    navy, light, rule = [colors.HexColor(s) for s in ('#16384b', '#e9f0f4', '#b8c7d1')]
    width, height = landscape(A3)
    margin, available = 34, width - 68
    rendered = []

    class NumberPair(Flowable):
        def __init__(self, cell, item, row, column, size=11):
            super().__init__()
            self.cell, self.item, self.row, self.column = cell, item, row, column
            self.base_size = self.size = size

        def parts(self):
            cell = self.cell
            font = 'ReviewBold' if cell.get('bold_original', False) else 'Review'
            result = [(cell['prefix'], 'ReviewBold', 1, 0, colors.black)] if cell.get('prefix') else []

            def value(text, face, color):
                match = re.match(r'^(.*?)(\*+)?$', text)
                result.append((match[1], face, 1, 0, color))
                if match[2]:
                    result.append((match[2], face, .69, .40, color))

            value(cell['original_display'], font, colors.black)
            if cell['mismatch']:
                color = blue if cell.get('annotation_color') == 'blue' else red
                result.append(('  [', 'Review', 1, 0, color))
                value(cell['replicated_display'], 'Review', color)
                result.append((']', 'Review', 1, 0, color))
            return result

        def wrap(self, avail_width, avail_height):
            self.width = avail_width
            total = sum(pdfmetrics.stringWidth(s, f, self.base_size * scale)
                        for s, f, scale, rise, color in self.parts())
            self.size = min(self.base_size, self.base_size * avail_width / max(total, 1))
            if self.size < 8.8:
                raise ValueError(f'Numeric cell too narrow: {self.item}, {self.row}, {self.column}')
            self.height = max(15, self.size * 1.35)
            return avail_width, self.height

        def draw(self):
            parts = self.parts()
            total = sum(pdfmetrics.stringWidth(s, f, self.size * scale)
                        for s, f, scale, rise, color in parts)
            x, y = (self.width - total) / 2, 2.2
            for text, font, scale, rise, color in parts:
                self.canv.setFont(font, self.size * scale)
                self.canv.setFillColor(color)
                self.canv.drawString(x, y + self.size * rise, text)
                x += pdfmetrics.stringWidth(text, font, self.size * scale)
            gx, gy = self.canv.absolutePosition(0, 0)
            color = self.cell.get('annotation_color')
            rendered.append(dict(item=self.item, row=self.row, column=self.column,
                kind=self.cell['kind'], page=self.canv.getPageNumber(),
                original=self.cell['original_display'], replicated=self.cell['replicated_display'],
                mismatch=self.cell['mismatch'], annotation_color=color,
                red=color == 'red', blue=color == 'blue', font_size=self.size,
                bbox_pdf=[gx, gy, self.width, self.height]))

    styles = {name: ParagraphStyle(name, fontName='Review', fontSize=size,
              leading=leading, textColor=colors.black, spaceAfter=0)
              for name, size, leading in [('cell', 10.8, 14), ('header', 10.5, 14), ('section', 10.5, 14)]}
    styles['header'].fontName = styles['section'].fontName = 'ReviewBold'
    styles['section'].textColor = navy

    def para(text, style='cell'):
        return Paragraph(html.escape(text), styles[style])

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(destination), pagesize=(width, height))
    pdf.setTitle('Tables: verified recalculations')
    pdf.setAuthor('Replication review from supplied data and code')
    page_checks = []
    for page, item in enumerate(ORDER, 1):
        table = tables[item]
        ncol = len(table['columns'])
        pdf.bookmarkPage(item)
        pdf.addOutlineEntry(table['title'], item, 0)
        title = Paragraph(html.escape(table['title']), ParagraphStyle('Title',
                    fontName='ReviewBold', fontSize=19, leading=24, textColor=navy))
        _, title_height = title.wrap(available, 1000)
        title.drawOn(pdf, margin, height - 31 - title_height)
        y = height - 31 - title_height - 19
        data, commands, header_rows = [], [], 0
        if table['column_groups']:
            groups = [''] * ncol
            for group in table['column_groups']:
                start, end = group['start_column'], group['end_column']
                groups[start] = (NumberPair(group['correction'], item, 'header', group['label'])
                                 if group.get('correction') else para(group['label'], 'header'))
                if start != end:
                    commands.append(('SPAN', (start, 0), (end, 0)))
            data.append(groups)
            header_rows += 1
        data.append([para(text, 'header') for text in table['columns']])
        header_rows += 1
        for row in table['rows']:
            index = len(data)
            if row['type'] == 'section':
                data.append([para(row['label'], 'section')] + [''] * (ncol - 1))
                commands += [('SPAN', (0, index), (-1, index)),
                             ('BACKGROUND', (0, index), (-1, index), light),
                             ('LINEABOVE', (0, index), (-1, index), .65, rule)]
            else:
                data.append([NumberPair(cell, item, cell['audit_row'], cell['audit_column'])
                             if cell['kind'] == 'numeric' else para(cell['original_display'])
                             for cell in row['cells']])
                if index % 2 == 0:
                    commands.append(('BACKGROUND', (0, index), (-1, index), colors.HexColor('#f7f9fa')))
        if item in ['T1', 'T2']:
            widths = [195, available - 195]
        elif item == 'T9':
            widths = [240, 225, 265, (available - 730) / 2, (available - 730) / 2]
        elif item == 'T11':
            widths = [208] + [(available - 208) / 8] * 8
        elif item == 'T12':
            widths = [195, 90] + [(available - 285) / 6] * 6
        elif ncol <= 6:
            widths = [230] + [(available - 230) / (ncol - 1)] * (ncol - 1)
        else:
            widths = [190] + [(available - 190) / (ncol - 1)] * (ncol - 1)
        commands += [('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('BACKGROUND', (0, 0), (-1, header_rows - 1), colors.HexColor('#dbe7ef')),
            ('LINEBELOW', (0, header_rows - 1), (-1, header_rows - 1), .8, navy),
            ('BOX', (0, 0), (-1, -1), .45, rule),
            ('INNERGRID', (0, 0), (-1, -1), .25, colors.HexColor('#dce3e8')),
            ('LEFTPADDING', (0, 0), (-1, -1), 7), ('RIGHTPADDING', (0, 0), (-1, -1), 7),
            ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]
        layout = Table(data, colWidths=widths, repeatRows=header_rows, hAlign='LEFT')
        layout.setStyle(TableStyle(commands))
        _, table_height = layout.wrap(available, height)
        if y - table_height < margin:
            layout = Table(data, colWidths=widths, repeatRows=header_rows, hAlign='LEFT')
            layout.setStyle(TableStyle(commands + [('TOPPADDING', (0, 0), (-1, -1), 2.8),
                                                  ('BOTTOMPADDING', (0, 0), (-1, -1), 2.8)]))
            _, table_height = layout.wrap(available, height)
        if y - table_height < margin:
            raise ValueError(f'Table does not fit its page: {item}')
        layout.drawOn(pdf, margin, y - table_height)
        page_checks.append(dict(id=item, page=page, table_bottom_pt=y - table_height,
                                annotated_body_entries=table['mismatch_count']))
        pdf.showPage()
    pdf.save()
    return dict(pdf=str(destination), pages=len(ORDER),
        numeric_cells_rendered=sum(c['kind'] == 'numeric' for c in rendered),
        red_body_entries=sum(c['red'] and c['kind'] == 'numeric' for c in rendered),
        blue_body_entries=sum(c['blue'] and c['kind'] == 'numeric' for c in rendered),
        header_corrections=sum(c['mismatch'] and c['kind'] == 'header' for c in rendered),
        expected_counts={item: tables[item]['mismatch_count'] for item in ORDER},
        minimum_numeric_font_size=min(c['font_size'] for c in rendered),
        page_checks=page_checks, rendered_cells=rendered)


def build_report(cells, output_path, *, verified_rounding=None):
    """Build the comparison from fresh estimates, render it, and return checks."""
    tables = build_tables(cells, verified_rounding=verified_rounding)
    return render(tables, output_path)
