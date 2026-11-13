import { analyzeCrossModalDiscordance } from './discordanceAnalysis.js';

export const NEXT_SCREENING_OPTIONS = [
  'In 7 days',
  'In 14 days',
  'In 4 weeks',
  'Within 48 hours',
  'Routine schedule',
];

export const CARE_ACTION_OPTIONS = [
  'Counselling referral',
  'Telehealth clinician check-in',
  'Perinatal specialist consult',
  'Supportive monitoring only',
];

export const ADDITIONAL_SUPPORT_OPTIONS = [
  'Emotional support & resources',
  'Peer support group',
  'Partner / family involvement',
  'Sleep & recovery guidance',
];

export function extractClinicalReviewSummary({ screening, mother }) {
  const discordanceAnalysis = analyzeCrossModalDiscordance({ screening });
  if (!screening || !discordanceAnalysis) {
    return null;
  }

  const modMap = Object.fromEntries(
    discordanceAnalysis.modalityRows.map((row) => [row.key, row])
  );

  const summaryRows = [
    {
      key: 'combined',
      icon: 'smile',
      label: 'Combined Risk Score',
      value: discordanceAnalysis.overallRisk.available
        ? `${discordanceAnalysis.overallRisk.score.toFixed(2)} (${discordanceAnalysis.overallRisk.category})`
        : 'Pending',
      tone:
        discordanceAnalysis.overallRisk.category === 'High'
          ? 'high'
          : discordanceAnalysis.overallRisk.category === 'Moderate'
            ? 'moderate'
            : discordanceAnalysis.overallRisk.available
              ? 'low'
              : 'muted',
    },
    {
      key: 'discordance',
      icon: 'bolt',
      label: 'Discordance Score',
      value: discordanceAnalysis.discordance.available
        ? `${discordanceAnalysis.discordance.score.toFixed(2)} (${discordanceAnalysis.discordance.category.replace(
            ' Discordance',
            ''
          )})`
        : 'Unavailable',
      tone:
        discordanceAnalysis.discordance.category === 'High Discordance'
          ? 'high'
          : discordanceAnalysis.discordance.category === 'Moderate Discordance'
            ? 'moderate'
            : discordanceAnalysis.discordance.available
              ? 'low'
              : 'muted',
    },
    {
      key: 'voice',
      icon: 'mic',
      label: 'Emotion (Voice)',
      value: modMap.voice?.isCompleted ? modMap.voice.score.toFixed(2) : 'Unavailable',
      tone: modMap.voice?.isCompleted ? modMap.voice.riskLevel.toLowerCase() : 'muted',
    },
    {
      key: 'video',
      icon: 'video',
      label: 'Facial Expression',
      value: modMap.video?.isCompleted ? modMap.video.score.toFixed(2) : 'Unavailable',
      tone: modMap.video?.isCompleted ? modMap.video.riskLevel.toLowerCase() : 'muted',
    },
    {
      key: 'text',
      icon: 'fileText',
      label: 'Self-report (Text)',
      value: modMap.text?.isCompleted ? modMap.text.score.toFixed(2) : 'Unavailable',
      tone: modMap.text?.isCompleted ? modMap.text.riskLevel.toLowerCase() : 'muted',
    },
  ];

  const factors = screening.contributingFactors || [];
  const findFactor = (icons) => factors.find((f) => icons.includes(f.icon));

  const evidenceItems = [];

  if (modMap.voice?.isCompleted) {
    const voiceFactor = findFactor(['waveform']);
    evidenceItems.push({
      key: 'voice',
      icon: 'mic',
      label: 'Voice',
      available: true,
      description:
        voiceFactor?.text ||
        mother?.voiceCueSummary ||
        `Acoustic indicators recorded (score ${modMap.voice.score.toFixed(2)}).`,
      meta: `Risk: ${modMap.voice.riskLevel} · Score ${modMap.voice.score.toFixed(2)}`,
    });
  } else {
    evidenceItems.push({
      key: 'voice',
      icon: 'micOff',
      label: 'Voice',
      available: false,
      description: 'Voice acoustic channel unavailable for this session; excluded from inference.',
      meta: 'Unavailable',
    });
  }

  if (modMap.video?.isCompleted) {
    const videoFactor = findFactor(['smile', 'video']);
    evidenceItems.push({
      key: 'facial',
      icon: 'video',
      label: 'Facial',
      available: true,
      description:
        videoFactor?.text ||
        `Facial affect indicators observed (score ${modMap.video.score.toFixed(2)}).`,
      meta: `Risk: ${modMap.video.riskLevel} · Score ${modMap.video.score.toFixed(2)}`,
    });
  } else {
    evidenceItems.push({
      key: 'facial',
      icon: 'videoOff',
      label: 'Facial',
      available: false,
      description: 'Optional facial video analysis not captured or consented in this session.',
      meta: 'Optional · Unavailable',
    });
  }

  if (modMap.text?.isCompleted) {
    const textFactor = findFactor(['alertTriangle']);
    evidenceItems.push({
      key: 'text',
      icon: 'fileText',
      label: 'Text',
      available: true,
      description:
        textFactor?.text ||
        mother?.textCueSummary ||
        `Self-report text signals processed (score ${modMap.text.score.toFixed(2)}).`,
      meta: `Risk: ${modMap.text.riskLevel} · Score ${modMap.text.score.toFixed(2)}`,
    });
  } else {
    evidenceItems.push({
      key: 'text',
      icon: 'fileText',
      label: 'Text',
      available: false,
      description: 'Self-report text channel unavailable for this session.',
      meta: 'Unavailable',
    });
  }

  const aiRisk = discordanceAnalysis.overallRisk.available
    ? `${discordanceAnalysis.overallRisk.category} Risk`
    : 'Pending Assessment';

  const discordanceBadgeLabel = discordanceAnalysis.discordance.available
    ? discordanceAnalysis.discordance.category.replace(' Discordance', '')
    : 'Unavailable';

  const screeningDateShort = screening.screeningDateTime
    ? screening.screeningDateTime.split('·')[0].trim()
    : mother?.lastScreeningDate || screening.completedAgo || '—';

  return {
    discordanceAnalysis,
    summaryRows,
    evidenceItems,
    aiRisk,
    aiRiskLevel: discordanceAnalysis.overallRisk.category || 'Pending',
    combinedScore: discordanceAnalysis.overallRisk.score,
    discordanceBadgeLabel,
    screeningDateShort,
  };
}

