function escapePdfText(str) {
  return String(str || '')
    .replace(/[^\x20-\x7E]/g, '-')
    .replace(/\\/g, '\\\\')
    .replace(/\(/g, '\\(')
    .replace(/\)/g, '\\)');
}

function wrapLine(text, maxLen = 84) {
  const words = String(text || '').split(/\s+/);
  const lines = [];
  let current = '';
  for (const word of words) {
    if (!current) {
      current = word;
    } else if (current.length + 1 + word.length <= maxLen) {
      current += ` ${word}`;
    } else {
      lines.push(current);
      current = word;
    }
  }
  if (current) lines.push(current);
  return lines;
}

export function formatCarePlanLines({
  mother,
  screening,
  overallRisk,
  discordanceLabel,
  insights,
  recommendations,
  milestones,
  notes,
  includeNotes = true,
  summaryText,
  generatedDate,
}) {
  const rawLines = [
    'MIORA - MATERNAL EMOTIONAL INTELLIGENCE',
    'Personalized Maternal Care Plan',
    `Generated: ${generatedDate}`,
    '--------------------------------------------------------------------------------',
    `Mother ID: ${mother.id} (${mother.initials}) | Postpartum Week: Week ${mother.postpartumWeek}`,
    `Screening Ref: ${screening?.id || 'N/A'} | Last Screening: ${mother.lastScreeningDate}`,
    `Overall Risk: ${overallRisk} | Cross-Modal Discordance: ${discordanceLabel}`,
    '',
    '1. KEY SCREENING OBSERVATIONS (Assistive Signals Only)',
    ...insights.map((item) => `* ${item.text}`),
    '',
    '2. CARE RECOMMENDATIONS',
    ...recommendations.map((rec) => `* ${rec.title}: ${rec.description}`),
    '',
    '3. FOLLOW-UP TIMELINE',
    ...milestones.map(
      (ms) =>
        `* [${ms.completed ? 'Completed' : 'Scheduled'}] ${ms.timeframe} - ${ms.title}: ${ms.description} (${ms.clinician || 'Care Team'})`
    ),
    '',
    '4. CARE TEAM NOTES',
    ...(includeNotes
      ? [notes?.trim() ? notes.trim() : 'No clinician notes recorded.']
      : ['Clinician notes omitted based on privacy permissions.']),
    '',
    '5. CARE PLAN SUMMARY',
    summaryText,
    '',
    'RESPONSIBLE AI & CLINICAL SAFETY DISCLAIMER',
    'Miora does not diagnose postpartum depression. Screening observations are supportive',
    'indicators only and must not replace professional clinical judgement.',
  ];

  return rawLines.flatMap((line) => (line === '' ? [''] : wrapLine(line, 84)));
}

/**
 * Generates a valid single-page/multi-line PDF 1.4 binary Blob using pure JS
 * without introducing third-party PDF dependencies.
 */
export function buildCarePlanPdfBlob(doc) {
  const lines = formatCarePlanLines(doc).slice(0, 56);
  const contentOps = ['BT', '/F1 10 Tf', '48 760 Td', '13 TL'];
  lines.forEach((line, idx) => {
    const escaped = escapePdfText(line);
    if (idx === 0) {
      contentOps.push('/F2 13 Tf', `(${escaped}) Tj`, '/F1 10 Tf');
    } else {
      contentOps.push('T*', `(${escaped}) Tj`);
    }
  });
  contentOps.push('ET');
  const streamContent = contentOps.join('\n');

  const objects = [
    '1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n',
    '2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n',
    '3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> >>\nendobj\n',
    `4 0 obj\n<< /Length ${streamContent.length} >>\nstream\n${streamContent}\nendstream\nendobj\n`,
    '5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n',
    '6 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>\nendobj\n',
  ];

  let pdf = '%PDF-1.4\n';
  const offsets = [0];
  for (const obj of objects) {
    offsets.push(pdf.length);
    pdf += obj;
  }
  const xrefStart = pdf.length;
  pdf += `xref\n0 ${objects.length + 1}\n`;
  pdf += '0000000000 65535 f \n';
  for (let i = 1; i < offsets.length; i += 1) {
    pdf += `${String(offsets[i]).padStart(10, '0')} 00000 n \n`;
  }
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefStart}\n%%EOF`;

  return new Blob([pdf], { type: 'application/pdf' });
}

