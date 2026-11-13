/**
 * Generates formatted text & pure-JS PDF 1.4 binary exports for
 * Miora Screen 06: Cross-Modal Discordance reports.
 */

function escapePdfText(str) {
  return String(str || '')
    .replace(/<->/g, '<->')
    .replace(/\u2194/g, '<->')
    .replace(/\u2206|\u0394/g, 'Delta ')
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

export function buildDiscordanceReportText({ screening, mother, analysis, notes = [] }) {
  if (!screening || !analysis) return '';

  const lines = [
    'MIORA - CROSS-MODAL DISCORDANCE REPORT',
    '========================================',
    `Screening ID: ${screening.id}`,
    `Mother ID: ${screening.motherId} (${screening.motherInitials || mother?.initials || '--'})`,
    `Postpartum Week: Week ${screening.postpartumWeek}`,
    `Screening Type: ${screening.modality}`,
    `Screening Date: ${screening.screeningDateTime || screening.completedAgo}`,
    `Status: ${screening.status}`,
    '',
    'SEPARATE ASSESSMENT METRICS',
    `- Overall Postpartum Risk: ${
      analysis.overallRisk.available
        ? `${analysis.overallRisk.score.toFixed(2)} / 1.00 (${analysis.overallRisk.category} Risk)`
        : 'Pending / Unavailable'
    }`,
    `- Cross-Modal Discordance Score: ${
      analysis.discordance.available
        ? `${analysis.discordance.score.toFixed(2)} (${analysis.discordance.category} - ${analysis.discordance.severityBadge})`
        : 'Unavailable (requires >= 2 completed modalities)'
    }`,
    `  Summary: ${analysis.discordance.explanation}`,
    '',
    'MODALITY COMPARISON',
    ...analysis.modalityRows.map(
      (row) =>
        `- ${row.name} (${row.subLabel}): ${
          row.isCompleted ? `${row.score.toFixed(2)} [${row.riskLevel}]` : row.riskLevel
        }`
    ),
    '',
    'PAIRWISE SIGNAL ALIGNMENT (0.00 = high divergence, 1.00 = closely aligned)',
    ...analysis.pairwiseAlignment.map((pair) =>
      pair.available
        ? `- ${pair.label}: ${pair.score.toFixed(2)} (Score Difference Delta ${pair.delta.toFixed(2)})`
        : `- ${pair.label}: Unavailable (${pair.unavailableReason})`
    ),
    '',
    'KEY OBSERVATIONS',
    ...(analysis.observations.length > 0
      ? analysis.observations.map(
          (obs) => `- ${obs.indicator ? `[${obs.indicator}] ` : ''}${obs.text}`
        )
      : ['- No cross-modal observations generated for this session.']),
    '',
    'CLINICAL INTERPRETATION & LIMITATIONS',
    ...analysis.interpretation.map((item) => `- ${item}`),
    `Limitations: ${analysis.limitations}`,
    '',
    'CONTEXTUAL CLINICIAN NOTES',
    ...(notes.length > 0
      ? notes.map((n) => `- [${n.category || 'Contextual Note'} · ${n.createdAt}] ${n.note}`)
      : ['- No contextual clinician notes recorded for this session.']),
    '',
    'RESPONSIBLE AI & CLINICAL SAFETY DISCLAIMER',
    'Discordance is a supportive signal requiring contextual clinician review, not a clinical',
    'diagnosis and not proof of concealment or intentional underreporting.',
  ];

  return lines.join('\n');
}

export function buildDiscordancePdfBlob({ screening, mother, analysis, notes = [] }) {
  const reportText = buildDiscordanceReportText({ screening, mother, analysis, notes });
  const rawLines = reportText.split('\n');
  const wrappedLines = rawLines
    .flatMap((line) => (line === '' ? [''] : wrapLine(line, 84)))
    .slice(0, 56);

  const contentOps = ['BT', '/F1 10 Tf', '48 760 Td', '13 TL'];
  wrappedLines.forEach((line, idx) => {
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

