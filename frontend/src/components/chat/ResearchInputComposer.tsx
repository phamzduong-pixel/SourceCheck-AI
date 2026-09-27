import React, { ChangeEvent, DragEvent, KeyboardEvent, useEffect, useRef, useState } from 'react';
import { documentService } from '../../services/documents';
import { QATaskType } from '../../types/qa';
import { useAIPreferences } from '../../hooks/useAIPreferences';

export interface ResearchSubmitOptions {
  taskType: QATaskType;
  documentIds: string[];
  searchEnabled: boolean;
}

type AttachmentStatus = 'uploading' | 'processing' | 'ready' | 'error';

interface Attachment {
  id: string;
  file: File;
  documentId?: string;
  status: AttachmentStatus;
  error?: string;
}

interface SpeechRecognitionLike {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((event: any) => void) | null;
  onerror: ((event: any) => void) | null;
  onend: (() => void) | null;
}

interface ResearchInputComposerProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (options: ResearchSubmitOptions) => void;
  onStop: () => void;
  isLoading: boolean;
  disabled?: boolean;
  variant?: 'welcome' | 'sticky';
}

const ALLOWED_EXTENSIONS = ['pdf', 'docx', 'txt'];

const isSupportedFile = (file: File) => {
  const extension = file.name.split('.').pop()?.toLowerCase();
  return Boolean(extension && ALLOWED_EXTENSIONS.includes(extension));
};

const PlusIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
    <path d="M12 5v14M5 12h14" />
  </svg>
);
const SearchIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
    <circle cx="10.8" cy="10.8" r="6.2" />
    <path d="m16 16 4.5 4.5" />
  </svg>
);

const MicrophoneIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
    <rect x="8" y="3" width="8" height="12" rx="4" />
    <path d="M5 11a7 7 0 0 0 14 0M12 18v3M8.5 21h7" />
  </svg>
);

const SendIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
    <path d="m21 3-7.5 18-3.8-7.7L2 9.5 21 3Z" />
    <path d="m9.7 13.3 4.2-4.2" />
  </svg>
);

const StopIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
    <rect x="6.5" y="6.5" width="11" height="11" rx="1.5" />
  </svg>
);

