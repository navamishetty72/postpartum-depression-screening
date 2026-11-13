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
  clinicalFeatures,
  audioFeatures,
  textContent,
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
    (typeof import.meta !== 'undefined' && import.meta.env?.VITE_MIORA_API_URL) ||
    (typeof window !== 'undefined' && window.location?.origin ? '' : 'http://127.0.0.1:8000');

  if (!fetchImpl) {
    return {
      ok: false,
      reason: 'backend-unavailable',
      message:
        'Multimodal analysis backend is not connected in this frontend environment. Your files were validated locally and have not been uploaded externally or assigned fabricated scores.',
    };
  }

  try {
    const formData = new FormData();
    formData.append('motherId', motherId);
    formData.append('modalities', JSON.stringify(selectedModalities));
    formData.append('consentConfirmed', String(consentConfirmed));

    if (clinicalFeatures) {
      formData.append(
        'clinical_features',
        typeof clinicalFeatures === 'string' ? clinicalFeatures : JSON.stringify(clinicalFeatures)
      );
    }
    if (audioFeatures) {
      formData.append(
        'audio_features',
        typeof audioFeatures === 'string' ? audioFeatures : JSON.stringify(audioFeatures)
      );
    }
    if (textContent) {
      formData.append('text_content', textContent);
    }

    files.forEach((entry) => {
      if (entry.rawFile) {
        const modKey = entry.modality === 'voice' ? 'voice' : entry.modality;
        formData.append(`files_${modKey}`, entry.rawFile, entry.name);
      }
    });

    const url = `${apiBase ? apiBase.replace(/\/$/, '') : ''}/api/screenings/analyze`;
    const response = await fetchImpl(url, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      let errorDetail = `Analysis request failed (HTTP ${response.status}).`;
      try {
        const errJson = await response.json();
        if (errJson?.detail) {
          errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
        }
      } catch (_) {}
      return {
        ok: false,
        reason: 'server-error',
        message: `${errorDetail} Please retry or save a draft.`,
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

