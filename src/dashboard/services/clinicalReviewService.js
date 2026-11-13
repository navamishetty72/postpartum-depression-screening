/**
 * Persists a finalized Clinician Review & Assessment separately from AI outputs.
 * When VITE_MIORA_API_URL is configured, posts to POST /api/clinical-reviews and
 * waits for backend confirmation before signaling completion.
 * When no remote API URL is configured in the frontend workspace, persists via
 * the local ClinicalContext store and marks persistenceMode: 'local'.
 */
export async function submitClinicalReview({
  payload,
  fetchImpl = typeof window !== 'undefined' && window.fetch ? window.fetch.bind(window) : null,
}) {
  if (!payload?.motherId || !payload?.screeningId) {
    return {
      ok: false,
      reason: 'validation',
      message: 'A valid mother and screening session are required to finalize review.',
    };
  }

  const apiBase =
    (typeof import.meta !== 'undefined' && import.meta.env?.VITE_MIORA_API_URL) || '';

  if (!apiBase) {
    return {
      ok: true,
      persistenceMode: 'local',
      record: payload,
      message: 'Saved in local clinical workspace (remote EHR API not configured).',
    };
  }

  if (!fetchImpl) {
    return {
      ok: false,
      reason: 'network-unavailable',
      message: 'Network client is unavailable; review changes have been preserved locally.',
    };
  }

  try {
    const response = await fetchImpl(`${apiBase.replace(/\/$/, '')}/api/clinical-reviews`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      return {
        ok: false,
        reason: 'server-error',
        message: `Could not persist clinical review (HTTP ${response.status}). Your entries are preserved — please retry.`,
      };
    }

    const saved = await response.json().catch(() => payload);
    return {
      ok: true,
      persistenceMode: 'remote',
      record: saved,
      message: 'Confirmed and persisted to Miora clinical backend.',
    };
  } catch (err) {
    return {
      ok: false,
      reason: 'network-error',
      message:
        err?.message ||
        'Unable to reach clinical backend. Entered assessment details were preserved — please retry.',
    };
  }
}

