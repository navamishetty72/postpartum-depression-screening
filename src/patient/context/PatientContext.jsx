import React, { createContext, useContext, useState, useMemo } from 'react';
import { getCurrentUser } from '../../auth/authService.js';

const PatientContext = createContext(null);

export const DEFAULT_PATIENT = {
  id: 'P-101',
  name: 'Amara',
  fullName: 'Amara Wilson',
  email: 'amara@miora.health',
  avatarInitials: 'A',
  postpartumWeek: 4,
};

export const DEFAULT_SCREENING = {
  id: 'SCR-2026-1117',
  date: '17 Nov 2026',
  completedDateTime: '17 Nov 2026 · 10:28 AM',
  riskScore: 64,
  riskLabel: 'Moderate Risk for PPD',
  summary:
    'Some signs of postpartum depression were observed. We recommend consulting a healthcare professional.',
  trend: [
    { week: 'Week 1', score: 42 },
    { week: 'Week 2', score: 50 },
    { week: 'Week 3', score: 58 },
    { week: 'Week 4', score: 64 },
  ],
  insights: {
    mood: 'Low to moderate',
    sleep: 'Disturbed',
    stress: 'Elevated',
    support: 'Recommended',
  },
  assessmentSummary: {
    emotionalSigns: 68,
    cognitiveSigns: 62,
    behaviouralSigns: 58,
    physicalIndicators: 46,
  },
  reports: [
    {
      id: 'rep-pdf',
      title: 'Screening Report',
      format: '.pdf',
      size: '2.4 MB',
      type: 'pdf',
      authorized: true,
      mimeType: 'application/pdf',
      filename: 'Miora_Screening_Report_17Nov2026.pdf',
    },
    {
      id: 'rep-txt',
      title: 'Conversation Transcript',
      format: '.txt',
      size: '24 KB',
      type: 'txt',
      authorized: true,
      mimeType: 'text/plain',
      filename: 'Miora_Conversation_Transcript_17Nov2026.txt',
    },
    {
      id: 'rep-wav',
      title: 'Audio Recording',
      format: '.wav',
      size: '7.8 MB',
      type: 'wav',
      authorized: true,
      mimeType: 'audio/wav',
      filename: 'Miora_Audio_Session_17Nov2026.wav',
    },
    {
      id: 'rep-mp4',
      title: 'Video Recording',
      format: '.mp4',
      size: '48.2 MB',
      type: 'mp4',
      authorized: true,
      mimeType: 'video/mp4',
      filename: 'Miora_Video_Session_17Nov2026.mp4',
    },
  ],
  nextSteps: [
    {
      id: 'step-consultation',
      title: 'Book a follow-up consultation',
      type: 'consultation',
      link: '/patient/connect-doctor',
    },
    {
      id: 'step-careplan',
      title: 'Try recommended self-care plan',
      type: 'careplan',
      link: '/patient/care-suggestions',
    },
    {
      id: 'step-retake',
      title: 'Retake screening (in 2 weeks)',
      type: 'screening',
      link: '/patient/ai-screening',
    },
  ],
};

export const INITIAL_NOTIFICATIONS = [
  {
    id: 'n-1',
    title: 'Screening Report Available',
    message: 'Your AI screening report for 17 Nov 2026 is ready to review and download.',
    date: '17 Nov 2026',
    read: false,
  },
  {
    id: 'n-2',
    title: 'Consultation Reminder',
    message: 'Follow-up with Dr. Elena Rostova is recommended within 7 days.',
    date: '16 Nov 2026',
    read: false,
  },
];

export const INITIAL_CONSULTATIONS = [
  {
    id: 'c-101',
    doctorName: 'Dr. Elena Rostova',
    role: 'Perinatal Psychiatry Lead',
    date: '20 Nov 2026',
    time: '11:00 AM',
    status: 'Scheduled',
    type: 'Telehealth Video',
    clinic: 'Miora Maternal Care Unit',
  },
  {
    id: 'c-100',
    doctorName: 'Dr. Elena Rostova',
    role: 'Perinatal Psychiatry Lead',
    date: '03 Nov 2026',
    time: '02:30 PM',
    status: 'Completed',
    type: 'Audio Consult',
    clinic: 'Miora Maternal Care Unit',
    summary: 'Reviewed postpartum baseline and sleep hygiene support.',
  },
];

export const DEFAULT_CARE_PLAN = {
  duration: '2 Weeks',
  totalDays: 14,
  currentDay: 1,
  focusAreas: ['Mood', 'Sleep', 'Stress', 'Support'],
  tasks: [
    { id: 'task-1', title: 'Breathing exercise', completed: true },
    { id: 'task-2', title: 'Mood check-in', completed: true },
    { id: 'task-3', title: 'Sleep routine', completed: true },
    { id: 'task-4', title: 'Journaling', completed: false },
    { id: 'task-5', title: 'Light activity', completed: false },
    { id: 'task-6', title: 'Self-care time', completed: false },
    { id: 'task-7', title: 'Reflection', completed: false },
  ],
};

