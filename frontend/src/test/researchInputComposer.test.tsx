import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ComponentProps } from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { ResearchInputComposer } from '../components/chat/ResearchInputComposer';
import { documentService } from '../services/documents';
import { AIPreferencesProvider } from '../context/AIPreferencesContext';

const renderComposer = (overrides: Partial<ComponentProps<typeof ResearchInputComposer>> = {}) => {
  const onChange = overrides.onChange || vi.fn();
  const onSubmit = overrides.onSubmit || vi.fn();
  const onStop = overrides.onStop || vi.fn();
  render(
    <ResearchInputComposer
      value={overrides.value ?? ''}
      onChange={onChange}
      onSubmit={onSubmit}
      onStop={onStop}
      isLoading={overrides.isLoading ?? false}
      disabled={overrides.disabled}
      variant="welcome"
    />
  );
  return { onChange, onSubmit, onStop };
};

const uploadResponse = {
  document_id: 'uploaded-doc-1',
  title: 'paper.pdf',
  doc_type: 'pdf',
  page_count: 1,
  total_chunks: 2,
  metadata: {},
  chunks: [],
};

describe('Research Input Composer (Checkpoint F1)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    delete (window as any).SpeechRecognition;
    delete (window as any).webkitSpeechRecognition;
    localStorage.removeItem('sourcecheck_ui_language');
  });

  it('uploads a supported file, renders its chip, and scopes the submitted request', async () => {
    vi.spyOn(documentService, 'uploadDocument').mockResolvedValue(uploadResponse);
    const { onSubmit } = renderComposer({ value: 'Summarize this document' });

    fireEvent.change(screen.getByTestId('research-task-type'), {
      target: { value: 'summary' },
    });
    const file = new File(['paper'], 'paper.pdf', { type: 'application/pdf' });
    fireEvent.change(screen.getByTestId('research-file-input'), {
      target: { files: [file] },
    });

    expect(await screen.findByTestId('file-chip-paper.pdf')).toHaveTextContent(/S\u1eb5n s\u00e0ng/i);
    fireEvent.click(screen.getByTestId('btn-ask'));

    expect(onSubmit).toHaveBeenCalledWith({
      taskType: 'summary',
      documentIds: ['uploaded-doc-1'],
      searchEnabled: true,
    });
  });

  it('shows an error for an invalid attachment type', async () => {
    const { onSubmit } = renderComposer({ value: 'Question' });
    const file = new File(['image'], 'image.png', { type: 'image/png' });

    fireEvent.change(screen.getByTestId('research-file-input'), {
      target: { files: [file] },
    });

    expect(await screen.findByTestId('research-composer-error')).toHaveTextContent(/PDF, DOCX ho\u1eb7c TXT/i);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('removes a selected file and its document scope', async () => {
    vi.spyOn(documentService, 'uploadDocument').mockResolvedValue(uploadResponse);
    renderComposer({ value: 'Question' });
    const file = new File(['paper'], 'remove-me.txt', { type: 'text/plain' });

    fireEvent.change(screen.getByTestId('research-file-input'), {
      target: { files: [file] },
    });
    expect(await screen.findByTestId('file-chip-remove-me.txt')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('remove-file-remove-me.txt'));
    expect(screen.queryByTestId('file-chip-remove-me.txt')).not.toBeInTheDocument();
  });

  it('writes a Vietnamese speech transcript into the textarea without submitting', async () => {
    let recognition: any;
    class FakeRecognition {
      lang = '';
      continuous = false;
      interimResults = false;
      onresult: any = null;
      onerror: any = null;
      onend: any = null;
      start = vi.fn();
      stop = vi.fn();
      abort = vi.fn();
      constructor() {
        recognition = this;
      }
    }
    (window as any).SpeechRecognition = FakeRecognition;

    const onChange = vi.fn();
    const onSubmit = vi.fn();
    renderComposer({ value: 'Mở đầu', onChange, onSubmit });

    fireEvent.click(screen.getByTestId('btn-voice-input'));
    expect(recognition.lang).toBe('vi-VN');
    expect(recognition.start).toHaveBeenCalled();

    act(() => {
      recognition.onresult({
        results: [[{ transcript: 'nội dung ghi âm' }]],
      });
    });

    expect(onChange).toHaveBeenCalledWith('Mở đầu nội dung ghi âm');
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('shows a clear fallback when speech recognition is unavailable', async () => {
    renderComposer({ value: 'Question' });

    fireEvent.click(screen.getByTestId('btn-voice-input'));

    expect(await screen.findByTestId('voice-unsupported')).toBeInTheDocument();
    expect(screen.getByTestId('research-composer-error')).toHaveTextContent(/ch\u01b0a h\u1ed7 tr\u1ee3/i);
  });

  it('submits on Enter, preserves Shift+Enter, and shows Stop while loading', () => {
    const { onSubmit, onStop } = renderComposer({ value: 'Question' });
    const textarea = screen.getByTestId('question-textarea');

    fireEvent.keyDown(textarea, { key: 'Enter' });
    expect(onSubmit).toHaveBeenCalledWith({ taskType: 'qa', documentIds: [], searchEnabled: true });

    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true });
    expect(onSubmit).toHaveBeenCalledTimes(1);

    const loading = renderComposer({ value: 'Question', isLoading: true, onStop });
    expect(screen.getAllByTestId('btn-stop')).toHaveLength(1);
    fireEvent.click(screen.getByTestId('btn-stop'));
    expect(loading.onStop).toHaveBeenCalledTimes(1);
    expect(screen.getAllByTestId('btn-attach-file')[1]).toBeDisabled();
  });

  it('renders the research placeholder and drag-and-drop overlay', async () => {
    vi.spyOn(documentService, 'uploadDocument').mockResolvedValue({
      ...uploadResponse,
      document_id: 'dropped-doc-1',
      title: 'dropped.txt',
    });
    renderComposer();

    const composer = screen.getByTestId('research-input-composer');
    const textarea = screen.getByTestId('question-textarea');
    expect(textarea).toHaveAttribute(
      'placeholder',
      '\u0110\u1eb7t c\u00e2u h\u1ecfi ho\u1eb7c nh\u1eadp n\u1ed9i dung c\u1ea7n tra c\u1ee9u...'
    );

    fireEvent.dragOver(composer, { dataTransfer: { files: [] } });
    expect(screen.getByTestId('research-drop-overlay')).toHaveTextContent(
      /Th\u1ea3 t\u00e0i li\u1ec7u \u0111\u1ec3 th\u00eam v\u00e0o SourceCheck/
    );

    const file = new File(['evidence'], 'dropped.txt', { type: 'text/plain' });
    fireEvent.drop(composer, { dataTransfer: { files: [file] } });
    expect(await screen.findByTestId('file-chip-dropped.txt')).toHaveTextContent(/S\u1eb5n s\u00e0ng/i);
  });
  it('starts compact and expands when the textarea receives focus', () => {
    renderComposer();

    const composer = screen.getByTestId('research-input-composer');
    const toolbar = screen.getByTestId('research-composer-toolbar');
    expect(composer).toHaveClass('is-compact');
    expect(toolbar).toHaveAttribute('aria-hidden', 'true');

    fireEvent.focus(screen.getByTestId('question-textarea'));

    expect(composer).toHaveClass('is-expanded');
    expect(toolbar).toHaveAttribute('aria-hidden', 'false');
  });

  it('opens the file picker from the plus document control', () => {
    const clickSpy = vi.spyOn(HTMLInputElement.prototype, 'click');
    renderComposer();

    fireEvent.click(screen.getByTestId('btn-attach-file'));

    expect(clickSpy).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId('btn-attach-file')).toHaveAttribute('title');
    clickSpy.mockRestore();
  });
  it('uses compact icon controls, exposes tooltips, and places microphone beside Send', () => {
    renderComposer({ value: 'Question' });

    const toolbar = screen.getByTestId('research-composer-toolbar');
    expect(toolbar).toHaveAttribute('aria-hidden', 'false');

    const attachment = screen.getByTestId('btn-attach-file');
    const microphone = screen.getByTestId('btn-voice-input');
    const send = screen.getByTestId('btn-ask');
    const taskSelect = screen.getByTestId('research-task-type');

    expect(attachment).toHaveAttribute('title', 'Th\u00eam t\u00e0i li\u1ec7u');
    expect(taskSelect).toHaveValue('qa');
    expect(taskSelect).toHaveAttribute('title', 'Ch\u1ecdn ch\u1ebf \u0111\u1ed9 H\u1ecfi & \u0111\u00e1p');
    expect(microphone).toHaveAttribute('title', 'Nh\u1eadp b\u1eb1ng gi\u1ecdng n\u00f3i');
    expect(send).toHaveAttribute('title', 'G\u1eedi c\u00e2u h\u1ecfi');

    const toolbarButtons = Array.from(toolbar.querySelectorAll('button'));
    expect(toolbarButtons.map((button) => button.dataset.testid)).toEqual([
      'btn-attach-file',
      'btn-search-toggle',
      'btn-voice-input',
      'btn-ask',
    ]);
  });


  it('toggles corpus Search and includes the selected state in the submit payload', () => {
    const { onSubmit } = renderComposer({ value: 'Tìm phần phương pháp' });
    const search = screen.getByTestId('btn-search-toggle');

    expect(search).toHaveAttribute('aria-pressed', 'true');
    expect(search).toHaveAttribute('title', '\u0110ang b\u1eadt t\u00ecm ki\u1ebfm');
    expect(search).toHaveTextContent('T\u00ecm ki\u1ebfm');
    expect(search.querySelector('.research-search-check')).toBeNull();

    fireEvent.click(search);
    expect(search).toHaveAttribute('aria-pressed', 'false');
    expect(search).toHaveAttribute('title', 'T\u00ecm ki\u1ebfm trong ngu\u1ed3n');

    fireEvent.click(screen.getByTestId('btn-ask'));
    expect(onSubmit).toHaveBeenCalledWith({
      taskType: 'qa',
      documentIds: [],
      searchEnabled: false,
    });
  });
  it('localizes operation labels and composer copy when the UI language is English', () => {
    localStorage.setItem('sourcecheck_ui_language', 'en');
    render(
      <AIPreferencesProvider>
        <ResearchInputComposer
          value="Question"
          onChange={vi.fn()}
          onSubmit={vi.fn()}
          onStop={vi.fn()}
          isLoading={false}
        />
      </AIPreferencesProvider>
    );

    expect(screen.getByTestId('question-textarea')).toHaveAttribute(
      'placeholder',
      'Ask a question or enter content to research...'
    );
    expect(screen.getByTestId('research-task-type')).toHaveTextContent('Q&A');
    expect(screen.getByTestId('research-task-type')).toHaveTextContent('Summary');
    expect(screen.getByTestId('btn-attach-file')).toHaveAttribute('title', 'Add document');
  });
  it('renders SVG action icons without visible legacy toolbar labels', () => {
    renderComposer({ value: 'Question' });

    const toolbar = screen.getByTestId('research-composer-toolbar');
    const attachment = screen.getByTestId('btn-attach-file');
    const microphone = screen.getByTestId('btn-voice-input');
    const send = screen.getByTestId('btn-ask');

    expect(attachment.querySelector('svg')).toBeInTheDocument();
    expect(microphone.querySelector('svg')).toBeInTheDocument();
    expect(send.querySelector('svg')).toBeInTheDocument();
    expect(toolbar.querySelector('.sr-only')).toBeNull();
    expect(toolbar).not.toHaveTextContent('Th\u00eam t\u00e0i li\u1ec7u');
    expect(toolbar).not.toHaveTextContent('Gi\u1ecdng n\u00f3i');
    expect(toolbar).not.toHaveTextContent('G\u1eedi');
  });
});