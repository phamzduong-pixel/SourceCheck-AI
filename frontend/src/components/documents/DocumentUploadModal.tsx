import React, { useState, useRef } from 'react';
import { documentService } from '../../services/documents';
import { ApiClientError } from '../../services/apiClient';

interface DocumentUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: () => void;
}

const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.txt'];
const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

export const DocumentUploadModal: React.FC<DocumentUploadModalProps> = ({
  isOpen,
  onClose,
  onUploadSuccess,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [chunkStrategy, setChunkStrategy] = useState<string>('fixed');
  const [sourceId, setSourceId] = useState<string>('');
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState<boolean>(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const validateFile = (file: File): string | null => {
    const fileName = file.name.toLowerCase();
    const isAllowed = ALLOWED_EXTENSIONS.some((ext) => fileName.endsWith(ext));

    if (!isAllowed) {
      return 'Định dạng tệp không được hỗ trợ. Vui lòng chọn tệp PDF, DOCX hoặc TXT.';
    }

    if (file.size > MAX_FILE_SIZE) {
      return 'Kích thước tệp quá lớn. Giới hạn tối đa là 50MB.';
    }

    if (file.size === 0) {
      return 'Tệp tin trống (0 bytes). Vui lòng chọn tệp có nội dung.';
    }

    return null;
  };

  const handleFileSelect = (file: File) => {
    setError(null);
    setSuccessMessage(null);
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      setSelectedFile(null);
      return;
    }
    setSelectedFile(file);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleUpload = async () => {
    if (!selectedFile || isUploading) return;

    setIsUploading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const response = await documentService.uploadDocument({
        file: selectedFile,
        chunk_strategy: chunkStrategy,
        source_id: sourceId.trim() ? sourceId.trim() : undefined,
      });

      setSuccessMessage(
        `Tài liệu "${response.title}" đã được nạp thành công với ${response.total_chunks} chunks!`
      );

      setTimeout(() => {
        setIsUploading(false);
        setSelectedFile(null);
        setSuccessMessage(null);
        onUploadSuccess();
        onClose();
      }, 1200);
    } catch (err: any) {
      setIsUploading(false);
      if (err instanceof ApiClientError) {
        if (err.statusCode === 400 || err.statusCode === 422) {
          setError(err.message || 'Tệp tin hoặc cấu hình không hợp lệ.');
        } else if (err.statusCode === 401) {
          setError('Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại.');
        } else if (err.statusCode >= 500) {
          setError('Lỗi máy chủ trong quá trình xử lý tài liệu. Vui lòng thử lại sau.');
        } else {
          setError(err.message || 'Tải lên tài liệu thất bại.');
        }
      } else {
        setError(err?.message || 'Đã xảy ra lỗi không xác định khi tải tài liệu.');
      }
    }
  };

  const resetFormAndClose = () => {
    if (isUploading) return;
    setSelectedFile(null);
    setError(null);
    setSuccessMessage(null);
    setChunkStrategy('fixed');
    setSourceId('');
    onClose();
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="upload-modal-overlay" data-testid="upload-modal-overlay" onClick={resetFormAndClose}>
      <div
        className="upload-modal-card"
        data-testid="upload-modal-card"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="upload-modal-title"
      >
        <div className="upload-modal-header">
          <div className="modal-title-wrap">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <h2 id="upload-modal-title">Nạp tài liệu vào Cơ sở tri thức</h2>
          </div>
          <button
            type="button"
            className="btn-modal-close"
            onClick={resetFormAndClose}
            disabled={isUploading}
            aria-label="Đóng"
            data-testid="btn-close-upload-modal"
          >
            ✕
          </button>
        </div>

        <div className="upload-modal-body">
          {/* Dropzone Area */}
          <div
            className={`file-dropzone ${isDragOver ? 'drag-over' : ''} ${selectedFile ? 'has-file' : ''}`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => !isUploading && fileInputRef.current?.click()}
            data-testid="file-dropzone"
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.txt"
              style={{ display: 'none' }}
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  handleFileSelect(e.target.files[0]);
                }
              }}
              data-testid="file-input"
            />

            {!selectedFile ? (
              <div className="dropzone-prompt">
                <svg className="dropzone-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="12" y1="18" x2="12" y2="12" />
                  <line x1="9" y1="15" x2="12" y2="12" />
                  <line x1="15" y1="15" x2="12" y2="12" />
                </svg>
                <p className="dropzone-main-text">
                  Kéo thả tệp tin vào đây hoặc <span className="browse-link">chọn từ thiết bị</span>
                </p>
                <p className="dropzone-sub-text">Hỗ trợ định dạng: <strong>PDF, DOCX, TXT</strong> (Tối đa 50MB)</p>
              </div>
            ) : (
              <div className="selected-file-preview" data-testid="selected-file-preview">
                <div className="file-info-group">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                  </svg>
                  <div className="file-details">
                    <span className="file-name" data-testid="selected-file-name">{selectedFile.name}</span>
                    <span className="file-size" data-testid="selected-file-size">{formatFileSize(selectedFile.size)}</span>
                  </div>
                </div>
                {!isUploading && (
                  <button
                    type="button"
                    className="btn-remove-file"
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedFile(null);
                    }}
                    aria-label="Chọn tệp khác"
                    data-testid="btn-remove-selected-file"
                  >
                    Thay đổi
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Configuration Options */}
          <div className="upload-options-grid">
            <div className="option-field">
              <label htmlFor="chunk-strategy-select" className="option-label">
                Chiến lược phân tách Chunks
              </label>
              <select
                id="chunk-strategy-select"
                className="option-select"
                value={chunkStrategy}
                onChange={(e) => setChunkStrategy(e.target.value)}
                disabled={isUploading}
                data-testid="chunk-strategy-select"
              >
                <option value="fixed">Cố định (Fixed Window - 500 ký tự / 50 overlap)</option>
                <option value="sentence">Theo câu & đoạn văn (Sentence Splitter)</option>
                <option value="recursive">Ngữ nghĩa đệ quy (Recursive Character)</option>
              </select>
            </div>

            <div className="option-field">
              <label htmlFor="source-id-input" className="option-label">
                Source ID / Nhãn nguồn (Tùy chọn)
              </label>
              <input
                id="source-id-input"
                type="text"
                placeholder="Ví dụ: bct-2024-report hoặc để trống"
                value={sourceId}
                onChange={(e) => setSourceId(e.target.value)}
                disabled={isUploading}
                className="option-input"
                data-testid="source-id-input"
              />
            </div>
          </div>

          {/* Feedback: Error Alert */}
          {error && (
            <div className="upload-error-alert" role="alert" data-testid="upload-error-alert">
              <span>{error}</span>
              <button
                type="button"
                onClick={() => setError(null)}
                style={{ background: 'none', border: 'none', color: '#991b1b', cursor: 'pointer', fontWeight: 'bold' }}
                aria-label="Đóng lỗi"
              >
                ✕
              </button>
            </div>
          )}

          {/* Feedback: Success Alert */}
          {successMessage && (
            <div className="upload-success-alert" role="status" data-testid="upload-success-alert">
              <span>✓ {successMessage}</span>
            </div>
          )}

          {/* Upload Progressing State */}
          {isUploading && (
            <div className="upload-loading-state" data-testid="upload-loading-state">
              <div className="spinner" style={{ width: '24px', height: '24px', borderWidth: '2.5px' }} />
              <p>Đang tải lên, trích xuất văn bản và phân tách chunks...</p>
            </div>
          )}
        </div>

        {/* Modal Footer Actions */}
        <div className="upload-modal-footer">
          <button
            type="button"
            className="btn-secondary"
            onClick={resetFormAndClose}
            disabled={isUploading}
            data-testid="btn-cancel-upload"
          >
            Hủy
          </button>
          <button
            type="button"
            className="btn-primary"
            onClick={handleUpload}
            disabled={!selectedFile || isUploading}
            data-testid="btn-submit-upload"
          >
            {isUploading ? 'Đang xử lý...' : 'Nạp tài liệu'}
          </button>
        </div>
      </div>
    </div>
  );
};
