/**
 * Clearly identified mock clinical dataset for the Miora Command Center.
 * In production, these structures map directly to backend EHR / screening endpoints.
 */
export const IS_MOCK_DATA = true;

export const CLINICIAN_PROFILE = {
  id: 'clinician-01',
  initials: 'DR',
  name: 'Dr. Elena Rostova',
  role: 'Perinatal Psychiatry Lead',
  clinic: 'Miora Maternal Care Unit',
};

export const KPI_TRENDS = {
  registeredMothers: '+5%',
  screeningsCompleted: '+8%',
  casesForReview: '+12%',
  potentialDiscordance: '+3%',
};

/**
 * Baseline historical cohort totals (combined with live detailed records below)
 * so initial Command Center metrics reflect 328 registered mothers,
 * 247 completed screenings, 18 cases for review, and 7 discordance flags.
 */
export const BASELINE_COHORT = {
  additionalMothers: 318, // + 10 detailed mother records = 328
  additionalScreenings: 237, // + 10 completed detailed screenings = 247
  additionalReviewCases: 13, // + 5 detailed review cases = 18
  additionalDiscordance: 4, // + 3 detailed discordance cases = 7
  riskCounts: {
    'Low Risk': 138, // + 5 detailed = 143 (58%)
    'Moderate Risk': 46, // + 3 detailed = 49 (20%)
    'High Risk': 33, // + 2 detailed = 35 (14%)
    'Requires Review': 20, // + 0 extra or derived via status; kept exact 20 (8%)
  },
};

/**
 * Weekly screening records used by the Screening Activity chart.
 * Supports 4-week, 8-week, and 12-week clinical reporting windows.
 */
export const SCREENING_WEEKLY_RECORDS = [
  { id: 'wk-01', week: 'Week 1', fullLabel: '12 Weeks Ago', dateRange: 'Aug 17 – Aug 23', screenings: 18, flagged: 2 },
  { id: 'wk-02', week: 'Week 2', fullLabel: '11 Weeks Ago', dateRange: 'Aug 24 – Aug 30', screenings: 21, flagged: 3 },
  { id: 'wk-03', week: 'Week 3', fullLabel: '10 Weeks Ago', dateRange: 'Aug 31 – Sep 6', screenings: 24, flagged: 2 },
  { id: 'wk-04', week: 'Week 4', fullLabel: '9 Weeks Ago', dateRange: 'Sep 7 – Sep 13', screenings: 22, flagged: 3 },
  { id: 'wk-05', week: 'Week 5', fullLabel: '8 Weeks Ago', dateRange: 'Sep 14 – Sep 20', screenings: 26, flagged: 4 },
  { id: 'wk-06', week: 'Week 6', fullLabel: '7 Weeks Ago', dateRange: 'Sep 21 – Sep 27', screenings: 29, flagged: 3 },
  { id: 'wk-07', week: 'Week 7', fullLabel: '6 Weeks Ago', dateRange: 'Sep 28 – Oct 4', screenings: 31, flagged: 4 },
  { id: 'wk-08', week: 'Week 8', fullLabel: '5 Weeks Ago', dateRange: 'Oct 5 – Oct 11', screenings: 35, flagged: 5 },
  { id: 'wk-09', week: 'Week 1', fullLabel: '4 Weeks Ago', dateRange: 'Oct 12 – Oct 18', screenings: 33, flagged: 4 },
  { id: 'wk-10', week: 'Week 2', fullLabel: '3 Weeks Ago', dateRange: 'Oct 19 – Oct 25', screenings: 46, flagged: 6 },
  { id: 'wk-11', week: 'Week 3', fullLabel: '2 Weeks Ago', dateRange: 'Oct 26 – Nov 1', screenings: 55, flagged: 5 },
  { id: 'wk-12', week: 'Week 4', fullLabel: 'Current Week', dateRange: 'Nov 2 – Nov 8', screenings: 68, flagged: 7 },
];

export const RISK_COLORS = {
  'Low Risk': '#f5d3dc',
  'Moderate Risk': '#f5cbb8',
  'High Risk': '#ea8cab',
  'Requires Review': '#df487e',
};

