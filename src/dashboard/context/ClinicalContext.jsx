import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import {
  CLINICAL_ALERTS,
  INITIAL_MOTHERS,
  INITIAL_SCREENINGS,
  KPI_TRENDS,
  RISK_COLORS,
  SCREENING_WEEKLY_RECORDS,
} from '../data/mockClinicalData.js';
import { dashboardService } from '../services/dashboardService.js';

const ClinicalContext = createContext(null);
const DRAFT_STORAGE_KEY = 'miora_live_screening_drafts_v1';
const UPLOAD_DRAFT_STORAGE_KEY = 'miora_upload_analyze_drafts_v1';
const CLINICAL_NOTES_STORAGE_KEY = 'miora_clinical_notes_v1';
const CLINICAL_REVIEWS_STORAGE_KEY = 'miora_clinical_reviews_v1';
const REVIEW_DRAFTS_STORAGE_KEY = 'miora_clinical_review_drafts_v1';

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

function mapBackendMother(backendMother, screeningsForMother = []) {
  const { initials, avatarInitials } = formatInitials(backendMother.name || 'Mother');
  const latestScreening = screeningsForMother[0];
  const rawRisk = latestScreening?.risk_classification || 'low';
  const risk = rawRisk.charAt(0).toUpperCase() + rawRisk.slice(1);
  const status = risk === 'High' ? 'Review' : latestScreening ? 'Completed' : 'Pending';

  return {
    id: backendMother.id,
    name: backendMother.name,
    initials,
    avatarInitials,
    age: backendMother.age || 28,
    phone: backendMother.phone || '',
    email: backendMother.email || '',
    postpartumWeek: 4,
    lastScreeningDate: latestScreening ? new Date(latestScreening.screening_date).toLocaleDateString() : 'Pending',
    lastScreeningIso: latestScreening?.screening_date || backendMother.created_at,
    status,
    risk,
    reasonForReview: backendMother.notes || 'Routine postpartum screening',
    priority: risk === 'High' || Boolean(latestScreening?.q10_safety_alert),
    discordanceFlag: Boolean(latestScreening?.fusion_status === 'completed' && latestScreening?.multimodal_scores?.discordance_detected),
    discordanceType: null,
    epdsScore: latestScreening?.total_score ?? null,
    lastScreeningTime: latestScreening ? 'Recently' : 'Not screened yet',
    voiceCueSummary: 'Screening data synced with clinical database.',
    textCueSummary: backendMother.notes || 'Enrolled postpartum mother.',
    carePlan: 'Individualized care plan active.',
    isGenuineRecord: true,
  };
}

function mapBackendScreening(backendScreening, motherMap = {}) {
  const mother = motherMap[backendScreening.mother_id];
  const motherName = mother?.name || `Mother ${backendScreening.mother_id?.slice?.(0, 8) || ''}`;
  const { initials } = formatInitials(motherName);
  const score = backendScreening.total_score;
  const rawRisk = backendScreening.risk_classification || 'low';
  const risk = rawRisk.charAt(0).toUpperCase() + rawRisk.slice(1);

  return {
    id: backendScreening.id,
    motherId: backendScreening.mother_id,
    motherName,
    motherInitials: initials,
    postpartumWeek: 4,
    status: backendScreening.screening_status === 'completed' ? 'Completed' : 'Requires Review',
    completedAgo: 'Persisted in database',
    screeningDateTime: new Date(backendScreening.screening_date).toLocaleString([], {
      dateStyle: 'medium',
      timeStyle: 'short',
    }),
    risk,
    modality: backendScreening.instrument || 'Multimodal (EPDS · Clinical Numerical · Text)',
    combinedScore: Number(((score || 0) / 30).toFixed(2)),
    epdsEquivalent: score,
    discordanceScore: backendScreening.multimodal_scores?.discordance_score || 0.1,
    q10SafetyAlert: backendScreening.q10_safety_alert,
    modalities: backendScreening.modality_status || { text: { status: 'completed' } },
    riskHistory: [
      { week: 'Week 4', score: Number(((score || 0) / 30).toFixed(2)), label: risk },
    ],
    contributingFactors: [],
    interpretation: [
      `EPDS Score: ${score}/30 (${risk} risk tier).`,
      backendScreening.q10_safety_alert ? 'SAFETY ALERT: Item 10 affirmative self-harm response.' : 'No self-harm ideation reported on Question 10.',
      'Persisted directly in clinical database.',
    ],
    limitations: 'Screening support only; confirm with clinical evaluation.',
    durationSeconds: 120,
    conversation: [],
    summary: backendScreening.notes || 'Standard clinical screening session',
    isGenuineRecord: true,
  };
}

