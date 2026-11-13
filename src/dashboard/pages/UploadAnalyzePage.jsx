import React, { useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useClinicalData } from '../context/ClinicalContext.jsx';
import { DashboardIcon } from '../components/DashboardIcon.jsx';
import { PatientInfoStrip } from '../components/PatientInfoStrip.jsx';
import { ModalityUploadCard } from '../components/ModalityUploadCard.jsx';
import { AnalysisPreviewCard } from '../components/AnalysisPreviewCard.jsx';
import {
  MODALITY_SPECS,
  formatFileSize,
  readMediaDuration,
  validateUploadFile,
} from '../utils/uploadValidation.js';
import { DEFAULT_CLINICAL_SURVEY_FEATURES } from '../data/mockClinicalData.js';
import { submitMultimodalAnalysis } from '../services/screeningAnalysisService.js';

export function UploadAnalyzePage({ analyzer = submitMultimodalAnalysis }) {
  const {
    mothers,
    uploadDrafts,
    recordScreening,
    saveUploadDraft,
    clearUploadDraft,
  } = useClinicalData();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const defaultMotherId = useMemo(() => {
    const paramId = searchParams.get('mother');
    if (paramId && mothers.some((m) => m.id === paramId)) return paramId;
    if (mothers.some((m) => m.id === 'M-108')) return 'M-108';
    return mothers[0]?.id || 'M-104';
  }, [mothers, searchParams]);

  const [motherId, setMotherId] = useState(defaultMotherId);
  const activeMother = useMemo(
    () => mothers.find((m) => m.id === motherId) || mothers[0],
    [mothers, motherId]
  );

  const initialDraft = uploadDrafts[defaultMotherId];

  const [uploadedFiles, setUploadedFiles] = useState(
    () => initialDraft?.files || []
  );
  const [selectedModalities, setSelectedModalities] = useState(
    () => initialDraft?.selectedModalities || []
  );
  const [consentConfirmed, setConsentConfirmed] = useState(
    () => Boolean(initialDraft?.consentConfirmed)
  );
  const [uploadError, setUploadError] = useState('');
  const [draftNotice, setDraftNotice] = useState(
    initialDraft ? 'Resumed saved upload draft' : ''
  );
  const [analysisStatus, setAnalysisStatus] = useState('idle'); // idle | processing | error | ready
  const [analysisError, setAnalysisError] = useState('');
  const [analysisResult, setAnalysisResult] = useState(null);

  const availableModalities = useMemo(
    () => ({
      text: uploadedFiles.some((f) => f.modality === 'text' && f.status === 'ready'),
      voice: uploadedFiles.some((f) => f.modality === 'voice' && f.status === 'ready'),
      video: uploadedFiles.some((f) => f.modality === 'video' && f.status === 'ready'),
    }),
    [uploadedFiles]
  );

  const activeSelectedModalities = useMemo(
    () => selectedModalities.filter((mod) => availableModalities[mod]),
    [selectedModalities, availableModalities]
  );

  const canRunAnalysis =
    uploadedFiles.some((f) => f.status === 'ready') &&
    activeSelectedModalities.length > 0 &&
    analysisStatus !== 'processing';

  const handleSelectMother = (nextId) => {
    setMotherId(nextId);
    setSearchParams({ mother: nextId });
    const nextDraft = uploadDrafts[nextId];
    if (nextDraft) {
      setUploadedFiles(nextDraft.files || []);
      setSelectedModalities(nextDraft.selectedModalities || []);
      setConsentConfirmed(Boolean(nextDraft.consentConfirmed));
      setDraftNotice('Resumed saved upload draft');
    } else {
      setUploadedFiles([]);
      setSelectedModalities([]);
      setConsentConfirmed(false);
      setDraftNotice('');
    }
    setUploadError('');
    setAnalysisStatus('idle');
    setAnalysisError('');
    setAnalysisResult(null);
  };

  const handleFilesAdded = async (files, modality) => {
    setUploadError('');
    setDraftNotice('');
    const validEntries = [];

    for (const file of files) {
      const validation = validateUploadFile(file, modality);
      if (!validation.valid) {
        setUploadError(validation.error);
        continue;
      }

      const id = `${modality}-${file.name}-${file.size}-${Date.now()}-${Math.random()
        .toString(36)
        .slice(2, 6)}`;

      validEntries.push({
        id,
        name: file.name,
        size: file.size,
        sizeLabel: formatFileSize(file.size),
        modality,
        durationLabel: null,
        progress: 100,
        status: 'ready',
        rawFile: file,
      });
    }

    if (validEntries.length === 0) return;

    setUploadedFiles((prev) => [...prev, ...validEntries]);
    setSelectedModalities((prev) =>
      prev.includes(modality) ? prev : [...prev, modality]
    );
    setAnalysisStatus('idle');
    setAnalysisError('');
    setAnalysisResult(null);

    // Resolve audio/video durations asynchronously without blocking UI
    for (const entry of validEntries) {
      if (modality === 'voice' || modality === 'video') {
        const duration = await readMediaDuration(entry.rawFile, modality);
        if (duration) {
          setUploadedFiles((prev) =>
            prev.map((item) =>
              item.id === entry.id ? { ...item, durationLabel: duration } : item
            )
          );
        }
      }
    }
  };

  const handleRemoveFile = (fileId) => {
    setUploadedFiles((prev) => {
      const next = prev.filter((f) => f.id !== fileId);
      const stillHasModality = (mod) => next.some((f) => f.modality === mod && f.status === 'ready');
      setSelectedModalities((mods) => mods.filter((m) => stillHasModality(m)));
      return next;
    });
    setUploadError('');
    setAnalysisStatus('idle');
    setAnalysisError('');
    setAnalysisResult(null);
  };

  const handleClearAll = () => {
    setUploadedFiles([]);
    setSelectedModalities([]);
    setUploadError('');
    setDraftNotice('');
    setAnalysisStatus('idle');
    setAnalysisError('');
    setAnalysisResult(null);
  };

  const handleToggleModality = (mod) => {
    if (!availableModalities[mod]) return;
    setSelectedModalities((prev) =>
      prev.includes(mod) ? prev.filter((m) => m !== mod) : [...prev, mod]
    );
  };

  const handleSaveDraft = () => {
    const serializableFiles = uploadedFiles.map(({ rawFile, ...metadata }) => {
      void rawFile;
      return metadata;
    });
    saveUploadDraft(activeMother.id, {
      motherId: activeMother.id,
      files: serializableFiles,
      selectedModalities: activeSelectedModalities,
      consentConfirmed,
    });
    const nowTime = new Date().toLocaleTimeString([], {
      hour: 'numeric',
      minute: '2-digit',
    });
    setDraftNotice(`Draft saved at ${nowTime}`);
  };

  const handleRunAnalysis = async () => {
    if (!canRunAnalysis) return;
    if (!consentConfirmed) {
      setAnalysisStatus('error');
      setAnalysisError('Please confirm mother consent before running multimodal analysis.');
      return;
    }

    setAnalysisStatus('processing');
    setAnalysisError('');

    // Attach registered clinical baseline survey features alongside uploaded modalities
    const modalitiesWithClinical = activeSelectedModalities.includes('clinical')
      ? activeSelectedModalities
      : ['clinical', ...activeSelectedModalities];

    const response = await analyzer({
      motherId: activeMother.id,
      selectedModalities: modalitiesWithClinical,
      files: uploadedFiles.filter((f) => activeSelectedModalities.includes(f.modality)),
      consentConfirmed,
      clinicalFeatures: DEFAULT_CLINICAL_SURVEY_FEATURES,
    });

    if (!response?.ok) {
      setAnalysisStatus('error');
      setAnalysisError(
        response?.message || 'Unable to process uploaded files. Please retry.'
      );
      return;
    }

    const result = response.result;
    setAnalysisResult(result);
    setAnalysisStatus('ready');

    const modalityLabels = activeSelectedModalities.map(
      (m) => m.charAt(0).toUpperCase() + m.slice(1)
    );

    // Extract risk tier from fusion or clinical prediction if available
    let riskTier = 'Moderate';
    const rawRisk =
      result.fusion?.risk_category ||
      result.clinical?.prediction?.risk_category ||
      result.riskCategory;
    if (rawRisk) {
      if (rawRisk.includes('HIGH')) riskTier = 'High';
      else if (rawRisk.includes('LOW')) riskTier = 'Low';
      else riskTier = 'Moderate';
    }

    const clinProb = result.clinical?.prediction?.predicted_risk_probability;
    const fusionScore = result.fusion?.combined_score;
    const effectiveScore =
      typeof fusionScore === 'number'
        ? fusionScore
        : typeof clinProb === 'number'
          ? clinProb
          : result.combinedScore || 0.5;

    const created = recordScreening({
      motherId: activeMother.id,
      risk: riskTier,
      modality: `Uploaded (${modalityLabels.join(' · ')})`,
      summary:
        result.indicators?.join('; ') ||
        result.fusion?.discordance_analysis?.explanation ||
        `Completed multimodal screening analysis (${modalityLabels.join(', ')}).`,
      epdsEquivalent:
        result.fusion?.epds_equivalent ??
        result.epdsEquivalent ??
        Math.round(effectiveScore * 20),
      discordanceDetected: Boolean(
        result.fusion?.discordance_analysis?.discordance_detected ??
          result.discordanceDetected
      ),
      capturedModalities: {
        clinical: Boolean(result.clinical?.status === 'completed'),
        text: activeSelectedModalities.includes('text') || Boolean(result.text?.status === 'completed'),
        voice: activeSelectedModalities.includes('voice') || Boolean(result.audio?.status === 'completed'),
        video: activeSelectedModalities.includes('video'),
      },
      preliminaryScore: effectiveScore,
      modalityContributions: result.fusion?.modality_contributions ?? result.modalityContributions,
      indicators: result.indicators,
      backendResult: result,
    });

    clearUploadDraft(activeMother.id);
    navigate(`/results/${created.motherId}`);
  };

  const derivedIndicators = useMemo(() => {
    if (analysisStatus === 'ready' && analysisResult?.indicators?.length) {
      return analysisResult.indicators;
    }
    if (uploadedFiles.length === 0) {
      return [
        'No files uploaded yet — upload Text, Voice, or Video to inspect readiness',
        'Unavailable modalities are excluded and not penalized as negative findings',
      ];
    }
    const items = [];
    ['text', 'voice', 'video'].forEach((mod) => {
      const count = uploadedFiles.filter((f) => f.modality === mod).length;
      if (count > 0) {
        items.push(
          `${MODALITY_SPECS[mod].label}: ${count} validated file${count > 1 ? 's' : ''} ready (${
            activeSelectedModalities.includes(mod) ? 'selected' : 'deselected'
          })`
        );
      } else {
        items.push(`${MODALITY_SPECS[mod].label}: Unavailable (no file uploaded — excluded)`);
      }
    });
    return items;
  }, [analysisStatus, analysisResult, uploadedFiles, activeSelectedModalities]);

  const derivedNextSteps = useMemo(() => {
    if (analysisStatus === 'ready' && analysisResult?.nextSteps?.length) {
      return analysisResult.nextSteps;
    }
    return [
      'Confirm mother consent and verify patient ID before submitting',
      'Review uploaded recordings or transcripts for completeness',
      'Consult clinical team or maternal support resources if distress is observed',
    ];
  }, [analysisStatus, analysisResult]);

  return (
    <div className="miora-command-shell">
      <div className="miora-command-frame">
        {/* Flowing Blush Header Waves */}
        <svg
          className="miora-header-ribbon miora-mothers-ribbon"
          viewBox="0 0 640 160"
          fill="none"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <defs>
            <linearGradient id="uploadAnalyzeWaveGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#fbdbe2" stopOpacity="0" />
              <stop offset="50%" stopColor="#f8c9d5" stopOpacity="0.45" />
              <stop offset="100%" stopColor="#fce8ec" stopOpacity="0.16" />
            </linearGradient>
          </defs>
          <path
            d="M0 135 C 150 128, 225 42, 395 48 C 515 52, 565 88, 640 24 L 640 160 L 0 160 Z"
            fill="url(#uploadAnalyzeWaveGrad)"
          />
        </svg>

        {/* Page Header */}
        <section className="miora-dash-header" aria-labelledby="upload-analyze-heading">
          <div className="miora-dash-header-copy">
            <div className="miora-dash-eyebrow">
              <span>UPLOAD &amp; ANALYZE</span>
              <span className="miora-dash-eyebrow-line" aria-hidden="true" />
            </div>
            <h1 id="upload-analyze-heading" className="miora-dash-title">
              Upload &amp; <em>Analyze</em>
            </h1>
            <p className="miora-dash-subtitle">
              Analyze previously recorded text, audio or video to assess maternal wellbeing.
            </p>
          </div>
        </section>

        {/* Two-Option Segmented Navigation */}
        <div className="miora-mode-switch" role="tablist" aria-label="Screening mode selector">
          <button
            type="button"
            role="tab"
            aria-selected={false}
            className="miora-mode-tab"
            onClick={() => navigate(`/live-screening?mother=${activeMother.id}`)}
          >
            <DashboardIcon name="video" size={16} />
            <span>Screening</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={true}
            className="miora-mode-tab is-active"
          >
            <DashboardIcon name="upload" size={16} />
            <span>Upload &amp; Analyze</span>
          </button>
        </div>

        {/* Patient Information Strip */}
        <PatientInfoStrip
          mothers={mothers}
          activeMother={activeMother}
          onSelectMother={handleSelectMother}
          selectId="upload-mother-select"
        />

        {/* Two-Column Main Content Layout (48% / 52%) */}
        <div className="miora-upload-layout">
          {/* LEFT COLUMN: Upload Maternal Data + Uploaded Files */}
          <section className="miora-card miora-upload-card" aria-labelledby="upload-maternal-title">
            <div className="miora-card-header">
              <div className="miora-card-title-group">
                <span className="miora-card-icon" aria-hidden="true">
                  <DashboardIcon name="uploadCloud" size={22} strokeWidth={1.65} />
                </span>
                <h2 id="upload-maternal-title" className="miora-card-title">
                  Upload Maternal Data
                </h2>
              </div>
            </div>

            <p className="miora-upload-desc">
              Upload one or more modalities for analysis. At least one file is required.
            </p>

            <div className="miora-upload-zones-grid">
              <ModalityUploadCard
                spec={MODALITY_SPECS.text}
                onFilesAdded={handleFilesAdded}
              />
              <ModalityUploadCard
                spec={MODALITY_SPECS.voice}
                onFilesAdded={handleFilesAdded}
              />
              <ModalityUploadCard
                spec={MODALITY_SPECS.video}
                onFilesAdded={handleFilesAdded}
              />
            </div>

            {uploadError && (
              <div className="miora-live-alert miora-upload-error" role="alert">
                {uploadError}
              </div>
            )}

            <div className="miora-uploaded-section">
              <div className="miora-uploaded-header">
                <div className="miora-card-title-group">
                  <span className="miora-card-icon" aria-hidden="true">
                    <DashboardIcon name="layers" size={18} strokeWidth={1.65} />
                  </span>
                  <h3 className="miora-uploaded-title">
                    Uploaded Files ({uploadedFiles.length})
                  </h3>
                </div>

                {uploadedFiles.length > 0 && (
                  <button
                    type="button"
                    className="miora-clear-all-btn"
                    onClick={handleClearAll}
                  >
                    <DashboardIcon name="trash" size={14} />
                    <span>Clear All</span>
                  </button>
                )}
              </div>

              {uploadedFiles.length > 0 ? (
                <ul className="miora-uploaded-list">
                  {uploadedFiles.map((file) => (
                    <li key={file.id} className="miora-uploaded-row">
                      <div className="miora-uploaded-row-left">
                        <span className="miora-uploaded-file-icon" aria-hidden="true">
                          <DashboardIcon
                            name={
                              file.modality === 'voice'
                                ? 'waveform'
                                : file.modality === 'video'
                                  ? 'video'
                                  : 'fileText'
                            }
                            size={18}
                          />
                        </span>
                        <div className="miora-uploaded-file-meta">
                          <strong>{file.name}</strong>
                          <span>
                            {file.sizeLabel}
                            {file.durationLabel ? ` · ${file.durationLabel}` : ''}
                            {' · '}
                            {file.status === 'ready' ? 'Validated (100%)' : `${file.progress}%`}
                          </span>
                        </div>
                      </div>

                      <div className="miora-uploaded-row-right">
                        <span
                          className="miora-file-valid-dot"
                          title="File validated"
                          aria-label="Validated"
                        >
                          <DashboardIcon name="check" size={12} strokeWidth={2.5} />
                        </span>
                        <button
                          type="button"
                          className="miora-file-remove-btn"
                          aria-label={`Remove ${file.name}`}
                          onClick={() => handleRemoveFile(file.id)}
                        >
                          <DashboardIcon name="close" size={15} />
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="miora-uploaded-empty">
                  No files uploaded yet. Select or drag &amp; drop a supported Text, Voice, or Video file above.
                </p>
              )}
            </div>
          </section>

          {/* RIGHT COLUMN: Selected Modalities + Analysis Preview + Key Indicators & Next Steps */}
          <div className="miora-upload-right-col">
            <section
              className="miora-card miora-selected-modalities-card"
              aria-labelledby="selected-modalities-title"
            >
              <div className="miora-card-header">
                <div className="miora-card-title-group">
                  <span className="miora-card-icon" aria-hidden="true">
                    <DashboardIcon name="layers" size={19} strokeWidth={1.65} />
                  </span>
                  <h2 id="selected-modalities-title" className="miora-card-title">
                    Selected Modalities
                  </h2>
                </div>
              </div>

              <div className="miora-modality-pills">
                {[
                  { id: 'text', label: 'Text' },
                  { id: 'voice', label: 'Voice' },
                  { id: 'video', label: 'Video' },
                ].map((mod) => {
                  const isAvailable = availableModalities[mod.id];
                  const isSelected = isAvailable && selectedModalities.includes(mod.id);
                  return (
                    <button
                      key={mod.id}
                      type="button"
                      disabled={!isAvailable}
                      aria-pressed={isSelected}
                      className={`miora-modality-toggle ${
                        isSelected
                          ? 'is-selected'
                          : isAvailable
                            ? 'is-available'
                            : 'is-unavailable'
                      }`}
                      onClick={() => handleToggleModality(mod.id)}
                    >
                      <span className="miora-modality-toggle-mark" aria-hidden="true">
                        {isSelected ? (
                          <DashboardIcon name="check" size={14} strokeWidth={2.3} />
                        ) : isAvailable ? (
                          '○'
                        ) : (
                          '–'
                        )}
                      </span>
                      <span>{mod.label}</span>
                      {!isAvailable && (
                        <small className="miora-modality-unavail-tag">Unavailable</small>
                      )}
                    </button>
                  );
                })}
              </div>
            </section>

            <AnalysisPreviewCard
              status={analysisStatus}
              errorMessage={analysisError}
              analysisResult={analysisResult}
              selectedModalities={activeSelectedModalities}
              availableModalities={availableModalities}
              onRetry={handleRunAnalysis}
            />

            <section className="miora-card miora-indicators-next-card" aria-label="Key Indicators and Next Steps">
              <div className="miora-prelim-col">
                <div className="miora-card-title-group">
                  <span className="miora-card-icon" aria-hidden="true">
                    <DashboardIcon name="barChart" size={19} strokeWidth={1.65} />
                  </span>
                  <h3 className="miora-card-title">Key Indicators</h3>
                </div>
                <ul className="miora-prelim-list">
                  {derivedIndicators.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>

              <div className="miora-prelim-col miora-prelim-col-bordered">
                <div className="miora-card-title-group">
                  <span className="miora-card-icon" aria-hidden="true">
                    <DashboardIcon name="calendar" size={19} strokeWidth={1.65} />
                  </span>
                  <h3 className="miora-card-title">Next Steps</h3>
                </div>
                <ul className="miora-prelim-list">
                  {derivedNextSteps.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            </section>
          </div>
        </div>

        {/* Consent & Draft Notice Row */}
        <div className="miora-live-feedback-row">
          <label className="miora-checkbox-field miora-upload-consent">
            <input
              type="checkbox"
              checked={consentConfirmed}
              onChange={(e) => {
                setConsentConfirmed(e.target.checked);
                if (analysisStatus === 'error') {
                  setAnalysisStatus('idle');
                  setAnalysisError('');
                }
              }}
            />
            <span>Mother consent confirmed for asynchronous multimodal analysis</span>
          </label>

          {draftNotice && (
            <div className="miora-draft-pill" role="status">
              <DashboardIcon name="check" size={14} />
              <span>{draftNotice}</span>
            </div>
          )}
        </div>

        {/* Bottom Action Bar */}
        <div className="miora-live-action-bar">
          <button
            type="button"
            className="miora-btn-secondary"
            onClick={() => navigate(`/live-screening?mother=${activeMother.id}`)}
          >
            <DashboardIcon name="arrowLeft" size={15} />
            <span>Back to Screening</span>
          </button>

          <div className="miora-live-action-right">
            <button
              type="button"
              className="miora-btn-secondary"
              onClick={handleSaveDraft}
            >
              Save Draft
            </button>

            <button
              type="button"
              className="miora-cta-primary"
              disabled={!canRunAnalysis}
              onClick={handleRunAnalysis}
            >
              <DashboardIcon name="play" size={14} strokeWidth={2.1} />
              <span>
                {analysisStatus === 'processing' ? 'Running Analysis...' : 'Run Analysis'}
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