export const INITIAL_MOTHERS = [
  {
    id: 'M-104',
    name: 'Amara K.',
    postpartumWeek: 6,
    status: 'Review',
    risk: 'High',
    reasonForReview: 'Elevated distress cues',
    priority: true,
    discordanceFlag: true,
    discordanceType: 'Vocal tension vs. flat text affect',
    epdsScore: 16,
    lastScreeningTime: '1 hr ago',
    voiceCueSummary: 'Elevated pitch variability, prolonged pauses (2.4s avg), audible sighing.',
    textCueSummary: 'Expressed persistent exhaustion and feeling disconnected during evening feedings.',
    carePlan: 'Schedule urgent telehealth check-in within 24 hours; evaluate perinatal support network.',
  },
  {
    id: 'M-108',
    name: 'Sofia M.',
    postpartumWeek: 2,
    status: 'Follow-up',
    risk: 'Moderate',
    reasonForReview: 'Voice-text mismatch',
    priority: true,
    discordanceFlag: true,
    discordanceType: 'Voice-text mismatch',
    epdsScore: 11,
    lastScreeningTime: '2 hrs ago',
    voiceCueSummary: 'Tremulous prosody and flattened cadence despite reassuring written responses.',
    textCueSummary: 'Reported "doing okay overall" with minimal elaboration on sleep.',
    carePlan: 'Warm clinician follow-up call; gently explore unspoken stressors in private session.',
  },
  {
    id: 'M-112',
    name: 'Hannah L.',
    postpartumWeek: 12,
    status: 'Pending',
    risk: 'Low',
    reasonForReview: 'Incomplete screening',
    priority: true,
    discordanceFlag: false,
    discordanceType: null,
    epdsScore: 6,
    lastScreeningTime: '3 hrs ago',
    voiceCueSummary: 'Audio segment ended early at 00:42 due to background interruption.',
    textCueSummary: 'Completed 6 of 10 check-in prompts with stable mood markers.',
    carePlan: 'Send gentle SMS reminder to finish remaining check-in prompts at convenient time.',
  },
  {
    id: 'M-117',
    name: 'Priya N.',
    postpartumWeek: 5,
    status: 'Completed',
    risk: 'Low',
    reasonForReview: 'Routine check-in',
    priority: false,
    discordanceFlag: false,
    discordanceType: null,
    epdsScore: 4,
    lastScreeningTime: '10 min ago',
    voiceCueSummary: 'Warm, steady cadence with natural emotional range.',
    textCueSummary: 'Shared positive bonding moments and manageable rest schedule.',
    carePlan: 'Continue standard bi-weekly check-in cadence.',
  },
  {
    id: 'M-116',
    name: 'Elena R.',
    postpartumWeek: 4,
    status: 'Completed',
    risk: 'Moderate',
    reasonForReview: 'Sleep disruption markers',
    priority: false,
    discordanceFlag: false,
    discordanceType: null,
    epdsScore: 10,
    lastScreeningTime: '24 min ago',
    voiceCueSummary: 'Mild vocal fatigue and slower speech rate.',
    textCueSummary: 'Noted fragmented sleep and mild anxiety around feeding routines.',
    carePlan: 'Provide guided restorative sleep resources and schedule 1-week check-in.',
  },
  {
    id: 'M-115',
    name: 'Maya T.',
    postpartumWeek: 8,
    status: 'Completed',
    risk: 'Low',
    reasonForReview: 'Routine check-in',
    priority: false,
    discordanceFlag: false,
    discordanceType: null,
    epdsScore: 5,
    lastScreeningTime: '36 min ago',
    voiceCueSummary: 'Balanced prosody and clear conversational engagement.',
    textCueSummary: 'Reported feeling supported by partner and local postpartum group.',
    carePlan: 'Continue routine postpartum monitoring.',
  },
  {
    id: 'M-101',
    name: 'Claire B.',
    postpartumWeek: 3,
    status: 'Review',
    risk: 'High',
    reasonForReview: 'Persistent anxiety & overwhelm',
    priority: false,
    discordanceFlag: true,
    discordanceType: 'Self-report minimization vs. acoustic stress',
    epdsScore: 15,
    lastScreeningTime: '4 hrs ago',
    voiceCueSummary: 'Rapid speech bursts with elevated vocal strain.',
    textCueSummary: 'Checked "manageable" while describing intrusive worry at night.',
    carePlan: 'Prioritize CBT-informed perinatal counselor referral.',
  },
  {
    id: 'M-109',
    name: 'Nadia W.',
    postpartumWeek: 9,
    status: 'Follow-up',
    risk: 'Moderate',
    reasonForReview: 'Mood dip from Week 6 baseline',
    priority: false,
    discordanceFlag: false,
    discordanceType: null,
    epdsScore: 12,
    lastScreeningTime: '5 hrs ago',
    voiceCueSummary: 'Noticeable drop in vocal energy compared to Week 6 screening.',
    textCueSummary: 'Expressed isolation after partner returned to full-time work.',
    carePlan: 'Connect with peer support circle and schedule 7-day reassessment.',
  },
  {
    id: 'M-113',
    name: 'Zara H.',
    postpartumWeek: 7,
    status: 'Completed',
    risk: 'Low',
    reasonForReview: 'Routine check-in',
    priority: false,
    discordanceFlag: false,
    discordanceType: null,
    epdsScore: 3,
    lastScreeningTime: '6 hrs ago',
    voiceCueSummary: 'Calm, steady tone with consistent response latency.',
    textCueSummary: 'Positive adjustment and steady physical recovery.',
    carePlan: 'Routine follow-up at Week 10.',
  },
  {
    id: 'M-114',
    name: 'Grace D.',
    postpartumWeek: 10,
    status: 'Completed',
    risk: 'Low',
    reasonForReview: 'Routine check-in',
    priority: false,
    discordanceFlag: false,
    discordanceType: null,
    epdsScore: 4,
    lastScreeningTime: '1 day ago',
    voiceCueSummary: 'Relaxed vocal tone and steady energy.',
    textCueSummary: 'Steady mood and strong community support.',
    carePlan: 'Routine postpartum care pathway.',
  },
];

