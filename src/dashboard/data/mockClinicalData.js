/**
 * Clearly identified mock clinical dataset for Miora Clinician Screens.
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
  highRiskCases: '-3%',
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

const FEATURED_MOTHERS = [
  {
    id: 'M-104',
    name: 'Amara K.',
    initials: 'A. S.',
    avatarInitials: 'AS',
    postpartumWeek: 6,
    lastScreeningDate: 'Apr 24, 2026',
    lastScreeningIso: '2026-04-24T11:30:00Z',
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
    initials: 'N. R.',
    avatarInitials: 'NR',
    postpartumWeek: 2,
    lastScreeningDate: 'Apr 23, 2026',
    lastScreeningIso: '2026-04-23T15:10:00Z',
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
    initials: 'P. K.',
    avatarInitials: 'PK',
    postpartumWeek: 12,
    lastScreeningDate: 'Apr 22, 2026',
    lastScreeningIso: '2026-04-22T14:20:00Z',
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
    id: 'M-115',
    name: 'Maya T.',
    initials: 'S. D.',
    avatarInitials: 'SD',
    postpartumWeek: 8,
    lastScreeningDate: 'Apr 21, 2026',
    lastScreeningIso: '2026-04-21T16:45:00Z',
    status: 'Active',
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
    id: 'M-117',
    name: 'Priya N.',
    initials: 'I. V.',
    avatarInitials: 'IV',
    postpartumWeek: 4,
    lastScreeningDate: 'Apr 20, 2026',
    lastScreeningIso: '2026-04-20T18:10:00Z',
    status: 'Active',
    risk: 'Moderate',
    reasonForReview: 'Sleep disruption markers',
    priority: false,
    discordanceFlag: false,
    discordanceType: null,
    epdsScore: 9,
    lastScreeningTime: '10 min ago',
    voiceCueSummary: 'Mild vocal fatigue with warm engagement.',
    textCueSummary: 'Shared positive bonding moments alongside fragmented nighttime sleep.',
    carePlan: 'Continue bi-weekly check-in cadence with rest support.',
  },
  {
    id: 'M-120',
    name: 'Riya T.',
    initials: 'R. T.',
    avatarInitials: 'RT',
    postpartumWeek: 10,
    lastScreeningDate: 'Apr 20, 2026',
    lastScreeningIso: '2026-04-20T09:15:00Z',
    status: 'Review',
    risk: 'High',
    reasonForReview: 'Elevated vocal strain',
    priority: false,
    discordanceFlag: true,
    discordanceType: 'Elevated vocal strain vs. brief text responses',
    epdsScore: 15,
    lastScreeningTime: '4 hrs ago',
    voiceCueSummary: 'Elevated pitch tension and faster speech cadence during stressor prompts.',
    textCueSummary: 'Expressed feeling overwhelmed balancing recovery and infant care.',
    carePlan: 'Schedule priority clinician outreach and perinatal counselor consultation.',
  },
  {
    id: 'M-116',
    name: 'Elena R.',
    initials: 'E. R.',
    avatarInitials: 'ER',
    postpartumWeek: 4,
    lastScreeningDate: 'Apr 19, 2026',
    lastScreeningIso: '2026-04-19T14:00:00Z',
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
    id: 'M-101',
    name: 'Claire B.',
    initials: 'C. B.',
    avatarInitials: 'CB',
    postpartumWeek: 3,
    lastScreeningDate: 'Apr 19, 2026',
    lastScreeningIso: '2026-04-19T10:30:00Z',
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
    initials: 'N. W.',
    avatarInitials: 'NW',
    postpartumWeek: 9,
    lastScreeningDate: 'Apr 18, 2026',
    lastScreeningIso: '2026-04-18T12:15:00Z',
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
    initials: 'Z. H.',
    avatarInitials: 'ZH',
    postpartumWeek: 7,
    lastScreeningDate: 'Apr 17, 2026',
    lastScreeningIso: '2026-04-17T16:00:00Z',
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
    initials: 'G. D.',
    avatarInitials: 'GD',
    postpartumWeek: 10,
    lastScreeningDate: 'Apr 17, 2026',
    lastScreeningIso: '2026-04-17T09:40:00Z',
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

const FIRST_LETTERS = 'ABCEGHKLMNPRSTZ';
const LAST_LETTERS = 'BDGHKLMNPRSTVW';
const MONTHS = ['Apr', 'Mar', 'Feb', 'Jan'];

function buildGeneratedCohort() {
  const generated = [];
  const baseDate = new Date('2026-04-16T12:00:00Z').getTime();

  for (let i = 0; i < 317; i += 1) {
    const first = FIRST_LETTERS[i % FIRST_LETTERS.length];
    const last = LAST_LETTERS[(i * 3 + 5) % LAST_LETTERS.length];
    const avatarInitials = `${first}${last}`;
    const initials = `${first}. ${last}.`;
    const id = `M-${201 + i}`;

    let risk = 'Low';
    let status = i % 2 === 0 ? 'Active' : 'Completed';
    let reasonForReview = 'Routine postpartum check-in';
    let epdsScore = 3 + (i % 5);

    if (i < 4) {
      risk = 'High';
      status = 'Review';
      reasonForReview = 'Elevated postpartum distress indicators';
      epdsScore = 15 + (i % 3);
    } else if (i < 13) {
      risk = 'Moderate';
      status = 'Follow-up';
      reasonForReview = 'Scheduled clinician follow-up';
      epdsScore = 10 + (i % 3);
    } else if (i < 93) {
      risk = i % 3 === 0 ? 'Moderate' : 'Low';
      status = 'Pending';
      reasonForReview = 'Pending weekly multimodal check-in';
      epdsScore = risk === 'Moderate' ? 9 : 5;
    } else if (i % 17 === 0) {
      risk = 'Requires Review';
      status = 'Active';
      reasonForReview = 'Nuanced tone shift flagged for review';
      epdsScore = 11;
    } else if (i % 5 === 0) {
      risk = 'Moderate';
      reasonForReview = 'Mild sleep fatigue noted';
      epdsScore = 9;
    }

    const dayOffset = Math.floor(i / 4);
    const dt = new Date(baseDate - dayOffset * 24 * 60 * 60 * 1000 - (i % 4) * 3600000);
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const formattedDate = `${monthNames[dt.getUTCMonth()]} ${dt.getUTCDate()}, ${dt.getUTCFullYear()}`;
    const week = (i * 5 + 2) % 25; // 0..24

    generated.push({
      id,
      name: `Mother ${initials}`,
      initials,
      avatarInitials,
      postpartumWeek: week,
      lastScreeningDate: formattedDate,
      lastScreeningIso: dt.toISOString(),
      status,
      risk,
      reasonForReview,
      priority: false,
      discordanceFlag: i < 3,
      discordanceType: i < 3 ? 'Prosody-text divergence' : null,
      epdsScore,
      lastScreeningTime: `${dayOffset + 2} days ago`,
      voiceCueSummary:
        risk === 'High'
          ? 'Heightened vocal tension and slower cadence detected.'
          : 'Steady conversational prosody within expected baseline.',
      textCueSummary:
        status === 'Pending'
          ? 'Awaiting scheduled self-reflection submission.'
          : 'Completed structured postpartum wellbeing prompts.',
      carePlan:
        risk === 'High'
          ? 'Prioritize clinician review and supportive care outreach.'
          : 'Continue standard Miora postpartum monitoring schedule.',
    });
  }

  return generated;
}

export const INITIAL_MOTHERS = [...FEATURED_MOTHERS, ...buildGeneratedCohort()];

// Keep MONTHS referenced cleanly if needed for exports; avoid unused-var warning
void MONTHS;

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
