import React, { useState, useRef } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import './medicalHistory.css';

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB
const ALLOWED_TYPES = [
  'application/pdf',
  'image/jpeg',
  'image/jpg',
  'image/png'
];
const STORAGE_KEY = 'miora_medical_history_v1';

export function MedicalHistoryScreen() {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  // 1. Diagnosis response state ('yes' | 'no' | 'not-sure')
  const [selectedOption, setSelectedOption] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.selectedOption) return parsed.selectedOption;
      }
    } catch {
      // ignore
    }
    return 'yes';
  });

  // 2. Uploaded documents state
  const [uploadedFiles, setUploadedFiles] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed.uploadedFiles) && parsed.uploadedFiles.length > 0) {
          return parsed.uploadedFiles;
        }
      }
    } catch {
      // ignore
    }
    return [
      {
        id: 'default-ppd-report',
        name: 'PPD_Diagnosis_Report.pdf',
        size: '1.2 MB',
        type: 'application/pdf',
      },
    ];
  });

  // 3. UI states
  const [isDragOver, setIsDragOver] = useState(false);
  const [validationError, setValidationError] = useState('');

  // Format bytes to human readable size
  const formatFileSize = (bytes) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  // Process incoming File objects from input or drop
  const handleFiles = (filesList) => {
    setValidationError('');
    const newFiles = [];
    const files = Array.from(filesList);

    for (const file of files) {
      const isAllowedType =
        ALLOWED_TYPES.includes(file.type.toLowerCase()) ||
        /\.(pdf|jpe?g|png)$/i.test(file.name);

      if (!isAllowedType) {
        setValidationError(`"${file.name}" is not a supported format. Please upload PDF, JPG, or PNG.`);
        return;
      }

      if (file.size > MAX_FILE_SIZE_BYTES) {
        setValidationError(`"${file.name}" exceeds the 10 MB limit (${formatFileSize(file.size)}).`);
        return;
      }

      newFiles.push({
        id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        name: file.name,
        size: formatFileSize(file.size),
        type: file.type || (file.name.endsWith('.pdf') ? 'application/pdf' : 'image/jpeg'),
      });
    }

    if (newFiles.length > 0) {
      setUploadedFiles((prev) => [...prev, ...newFiles]);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleFileInputChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(e.target.files);
      e.target.value = '';
    }
  };

  const removeFile = (id) => {
    setUploadedFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const handleSaveAndContinue = () => {
    try {
      const dataToSave = {
        selectedOption,
        uploadedFiles,
        savedAt: new Date().toISOString(),
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(dataToSave));
    } catch (err) {
      console.warn('Could not save medical history to localStorage:', err);
    }

    navigate('/patient/screening');
  };

  return (
    <div className="medhist-container">
      {/* Breadcrumb & Header Banner */}
      <div className="medhist-breadcrumb-bar">
        <NavLink to="/patient/dashboard" className="medhist-breadcrumb-link">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M3 10.5L12 3l9 7.5V20a1.5 1.5 0 0 1-1.5 1.5H4.5A1.5 1.5 0 0 1 3 20v-9.5z" />
            <path d="M9.5 21v-7h5v7" />
          </svg>
          <span>Home</span>
        </NavLink>
        <span className="medhist-breadcrumb-sep" aria-hidden="true">&rsaquo;</span>
        <span className="medhist-breadcrumb-current">Medical History</span>
      </div>

      <div className="patient-page-banner">
        <h1 className="patient-page-heading">Medical History</h1>
        <p className="patient-page-subheading">
          Help us understand your background for a more accurate and personalised emotional wellbeing screening.
        </p>
      </div>

      {/* Card 1: Question & Options with Clipboard Illustration */}
      <section className="patient-card medhist-question-card" aria-labelledby="question-heading">
        <div className="medhist-question-content">
          <h2 id="question-heading" className="medhist-question-text">
            Have you ever been diagnosed with Postpartum Depression (PPD) or received related treatment?
          </h2>
          <p className="medhist-question-note">
            Your responses remain private, encrypted, and strictly confidential.
          </p>

          <div className="medhist-options-grid" role="radiogroup" aria-labelledby="question-heading">
            {/* Option Yes */}
            <button
              type="button"
              className={`medhist-option-btn ${selectedOption === 'yes' ? 'is-selected' : ''}`}
              onClick={() => setSelectedOption('yes')}
              role="radio"
              aria-checked={selectedOption === 'yes'}
            >
              <span className="medhist-radio-indicator">
                {selectedOption === 'yes' && (
                  <svg width="11" height="11" viewBox="0 0 12 12" fill="none" stroke="white" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="2.5 6.2 4.8 8.6 9.5 3.6" />
                  </svg>
                )}
              </span>
              <span className="medhist-option-label">Yes</span>
            </button>

            {/* Option No */}
            <button
              type="button"
              className={`medhist-option-btn ${selectedOption === 'no' ? 'is-selected' : ''}`}
              onClick={() => setSelectedOption('no')}
              role="radio"
              aria-checked={selectedOption === 'no'}
            >
              <span className="medhist-radio-indicator">
                {selectedOption === 'no' && (
                  <svg width="11" height="11" viewBox="0 0 12 12" fill="none" stroke="white" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="2.5 6.2 4.8 8.6 9.5 3.6" />
                  </svg>
                )}
              </span>
              <span className="medhist-option-label">No</span>
            </button>

            {/* Option Not Sure */}
            <button
              type="button"
              className={`medhist-option-btn ${selectedOption === 'not-sure' ? 'is-selected' : ''}`}
              onClick={() => setSelectedOption('not-sure')}
              role="radio"
              aria-checked={selectedOption === 'not-sure'}
            >
              <span className="medhist-radio-indicator">
                {selectedOption === 'not-sure' && (
                  <svg width="11" height="11" viewBox="0 0 12 12" fill="none" stroke="white" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="2.5 6.2 4.8 8.6 9.5 3.6" />
                  </svg>
                )}
              </span>
              <span className="medhist-option-label">Not Sure</span>
            </button>
          </div>
        </div>

        {/* Right illustration */}
        <div className="medhist-question-illustration-wrap" aria-hidden="true">
          <img
            src="/assets/medical-history-clipboard.png"
            alt=""
            className="medhist-question-illustration"
          />
        </div>
      </section>

      {/* Card 2: Upload Relevant Records (Optional) */}
      <section className="patient-card medhist-upload-card" aria-labelledby="upload-card-heading">
        <div className="medhist-card-title-row">
          <h2 id="upload-card-heading" className="medhist-upload-title">
            Upload Relevant Records <span className="medhist-optional-tag">(Optional)</span>
          </h2>
          <span className="medhist-secure-badge">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
            256-bit Encrypted
          </span>
        </div>
        <p className="medhist-upload-subtitle">
          You can securely upload previous diagnoses, prescriptions, lab results, or hospital records.
        </p>

        {/* Dashed Drag & Drop Area */}
        <div
          className={`medhist-dropzone ${isDragOver ? 'is-dragover' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              fileInputRef.current?.click();
            }
          }}
          aria-label="Upload files by dragging or clicking"
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileInputChange}
            multiple
            accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
            style={{ display: 'none' }}
            tabIndex={-1}
          />

          <div className="medhist-cloud-icon-wrap" aria-hidden="true">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242" />
              <path d="M12 20V11" />
              <path d="m8 15 4-4 4 4" />
            </svg>
          </div>

          <p className="medhist-dropzone-prompt">
            Drag and drop files here, or{' '}
            <button
              type="button"
              className="medhist-click-upload-btn"
              onClick={(e) => {
                e.stopPropagation();
                fileInputRef.current?.click();
              }}
            >
              click to upload
            </button>
          </p>

          <span className="medhist-dropzone-hint">
            Supports PDF, JPG, PNG (up to 10 MB each)
          </span>
        </div>

        {/* Validation Notice if any */}
        {validationError && (
          <div className="medhist-validation-error" role="alert">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <span>{validationError}</span>
          </div>
        )}

        {/* Bottom Section: Uploaded Files & Save & Continue */}
        <div className="medhist-card2-bottom-row">
          <div className="medhist-uploaded-section">
            <div className="medhist-uploaded-header">
              <span>Uploaded Records</span>
              <span className="medhist-uploaded-count-pill">{uploadedFiles.length}</span>
            </div>

            <div className="medhist-uploaded-list">
              {uploadedFiles.length === 0 ? (
                <div className="medhist-uploaded-empty">No documents uploaded yet.</div>
              ) : (
                uploadedFiles.map((file) => {
                  const isPdf =
                    file.type === 'application/pdf' ||
                    file.name.toLowerCase().endsWith('.pdf');

                  return (
                    <div key={file.id} className="medhist-file-item">
                      <div className="medhist-file-info">
                        {isPdf ? (
                          <div className="medhist-pdf-badge" aria-label="PDF file">
                            PDF
                          </div>
                        ) : (
                          <div className="medhist-img-badge" aria-label="Image file">
                            IMG
                          </div>
                        )}
                        <div className="medhist-file-meta">
                          <span className="medhist-file-name" title={file.name}>{file.name}</span>
                          <span className="medhist-file-size">{file.size}</span>
                        </div>
                      </div>

                      <button
                        type="button"
                        className="medhist-file-remove-btn"
                        onClick={() => removeFile(file.id)}
                        aria-label={`Remove file ${file.name}`}
                      >
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                          <line x1="18" y1="6" x2="6" y2="18" />
                          <line x1="6" y1="6" x2="18" y2="18" />
                        </svg>
                      </button>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Action Row */}
          <div className="medhist-actions-bar">
            <button
              type="button"
              className="patient-btn-primary medhist-save-btn"
              onClick={handleSaveAndContinue}
            >
              <span>Save &amp; Continue</span>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <line x1="5" y1="12" x2="19" y2="12" />
                <polyline points="12 5 19 12 12 19" />
              </svg>
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

export default MedicalHistoryScreen;