export const INITIAL_SCREENINGS = [
  {
    id: 'SCR-247',
    motherId: 'M-117',
    motherName: 'Priya N.',
    postpartumWeek: 5,
    status: 'Completed',
    completedAgo: '10 min ago',
    risk: 'Low',
    modality: 'Voice + Text',
    epdsEquivalent: 4,
    discordanceScore: 0.12,
    summary: 'Consistent low-distress prosody and grounded narrative reflection.',
  },
  {
    id: 'SCR-246',
    motherId: 'M-116',
    motherName: 'Elena R.',
    postpartumWeek: 4,
    status: 'Completed',
    completedAgo: '24 min ago',
    risk: 'Moderate',
    modality: 'Voice + Text',
    epdsEquivalent: 10,
    discordanceScore: 0.28,
    summary: 'Mild fatigue cues in voice; recommends sleep-restoration check-in.',
  },
  {
    id: 'SCR-245',
    motherId: 'M-115',
    motherName: 'Maya T.',
    postpartumWeek: 8,
    status: 'Completed',
    completedAgo: '36 min ago',
    risk: 'Low',
    modality: 'Voice + Text',
    epdsEquivalent: 5,
    discordanceScore: 0.09,
    summary: 'Stable wellbeing indicators across acoustic and lexical channels.',
  },
  {
    id: 'SCR-244',
    motherId: 'M-104',
    motherName: 'Amara K.',
    postpartumWeek: 6,
    status: 'Completed',
    completedAgo: '1 hr ago',
    risk: 'High',
    modality: 'Voice + Text',
    epdsEquivalent: 16,
    discordanceScore: 0.74,
    summary: 'Elevated distress markers and vocal tension requiring clinician review.',
  },
  {
    id: 'SCR-243',
    motherId: 'M-108',
    motherName: 'Sofia M.',
    postpartumWeek: 2,
    status: 'Completed',
    completedAgo: '2 hrs ago',
    risk: 'Moderate',
    modality: 'Voice + Text',
    epdsEquivalent: 11,
    discordanceScore: 0.81,
    summary: 'Notable voice-text mismatch between calm text and tremulous speech.',
  },
  {
    id: 'SCR-242',
    motherId: 'M-112',
    motherName: 'Hannah L.',
    postpartumWeek: 12,
    status: 'Pending',
    completedAgo: '3 hrs ago',
    risk: 'Low',
    modality: 'Text (Partial)',
    epdsEquivalent: 6,
    discordanceScore: 0.15,
    summary: 'Partial screening captured; voice prompt deferred.',
  },
];

export const CLINICAL_ALERTS = [
  {
    id: 'alert-1',
    motherId: 'M-104',
    title: 'High distress cues flagged for M-104',
    time: '12 min ago',
    severity: 'high',
  },
  {
    id: 'alert-2',
    motherId: 'M-108',
    title: 'Voice-text mismatch detected in Week 2 check-in',
    time: '48 min ago',
    severity: 'moderate',
  },
  {
    id: 'alert-3',
    motherId: 'M-112',
    title: 'Incomplete screening reminder pending for M-112',
    time: '3 hrs ago',
    severity: 'low',
  },
];

