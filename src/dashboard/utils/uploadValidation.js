export const MODALITY_SPECS = {
  text: {
    id: 'text',
    label: 'Text',
    icon: 'fileText',
    extensions: ['.txt', '.pdf', '.docx'],
    accept: '.txt,.pdf,.docx,text/plain,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    maxBytes: 10 * 1024 * 1024, // 10 MB
    maxLabel: '10 MB',
  },
  voice: {
    id: 'voice',
    label: 'Voice / Audio',
    icon: 'mic',
    extensions: ['.wav', '.mp3', '.m4a'],
    accept: '.wav,.mp3,.m4a,audio/wav,audio/mpeg,audio/mp4,audio/x-m4a',
    maxBytes: 50 * 1024 * 1024, // 50 MB
    maxLabel: '50 MB',
  },
  video: {
    id: 'video',
    label: 'Video',
    icon: 'video',
    extensions: ['.mp4', '.mov', '.avi'],
    accept: '.mp4,.mov,.avi,video/mp4,video/quicktime,video/x-msvideo',
    maxBytes: 150 * 1024 * 1024, // 150 MB
    maxLabel: '150 MB',
  },
};

export function getFileExtension(fileName = '') {
  const idx = fileName.lastIndexOf('.');
  return idx >= 0 ? fileName.slice(idx).toLowerCase() : '';
}

export function validateUploadFile(file, modality) {
  const spec = MODALITY_SPECS[modality];
  if (!spec) {
    return { valid: false, error: 'Unsupported modality selected.' };
  }
  if (!file || !file.name) {
    return { valid: false, error: 'No file selected.' };
  }

  const ext = getFileExtension(file.name);
  if (!spec.extensions.includes(ext)) {
    return {
      valid: false,
      error: `"${file.name}" is not a supported ${spec.label} file. Accepted formats: ${spec.extensions.join(', ')}.`,
    };
  }

  if (typeof file.size === 'number') {
    if (file.size === 0) {
      return { valid: false, error: `"${file.name}" is empty (0 bytes).` };
    }
    if (file.size > spec.maxBytes) {
      return {
        valid: false,
        error: `"${file.name}" exceeds the ${spec.maxLabel} limit for ${spec.label} files.`,
      };
    }
  }

  return { valid: true };
}

export function formatFileSize(bytes) {
  if (typeof bytes !== 'number' || Number.isNaN(bytes)) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatDuration(seconds) {
  if (typeof seconds !== 'number' || !Number.isFinite(seconds) || seconds <= 0) {
    return null;
  }
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

export function readMediaDuration(file, modality) {
  if (modality !== 'voice' && modality !== 'video') {
    return Promise.resolve(null);
  }
  if (typeof document === 'undefined' || typeof URL === 'undefined' || !URL.createObjectURL) {
    return Promise.resolve(null);
  }

  return new Promise((resolve) => {
    let settled = false;
    const tagName = modality === 'video' ? 'video' : 'audio';
    const mediaEl = document.createElement(tagName);
    let objectUrl = '';

    const finish = (duration) => {
      if (settled) return;
      settled = true;
      if (objectUrl && URL.revokeObjectURL) {
        try {
          URL.revokeObjectURL(objectUrl);
        } catch {
          // ignore
        }
      }
      resolve(duration);
    };

    const timer = setTimeout(() => finish(null), 1000);

    try {
      objectUrl = URL.createObjectURL(file);
      mediaEl.preload = 'metadata';
      mediaEl.onloadedmetadata = () => {
        clearTimeout(timer);
        finish(formatDuration(mediaEl.duration));
      };
      mediaEl.onerror = () => {
        clearTimeout(timer);
        finish(null);
      };
      mediaEl.src = objectUrl;
    } catch {
      clearTimeout(timer);
      finish(null);
    }
  });
}

