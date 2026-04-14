"""
pdf_report_additions.py — New PDF sections for generate_pdf_report.py
=====================================================================
YASAFlaskified v0.8.36

Adds 5 sections missing vs Medatec:
  1. Position × stage cross-table (sleep time + events + mean duration)
  2. Snoring × position × stage cross-table
  3. Stage-specific sleep latencies (N1, N2, N3, REM)
  4. ESS input field + OSAS score (if ESS provided)
  5. Conclusion/clinical notes placeholder

Integration:
  Import these functions in generate_pdf_report.py and call them
  at the appropriate point in the PDF build sequence.

  from pdf_report_additions import (
      draw_position_stage_table,
      draw_snoring_crosstab,
      draw_stage_latencies,
      draw_ess_section,
      draw_conclusion_section,
  )
"""

from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    Table, TableStyle, Paragraph, Spacer, KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


# ═══════════════════════════════════════════════════════════════
# Shared styles (adapt to match existing generate_pdf_report.py)
# ═══════════════════════════════════════════════════════════════

NAVY = colors.HexColor('#1A3A8F')
DGRAY = colors.HexColor('#6B7A99')
LIGHT_BG = colors.HexColor('#F4F6FA')
WHITE = colors.white
BLACK = colors.black

def _heading_style():
    styles = getSampleStyleSheet()
    return ParagraphStyle(
        'SectionHeading', parent=styles['Heading2'],
        fontSize=11, textColor=NAVY, spaceAfter=4*mm,
        spaceBefore=6*mm,
    )

def _subheading_style():
    styles = getSampleStyleSheet()
    return ParagraphStyle(
        'SubHeading', parent=styles['Heading3'],
        fontSize=9.5, textColor=NAVY, spaceAfter=2*mm,
        spaceBefore=4*mm,
    )

def _body_style():
    styles = getSampleStyleSheet()
    return ParagraphStyle(
        'BodyText', parent=styles['Normal'],
        fontSize=8.5, leading=11, textColor=BLACK,
    )

def _cell_style(bold=False, align='center', size=8):
    return ParagraphStyle(
        'Cell', fontSize=size, leading=size+2,
        alignment={'left': TA_LEFT, 'center': TA_CENTER,
                   'right': TA_RIGHT}[align],
        fontName='Helvetica-Bold' if bold else 'Helvetica',
    )