export const ResearchInputComposer: React.FC<ResearchInputComposerProps> = ({
  value,
  onChange,
  onSubmit,
  onStop,
  isLoading,
  disabled = false,
  variant = 'welcome',
}) => {
  const { uiLanguage } = useAIPreferences();
  const copy = uiLanguage === 'vi'
    ? {
        placeholder: '\u0110\u1eb7t c\u00e2u h\u1ecfi ho\u1eb7c nh\u1eadp n\u1ed9i dung c\u1ea7n tra c\u1ee9u...',
        attach: 'Th\u00eam t\u00e0i li\u1ec7u',
        qa: 'H\u1ecfi & \u0111\u00e1p',
        summary: 'T\u00f3m t\u1eaft',
        chooseQa: 'Ch\u1ecdn ch\u1ebf \u0111\u1ed9 H\u1ecfi & \u0111\u00e1p',
        summarize: 'T\u00f3m t\u1eaft t\u00e0i li\u1ec7u',
        voice: 'Nh\u1eadp b\u1eb1ng gi\u1ecdng n\u00f3i',
        listening: '\u0110ang nghe...',
        stop: 'D\u1eebng x\u1eed l\u00fd',
        send: 'G\u1eedi c\u00e2u h\u1ecfi',
        search: 'T\u00ecm ki\u1ebfm',
        searchOff: 'T\u00ecm ki\u1ebfm trong ngu\u1ed3n',
        searchOn: '\u0110ang b\u1eadt t\u00ecm ki\u1ebfm',
        invalidFile: 'Ch\u1ec9 h\u1ed7 tr\u1ee3 t\u00e0i li\u1ec7u PDF, DOCX ho\u1eb7c TXT.',
        uploadFailed: 'Kh\u00f4ng th\u1ec3 t\u1ea3i t\u00e0i li\u1ec7u l\u00ean.',
        summaryError: 'T\u00f3m t\u1eaft c\u1ea7n \u0111\u00fang m\u1ed9t t\u00e0i li\u1ec7u \u0111\u00e3 t\u1ea3i l\u00ean v\u00e0 x\u1eed l\u00fd xong.',
        drop: 'Th\u1ea3 t\u00e0i li\u1ec7u \u0111\u1ec3 th\u00eam v\u00e0o SourceCheck',
        uploading: '\u0110ang t\u1ea3i l\u00ean',
        processing: '\u0110ang x\u1eed l\u00fd',
        ready: '\u2713 S\u1eb5n s\u00e0ng',
        uploadError: 'T\u1ea3i l\u00ean th\u1ea5t b\u1ea1i',
        voiceError: 'Kh\u00f4ng th\u1ec3 nh\u1eadn di\u1ec7n gi\u1ecdng n\u00f3i. Vui l\u00f2ng th\u1eed l\u1ea1i ho\u1eb7c nh\u1eadp v\u0103n b\u1ea3n.',
        unsupported: 'Tr\u00ecnh duy\u1ec7t n\u00e0y ch\u01b0a h\u1ed7 tr\u1ee3 nh\u1eadp b\u1eb1ng gi\u1ecdng n\u00f3i. H\u00e3y nh\u1eadp v\u0103n b\u1ea3n tr\u1ef1c ti\u1ebfp.',
      }
    : {
        placeholder: 'Ask a question or enter content to research...',
        attach: 'Add document',
        qa: 'Q&A',
        summary: 'Summary',
        chooseQa: 'Choose Q&A mode',
        summarize: 'Summarize document',
        voice: 'Voice input',
        listening: 'Listening...',
        stop: 'Stop processing',
        send: 'Send question',
        search: 'Search',
        searchOff: 'Search within sources',
        searchOn: 'Search enabled',
        invalidFile: 'Only PDF, DOCX, or TXT documents are supported.',
        uploadFailed: 'Unable to upload the document.',
        summaryError: 'Summary requires exactly one uploaded and processed document.',
        drop: 'Drop a document to add it to SourceCheck',
        uploading: 'Uploading',
        processing: 'Processing',
        ready: '\u2713 Ready',
        uploadError: 'Upload failed',
        voiceError: 'Voice input failed. Please try again or type your text.',
        unsupported: 'Voice input is not supported in this browser. Please type your text instead.',
      };
  const [taskType, setTaskType] = useState<QATaskType>('qa');
  const [isSearchEnabled, setIsSearchEnabled] = useState(true);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [composerError, setComposerError] = useState<string | null>(null);
  const [isDragActive, setIsDragActive] = useState(false);
  const [isFocused, setIsFocused] = useState(false);
  const [voiceState, setVoiceState] = useState<'idle' | 'listening' | 'error' | 'unsupported'>('idle');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);

  const readyDocumentIds = attachments
    .filter((attachment) => attachment.status === 'ready' && attachment.documentId)
    .map((attachment) => attachment.documentId as string);
  const isUploading = attachments.some(
    (attachment) => attachment.status === 'uploading' || attachment.status === 'processing'
  );
  const isBusy = disabled || isLoading || isUploading;
  const isExpanded = Boolean(isFocused || value.length > 0 || attachments.length > 0 || isDragActive || isLoading || voiceState === 'listening' || composerError);

  useEffect(() => () => recognitionRef.current?.abort(), []);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const maxHeight = variant === 'sticky' ? 140 : 220;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, maxHeight) + 'px';
    textarea.style.overflowY = textarea.scrollHeight > maxHeight ? 'auto' : 'hidden';
  }, [value, variant]);

  const updateAttachment = (id: string, patch: Partial<Attachment>) => {
    setAttachments((current) =>
      current.map((attachment) =>
        attachment.id === id ? { ...attachment, ...patch } : attachment
      )
    );
  };

  const uploadFiles = async (files: File[]) => {
    if (isBusy) return;
    setComposerError(null);

    for (const file of files) {
      if (!isSupportedFile(file)) {
        setComposerError(copy.invalidFile);
        continue;
      }

      const attachmentId = file.name + '-' + file.size + '-' + Date.now() + '-' + Math.random();
      setAttachments((current) => [
        ...current,
        { id: attachmentId, file, status: 'uploading' },
      ]);

      try {
        const response = await documentService.uploadDocument({ file });
        updateAttachment(attachmentId, { status: 'processing' });
        await new Promise((resolve) => window.setTimeout(resolve, 0));
        updateAttachment(attachmentId, {
          status: 'ready',
          documentId: response.document_id,
        });
      } catch (error: any) {
        updateAttachment(attachmentId, {
          status: 'error',
          error: error?.message || copy.uploadFailed,
        });
      }
    }
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    void uploadFiles(files);
    event.target.value = '';
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragActive(false);
    void uploadFiles(Array.from(event.dataTransfer.files || []));
  };

  const handleSubmit = () => {
    if (!value.trim() || isBusy) return;
    if (taskType === 'summary' && readyDocumentIds.length !== 1) {
      setComposerError(copy.summaryError);
      return;
    }
    setComposerError(null);
    onSubmit({ taskType, documentIds: readyDocumentIds, searchEnabled: isSearchEnabled });
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key !== 'Enter') return;
    if (event.shiftKey) return;
    event.preventDefault();
    handleSubmit();
  };

  const toggleVoice = () => {
    if (isBusy) return;

    if (voiceState === 'listening') {
      recognitionRef.current?.stop();
      return;
    }

    const RecognitionConstructor =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!RecognitionConstructor) {
      setVoiceState('unsupported');
      setComposerError(copy.unsupported);
      return;
    }

    const recognition: SpeechRecognitionLike = new RecognitionConstructor();
    recognition.lang = 'vi-VN';
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.onresult = (event: any) => {
      const transcript = Array.from(event.results || [])
        .map((result: any) => result?.[0]?.transcript || '')
        .join(' ')
        .trim();
      if (transcript) {
        onChange(value.trim() ? value.trim() + ' ' + transcript : transcript);
      }
      setVoiceState('idle');
    };
    recognition.onerror = () => {
      setVoiceState('error');
      setComposerError(copy.voiceError);
    };
    recognition.onend = () => {
      setVoiceState((current) => (current === 'listening' ? 'idle' : current));
    };
    recognitionRef.current = recognition;
    setComposerError(null);
    setVoiceState('listening');
    recognition.start();
  };

  const handleComposerBlur = (event: React.FocusEvent<HTMLDivElement>) => {
    const nextTarget = event.relatedTarget as Node | null;
    if (!nextTarget || !event.currentTarget.contains(nextTarget)) {
      setIsFocused(false);
    }
  };
  const removeAttachment = (attachmentId: string) => {
    if (isBusy) return;
    setAttachments((current) => current.filter((attachment) => attachment.id !== attachmentId));
  };

  return (
    <div
      className={[
        'research-input-composer',
        variant === 'sticky' ? 'is-sticky' : '',
        isExpanded ? 'is-expanded' : 'is-compact',
        isDragActive ? 'is-drag-active' : '',
      ].filter(Boolean).join(' ')}
      onFocusCapture={() => setIsFocused(true)}
      onBlurCapture={handleComposerBlur}
      onDragOver={(event) => {
        event.preventDefault();
        if (!isBusy) setIsDragActive(true);
      }}
      onDragLeave={() => setIsDragActive(false)}
      onDrop={handleDrop}
      data-testid="research-input-composer"
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
        multiple
        hidden
        onChange={handleFileChange}
        data-testid="research-file-input"
      />

      {isDragActive && (
        <div className="research-drop-overlay" data-testid="research-drop-overlay">
          <span aria-hidden="true">&#128206;</span>
          <span>{copy.drop}</span>
        </div>
      )}

      {attachments.length > 0 && (
        <div className="research-attachment-list" data-testid="research-attachment-list">
          {attachments.map((attachment) => (
            <div
              className={'research-file-chip is-' + attachment.status}
              key={attachment.id}
              data-testid={'file-chip-' + attachment.file.name}
            >
              <span className="research-file-icon" aria-hidden="true">&#128196;</span>
              <span className="research-file-name">{attachment.file.name}</span>
              <span className="research-file-status">
                {attachment.status === 'uploading' && copy.uploading}
                {attachment.status === 'processing' && copy.processing}
                {attachment.status === 'ready' && copy.ready}
                {attachment.status === 'error' && (attachment.error || copy.uploadError)}
              </span>
              <button
                type="button"
                onClick={() => removeAttachment(attachment.id)}
                disabled={isBusy}
                aria-label={'Remove ' + attachment.file.name}
                data-testid={'remove-file-' + attachment.file.name}
              >
                {'\u00d7'}
              </button>
            </div>
          ))}
        </div>
      )}

      <textarea
        ref={textareaRef}
        className={variant === 'sticky' ? 'chat-sticky-textarea question-textarea' : 'question-textarea'}
        placeholder={copy.placeholder}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled || isLoading}
        rows={variant === 'sticky' || !isExpanded ? 1 : 2}
        aria-label={copy.placeholder}
        data-testid="question-textarea"
      />

      {composerError && (
        <p className="research-composer-error" role="alert" data-testid="research-composer-error">
          {composerError}
        </p>
      )}

      <div className="research-composer-toolbar-shell" data-testid="research-composer-toolbar" aria-hidden={!isExpanded}>
        <div className="research-input-toolbar composer-controls">
          <div className="research-input-leading-controls">
            <button
              type="button"
              className="research-toolbar-button research-icon-button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isBusy}
              aria-label={copy.attach}
              title={copy.attach}
              data-testid="btn-attach-file"
            >
              <PlusIcon />
            </button>
            <button
              type="button"
              className={'research-toolbar-button research-search-toggle ' + (isSearchEnabled ? 'is-active' : '')}
              onClick={() => setIsSearchEnabled((current) => !current)}
              disabled={isBusy || taskType === 'summary'}
              aria-pressed={isSearchEnabled}
              aria-label={isSearchEnabled ? copy.searchOn : copy.searchOff}
              title={isSearchEnabled ? copy.searchOn : copy.searchOff}
              data-testid="btn-search-toggle"
            >
              <SearchIcon />
              <span className="research-search-label">{copy.search}</span>

            </button>

            <label
              className="research-task-select"
              data-tooltip={taskType === 'summary' ? copy.summarize : copy.chooseQa}
            >
              <select
                value={taskType}
                onChange={(event) => setTaskType(event.target.value as QATaskType)}
                disabled={isBusy}
                aria-label={taskType === 'summary' ? copy.summarize : copy.chooseQa}
                title={taskType === 'summary' ? copy.summarize : copy.chooseQa}
                data-testid="research-task-type"
              >
                <option value="qa">{copy.qa}</option>
                <option value="summary">{copy.summary}</option>
              </select>
            </label>
          </div>

          <div className="research-input-actions">
            <button
              type="button"
              className={'research-toolbar-button research-icon-button ' + (voiceState === 'listening' ? 'is-listening' : '')}
              onClick={toggleVoice}
              disabled={isBusy}
              aria-label={copy.voice}
              title={voiceState === 'listening' ? copy.listening : copy.voice}
              data-testid="btn-voice-input"
            >
              <MicrophoneIcon />
            </button>

            {isLoading ? (
              <button
                type="button"
                className="btn-ask research-stop-button research-icon-button"
                onClick={onStop}
                aria-label={copy.stop}
                title={copy.stop}
                data-testid="btn-stop"
              >
                <StopIcon />
              </button>
            ) : (
              <button
                type="button"
                className="btn-ask research-icon-button"
                onClick={handleSubmit}
                disabled={!value.trim() || isBusy || (taskType === 'summary' && readyDocumentIds.length !== 1)}
                aria-label={copy.send}
                title={copy.send}
                data-testid="btn-ask"
              >
                <SendIcon />
              </button>
            )}
          </div>
        </div>
      </div>

      {voiceState === 'unsupported' && (
        <p className="research-voice-fallback" data-testid="voice-unsupported">
          {copy.unsupported}
        </p>
      )}
    </div>
  );
};
