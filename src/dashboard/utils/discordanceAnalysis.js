/**
 * Cross-Modal Discordance Derivation & Responsible Clinical Guardrails
 *
 * Strictly separates:
 * 1. Overall Postpartum Risk (combinedScore / screening.risk)
 * 2. Individual Modality Risk (text, voice, video scores & classifications)
 * 3. Cross-Modal Discordance (divergence across completed modalities)
 * 4. Pairwise Signal Alignment (agreement between completed pairs)
 *
 * Never computes metrics requiring unavailable modalities and never infers deception
 * or intentional underreporting.
 */

const MODALITY_DEFS = [
  { key: 'text', name: 'Text', subLabel: 'Self-report', icon: 'fileText', optional: false },
  { key: 'voice', name: 'Voice', subLabel: 'Acoustic', icon: 'mic', optional: false },
  { key: 'video', name: 'Video', subLabel: 'Facial', icon: 'video', optional: true },
];

const PAIR_DEFS = [
  { key: 'text-voice', label: 'Text ↔ Voice', a: 'text', b: 'voice' },
  { key: 'text-video', label: 'Text ↔ Video', a: 'text', b: 'video' },
  { key: 'voice-video', label: 'Voice ↔ Video', a: 'voice', b: 'video' },
];

export function classifyModalityRisk(score) {
  if (typeof score !== 'number' || Number.isNaN(score)) return null;
  if (score >= 0.7) return 'High';
  if (score >= 0.45) return 'Moderate';
  return 'Low';
}

export function classifyDiscordanceScore(score) {
  if (typeof score !== 'number' || Number.isNaN(score)) return null;
  if (score >= 0.65) {
    return {
      category: 'High Discordance',
      severityBadge: 'Notable Difference',
      badgeTone: 'peach',
    };
  }
  if (score >= 0.3) {
    return {
      category: 'Moderate Discordance',
      severityBadge: 'Moderate Difference',
      badgeTone: 'peach',
    };
  }
  return {
    category: 'Low Discordance',
    severityBadge: 'Closely Aligned',
    badgeTone: 'green',
  };
}

function buildModalityRow(def, rawModality) {
  const status = rawModality?.status || 'unavailable';
  const score =
    status === 'completed' && typeof rawModality?.score === 'number' && !Number.isNaN(rawModality.score)
      ? Number(rawModality.score.toFixed(2))
      : null;
  const isCompleted = score !== null;
  const riskLevel = isCompleted
    ? rawModality?.riskLevel || classifyModalityRisk(score)
    : status === 'failed'
      ? 'Failed'
      : 'Unavailable';

  return {
    ...def,
    status,
    score,
    isCompleted,
    riskLevel,
  };
}