export function getAssessmentComparison({ aiRiskLevel, aiAvailable, clinicianRisk }) {
  if (!clinicianRisk) {
    return {
      status: 'pending',
      label: 'Pending Clinician Assessment',
      description: 'Select Low, Moderate, or High under Clinical Risk (Clinician) to compare.',
    };
  }
  if (!aiAvailable || !aiRiskLevel || aiRiskLevel === 'Pending') {
    return {
      status: 'different',
      label: 'Independent Clinician Assessment',
      description: 'AI overall assessment is pending; clinician judgment recorded independently.',
    };
  }
  if (clinicianRisk.toLowerCase() === aiRiskLevel.toLowerCase()) {
    return {
      status: 'agreement',
      label: 'Agreement',
      description: 'Clinician risk classification aligns with the AI screening indicator.',
    };
  }
  return {
    status: 'different',
    label: 'Different Assessment',
    description:
      'Independent clinician assessment differs from AI output; both assessments are preserved separately.',
  };
}

export function formatClinicalDecisionLabel(decision) {
  if (decision === 'agree') return 'Agree with AI assessment';
  if (decision === 'partial') return 'Partially agree (with notes)';
  if (decision === 'disagree') return 'Do not agree (specify reason)';
  return 'Not yet recorded';
}

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

export function buildClinicalNoteText({
  mother,
  screening,
  summary,
  savedReview,
  draftReview,
}) {
  if (!mother || !screening || !summary) return '';
  const activeReview = savedReview || draftReview || {};
  const isSaved = Boolean(savedReview?.finalizedAt);

  const lines = [
    'MIORA - CLINICAL REVIEW & ASSESSMENT NOTE',
    '==========================================',
    `Mother ID: ${mother.id} (${mother.initials || screening.motherInitials || '--'})`,
    `Postpartum Week: Week ${mother.postpartumWeek}`,
    `Screening Reference: ${screening.id} | Screening Date: ${screening.screeningDateTime || summary.screeningDateShort}`,
    `Case Status: ${mother.status} | Note Status: ${
      isSaved ? `Finalized (${savedReview.finalizedAt})` : 'Draft (Unsaved Review)'
    }`,
    '',
    'AI SCREENING SUMMARY (ASSISTIVE ONLY - PRESERVED INDEPENDENTLY)',
    ...summary.summaryRows.map((row) => `- ${row.label}: ${row.value}`),
    '',
    'MODALITY-SPECIFIC EVIDENCE',
    ...summary.evidenceItems.map(
      (ev) => `- ${ev.label} [${ev.meta}]: ${ev.description}`
    ),
    '',
    'CROSS-MODAL DISCORDANCE FINDINGS',
    `- Category: ${summary.discordanceAnalysis.discordance.category} (${
      summary.discordanceAnalysis.discordance.available
        ? summary.discordanceAnalysis.discordance.score.toFixed(2)
        : 'Unavailable'
    })`,
    `- Detail: ${summary.discordanceAnalysis.discordance.explanation}`,
    '',
    'INDEPENDENT CLINICIAN ASSESSMENT',
    `- Clinician-Selected Risk: ${
      activeReview.clinicianRisk ? `${activeReview.clinicianRisk} Risk` : 'Pending Selection'
    }`,
    `- Clinical Decision: ${formatClinicalDecisionLabel(activeReview.decision)}`,
    ...(activeReview.decisionReason?.trim()
      ? [`- Decision Rationale: ${activeReview.decisionReason.trim()}`]
      : []),
    `- Clinician Observations: ${
      activeReview.reviewNotes?.trim() || 'No clinician observations entered yet.'
    }`,
    '',
    'FOLLOW-UP & CARE PLAN RECOMMENDATIONS',
    `- Next Screening: ${activeReview.nextScreening || 'In 7 days'}`,
    `- Care Action: ${activeReview.careAction || 'Counselling referral'}`,
    `- Additional Support: ${activeReview.additionalSupport || 'Emotional support & resources'}`,
    '',
    'LIMITATIONS & RESPONSIBLE AI DISCLAIMER',
    `Limitations: ${summary.discordanceAnalysis.limitations}`,
    'Miora provides screening-support indicators only and does not diagnose postpartum',
    'depression or prescribe treatment. Clinicians retain full decision-making authority.',
  ];

  return lines.join('\n');
}

export function buildClinicalNotePdfBlob(params) {
  const reportText = buildClinicalNoteText(params);
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