def _make_table(data, col_widths=None, header_rows=1):
    """Create a styled table with standard formatting."""
    t = Table(data, colWidths=col_widths, repeatRows=header_rows)
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, header_rows-1), NAVY),
        ('TEXTCOLOR', (0, 0), (-1, header_rows-1), WHITE),
        ('FONTNAME', (0, 0), (-1, header_rows-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#C8D0E0')),
        ('ROWBACKGROUNDS', (0, header_rows), (-1, -1),
         [WHITE, LIGHT_BG]),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]
    t.setStyle(TableStyle(style_cmds))
    return t


# ═══════════════════════════════════════════════════════════════
# 1. POSITION × STAGE CROSS-TABLE
# ═══════════════════════════════════════════════════════════════

def compute_position_stage_crosstab(events, hypno, position_data,
                                     sf_pos, tst_hours):
    """
    Compute a cross-tabulation of respiratory events by position and
    sleep stage (NREM/REM) with sleep time per cell.

    Args:
        events: list of event dicts from psgscoring
        hypno: list of stage labels per 30-s epoch
        position_data: dict with 'epochs' key → list of position labels
                       per 30-s epoch, or None
        sf_pos: not used (epochs are 30s)
        tst_hours: total sleep time in hours

    Returns:
        dict with keys like 'nrem_supine', 'nrem_nonsupine',
        'rem_supine', 'rem_nonsupine', each containing:
            sleep_min, n_events, mean_dur, ahi
    """
    cells = {
        'nrem_supine': {'sleep_min': 0, 'events': [], 'n': 0},
        'nrem_nonsupine': {'sleep_min': 0, 'events': [], 'n': 0},
        'rem_supine': {'sleep_min': 0, 'events': [], 'n': 0},
        'rem_nonsupine': {'sleep_min': 0, 'events': [], 'n': 0},
    }

    # Compute sleep time per cell from hypnogram + position
    pos_epochs = position_data.get('epochs', []) if position_data else []
    for i, stage in enumerate(hypno):
        if stage == 'W':
            continue
        is_rem = (stage == 'R')
        pos = pos_epochs[i] if i < len(pos_epochs) else 'unknown'
        is_supine = (pos in ('supine', 'Supine', 0, '0'))

        key = ('rem' if is_rem else 'nrem') + \
              ('_supine' if is_supine else '_nonsupine')
        cells[key]['sleep_min'] += 0.5  # 30-s epoch = 0.5 min

    # Assign events to cells
    for ev in events:
        stage = ev.get('stage', 'N2')
        pos = ev.get('position', 'unknown')
        is_rem = (stage == 'R')
        is_supine = (pos in ('supine', 'Supine', 0, '0'))

        key = ('rem' if is_rem else 'nrem') + \
              ('_supine' if is_supine else '_nonsupine')
        cells[key]['events'].append(ev)
        cells[key]['n'] += 1

    # Compute summary per cell
    result = {}
    for key, cell in cells.items():
        sleep_h = cell['sleep_min'] / 60
        evts = cell['events']
        durations = [e.get('duration_s', 0) for e in evts]
        result[key] = {
            'sleep_min': round(cell['sleep_min']),
            'n_events': cell['n'],
            'mean_dur': round(sum(durations) / len(durations), 1)
                        if durations else 0,
            'ahi': round(cell['n'] / sleep_h, 1) if sleep_h > 0 else 0,
        }

    return result


def draw_position_stage_table(story, events, hypno, position_data,
                               sf_pos, tst_hours, t=None):
    """
    Draw the position × stage cross-table into the PDF story.

    Args:
        story: list of ReportLab flowables
        t: translation function (optional); if None, English labels
    """
    tr = t if t else lambda x, **kw: x

    ct = compute_position_stage_crosstab(
        events, hypno, position_data, sf_pos, tst_hours)

    story.append(Paragraph(
        tr('Respiratory events by sleep stage and body position'),
        _subheading_style()))

    # Header row
    data = [[
        '',
        tr('NREM supine'),
        tr('NREM non-supine'),
        tr('REM supine'),
        tr('REM non-supine'),
    ]]

    # Sleep time row
    data.append([
        tr('Sleep time (min)'),
        str(ct['nrem_supine']['sleep_min']),
        str(ct['nrem_nonsupine']['sleep_min']),
        str(ct['rem_supine']['sleep_min']),
        str(ct['rem_nonsupine']['sleep_min']),
    ])

    # Number of events
    data.append([
        tr('Respiratory events'),
        str(ct['nrem_supine']['n_events']),
        str(ct['nrem_nonsupine']['n_events']),
        str(ct['rem_supine']['n_events']),
        str(ct['rem_nonsupine']['n_events']),
    ])

    # Mean duration
    data.append([
        tr('Mean duration (s)'),
        f"{ct['nrem_supine']['mean_dur']:.1f}",
        f"{ct['nrem_nonsupine']['mean_dur']:.1f}",
        f"{ct['rem_supine']['mean_dur']:.1f}",
        f"{ct['rem_nonsupine']['mean_dur']:.1f}",
    ])

    # AHI per cell
    data.append([
        tr('AHI (/h)'),
        f"{ct['nrem_supine']['ahi']:.1f}",
        f"{ct['nrem_nonsupine']['ahi']:.1f}",
        f"{ct['rem_supine']['ahi']:.1f}",
        f"{ct['rem_nonsupine']['ahi']:.1f}",
    ])

    col_w = [38*mm, 30*mm, 34*mm, 28*mm, 34*mm]
    tbl = _make_table(data, col_widths=col_w)
    story.append(KeepTogether([tbl]))
    story.append(Spacer(1, 3*mm))

    # Supine-dominance annotation
    sup_ahi = ct['nrem_supine']['ahi'] + ct['rem_supine']['ahi']
    nonsup_ahi = ct['nrem_nonsupine']['ahi'] + ct['rem_nonsupine']['ahi']
    if nonsup_ahi > 0 and sup_ahi / nonsup_ahi >= 2.0:
        story.append(Paragraph(
            f"<b>{tr('Supine-dominant OSA')}</b>: "
            f"{tr('supine AHI')} ({sup_ahi:.1f}/h) ≥ 2× "
            f"{tr('non-supine AHI')} ({nonsup_ahi:.1f}/h). "
            f"{tr('Positional therapy may be considered.')}",
            _body_style()))
        story.append(Spacer(1, 2*mm))

    # REM-dominance annotation
    rem_ahi = ct['rem_supine']['ahi'] + ct['rem_nonsupine']['ahi']
    nrem_ahi = ct['nrem_supine']['ahi'] + ct['nrem_nonsupine']['ahi']
    if nrem_ahi > 0 and rem_ahi / nrem_ahi >= 2.0:
        rem_min = ct['rem_supine']['sleep_min'] + \
                  ct['rem_nonsupine']['sleep_min']
        story.append(Paragraph(
            f"<b>{tr('REM-dominant OSA')}</b>: "
            f"REM AHI ({rem_ahi:.1f}/h) ≥ 2× "
            f"NREM AHI ({nrem_ahi:.1f}/h) "
            f"({rem_min} {tr('min REM sleep')}).",
            _body_style()))
        story.append(Spacer(1, 2*mm))


# ═══════════════════════════════════════════════════════════════
# 2. SNORING CROSS-TABLE
# ═══════════════════════════════════════════════════════════════

def draw_snoring_crosstab(story, snore_data, hypno, position_data,
                           t=None):
    """
    Draw snoring percentage by position × stage.

    Args:
        snore_data: dict from psgscoring snoring analysis, must contain
            'epochs' → boolean list (True = snoring) per 30-s epoch,
            or 'snore_mask' → same
    """
    tr = t if t else lambda x, **kw: x

    snore_epochs = snore_data.get('epochs',
                   snore_data.get('snore_mask', []))
    pos_epochs = position_data.get('epochs', []) if position_data else []

    if not snore_epochs:
        return

    # Count snore/total per cell
    cells = {}
    for combo in ['nrem_supine', 'nrem_nonsupine',
                   'rem_supine', 'rem_nonsupine']:
        cells[combo] = {'snore': 0, 'total': 0}

    for i, stage in enumerate(hypno):
        if stage == 'W':
            continue
        is_rem = (stage == 'R')
        pos = pos_epochs[i] if i < len(pos_epochs) else 'unknown'
        is_supine = (pos in ('supine', 'Supine', 0, '0'))
        is_snoring = snore_epochs[i] if i < len(snore_epochs) else False

        key = ('rem' if is_rem else 'nrem') + \
              ('_supine' if is_supine else '_nonsupine')
        cells[key]['total'] += 1
        if is_snoring:
            cells[key]['snore'] += 1

    def pct(key):
        c = cells[key]
        if c['total'] == 0:
            return '—'
        return f"{c['snore'] / c['total'] * 100:.0f}%"

    story.append(Paragraph(
        tr('Snoring by sleep stage and body position'),
        _subheading_style()))

    data = [
        ['', tr('Supine'), tr('Non-supine')],
        [tr('NREM'), pct('nrem_supine'), pct('nrem_nonsupine')],
        [tr('REM'), pct('rem_supine'), pct('rem_nonsupine')],
    ]

    # Add TST row
    total_sup = cells['nrem_supine']['snore'] + cells['rem_supine']['snore']
    total_sup_n = cells['nrem_supine']['total'] + cells['rem_supine']['total']
    total_nonsup = cells['nrem_nonsupine']['snore'] + \
                   cells['rem_nonsupine']['snore']
    total_nonsup_n = cells['nrem_nonsupine']['total'] + \
                     cells['rem_nonsupine']['total']
    pct_sup = f"{total_sup/total_sup_n*100:.0f}%" if total_sup_n > 0 else '—'
    pct_nonsup = f"{total_nonsup/total_nonsup_n*100:.0f}%" \
                 if total_nonsup_n > 0 else '—'
    data.append([tr('TST'), pct_sup, pct_nonsup])

    col_w = [38*mm, 35*mm, 35*mm]
    tbl = _make_table(data, col_widths=col_w)
    story.append(KeepTogether([tbl]))
    story.append(Spacer(1, 3*mm))


# ═══════════════════════════════════════════════════════════════
# 3. STAGE-SPECIFIC SLEEP LATENCIES
# ═══════════════════════════════════════════════════════════════

def compute_stage_latencies(hypno):
    """
    Compute latency to each sleep stage from sleep onset.

    Returns:
        dict: {stage: latency_min} for N1, N2, N3, REM.
        None if stage never reached.
    """
    # Find sleep onset (first non-W epoch)
    onset_epoch = None
    for i, s in enumerate(hypno):
        if s != 'W':
            onset_epoch = i
            break

    if onset_epoch is None:
        return {'N1': None, 'N2': None, 'N3': None, 'R': None}

    latencies = {}
    for target in ['N1', 'N2', 'N3', 'R']:
        first_epoch = None
        for i, s in enumerate(hypno):
            if s == target:
                first_epoch = i
                break
        if first_epoch is not None and first_epoch >= onset_epoch:
            latencies[target] = round(
                (first_epoch - onset_epoch) * 30 / 60, 1)
        elif first_epoch is not None:
            latencies[target] = 0.0
        else:
            latencies[target] = None

    return latencies


def draw_stage_latencies(story, hypno, t=None):
    """Draw stage-specific latency table."""
    tr = t if t else lambda x, **kw: x

    lats = compute_stage_latencies(hypno)

    story.append(Paragraph(
        tr('Sleep latencies'),
        _subheading_style()))

    data = [
        [tr('Stage'), tr('Latency (min)')],
    ]
    for stage, label in [('N1', 'N1'), ('N2', 'N2'),
                          ('N3', 'N3'), ('R', 'REM')]:
        val = lats.get(stage)
        data.append([label, f"{val:.1f}" if val is not None else '—'])

    col_w = [30*mm, 30*mm]
    tbl = _make_table(data, col_widths=col_w)
    story.append(KeepTogether([tbl]))
    story.append(Spacer(1, 3*mm))


# ═══════════════════════════════════════════════════════════════
# 4. ESS + OSAS SCORE
# ═══════════════════════════════════════════════════════════════

def compute_osas_score(results, ess=None):
    """
    Compute the OSAS severity score from pipeline results.

    O = Oxygen deficit (hypoxic burden)
    S = Sleep disruption (arousal index)
    A = Apnea frequency (AHI)
    S = Symptoms (ESS)

    Returns:
        dict with O, S_sleep, A, S_symp, total, label, modifiers
    """
    # O — hypoxic burden
    hb = 0
    hb_data = results.get('hypoxic_burden', {})
    if isinstance(hb_data, dict):
        hb = hb_data.get('hypoxic_burden', 0) or 0
    if hb < 20:
        O = 0
    elif hb < 50:
        O = 1
    elif hb <= 73:
        O = 2
    else:
        O = 3

    # S — arousal index (lives in arousal.summary, NOT respiratory.summary)
    ari = 0
    arousal_data = results.get('arousal', {})
    arousal_summary = arousal_data.get('summary', {}) if isinstance(arousal_data, dict) else {}
    ari = float(arousal_summary.get('arousal_index', 0) or 0)
    if ari < 10:
        S_sleep = 0
    elif ari < 25:
        S_sleep = 1
    elif ari < 50:
        S_sleep = 2
    else:
        S_sleep = 3

    # A — AHI (lives in respiratory.summary)
    resp = results.get('respiratory', {})
    summary = resp.get('summary', {}) if isinstance(resp, dict) else {}
    ahi = float(summary.get('ahi_total', summary.get('ahi', 0)) or 0)
    if ahi < 5:
        A = 0
    elif ahi < 15:
        A = 1
    elif ahi < 30:
        A = 2
    else:
        A = 3

    # S — symptoms (ESS)
    S_symp = None
    if ess is not None:
        if ess < 8:
            S_symp = 0
        elif ess < 11:
            S_symp = 1
        elif ess < 16:
            S_symp = 2
        else:
            S_symp = 3

    # Modifiers
    modifiers = []
    sup_ahi = summary.get('ahi_supine', 0) or 0
    nonsup_ahi = summary.get('ahi_nonsupine', 0) or 0
    if nonsup_ahi > 0 and sup_ahi / nonsup_ahi >= 2.0:
        modifiers.append('p')

    rem_ahi = summary.get('ahi_rem', 0) or 0
    nrem_ahi = summary.get('ahi_nrem', 0) or 0
    if nrem_ahi > 0 and rem_ahi / nrem_ahi >= 2.0:
        modifiers.append('r')

    cai = summary.get('cahi', summary.get('cai', 0)) or 0
    csr = summary.get('csr_detected', False)
    if cai > 5 or csr:
        modifiers.append('c')

    # Build label
    s_symp_str = str(S_symp) if S_symp is not None else '?'
    label = f"O{O}S{S_sleep}A{A}S{s_symp_str}"
    if modifiers:
        label += '-' + ','.join(modifiers)

    total = O + S_sleep + A + (S_symp if S_symp is not None else 0)

    return {
        'O': O, 'S_sleep': S_sleep, 'A': A, 'S_symp': S_symp,
        'total': total,
        'label': label,
        'modifiers': modifiers,
        'hb_value': round(hb, 1),
        'ari_value': round(ari, 1),
        'ahi_value': round(ahi, 1),
        'ess_value': ess,
    }


def draw_ess_section(story, results, ess=None, t=None):
    """
    Draw ESS input and OSAS score section.

    Args:
        ess: Epworth Sleepiness Scale score (0-24), or None if unknown
    """
    tr = t if t else lambda x, **kw: x

    story.append(Paragraph(
        tr('Symptom assessment and severity profile'),
        _heading_style()))

    # ESS
    if ess is not None:
        ess_text = f"<b>Epworth Sleepiness Score (ESS):</b> {ess}/24"
        if ess < 8:
            ess_text += f"  ({tr('normal')})"
        elif ess < 11:
            ess_text += f"  ({tr('mild sleepiness')})"
        elif ess < 16:
            ess_text += f"  ({tr('moderate sleepiness')})"
        else:
            ess_text += f"  ({tr('severe sleepiness')})"
    else:
        ess_text = f"<b>Epworth Sleepiness Score (ESS):</b> " \
                   f"{tr('not provided')}"

    story.append(Paragraph(ess_text, _body_style()))
    story.append(Spacer(1, 3*mm))

    # OSAS score
    score = compute_osas_score(results, ess=ess)

    story.append(Paragraph(
        tr('OSAS severity profile'),
        _subheading_style()))

    data = [
        [tr('Dimension'), tr('Metric'), tr('Value'),
         tr('Grade (0-3)')],
        ['O — ' + tr('Oxygen deficit'),
         tr('Hypoxic burden'), f"{score['hb_value']} %·min/h",
         str(score['O'])],
        ['S — ' + tr('Sleep disruption'),
         tr('Arousal index'), f"{score['ari_value']}/h",
         str(score['S_sleep'])],
        ['A — ' + tr('Apnea frequency'),
         'AHI', f"{score['ahi_value']}/h",
         str(score['A'])],
        ['S — ' + tr('Symptoms'),
         'ESS',
         f"{score['ess_value']}/24" if score['ess_value'] is not None
         else '?',
         str(score['S_symp']) if score['S_symp'] is not None else '?'],
    ]

    col_w = [40*mm, 32*mm, 32*mm, 25*mm]
    tbl = _make_table(data, col_widths=col_w)
    story.append(KeepTogether([tbl]))
    story.append(Spacer(1, 2*mm))

    # Score summary line
    mod_str = ''
    if score['modifiers']:
        mod_str = '  Modifiers: ' + ', '.join(
            {'p': tr('positional'), 'r': tr('REM-dominant'),
             'c': tr('central component')}[m]
            for m in score['modifiers']
        )

    story.append(Paragraph(
        f"<b>{tr('OSAS code')}: {score['label']}</b>  "
        f"({tr('total')}: {score['total']}/12){mod_str}",
        _body_style()))
    story.append(Spacer(1, 3*mm))


# ═══════════════════════════════════════════════════════════════
# 5. CONCLUSION / CLINICAL NOTES PLACEHOLDER
# ═══════════════════════════════════════════════════════════════

def draw_conclusion_section(story, clinical_notes=None, t=None):
    """
    Draw the conclusion section with optional pre-filled notes.

    In the web UI, this maps to the report editor fields.
    In the PDF, it provides structure for physician review.
    """
    tr = t if t else lambda x, **kw: x

    story.append(Paragraph(
        tr('Clinical assessment'),
        _heading_style()))

    sections = [
        ('a', tr('Overall assessment'), ''),
        ('b', tr('Conclusion'), ''),
        ('c', tr('Recommendations'), ''),
    ]

    for letter, label, default_text in sections:
        text = default_text
        if clinical_notes and isinstance(clinical_notes, dict):
            text = clinical_notes.get(label.lower(),
                   clinical_notes.get(letter, default_text))

        story.append(Paragraph(
            f"<b>{letter}. {label}:</b>", _body_style()))

        if text:
            story.append(Paragraph(text, _body_style()))
        else:
            # Empty lines for handwritten notes if printed
            story.append(Spacer(1, 12*mm))

        story.append(Spacer(1, 2*mm))

    # Signature lines
    story.append(Spacer(1, 8*mm))
    story.append(Paragraph(
        '___________________________________&nbsp;&nbsp;&nbsp;&nbsp;'
        '&nbsp;&nbsp;&nbsp;&nbsp;'
        '_______________',
        _body_style()))
    story.append(Paragraph(
        f'{tr("Physician signature")}'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'
        f'{tr("Date")}',
        ParagraphStyle('Sig', fontSize=7.5, textColor=DGRAY)))
    story.append(Spacer(1, 4*mm))


# ═══════════════════════════════════════════════════════════════
# 6. SpO2 SATURATION BANDS (detailed breakdown)
# ═══════════════════════════════════════════════════════════════

def draw_spo2_bands(story, spo2_summary, tib_min, t=None):
    """
    Draw time-in-saturation-bands table (like Medatec).

    Args:
        spo2_summary: dict from psgscoring SpO2 analysis
        tib_min: time in bed (minutes)
    """
    tr = t if t else lambda x, **kw: x

    story.append(Paragraph(
        tr('Time in saturation bands'),
        _subheading_style()))

    # Define bands
    bands = [
        ('95-100%', 'time_95_100_min', 'pct_95_100'),
        ('90-95%',  'time_90_95_min',  'pct_90_95'),
        ('80-90%',  'time_80_90_min',  'pct_80_90'),
        ('70-80%',  'time_70_80_min',  'pct_70_80'),
        ('<70%',    'time_below_70_min', 'pct_below_70'),
    ]

    data = [[tr('SpO₂ range'), tr('Duration (min)'),
             tr('% of recording')]]

    for label, time_key, pct_key in bands:
        minutes = spo2_summary.get(time_key, 0)
        pct = spo2_summary.get(pct_key)
        if pct is None and tib_min > 0:
            pct = round(minutes / tib_min * 100, 1)
        data.append([
            label,
            f"{minutes:.1f}" if minutes else '0.0',
            f"{pct:.1f}%" if pct is not None else '0.0%',
        ])

    col_w = [30*mm, 35*mm, 35*mm]
    tbl = _make_table(data, col_widths=col_w)
    story.append(KeepTogether([tbl]))
    story.append(Spacer(1, 3*mm))


# ═══════════════════════════════════════════════════════════════
# INTEGRATION GUIDE
# ═══════════════════════════════════════════════════════════════
"""
In generate_pdf_report.py, add calls at the appropriate sections:

# After existing respiratory events table:
draw_position_stage_table(
    story, events=resp_events, hypno=hypno,
    position_data=position_results, sf_pos=1,
    tst_hours=tst_hours, t=t)

# After existing snoring section:
draw_snoring_crosstab(
    story, snore_data=snore_results, hypno=hypno,
    position_data=position_results, t=t)

# In sleep architecture section (after SOL):
draw_stage_latencies(story, hypno=hypno, t=t)

# After existing SpO2 table:
draw_spo2_bands(
    story, spo2_summary=spo2_results['summary'],
    tib_min=tib_min, t=t)

# New section after all analyses:
draw_ess_section(
    story, results=full_results, ess=study.get('ess'), t=t)

# Final section:
draw_conclusion_section(
    story, clinical_notes=study.get('clinical_notes'), t=t)

# Also add ESS to the upload form / analysis parameters:
#   - New optional field in the UI: ESS score (0-24)
#   - Stored in study metadata: study['ess'] = int or None
#   - Passed through to PDF generation

# i18n keys to add (449 existing + ~25 new):
#   'Respiratory events by sleep stage and body position'
#   'NREM supine' / 'NREM non-supine' / 'REM supine' / 'REM non-supine'
#   'Sleep time (min)' / 'Respiratory events' / 'Mean duration (s)'
#   'Supine-dominant OSA' / 'REM-dominant OSA'
#   'Positional therapy may be considered.'
#   'Snoring by sleep stage and body position'
#   'Sleep latencies'
#   'Symptom assessment and severity profile'
#   'OSAS severity profile' / 'OSAS code'
#   'Oxygen deficit' / 'Sleep disruption' / 'Apnea frequency' / 'Symptoms'
#   'positional' / 'REM-dominant' / 'central component'
#   'Clinical assessment' / 'Overall assessment' / 'Conclusion'
#   'Recommendations' / 'Physician signature' / 'Date'
#   'Time in saturation bands' / 'SpO₂ range' / 'Duration (min)'
#   '% of recording'
"""