function mapBackendAlert(alert) {
  return {
    id: alert.alert_id,
    motherId: alert.mother_id,
    title: alert.description || `${alert.alert_type} for ${alert.mother_name}`,
    time: new Date(alert.timestamp).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }),
    severity: alert.severity === 'critical' || alert.severity === 'high' ? 'high' : 'low',
    alertType: alert.alert_type,
    isGenuineRecord: true,
  };
}

function mapBackendActivity(activityData) {
  if (!activityData?.data || activityData.data.length === 0) return null;
  return activityData.data.map((dp, idx) => ({
    id: `w-${idx + 1}`,
    week: `Week ${idx + 1}`,
    dateRange: `${dp.period_start} - ${dp.period_end}`,
    screenings: dp.screening_count,
    flagged: dp.flagged_count || 0,
    isGenuineRecord: true,
  }));
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
  const [clinicalReviews, setClinicalReviews] = useState(() =>
    readStoredMap(CLINICAL_REVIEWS_STORAGE_KEY)
  );
  const [reviewDrafts, setReviewDrafts] = useState(() =>
    readStoredMap(REVIEW_DRAFTS_STORAGE_KEY)
  );

  const [backendStatus, setBackendStatus] = useState('connecting');
  const [isDemoData, setIsDemoData] = useState(true);
  const [backendMetrics, setBackendMetrics] = useState(null);

  // Sync data with backend on mount
  useEffect(() => {
    let isMounted = true;
    async function syncBackend() {
      try {
        const [metricsRes, activityRes, alertsRes, mothersRes, screeningsRes] =
          await Promise.allSettled([
            dashboardService.getMetrics(),
            dashboardService.getScreeningActivity('4w'),
            dashboardService.getAlerts(),
            dashboardService.getMothers(0, 100),
            dashboardService.getScreenings(0, 100),
          ]);

        if (!isMounted) return;

        let hasGenuineData = false;

        // Metrics
        if (metricsRes.status === 'fulfilled' && metricsRes.value) {
          setBackendMetrics(metricsRes.value);
          setBackendStatus('connected');
          if (metricsRes.value.total_mothers > 0 || metricsRes.value.total_screenings > 0) {
            hasGenuineData = true;
          }
        }

        // Mothers
        if (mothersRes.status === 'fulfilled' && Array.isArray(mothersRes.value) && mothersRes.value.length > 0) {
          hasGenuineData = true;
          const screeningsList = screeningsRes.status === 'fulfilled' && Array.isArray(screeningsRes.value) ? screeningsRes.value : [];
          const mappedMothers = mothersRes.value.map((bm) => {
            const mScreenings = screeningsList.filter((s) => s.mother_id === bm.id);
            return mapBackendMother(bm, mScreenings);
          });
          setMothers(mappedMothers);
          if (mappedMothers[0]?.id) {
            setSelectedMotherId(mappedMothers[0].id);
          }
        }

        // Screenings
        if (screeningsRes.status === 'fulfilled' && Array.isArray(screeningsRes.value) && screeningsRes.value.length > 0) {
          hasGenuineData = true;
          const motherMap = {};
          if (mothersRes.status === 'fulfilled' && Array.isArray(mothersRes.value)) {
            mothersRes.value.forEach((m) => { motherMap[m.id] = m; });
          }
          const mappedScreenings = screeningsRes.value.map((bs) => mapBackendScreening(bs, motherMap));
          setScreenings(mappedScreenings);
        }

        // Alerts
        if (alertsRes.status === 'fulfilled' && alertsRes.value?.alerts?.length > 0) {
          const mappedAlerts = alertsRes.value.alerts.map(mapBackendAlert);
          setAlerts(mappedAlerts);
        }

        // Activity
        if (activityRes.status === 'fulfilled' && activityRes.value?.data?.length > 0) {
          const mappedActivity = mapBackendActivity(activityRes.value);
          if (mappedActivity) {
            setWeeklyRecords(mappedActivity);
          }
        }

        if (hasGenuineData) {
          setIsDemoData(false);
        }
      } catch (err) {
        if (isMounted) {
          setBackendStatus('offline');
        }
      }
    }

    syncBackend();
    return () => { isMounted = false; };
  }, []);

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

  const addMother = ({ name, age, phone, email, postpartumWeek, reasonForReview, risk = 'Low' }) => {
    const trimmedName = name.trim();
    const { initials, avatarInitials } = formatInitials(trimmedName);
    const nowIso = new Date().toISOString();
    const nextNum = 118 + (mothers.length - INITIAL_MOTHERS.length);
    const newId = `M-${nextNum}`;
    const newMother = {
      id: newId,
      name: trimmedName,
      initials,
      avatarInitials,
      age: age ? Number(age) : 28,
      phone: phone || '',
      email: email || '',
      postpartumWeek: Number(postpartumWeek) || 1,
      lastScreeningDate: 'Just registered',
      lastScreeningIso: nowIso,
      status: risk === 'High' ? 'Review' : 'Pending',
      risk,
      reasonForReview: reasonForReview?.trim() || 'Initial postpartum intake',
      priority: risk === 'High',
      discordanceFlag: false,
      discordanceType: null,
      epdsScore: risk === 'High' ? 14 : risk === 'Moderate' ? 9 : 4,
      lastScreeningTime: 'Just now',
      voiceCueSummary: 'Awaiting initial check-in.',
      textCueSummary: reasonForReview?.trim() || 'Newly registered mother.',
      carePlan: 'Schedule baseline Miora multimodal screening within 48 hours.',
      isGenuineRecord: true,
    };
    setMothers((prev) => [newMother, ...prev]);
    setSelectedMotherId(newId);
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

    // Background sync to backend EHR if available
    dashboardService.createMother({
      name: trimmedName,
      age: age ? Number(age) : 28,
      phone: phone || null,
      email: email || null,
      notes: reasonForReview || null,
    }).catch((err) => {
      console.warn('Mother created locally (backend offline or notice):', err.message);
    });

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
    const isQ10Alert = risk === 'High' && Number(epdsEquivalent) >= 15;
    const newId = `SCR-${248 + (screenings.length - INITIAL_SCREENINGS.length)}`;
    const newScreening = {
      id: newId,
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
      isGenuineRecord: true,
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

    // Background sync to backend EHR if motherId is UUID
    if (motherId && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(motherId)) {
      dashboardService.persistScreening({
        mother_id: motherId,
        instrument: 'EPDS',
        total_score: Number(epdsEquivalent) || 6,
        risk_classification: (risk || 'low').toLowerCase(),
        q10_safety_alert: isQ10Alert,
        submitted_answers: { EPDS_Q01: 1 },
        item_scores: { EPDS_Q01: 1 },
        modality_status: {
          text: cap.text ? 'completed' : 'unavailable',
          audio: cap.voice ? 'completed' : 'unavailable',
          video: cap.video ? 'completed' : 'unavailable',
        },
        multimodal_scores: {
          fused_score: score,
          discordance_detected: Boolean(discordanceDetected),
        },
        notes: summary || 'Clinician screening session',
      }).catch((err) => {
        console.warn('Screening recorded in local state (backend notice):', err.message);
      });
    }

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

    if (screeningId && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(screeningId)) {
      dashboardService.handoffScreening(screeningId, {
        recipient_team: recipientTeam,
        handoff_notes: note?.trim() || 'Clinical handoff',
        consent_confirmed: true,
      }).catch((err) => {
        console.warn('Handoff audit event saved locally (backend notice):', err.message);
      });
    }

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

    if (/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(motherId)) {
      dashboardService.upsertCarePlan(motherId, {
        status: 'active',
        goals: plan.includedRecommendations,
        actions: plan.milestones.map((m) => m.title),
        scheduled_follow_ups: plan.milestones.map((m) => ({
          date: m.timeframe,
          type: m.title,
          clinician: m.clinician,
        })),
        notes: plan.notes || summaryText || 'Care plan finalized',
      }).catch((err) => {
        console.warn('Care plan preserved locally (backend upsert notice):', err.message);
      });
    }

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

  const saveReviewDraft = (motherId, draft) => {
    setReviewDrafts((prev) => {
      const next = {
        ...prev,
        [motherId]: {
          ...draft,
          updatedAt: new Date().toISOString(),
        },
      };
      writeStoredMap(REVIEW_DRAFTS_STORAGE_KEY, next);
      return next;
    });
  };

  const saveFinalClinicalReview = async ({
    motherId,
    screeningId,
    aiAssessment,
    clinicianAssessment,
    followUpPlan,
    persistenceMode = 'local',
  }) => {
    const finalizedAt = new Date().toLocaleTimeString([], {
      hour: 'numeric',
      minute: '2-digit',
    });

    let persistedReview = null;
    if (motherId && screeningId &&
        /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(motherId) &&
        /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(screeningId)) {
      try {
        persistedReview = await dashboardService.createClinicalReview({
          mother_id: motherId,
          screening_id: screeningId,
          clinician_name: clinicianAssessment?.clinicianName || 'Attending Clinician',
          clinician_risk_tier: (clinicianAssessment?.risk || 'moderate').toLowerCase(),
          clinical_summary: clinicianAssessment?.reviewNotes || 'Final clinical review',
          action_recommended: followUpPlan?.careAction || 'Routine follow-up',
          required_immediate_escalation: clinicianAssessment?.risk === 'High',
        });
      } catch (err) {
        console.warn('Clinical review saved locally (backend notice):', err.message);
      }
    }

    const record = {
      id: persistedReview?.id || `REV-${Date.now()}`,
      motherId,
      screeningId,
      aiAssessment,
      clinicianAssessment,
      followUpPlan,
      persistenceMode: persistedReview ? 'remote' : persistenceMode,
      finalizedAt,
      createdAtIso: new Date().toISOString(),
      isGenuineRecord: Boolean(persistedReview),
    };

    setClinicalReviews((prev) => {
      const existingHistory = Array.isArray(prev[motherId]?.history)
        ? prev[motherId].history
        : prev[motherId]?.id
          ? [prev[motherId]]
          : [];
      const next = {
        ...prev,
        [motherId]: {
          ...record,
          history: [record, ...existingHistory],
        },
      };
      writeStoredMap(CLINICAL_REVIEWS_STORAGE_KEY, next);
      return next;
    });

    setReviewDrafts((prev) => {
      const next = { ...prev };
      delete next[motherId];
      writeStoredMap(REVIEW_DRAFTS_STORAGE_KEY, next);
      return next;
    });

    const nextMotherStatus =
      clinicianAssessment.risk === 'High'
        ? 'Review'
        : clinicianAssessment.risk === 'Moderate'
          ? 'Follow-up'
          : 'Completed';

    setMothers((prev) =>
      prev.map((m) =>
        m.id === motherId
          ? {
              ...m,
              status: nextMotherStatus,
              carePlan: `${followUpPlan.nextScreening} · ${followUpPlan.careAction} (${followUpPlan.additionalSupport})`,
            }
          : m
      )
    );

    updateCarePlanField(motherId, (base) => {
      const nextMilestone = {
        id: `ms-rev-${Date.now()}`,
        timeframe: followUpPlan.nextScreening,
        title: followUpPlan.careAction,
        description: `${followUpPlan.additionalSupport} (confirmed via clinical review).`,
        clinician: 'Clinician Review Team',
        completed: false,
      };
      return {
        ...base,
        notes: clinicianAssessment.reviewNotes,
        notesSavedAt: finalizedAt,
        finalized: true,
        finalizedAt,
        milestones: [nextMilestone, ...base.milestones],
        summaryText: `Clinical review finalized (${clinicianAssessment.risk} clinical risk): ${followUpPlan.careAction} and ${followUpPlan.additionalSupport} planned with next screening ${followUpPlan.nextScreening}.`,
      };
    });

    setAlerts((prev) => [
      {
        id: `alert-rev-${Date.now()}`,
        motherId,
        title: `Clinical review finalized for ${motherId} (${clinicianAssessment.risk} clinical risk)`,
        time: 'Just now',
        severity: clinicianAssessment.risk === 'High' ? 'high' : 'low',
      },
      ...prev,
    ]);

    return record;
  };

  const value = {
    backendStatus,
    isDemoData,
    backendMetrics,
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
    clinicalReviews,
    reviewDrafts,
    saveReviewDraft,
    saveFinalClinicalReview,
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
