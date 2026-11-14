/**
 * Submits uploaded maternal screening files & selected modalities to the
 * configured backend multimodal analysis endpoint.
 *
 * When no backend URL is configured in this frontend-only build, this service
 * honestly reports backend unavailability rather than fabricating clinical scores.
 */
export async function submitMultimodalAnalysis({
  motherId,
  selectedModalities,
  files,
  consentConfirmed,
  fetchImpl = typeof window !== 'undefined' && window.fetch ? window.fetch.bind(window) : null,
}) {
  if (!motherId) {
    return { ok: false, reason: 'validation', message: 'A registered Mother ID is required.' };
  }
  if (!consentConfirmed) {
    return {
      ok: false,
      reason: 'consent',
      message: 'Please confirm mother consent before submitting files for analysis.',
    };
  }
  if (!files || files.length === 0 || !selectedModalities.length) {
    return {
      ok: false,
      reason: 'validation',
      message: 'Upload at least one valid file and select at least one modality.',
    };
  }

  const apiBase =
    (typeof import.meta !== 'undefined' && import.meta.env?.VITE_MIORA_API_URL) || '';

  if (!fetchImpl) {
    return {
      ok: false,
      reason: 'backend-unavailable',
      message:
        'Network client unavailable in this environment. Your files were validated locally.',
    };
  }

  try {
    const formData = new FormData();
    formData.append('motherId', motherId);
    formData.append('modalities', JSON.stringify(selectedModalities));
    formData.append('consentConfirmed', String(consentConfirmed));
    files.forEach((entry) => {
      if (entry.rawFile) {
        formData.append(`files_${entry.modality}`, entry.rawFile, entry.name);
      }
    });

    const targetUrl = apiBase ? `${apiBase.replace(/\/$/, '')}/api/screenings/analyze` : '/api/screenings/analyze';
    const response = await fetchImpl(targetUrl, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      return {
        ok: false,
        reason: 'server-error',
        message: `Analysis request failed (HTTP ${response.status}). Please retry or save a draft.`,
      };
    }

    const result = await response.json();
    return { ok: true, result };
  } catch (err) {
    return {
      ok: false,
      reason: 'network-error',
      message: err?.message || 'Unable to reach the analysis service. Please retry.',
    };
  }
}