export function analyzeCrossModalDiscordance({ screening }) {
  if (!screening) {
    return null;
  }

  const rawModalities = screening.modalities || {};
  const modalityRows = MODALITY_DEFS.map((def) => buildModalityRow(def, rawModalities[def.key]));
  const modalityMap = Object.fromEntries(modalityRows.map((row) => [row.key, row]));

  const completedModalities = modalityRows.filter((row) => row.isCompleted);
  const missingModalities = modalityRows.filter((row) => !row.isCompleted);

  const highestModality = completedModalities.length
    ? completedModalities.reduce((top, item) => (item.score > top.score ? item : top), completedModalities[0])
    : null;
  const lowestModality = completedModalities.length
    ? completedModalities.reduce((low, item) => (item.score < low.score ? item : low), completedModalities[0])
    : null;

  // 1. Overall Postpartum Risk (kept explicitly distinct from Discordance)
  const hasOverallScore =
    typeof screening.combinedScore === 'number' && !Number.isNaN(screening.combinedScore);
  const overallRisk = {
    available: hasOverallScore,
    score: hasOverallScore ? Number(screening.combinedScore.toFixed(2)) : null,
    category: screening.risk || null,
  };

  // 2. Pairwise Signal Alignment
  const pairwiseAlignment = PAIR_DEFS.map((pair) => {
    const modA = modalityMap[pair.a];
    const modB = modalityMap[pair.b];
    const backendPair = screening.pairwiseAlignment?.[pair.key];

    if (backendPair && typeof backendPair.score === 'number') {
      const clamped = Number(Math.min(Math.max(backendPair.score, 0), 1).toFixed(2));
      return {
        key: pair.key,
        label: pair.label,
        available: true,
        score: clamped,
        delta: modA.isCompleted && modB.isCompleted ? Number(Math.abs(modA.score - modB.score).toFixed(2)) : null,
        metricType: backendPair.metricType || 'alignment',
        barPercent: Math.round(clamped * 100),
      };
    }

    if (!modA.isCompleted || !modB.isCompleted) {
      const missingNames = [!modA.isCompleted ? modA.name : null, !modB.isCompleted ? modB.name : null]
        .filter(Boolean)
        .join(' & ');
      return {
        key: pair.key,
        label: pair.label,
        available: false,
        score: null,
        delta: null,
        metricType: 'alignment',
        barPercent: 0,
        unavailableReason: `${missingNames} unavailable`,
      };
    }

    const delta = Number(Math.abs(modA.score - modB.score).toFixed(2));
    const alignmentScore = Number(Math.max(0, 1 - delta).toFixed(2));
    return {
      key: pair.key,
      label: pair.label,
      available: true,
      score: alignmentScore,
      delta,
      metricType: 'alignment',
      barPercent: Math.round(alignmentScore * 100),
    };
  });

  // 3. Cross-Modal Discordance Assessment
  const canAssessDiscordance = completedModalities.length >= 2;
  let discordance;

  if (!canAssessDiscordance) {
    discordance = {
      available: false,
      score: null,
      category: 'Unavailable',
      severityBadge: 'Insufficient Modalities',
      badgeTone: 'muted',
      explanation:
        'Cross-modal discordance requires at least two completed modalities. Unavailable channels are excluded and not treated as negative findings.',
    };
  } else {
    const rawScore =
      typeof screening.discordance?.score === 'number'
        ? screening.discordance.score
        : typeof screening.discordanceScore === 'number'
          ? screening.discordanceScore
          : Number((highestModality.score - lowestModality.score).toFixed(2));

    const score = Number(Math.min(Math.max(rawScore, 0), 1).toFixed(2));
    const classified = classifyDiscordanceScore(score);
    const category = screening.discordance?.category || classified.category;
    const severityBadge = screening.discordance?.severityBadge || classified.severityBadge;
    const badgeTone = classified.badgeTone;

    const textRow = modalityMap.text;
    const observedRows = completedModalities.filter((m) => m.key !== 'text');
    let explanation = screening.discordance?.explanation || '';

    if (!explanation) {
      if (category === 'Low Discordance') {
        explanation = `Observed signals across completed modalities (${completedModalities
          .map((m) => `${m.name} ${m.score.toFixed(2)}`)
          .join(', ')}) are closely aligned.`;
      } else if (textRow.isCompleted && observedRows.length > 0 && highestModality.key !== 'text') {
        explanation = `Self-reported text score (${textRow.score.toFixed(
          2
        )}) is lower than ${observedRows
          .map((m) => `${m.name.toLowerCase()} (${m.score.toFixed(2)})`)
          .join(' and ')} indicators, reflecting a divergence for contextual clinical review.`;
      } else if (textRow.isCompleted && observedRows.length > 0 && lowestModality.key !== 'text') {
        explanation = `Self-reported text score (${textRow.score.toFixed(
          2
        )}) exceeds ${lowestModality.name.toLowerCase()} (${lowestModality.score.toFixed(
          2
        )}) signals, warranting contextual discussion across channels.`;
      } else {
        explanation = `Completed modalities span from ${lowestModality.name} (${lowestModality.score.toFixed(
          2
        )}) to ${highestModality.name} (${highestModality.score.toFixed(
          2
        )}), indicating cross-modal variance for clinician review.`;
      }
    }

    discordance = {
      available: true,
      score,
      category,
      severityBadge,
      badgeTone,
      explanation,
    };
  }

  // 4. Key Observations (only from actual screening / mother outputs for completed channels)
  const observations = [];
  if (Array.isArray(screening.discordanceObservations) && screening.discordanceObservations.length > 0) {
    screening.discordanceObservations.forEach((item, idx) => {
      observations.push({
        id: item.id || `obs-backend-${idx}`,
        icon: item.icon || 'info',
        text: item.text,
        indicator: item.indicator || item.severity || null,
      });
    });
  } else if (canAssessDiscordance) {
    const channelEnabled = {
      alertTriangle: modalityMap.text.isCompleted,
      waveform: modalityMap.voice.isCompleted,
      smile: modalityMap.video.isCompleted,
    };
    (screening.contributingFactors || []).forEach((factor) => {
      const enabled = channelEnabled[factor.icon] ?? true;
      if (enabled) {
        observations.push({
          id: factor.id,
          icon: factor.icon === 'smile' ? 'video' : factor.icon || 'info',
          text: factor.text,
          indicator: factor.severity || null,
        });
      }
    });

    if (
      modalityMap.text.isCompleted &&
      highestModality &&
      highestModality.key !== 'text' &&
      highestModality.score - modalityMap.text.score >= 0.05 &&
      observations.length < 3
    ) {
      observations.push({
        id: `obs-gap-${screening.id}`,
        icon: 'info',
        text: `Self-reported text score (${modalityMap.text.score.toFixed(
          2
        )}) sits below ${highestModality.name.toLowerCase()} signal intensity (${highestModality.score.toFixed(2)}).`,
        indicator: discordance.category === 'High Discordance' ? 'High' : 'Moderate',
      });
    }
  }

  // 5. Clinical Interpretation (strictly non-diagnostic & never implies deception)
  const interpretation = [];
  if (!canAssessDiscordance) {
    interpretation.push(
      `Only ${completedModalities.length} screening modality (${completedModalities[0]?.name || 'None'}) was completed; cross-modal comparison is unavailable.`
    );
    interpretation.push(
      'Missing modalities are excluded rather than treated as negative findings; consider completing Voice or optional Video channels if consented.'
    );
  } else {
    const spread = Number((highestModality.score - lowestModality.score).toFixed(2));
    if (discordance.category === 'High Discordance' || discordance.category === 'Moderate Discordance') {
      interpretation.push(
        `${discordance.category} (${discordance.score.toFixed(
          2
        )}) detected across ${completedModalities.map((m) => m.name).join(', ')}, separate from ${overallRisk.available ? `${overallRisk.category} (${overallRisk.score.toFixed(2)}) overall risk` : 'overall risk assessment'
        }.`
      );
    } else {
      interpretation.push(
        `No meaningful cross-modal discordance detected (${discordance.score.toFixed(
          2
        )}); completed channels show closely aligned signal levels.`
      );
    }

    interpretation.push(
      `${highestModality.name} (${highestModality.score.toFixed(
        2
      )}) recorded higher strain indicators than ${lowestModality.name} (${lowestModality.score.toFixed(
        2
      )}; spread Δ ${spread.toFixed(2)}).`
    );

    interpretation.push(
      'Modalities can diverge due to situational fatigue, recording environment, or individual communication comfort; discordance is a supportive prompt for open clinical conversation, not a diagnosis.'
    );

    if (missingModalities.length > 0) {
      interpretation.push(
        `Partial modality coverage: ${missingModalities
          .map((m) => `${m.name}${m.optional ? ' (optional/consent-based)' : ''}`)
          .join(', ')} unavailable and excluded from comparisons.`
      );
    }
  }

  const limitations =
    screening.limitations ||
    (missingModalities.length > 0
      ? `Partial coverage (${missingModalities.map((m) => m.name).join(', ')} unavailable). Assistive screening signal only; not a diagnosis.`
      : 'Assistive screening indicator only; clinical judgment and maternal context are essential.');

  return {
    modalityRows,
    completedModalities,
    missingModalities,
    highestModality,
    lowestModality,
    overallRisk,
    pairwiseAlignment,
    discordance,
    observations,
    interpretation,
    limitations,
  };
}
