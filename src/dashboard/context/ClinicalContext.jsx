import React, { createContext, useContext, useMemo, useState } from 'react';
import {
  BASELINE_COHORT,
  CLINICAL_ALERTS,
  INITIAL_MOTHERS,
  INITIAL_SCREENINGS,
  KPI_TRENDS,
  RISK_COLORS,
  SCREENING_WEEKLY_RECORDS,
} from '../data/mockClinicalData.js';

const ClinicalContext = createContext(null);

export function ClinicalProvider({ children }) {
  const [mothers, setMothers] = useState(INITIAL_MOTHERS);
  const [screenings, setScreenings] = useState(INITIAL_SCREENINGS);
  const [weeklyRecords, setWeeklyRecords] = useState(SCREENING_WEEKLY_RECORDS);
  const [alerts, setAlerts] = useState(CLINICAL_ALERTS);
  const [isAddMotherOpen, setIsAddMotherOpen] = useState(false);

  const metrics = useMemo(() => {
    const addedMothers = mothers.length - INITIAL_MOTHERS.length;
    const addedScreenings = screenings.filter(
      (s) => !INITIAL_SCREENINGS.some((init) => init.id === s.id)
    );
    const addedCompleted = addedScreenings.filter((s) => s.status === 'Completed').length;

    const registeredMothers = BASELINE_COHORT.additionalMothers + INITIAL_MOTHERS.length + addedMothers;
    const screeningsCompleted = 247 + addedCompleted;

    const initialReviewCount = INITIAL_MOTHERS.filter(
      (m) => m.status === 'Review' || m.status === 'Follow-up' || m.status === 'Pending'
    ).length;
    const currentReviewCount = mothers.filter(
      (m) => m.status === 'Review' || m.status === 'Follow-up' || m.status === 'Pending'
    ).length;
    const casesForReview = 18 + (currentReviewCount - initialReviewCount);

    const initialDiscordanceCount = INITIAL_MOTHERS.filter((m) => m.discordanceFlag).length;
    const currentDiscordanceCount = mothers.filter((m) => m.discordanceFlag).length;
    const potentialDiscordance = 7 + (currentDiscordanceCount - initialDiscordanceCount);

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
      screeningsCompleted,
      casesForReview,
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
    const nextNum = 118 + (mothers.length - INITIAL_MOTHERS.length);
    const newId = `M-${nextNum}`;
    const newMother = {
      id: newId,
      name: name.trim(),
      postpartumWeek: Number(postpartumWeek) || 1,
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

  const recordScreening = ({ motherId, risk, modality, summary, epdsEquivalent, discordanceDetected }) => {
    const mother = mothers.find((m) => m.id === motherId);
    const newScreening = {
      id: `SCR-${248 + (screenings.length - INITIAL_SCREENINGS.length)}`,
      motherId,
      motherName: mother?.name || motherId,
      postpartumWeek: mother?.postpartumWeek || 4,
      status: 'Completed',
      completedAgo: 'Just now',
      risk,
      modality: modality || 'Voice + Text',
      epdsEquivalent: Number(epdsEquivalent) || 6,
      discordanceScore: discordanceDetected ? 0.72 : 0.14,
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

  const value = {
    mothers,
    screenings,
    weeklyRecords,
    alerts,
    metrics,
    priorityCases,
    isAddMotherOpen,
    setIsAddMotherOpen,
    addMother,
    recordScreening,
    updateMotherStatus,
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

