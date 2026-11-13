import React, { useRef, useState } from 'react';
import { DashboardIcon } from './DashboardIcon.jsx';

export function ModalityUploadCard({ spec, onFilesAdded }) {
  const inputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFileList = (fileList) => {
    if (!fileList || fileList.length === 0) return;
    onFilesAdded(Array.from(fileList), spec.id);
  };

  return (
    <div
      className={`miora-upload-dropzone ${isDragging ? 'is-dragging' : ''}`}
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={(e) => {
        e.preventDefault();
        setIsDragging(false);
      }}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragging(false);
        handleFileList(e.dataTransfer?.files);
      }}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={spec.accept}
        className="sr-only"
        aria-label={`Upload ${spec.label} files`}
        onChange={(e) => {
          handleFileList(e.target.files);
          e.target.value = '';
        }}
      />

      <span className="miora-upload-zone-icon" aria-hidden="true">
        <DashboardIcon name={spec.icon} size={23} strokeWidth={1.65} />
      </span>

      <div className="miora-upload-zone-title">{spec.label}</div>
      <div className="miora-upload-zone-formats">
        ({spec.extensions.join(', ')})
      </div>

      <button
        type="button"
        className="miora-upload-zone-btn"
        onClick={() => inputRef.current?.click()}
      >
        Upload File
      </button>
    </div>
  );
}

