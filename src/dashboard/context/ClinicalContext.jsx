import React, { createContext, useContext, useMemo, useState } from 'react';
import {
  CLINICAL_ALERTS,
  INITIAL_MOTHERS,
  INITIAL_SCREENINGS,
  KPI_TRENDS,
  RISK_COLORS,
  SCREENING_WEEKLY_RECORDS,
} from '../data/mockClinicalData.js';

const ClinicalContext = createContext(null);
const DRAFT_STORAGE_KEY = 'miora_live_screening_drafts_v1';
const UPLOAD_DRAFT_STORAGE_KEY = 'miora_upload_analyze_drafts_v1';
const CLINICAL_NOTES_STORAGE_KEY = 'miora_clinical_notes_v1';

function readStoredList(key) {
  try {
    if (typeof window === 'undefined' || !window.localStorage) return [];
    const raw = window.localStorage.getItem(key);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}
const CARE_PLAN_STORAGE_KEY = 'miora_care_plans_v1';

export const DEFAULT_FOLLOWUP_MILESTONES = [
  {
    id: 'ms-7d',
    timeframe: 'In 7 days',
    title: 'Follow-up screening',
    description: 'Reassess emotional wellbeing and available signals.',
    clinician: 'Dr. Elena Rostova',
    completed: false,
  },
  {
    id: 'ms-2w',
    timeframe: 'In 2 weeks',
    title: 'Clinical review',
    description: 'Discuss progress and ongoing concerns.',
    clinician: 'Dr. Elena Rostova',
    completed: false,
  },
  {
    id: 'ms-4w',
    timeframe: 'In 4 weeks',
    title: 'Re-evaluation',
    description: 'Review changes and adjust the care plan if appropriate.',
    clinician: 'Dr. Elena Rostova',
    completed: false,
  },
];

export const DEFAULT_INCLUDED_RECOMMENDATIONS = [
  'emotional-support',
  'counselling-referral',
  'wellbeing-practices',
];

function readStoredMap(key) {
  try {
    if (typeof window === 'undefined' || !window.localStorage) return {};
    const raw = window.localStorage.getItem(key);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function writeStoredMap(key, value) {
  try {
    if (typeof window === 'undefined' || !window.localStorage) return;
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Ignore storage quota or private-mode errors
  }
}

function formatInitials(rawName) {
  const parts = rawName.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return { initials: 'N. M.', avatarInitials: 'NM' };
  if (parts.length === 1) {
    const first = parts[0][0].toUpperCase();
    return { initials: `${first}.`, avatarInitials: first };
  }
  const first = parts[0][0].toUpperCase();
  const last = parts[parts.length - 1][0].toUpperCase();
  return {
    initials: `${first}. ${last}.`,
    avatarInitials: `${first}${last}`,
  };
}

export function ClinicalProvider({ children }) {
  const [mothers, setMothers] = useState(INITIAL_MOTHERS);
  const [screenings, setScreenings] = useState(INITIAL_SCREENINGS);
  const [weeklyRecords, setWeeklyRecords] = useState(SCREENING_WEEKLY_RECORDS);
  const [alerts, setAlerts] = useState(CLINICAL_ALERTS);
  const [isAddMotherOpen, setIsAddMotherOpen] = useState(false);
  const [screeningDrafts, setScreeningDrafts] = useState(() => readStoredMap(DRAFT_STORAGE_KEY));
  const [uploadDrafts, setUploadDrafts] = useState(() => readStoredMap(UPLOAD_DRAFT_STORAGE_KEY));
  const [carePlans, setCarePlans] = useState(() => readStoredMap(CARE_PLAN_STORAGE_KEY));
  const [caseShares, setCaseShares] = useState([]);
  const [selectedMotherId, setSelectedMotherId] = useState('M-108');
  const [clinicalNotes, setClinicalNotes] = useState(() =>
    readStoredList(CLINICAL_NOTES_STORAGE_KEY)
  );

  const metrics = useMemo(() => {
    const addedScreenings = screenings.filter(
      (s) => !INITIAL_SCREENINGS.some((init) => init.id === s.id)
    );
    const addedCompleted = addedScreenings.filter((s) => s.status === 'Completed').length;

    const registeredMothers = mothers.length;
    const activeCases = mothers.filter((m) => m.status !== 'Pending').length;
    const screeningsCompleted = 247 + addedCompleted;
    const casesForReview = mothers.filter(
      (m) => m.status === 'Review' || m.status === 'Follow-up'
    ).length;
    const highRiskCases = mothers.filter((m) => m.risk === 'High').length;
    const potentialDiscordance = mothers.filter((m) => m.discordanceFlag).length;

    // Risk distribution counts (exact initial baseline: 143, 49, 35, 20 = 247)
    const extraLow = addedCompleted ? addedScreenings.filter((s) => s.risk === 'Low').length : 0;
    const extraMod = addedCompleted ? addedScreenings.filter((s) => s.risk === 'Moderate').length : 0;
    const extraHigh = addedCompleted ? addedScreenings.filter((s) => s.risk === 'High').length : 0;
    const extraReview = addedCompleted
      ? addedScreenings.filter((s) => s.risk === 'Requires Review').length
      : 0;

    const rawCounts = [
      { key: 'Low Risk', count: 143 + extraLow, color: RISK_COLORS['Low Risk'] },
      { key: 'Moderate Risk', count: 49 + extraMod, color: RISK_COLORS['Moderate Risk'] },
      { key: 'High Risk', count: 35 + extraHigh, color: RISK_COLORS['High Risk'] },
      { key: 'Requires Review', count: 20 + extraReview, color: RISK_COLORS['Requires Review'] },
    ];

    const totalDistribution = rawCounts.reduce((acc, item) => acc + item.count, 0);
    const riskDistribution = rawCounts.map((item) => ({
      name: item.key,
      count: item.count,
      percentage: totalDistribution > 0 ? Math.round((item.count / totalDistribution) * 100) : 0,
      color: item.color,
    }));

    return {
      registeredMothers,
      activeCases,
      screeningsCompleted,
      casesForReview,
      highRiskCases,
      potentialDiscordance,
      trends: KPI_TRENDS,
      riskDistribution,
      totalDistribution,
    };
  }, [mothers, screenings]);

  const priorityCases = useMemo(() => {
    const explicitlyPrioritized = mothers.filter((m) => m.priority);
    if (explicitlyPrioritized.length >= 3) return explicitlyPrioritized;
    return mothers.filter(
      (m) => m.status === 'Review' || m.status === 'Follow-up' || m.status === 'Pending'
    );
  }, [mothers]);

  const addMother = ({ name, postpartumWeek, reasonForReview, risk = 'Low' }) => {
    const addedCount = mothers.length - INITIAL_MOTHERS.length;
    const nextNum = 118 + addedCount;
    const newId = `M-${nextNum}`;
    const { initials, avatarInitials } = formatInitials(name);
    const nowIso = new Date().toISOString();

    const newMother = {
      id: newId,
      name: name.trim(),
      initials,
      avatarInitials,
      postpartumWeek: Number(postpartumWeek) || 1,
      lastScreeningDate: 'Apr 25, 2026',
      lastScreeningIso: nowIso,
      status: risk === 'High' ? 'Review' : 'Pending',
      risk,
      reasonForReview: reasonForReview?.trim() || 'Initial postpartum intake',
      priority: true,
      discordanceFlag: false,
      discordanceType: null,
      epdsScore: risk === 'High' ? 14 : risk === 'Moderate' ? 9 : 4,
      lastScreeningTime: 'Just now',
      voiceCueSummary: 'Awaiting initial voice-assisted check-in.',
      textCueSummary: reasonForReview?.trim() || 'Newly registered mother.',
      carePlan: 'Schedule baseline Miora multimodal screening within 48 hours.',
    };
    setMothers((prev) => [newMother, ...prev]);
    setAlerts((prev) => [
      {
        id: `alert-${Date.now()}`,
        motherId: newId,
        title: `New mother ${newId} (${newMother.name}) registered`,
        time: 'Just now',
        severity: risk === 'High' ? 'high' : 'low',
      },
      ...prev,
    ]);
    return newMother;
  };

  const recordScreening = ({
    motherId,
    risk,
    modality,
    summary,
    epdsEquivalent,
    discordanceDetected,
    conversation,
    capturedModalities,
    durationSeconds,
    preliminaryScore,
    modalityContributions,
    indicators,
  }) => {
    const mother = mothers.find((m) => m.id === motherId);
    const cap = capturedModalities || { text: true, voice: false, video: false };
    const nowTime = new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
    const score = preliminaryScore ?? Number(((Number(epdsEquivalent) || 6) / 20).toFixed(2));
    const newScreening = {
      id: `SCR-${248 + (screenings.length - INITIAL_SCREENINGS.length)}`,
      motherId,
      motherName: mother?.name || motherId,
      motherInitials: mother?.initials || 'N. M.',
      postpartumWeek: mother?.postpartumWeek || 4,
      status: 'Completed',
      completedAgo: 'Just now',
      screeningDateTime: `Today · ${nowTime}`,
      risk,
      modality: modality || 'Multimodal (Text · Voice · Video)',
      combinedScore: score,
      epdsEquivalent: Number(epdsEquivalent) || 6,
      discordanceScore: discordanceDetected ? 0.72 : 0.14,
      preliminaryScore: preliminaryScore ?? null,
      capturedModalities: cap,
      modalities: {
        text: cap.text
          ? { status: 'completed', score: modalityContributions?.text ?? score }
          : { status: 'unavailable', score: null },
        voice: cap.voice
          ? { status: 'completed', score: modalityContributions?.voice ?? score }
          : { status: 'unavailable', score: null },
        video: cap.video
          ? { status: 'completed', score: modalityContributions?.video ?? score }
          : { status: 'unavailable', score: null },
      },
      riskHistory: [
        { week: `Week ${mother?.postpartumWeek || 4}`, score, label: risk },
      ],
      contributingFactors: (indicators || []).map((text, idx) => ({
        id: `cf-${Date.now()}-${idx}`,
        icon: idx === 0 ? 'alertTriangle' : idx === 1 ? 'waveform' : 'smile',
        text,
        severity: risk === 'High' ? 'High' : risk === 'Moderate' ? 'Moderate' : 'Low',
      })),
      interpretation: [
        summary || 'Completed clinician-assisted screening session.',
        !cap.voice || !cap.video
          ? 'Partial modality availability: missing channels were excluded and not treated as negative.'
          : 'All three screening modalities captured for multimodal review.',
        'Assistive screening indicators only; confirm with clinician judgment.',
      ],
      limitations:
        !cap.voice || !cap.video
          ? 'Some modalities were unavailable during this session.'
          : 'Assistive screening estimate; not a clinical diagnosis.',
      durationSeconds: durationSeconds || 0,
      conversation: conversation || [],
      summary,
    };
    setScreenings((prev) => [newScreening, ...prev]);
    setWeeklyRecords((prev) =>
      prev.map((w, idx) =>
        idx === prev.length - 1
          ? {
              ...w,
              screenings: w.screenings + 1,
              flagged: risk === 'High' || discordanceDetected ? w.flagged + 1 : w.flagged,
            }
          : w
      )
    );
    setMothers((prev) =>
      prev.map((m) =>
        m.id === motherId
          ? {
              ...m,
              risk,
              status: risk === 'High' ? 'Review' : discordanceDetected ? 'Follow-up' : 'Completed',
              discordanceFlag: Boolean(discordanceDetected) || m.discordanceFlag,
              lastScreeningTime: 'Just now',
              lastScreeningIso: new Date().toISOString(),
              textCueSummary: summary,
            }
          : m
      )
    );
    return newScreening;
  };

  const updateMotherStatus = (motherId, nextStatus) => {
    setMothers((prev) =>
      prev.map((m) => (m.id === motherId ? { ...m, status: nextStatus } : m))
    );
  };

  const saveScreeningDraft = (motherId, draftData) => {
    setScreeningDrafts((prev) => {
      const next = {
        ...prev,
        [motherId]: {
          ...draftData,
          savedAt: new Date().toISOString(),
        },
      };
      writeStoredMap(DRAFT_STORAGE_KEY, next);
      return next;
    });
  };

  const clearScreeningDraft = (motherId) => {
    setScreeningDrafts((prev) => {
      const next = { ...prev };
      delete next[motherId];
      writeStoredMap(DRAFT_STORAGE_KEY, next);
      return next;
    });
  };

  const saveUploadDraft = (motherId, draftData) => {
    setUploadDrafts((prev) => {
      const next = {
        ...prev,
        [motherId]: {
          ...draftData,
          savedAt: new Date().toISOString(),
        },
      };
      writeStoredMap(UPLOAD_DRAFT_STORAGE_KEY, next);
      return next;
    });
  };

  const clearUploadDraft = (motherId) => {
    setUploadDrafts((prev) => {
      const next = { ...prev };
      delete next[motherId];
      writeStoredMap(UPLOAD_DRAFT_STORAGE_KEY, next);
      return next;
    });
  };

  const shareCaseHandoff = ({ screeningId, motherId, recipientTeam, note, consentConfirmed }) => {
    if (!consentConfirmed) return null;
    const entry = {
      id: `SHARE-${Date.now()}`,
      screeningId,
      motherId,
      recipientTeam,
      note: note?.trim() || '',
      sharedAt: new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }),
    };
    setCaseShares((prev) => [entry, ...prev]);
    setAlerts((prev) => [
      {
        id: `alert-share-${Date.now()}`,
        motherId,
        title: `Case ${motherId} securely shared with ${recipientTeam}`,
        time: 'Just now',
        severity: 'low',
      },
      ...prev,
    ]);
    return entry;
  };

  const getCarePlan = (motherId) => {
    const existing = carePlans[motherId];
    return {
      notes: existing?.notes || '',
      notesSavedAt: existing?.notesSavedAt || null,
      milestones: existing?.milestones || DEFAULT_FOLLOWUP_MILESTONES,
      includedRecommendations:
        existing?.includedRecommendations || DEFAULT_INCLUDED_RECOMMENDATIONS,
      finalized: Boolean(existing?.finalized),
      finalizedAt: existing?.finalizedAt || null,
      summaryText: existing?.summaryText || '',
    };
  };

  const updateCarePlanField = (motherId, updater) => {
    setCarePlans((prev) => {
      const base = {
        notes: prev[motherId]?.notes || '',
        notesSavedAt: prev[motherId]?.notesSavedAt || null,
        milestones: prev[motherId]?.milestones || DEFAULT_FOLLOWUP_MILESTONES,
        includedRecommendations:
          prev[motherId]?.includedRecommendations || DEFAULT_INCLUDED_RECOMMENDATIONS,
        finalized: Boolean(prev[motherId]?.finalized),
        finalizedAt: prev[motherId]?.finalizedAt || null,
        summaryText: prev[motherId]?.summaryText || '',
      };
      const next = {
        ...prev,
        [motherId]: updater(base),
      };
      writeStoredMap(CARE_PLAN_STORAGE_KEY, next);
      return next;
    });
  };

  const saveCareNotes = (motherId, notes) => {
    if (notes.length > 500) {
      return { ok: false, error: 'Care team notes cannot exceed 500 characters.' };
    }
    const savedAt = new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
    updateCarePlanField(motherId, (base) => ({
      ...base,
      notes,
      notesSavedAt: savedAt,
    }));
    return { ok: true, savedAt };
  };

  const saveFollowUpMilestones = (motherId, milestones) => {
    updateCarePlanField(motherId, (base) => ({
      ...base,
      milestones,
    }));
  };

  const addScheduledFollowUp = (motherId, appointment) => {
    const newMilestone = {
      id: `ms-${Date.now()}`,
      timeframe: appointment.date,
      title: appointment.type,
      description: appointment.description,
      clinician: appointment.clinician,
      completed: false,
    };
    updateCarePlanField(motherId, (base) => ({
      ...base,
      milestones: [newMilestone, ...base.milestones],
    }));
    return newMilestone;
  };

  const toggleRecommendationInPlan = (motherId, recId) => {
    updateCarePlanField(motherId, (base) => {
      const exists = base.includedRecommendations.includes(recId);
      const nextList = exists
        ? base.includedRecommendations.filter((id) => id !== recId)
        : [...base.includedRecommendations, recId];
      return {
        ...base,
        includedRecommendations: nextList,
      };
    });
  };

  const finalizeCarePlan = (motherId, summaryText) => {
    const plan = getCarePlan(motherId);
    if (!motherId || plan.includedRecommendations.length === 0 || plan.milestones.length === 0) {
      return {
        ok: false,
        error:
          'Ensure at least one care recommendation and one follow-up milestone are included before finalizing.',
      };
    }
    const finalizedAt = new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
    updateCarePlanField(motherId, (base) => ({
      ...base,
      finalized: true,
      finalizedAt,
      summaryText,
    }));
    setMothers((prev) =>
      prev.map((m) =>
        m.id === motherId
          ? {
              ...m,
              carePlan: summaryText,
            }
          : m
      )
    );
    setAlerts((prev) => [
      {
        id: `alert-plan-${Date.now()}`,
        motherId,
        title: `Care plan finalized for ${motherId}`,
        time: 'Just now',
        severity: 'low',
      },
      ...prev,
    ]);
    return { ok: true, finalizedAt };
  };

  const addClinicalNote = ({ motherId, screeningId, note, category = 'Contextual Observation' }) => {
    const trimmed = note?.trim();
    if (!trimmed) return null;
    const entry = {
      id: `NOTE-${Date.now()}`,
      motherId,
      screeningId,
      category,
      note: trimmed,
      createdAt: new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }),
    };
    setClinicalNotes((prev) => {
      const next = [entry, ...prev];
      writeStoredMap(CLINICAL_NOTES_STORAGE_KEY, next);
      return next;
    });
    setAlerts((prev) => [
      {
        id: `alert-note-${Date.now()}`,
        motherId,
        title: `Contextual clinical note saved for ${motherId} (${screeningId})`,
        time: 'Just now',
        severity: 'low',
      },
      ...prev,
    ]);
    return entry;
  };

  const value = {
    mothers,
    screenings,
    weeklyRecords,
    alerts,
    metrics,
    priorityCases,
    screeningDrafts,
    uploadDrafts,
    carePlans,
    caseShares,
    selectedMotherId,
    setSelectedMotherId,
    clinicalNotes,
    addClinicalNote,
    isAddMotherOpen,
    setIsAddMotherOpen,
    addMother,
    recordScreening,
    updateMotherStatus,
    saveScreeningDraft,
    clearScreeningDraft,
    saveUploadDraft,
    clearUploadDraft,
    shareCaseHandoff,
    getCarePlan,
    saveCareNotes,
    saveFollowUpMilestones,
    addScheduledFollowUp,
    toggleRecommendationInPlan,
    finalizeCarePlan,
  };

  return <ClinicalContext.Provider value={value}>{children}</ClinicalContext.Provider>;
}

export function useClinicalData() {
  const ctx = useContext(ClinicalContext);
  if (!ctx) {
    throw new Error('useClinicalData must be used inside ClinicalProvider');
  }
  return ctx;
}