export function PatientProvider({ children }) {
  const [patient, setPatient] = useState(() => {
    try {
      const authUser = getCurrentUser();
      if (authUser && authUser.role === 'patient') {
        const parts = (authUser.name || 'Amara Wilson').trim().split(/\s+/);
        const firstName = parts[0] || 'Amara';
        return {
          id: authUser.id || 'P-101',
          name: firstName,
          fullName: authUser.name || 'Amara Wilson',
          email: authUser.email || 'amara@miora.health',
          avatarInitials: firstName[0]?.toUpperCase() || 'A',
          postpartumWeek: authUser.postpartumWeek || 4,
        };
      }
    } catch {
      // ignore
    }
    return DEFAULT_PATIENT;
  });
  const [screening, setScreening] = useState(DEFAULT_SCREENING);
  const [notifications, setNotifications] = useState(INITIAL_NOTIFICATIONS);
  const [consultations] = useState(INITIAL_CONSULTATIONS);
  const [downloadToast, setDownloadToast] = useState(null);
  const [carePlan, setCarePlan] = useState(() => {
    try {
      const saved = localStorage.getItem('miora_care_plan_v1');
      if (saved) return JSON.parse(saved);
    } catch {
      // ignore
    }
    return DEFAULT_CARE_PLAN;
  });

  const toggleCareTask = (taskId) => {
    setCarePlan((prev) => {
      const updated = {
        ...prev,
        tasks: (prev.tasks || DEFAULT_CARE_PLAN.tasks).map((t) =>
          t.id === taskId ? { ...t, completed: !t.completed } : t
        ),
      };
      try {
        localStorage.setItem('miora_care_plan_v1', JSON.stringify(updated));
      } catch {
        // ignore
      }
      return updated;
    });
  };

  const markNotificationRead = (id) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
  };

  const markAllNotificationsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  // Secure report download action respecting authorization
  const downloadReport = (report) => {
    if (!report) return { success: false, error: 'No report selected' };

    // Authorization check
    if (!report.authorized) {
      const errorMsg = 'Access Denied: You are not authorized to download this file.';
      setDownloadToast({ type: 'error', message: errorMsg });
      setTimeout(() => setDownloadToast(null), 4000);
      return { success: false, error: errorMsg };
    }

    try {
      let content = '';
      if (report.type === 'pdf') {
        content = `%PDF-1.4\n% Miora Maternal Emotional Intelligence Report\n% Patient: ${patient.fullName} (${patient.id})\n% Screening Date: ${screening.date}\n% Risk Score: ${screening.riskScore}% (${screening.riskLabel})\n% Summary: ${screening.summary}\n%%EOF`;
      } else if (report.type === 'txt') {
        content = `MIORA SCREENING CONVERSATION TRANSCRIPT\nDate: ${screening.date}\nPatient: ${patient.fullName}\n\n[10:24 AM] Miora AI: Hi Amara! I'm Miora, your AI screening companion.\n[10:24 AM] Amara: Yes, we can start.\n[10:25 AM] Miora AI: In the past two weeks, how often have you felt low, sad, or hopeless?\n[10:25 AM] Amara: I've been feeling a bit low almost every day.\n`;
      } else if (report.type === 'wav') {
        content = 'RIFF....WAVEfmt ....data....Miora Audio Session Mock Data';
      } else {
        content = 'ftypisom....moov....Miora Video Recording Mock Data';
      }

      const blob = new Blob([content], { type: report.mimeType || 'application/octet-stream' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = report.filename || `${report.title.replace(/\s+/g, '_')}${report.format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      const msg = `Downloaded ${report.title} (${report.format.toUpperCase()})`;
      setDownloadToast({ type: 'success', message: msg });
      setTimeout(() => setDownloadToast(null), 3500);
      return { success: true };
    } catch (err) {
      const errorMsg = 'An error occurred while downloading the file.';
      setDownloadToast({ type: 'error', message: errorMsg });
      setTimeout(() => setDownloadToast(null), 4000);
      return { success: false, error: errorMsg };
    }
  };

  const value = useMemo(
    () => ({
      patient,
      screening,
      setScreening,
      notifications,
      markNotificationRead,
      markAllNotificationsRead,
      consultations,
      downloadReport,
      downloadToast,
      setDownloadToast,
      carePlan,
      setCarePlan,
      toggleCareTask,
    }),
    [patient, screening, notifications, consultations, downloadToast, carePlan]
  );

  return <PatientContext.Provider value={value}>{children}</PatientContext.Provider>;
}

export function usePatient() {
  const context = useContext(PatientContext);
  if (!context) {
    // Provide sensible default fallback if used outside provider
    return {
      patient: DEFAULT_PATIENT,
      screening: DEFAULT_SCREENING,
      notifications: INITIAL_NOTIFICATIONS,
      consultations: INITIAL_CONSULTATIONS,
      carePlan: DEFAULT_CARE_PLAN,
      toggleCareTask: () => {},
      setCarePlan: () => {},
      markNotificationRead: () => {},
      markAllNotificationsRead: () => {},
      downloadReport: () => ({ success: true }),
      downloadToast: null,
      setDownloadToast: () => {},
    };
  }
  return context;
}
