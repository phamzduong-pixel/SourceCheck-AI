/**
 * Test Suite for Main Research Chat Assistant Feature (FE-CHAT-01).
 * Tests Perplexity-style research assistant workflow:
 * - Empty / Welcome state with prompt starters
 * - Submitting queries via Enter key and button click
 * - Multi-turn conversation display (user bubble & grounded AI answer)
 * - Interactive citations & Evidence Drawer inspection
 * - Loading indicator during research
 * - Error alert handling
 * - Starting a new session / Reset conversation via '+ Tra cứu mới'
 * - Independent UI and AI language settings
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ResearchChatPage } from '../pages/ResearchChatPage';
import { qaService } from '../services/qa';
import { ApiClientError } from '../services/apiClient';
import { FinalAnswerResponse } from '../types/qa';
import {
  AIPreferencesProvider,
  UI_LANGUAGE_STORAGE_KEY,
  AI_LANGUAGE_STORAGE_KEY,
} from '../context/AIPreferencesContext';
import { AuthProvider } from '../context/AuthContext';
import conversationService from '../services/conversations';

const mockFinalAnswer: FinalAnswerResponse = {
  question: 'Việt Nam gia nhập WTO năm nào?',
  answer: 'Việt Nam chính thức trở thành thành viên thứ 150 của WTO vào ngày 11 tháng 1 năm 2007 [1]. Tiến trình này kéo dài 11 năm đàm phán [2].',
  status: 'SUPPORTED',
  claims: [
    {
      claim_id: 'claim-1',
      text: 'Việt Nam chính thức trở thành thành viên thứ 150 của WTO vào năm 2007',
      order: 1,
      context_sentence: 'Việt Nam chính thức trở thành thành viên thứ 150 của WTO vào ngày 11 tháng 1 năm 2007.',
      verifiable: true,
    },
    {
      claim_id: 'claim-2',
      text: 'Tiến trình đàm phán gia nhập kéo dài 11 năm',
      order: 2,
      context_sentence: 'Tiến trình này kéo dài 11 năm đàm phán.',
      verifiable: true,
    },
  ],
  evidence: [
    {
      evidence_id: 'E1',
      chunk_id: 'chunk-101',
      content: 'Ngày 11-1-2007, Việt Nam chính thức trở thành thành viên thứ 150 của WTO.',
      score: 0.98,
      source_title: 'Cổng thông tin điện tử Bộ Công Thương',
      source_url: 'https://moit.gov.vn/wto-2007',
      publisher: 'Bộ Công Thương',
      page_number: 1,
    },
    {
      evidence_id: 'E2',
      chunk_id: 'chunk-102',
      content: 'Sau 11 năm đàm phán kiên trì kể từ năm 1995, Việt Nam đã hoàn tất tiến trình.',
      score: 0.92,
      source_title: 'Báo Chính phủ',
      source_url: 'https://baochinhphu.vn/wto-11-nam',
      publisher: 'Báo Chính phủ',
      page_number: 2,
    },
  ],
  citations: [
    {
      citation_id: 'cit-1',
      claim_id: 'claim-1',
      evidence_id: 'E1',
      source_name: 'Bộ Công Thương',
      source_url: 'https://moit.gov.vn/wto-2007',
      quote: 'Ngày 11-1-2007, Việt Nam chính thức trở thành thành viên thứ 150 của WTO.',
      stance: 'SUPPORTS',
      footnote_index: 1,
      relevance_score: 0.98,
    },
    {
      citation_id: 'cit-2',
      claim_id: 'claim-2',
      evidence_id: 'E2',
      source_name: 'Báo Chính phủ',
      source_url: 'https://baochinhphu.vn/wto-11-nam',
      quote: 'Sau 11 năm đàm phán kiên trì...',
      stance: 'SUPPORTS',
      footnote_index: 2,
      relevance_score: 0.92,
    },
  ],
  evidence_coverage: 1.0,
  verification_summary: {
    SUPPORTED: 2,
    PARTIALLY_SUPPORTED: 0,
    REFUTED: 0,
    NOT_ENOUGH_INFO: 0,
  },
  metadata: {
    retriever: 'hybrid_rrf',
  },
};

const mockFollowUpAnswer: FinalAnswerResponse = {
  question: 'Ai là người dẫn đầu đoàn đàm phán khi đó?',
  answer: 'Đoàn đàm phán của Việt Nam do Bộ trưởng Thương mại Trương Đình Tuyển trực tiếp chỉ đạo [1].',
  status: 'SUPPORTED',
  claims: [
    {
      claim_id: 'claim-3',
      text: 'Bộ trưởng Trương Đình Tuyển chỉ đạo đoàn đàm phán',
      order: 1,
      context_sentence: 'Đoàn đàm phán của Việt Nam do Bộ trưởng Thương mại Trương Đình Tuyển chỉ đạo.',
      verifiable: true,
    },
  ],
  evidence: [
    {
      evidence_id: 'E3',
      chunk_id: 'chunk-103',
      content: 'Bộ trưởng Trương Đình Tuyển cùng các thành viên đoàn đàm phán đã nỗ lực không ngừng.',
      score: 0.95,
      source_title: 'Tư liệu Lịch sử Ngoại thương',
      source_url: 'https://moit.gov.vn/lich-su-wto',
      publisher: 'Bộ Công Thương',
      page_number: 5,
    },
  ],
  citations: [
    {
      citation_id: 'cit-3',
      claim_id: 'claim-3',
      evidence_id: 'E3',
      source_name: 'Tư liệu Lịch sử Ngoại thương',
      source_url: 'https://moit.gov.vn/lich-su-wto',
      quote: 'Bộ trưởng Trương Đình Tuyển cùng các thành viên đoàn đàm phán...',
      stance: 'SUPPORTS',
      footnote_index: 1,
      relevance_score: 0.95,
    },
  ],
  evidence_coverage: 1.0,
  verification_summary: {
    SUPPORTED: 1,
    PARTIALLY_SUPPORTED: 0,
    REFUTED: 0,
    NOT_ENOUGH_INFO: 0,
  },
  metadata: {
    retriever: 'hybrid_rrf',
  },
};

import { Routes, Route } from 'react-router-dom';

const renderResearchChat = (initialRoute = '/') => {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <AuthProvider>
        <AIPreferencesProvider>
          <Routes>
            <Route path="/" element={<ResearchChatPage />} />
            <Route path="/chat" element={<ResearchChatPage />} />
            <Route path="/chat/:conversationId" element={<ResearchChatPage />} />
          </Routes>
        </AIPreferencesProvider>
      </AuthProvider>
    </MemoryRouter>
  );
};

describe('Main Research Chat Feature (FE-CHAT-01)', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
    vi.spyOn(conversationService, 'createConversation').mockResolvedValue({
      id: 'conv-test-123',
      title: 'Cuộc trò chuyện mới',
      is_pinned: false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });
    vi.spyOn(conversationService, 'listMessages').mockResolvedValue([]);
  });

  describe('1. Welcome / Empty State', () => {
    it('renders Perplexity-style welcome hero, central composer, and research starters initially', () => {
      renderResearchChat();

      // Opening Chat/refreshing the empty state must not create a conversation.
      expect(conversationService.createConversation).not.toHaveBeenCalled();

      // Welcome title and description
      expect(
        screen.getByText(/Bạn muốn tìm hiểu hoặc đối soát điều gì hôm nay\?|What would you like to research/i)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Trợ lý nghiên cứu AI với trích dẫn minh bạch|Hệ thống AI đối soát nguồn minh bạch/i)
      ).toBeInTheDocument();

      // Centered Composer
      const textarea = screen.getByTestId('question-textarea');
      expect(textarea).toBeInTheDocument();
      expect(screen.getByTestId('btn-ask')).toBeDisabled();

      // Research Starters / Sample Questions
      expect(screen.getByText('Gợi ý chủ đề tra cứu:')).toBeInTheDocument();
      expect(screen.getByTestId('sample-question-0')).toBeInTheDocument();
      expect(screen.getByTestId('sample-question-1')).toBeInTheDocument();
      expect(screen.getByTestId('sample-question-2')).toBeInTheDocument();
    });

    it('enables send button when input has text and disables when whitespace only', () => {
      renderResearchChat();

      const textarea = screen.getByTestId('question-textarea');
      const sendBtn = screen.getByTestId('btn-ask');

      expect(sendBtn).toBeDisabled();

      fireEvent.change(textarea, { target: { value: '   ' } });
      expect(sendBtn).toBeDisabled();

      fireEvent.change(textarea, { target: { value: 'Kinh tế Việt Nam' } });
      expect(sendBtn).not.toBeDisabled();
    });

    it('clicking a starter prompt immediately fills query and dispatches research API', async () => {
      const askSpy = vi.spyOn(qaService, 'askQuestion').mockResolvedValueOnce(mockFinalAnswer);
      renderResearchChat();

      const starterBtn = screen.getByTestId('sample-question-0');
      fireEvent.click(starterBtn);

      await waitFor(() => {
        expect(askSpy).toHaveBeenCalledTimes(1);
      });
      expect(askSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          question: expect.stringContaining('WTO'),
          top_k: 5,
          search_mode: 'hybrid',
          conversation_id: 'conv-test-123',
        })
      );

      await waitFor(() => {
        expect(screen.getByTestId('chat-conversation-flow')).toBeInTheDocument();
      });
    });
  });

  describe('2. Query Submission & Loading State', () => {
    it('submits research query via Enter key without Shift', async () => {
      const askSpy = vi.spyOn(qaService, 'askQuestion').mockResolvedValueOnce(mockFinalAnswer);
      renderResearchChat();

      const textarea = screen.getByTestId('question-textarea');
      fireEvent.change(textarea, { target: { value: 'Việt Nam gia nhập WTO năm nào?' } });

      // Press Enter
      fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter', shiftKey: false });

      await waitFor(() => {
        expect(askSpy).toHaveBeenCalledTimes(1);
      });
      expect(askSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          question: 'Việt Nam gia nhập WTO năm nào?',
          top_k: 5,
          search_mode: 'hybrid',
          conversation_id: 'conv-test-123',
        })
      );

      await waitFor(() => {
        expect(screen.getByTestId('chat-conversation-flow')).toBeInTheDocument();
      });
    });

    it('allows newline when pressing Shift+Enter instead of submitting', () => {
      const askSpy = vi.spyOn(qaService, 'askQuestion');
      renderResearchChat();

      const textarea = screen.getByTestId('question-textarea');
      fireEvent.change(textarea, { target: { value: 'Dòng 1' } });

      // Press Shift + Enter
      fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter', shiftKey: true });

      // Should NOT submit
      expect(askSpy).not.toHaveBeenCalled();
    });

    it('displays loading state while waiting for grounded answer', async () => {
      let resolvePromise: (val: any) => void = () => {};
      const pendingPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });
      vi.spyOn(qaService, 'askQuestion').mockReturnValueOnce(pendingPromise as any);

      renderResearchChat();

      const textarea = screen.getByTestId('question-textarea');
      fireEvent.change(textarea, { target: { value: 'Việt Nam gia nhập WTO năm nào?' } });
      fireEvent.click(screen.getByTestId('btn-ask'));

      // Loading state visible
      expect(screen.getByTestId('qa-loading-state')).toBeInTheDocument();
      expect(screen.getByText(/Đang thực hiện Hybrid Search và kiểm chứng nguồn/i)).toBeInTheDocument();

      // Resolve API
      resolvePromise(mockFinalAnswer);

      await waitFor(() => {
        expect(screen.queryByTestId('qa-loading-state')).not.toBeInTheDocument();
        expect(screen.getByTestId('chat-conversation-flow')).toBeInTheDocument();
      });
    });
  });

  describe('3. Grounded Answer, Citations & Evidence Drawer', () => {
    it('renders user prompt card and grounded AI response with citations and coverage', async () => {
      vi.spyOn(qaService, 'askQuestion').mockResolvedValueOnce(mockFinalAnswer);
      renderResearchChat();

      const textarea = screen.getByTestId('question-textarea');
      fireEvent.change(textarea, { target: { value: 'Việt Nam gia nhập WTO năm nào?' } });
      fireEvent.click(screen.getByTestId('btn-ask'));

      await waitFor(() => {
        expect(screen.getByTestId('chat-conversation-flow')).toBeInTheDocument();
      });

      // Check User message card
      const userTurn = screen.getByTestId('chat-turn-user-0');
      expect(userTurn).toBeInTheDocument();
      expect(within(userTurn).getByText('Việt Nam gia nhập WTO năm nào?')).toBeInTheDocument();

      // Check AI response card
      const aiTurn = screen.getByTestId('chat-turn-ai-0');
      expect(aiTurn).toBeInTheDocument();
      expect(within(aiTurn).getByTestId('answer-rendered-text')).toHaveTextContent(/thành viên thứ 150 của WTO/i);

      // Citations [1] and [2] rendered
      expect(screen.getByTestId('citation-btn-1')).toBeInTheDocument();
      expect(screen.getByTestId('citation-btn-2')).toBeInTheDocument();

      // Evidence Coverage Card
      expect(screen.getByTestId('evidence-coverage-card')).toBeInTheDocument();
      expect(screen.getByText('100%')).toBeInTheDocument();

      // Claims list
      expect(screen.getByTestId('claim-item-claim-1')).toBeInTheDocument();
      expect(screen.getByTestId('claim-item-claim-2')).toBeInTheDocument();
    });

    it('clicking citation opens Evidence Drawer with correct provenance details and closes it', async () => {
      vi.spyOn(qaService, 'askQuestion').mockResolvedValueOnce(mockFinalAnswer);
      renderResearchChat();

      const textarea = screen.getByTestId('question-textarea');
      fireEvent.change(textarea, { target: { value: 'Việt Nam gia nhập WTO năm nào?' } });
      fireEvent.click(screen.getByTestId('btn-ask'));

      await waitFor(() => {
        expect(screen.getByTestId('citation-btn-1')).toBeInTheDocument();
      });

      // Drawer is initially closed
      expect(screen.queryByTestId('evidence-drawer')).not.toBeInTheDocument();

      // Click citation [1]
      fireEvent.click(screen.getByTestId('citation-btn-1'));

      // Drawer is now open
      const drawer = screen.getByTestId('evidence-drawer');
      expect(drawer).toBeInTheDocument();
      expect(within(drawer).getByText('Bộ Công Thương')).toBeInTheDocument();
      expect(within(drawer).getByTestId('evidence-quote')).toHaveTextContent(/thành viên thứ 150 của WTO/i);

      // Close drawer
      const closeBtn = screen.getByTestId('drawer-close-btn');
      fireEvent.click(closeBtn);

      expect(screen.queryByTestId('evidence-drawer')).not.toBeInTheDocument();
    });
  });

  describe('4. Multi-turn Follow-up & Reset Conversation', () => {
    it('supports asking follow-up question via docked bottom composer', async () => {
      vi.spyOn(qaService, 'askQuestion')
        .mockResolvedValueOnce(mockFinalAnswer)
        .mockResolvedValueOnce(mockFollowUpAnswer);

      renderResearchChat();

      // Turn 1
      const initialTextarea = screen.getByTestId('question-textarea');
      fireEvent.change(initialTextarea, { target: { value: 'Việt Nam gia nhập WTO năm nào?' } });
      fireEvent.click(screen.getByTestId('btn-ask'));

      await waitFor(() => {
        expect(screen.getByTestId('chat-turn-0')).toBeInTheDocument();
      });

      // Docked composer is visible for follow-up
      const followUpTextarea = screen.getByTestId('question-textarea');
      fireEvent.change(followUpTextarea, { target: { value: 'Ai là người dẫn đầu đoàn đàm phán khi đó?' } });
      fireEvent.click(screen.getByTestId('btn-ask'));

      await waitFor(() => {
        expect(screen.getByTestId('chat-turn-1')).toBeInTheDocument();
      });

      // Both turns are in the conversation flow
      expect(screen.getByTestId('chat-turn-0')).toBeInTheDocument();
      expect(screen.getByTestId('chat-turn-1')).toBeInTheDocument();
      expect(screen.getByText('Ai là người dẫn đầu đoàn đàm phán khi đó?')).toBeInTheDocument();
      expect(screen.getAllByText(/Trương Đình Tuyển/i).length).toBeGreaterThan(0);
    });

    it('clicking "+ Tra cứu mới" (reset chat) returns to the empty welcome state', async () => {
      vi.spyOn(qaService, 'askQuestion').mockResolvedValueOnce(mockFinalAnswer);
      renderResearchChat();

      // Ask question to have active conversation
      const textarea = screen.getByTestId('question-textarea');
      fireEvent.change(textarea, { target: { value: 'Việt Nam gia nhập WTO năm nào?' } });
      fireEvent.click(screen.getByTestId('btn-ask'));

      await waitFor(() => {
        expect(screen.getByTestId('chat-conversation-flow')).toBeInTheDocument();
      });

      // Reset button in header
      const resetBtn = screen.getByTestId('btn-reset-chat');
      expect(resetBtn).toBeInTheDocument();
      fireEvent.click(resetBtn);

      // Now returned to welcome empty state
      expect(screen.queryByTestId('chat-conversation-flow')).not.toBeInTheDocument();
      expect(screen.getByTestId('qa-empty-state')).toBeInTheDocument();
      expect(screen.getByText(/Bạn muốn tìm hiểu hoặc đối soát điều gì hôm nay\?/i)).toBeInTheDocument();
    });
  });

  describe('5. Error Handling', () => {
    it('displays error alert when API call fails and retains user query', async () => {
      vi.spyOn(qaService, 'askQuestion').mockRejectedValueOnce(
        new ApiClientError('Dữ liệu câu hỏi không hợp lệ.', 422)
      );

      renderResearchChat();

      const textarea = screen.getByTestId('question-textarea') as HTMLTextAreaElement;
      fireEvent.change(textarea, { target: { value: 'Câu hỏi lỗi' } });
      fireEvent.click(screen.getByTestId('btn-ask'));

      await waitFor(() => {
        expect(screen.getByTestId('qa-error-alert')).toBeInTheDocument();
      });

      expect(screen.getByText('Dữ liệu câu hỏi không hợp lệ.')).toBeInTheDocument();
      // Text is preserved in textarea
      expect(textarea.value).toBe('Câu hỏi lỗi');
    });
  });

  describe('6. Independent UI Language & AI Response Language', () => {
    it('respects UI language setting while maintaining separate AI response setting', () => {
      localStorage.setItem(UI_LANGUAGE_STORAGE_KEY, 'en');
      localStorage.setItem(AI_LANGUAGE_STORAGE_KEY, 'vi');

      renderResearchChat();

      // UI is English
      expect(screen.getByText('What would you like to research or verify today?')).toBeInTheDocument();
      expect(screen.getByText('Suggested research topics:')).toBeInTheDocument();
    });
  });

  describe('7. Conversation Context & History Hydration (CHAT-03.3)', () => {
    it('(A) Send message flow includes conversation_id and avoids duplicate conversation creation', async () => {
      const askSpy = vi.spyOn(qaService, 'askQuestion').mockResolvedValueOnce(mockFinalAnswer);
      const createConvSpy = vi.spyOn(conversationService, 'createConversation').mockResolvedValueOnce({
        id: 'conv-new-999',
        title: 'Cuộc trò chuyện mới',
        is_pinned: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });

      renderResearchChat();

      const textarea = screen.getByTestId('question-textarea');
      fireEvent.change(textarea, { target: { value: 'WTO là gì?' } });
      fireEvent.click(screen.getByTestId('btn-ask'));

      await waitFor(() => {
        expect(createConvSpy).toHaveBeenCalledTimes(1);
        expect(askSpy).toHaveBeenCalledTimes(1);
      });

      expect(askSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          question: 'WTO là gì?',
          conversation_id: 'conv-new-999',
        })
      );
    });

    it('(B & C) Load messages and hydrate history when opening /chat/:conversationId (e.g. on direct open or F5)', async () => {
      const mockMessages = [
        {
          id: 'msg-1',
          role: 'user',
          content: 'Việt Nam gia nhập WTO năm nào?',
          created_at: '2026-09-14T10:00:00Z',
        },
        {
          id: 'msg-2',
          role: 'assistant',
          content: 'Việt Nam chính thức trở thành thành viên WTO năm 2007 [1].',
          extra_metadata: {
            status: 'SUPPORTED',
            evidence_coverage: 1.0,
            citations: mockFinalAnswer.citations,
            evidence: mockFinalAnswer.evidence,
            claims: mockFinalAnswer.claims,
            verification_summary: mockFinalAnswer.verification_summary,
          },
          created_at: '2026-09-14T10:00:05Z',
        },
      ];

      vi.spyOn(conversationService, 'listMessages').mockResolvedValueOnce(mockMessages);

      renderResearchChat('/chat/conv-existing-123');

      // Should show loading state or directly resolve to chat turns
      await waitFor(() => {
        expect(screen.getByTestId('chat-conversation-flow')).toBeInTheDocument();
      });

      expect(screen.getAllByText('Việt Nam gia nhập WTO năm nào?').length).toBeGreaterThan(0);
      expect(screen.getByText(/Việt Nam chính thức trở thành thành viên WTO năm 2007/i)).toBeInTheDocument();
      // Citation badge [1] should be present
      expect(screen.getByTestId('citation-btn-1')).toBeInTheDocument();
    });

    it('(D) Switching between conversations isolates data without bleeding messages', async () => {
      const messagesConv1 = [
        {
          id: 'msg-1',
          role: 'user',
          content: 'Nội dung Conversation 1',
          created_at: '2026-09-14T10:00:00Z',
        },
        {
          id: 'msg-2',
          role: 'assistant',
          content: 'Câu trả lời 1',
          extra_metadata: { status: 'SUPPORTED' },
          created_at: '2026-09-14T10:00:05Z',
        },
      ];

      vi.spyOn(conversationService, 'listMessages').mockResolvedValueOnce(messagesConv1);

      const { unmount } = renderResearchChat('/chat/conv-1');

      await waitFor(() => {
        expect(screen.getAllByText('Nội dung Conversation 1').length).toBeGreaterThan(0);
      });

      unmount();

      const messagesConv2 = [
        {
          id: 'msg-3',
          role: 'user',
          content: 'Nội dung Conversation 2 hoàn toàn khác',
          created_at: '2026-09-14T11:00:00Z',
        },
        {
          id: 'msg-4',
          role: 'assistant',
          content: 'Câu trả lời 2',
          extra_metadata: { status: 'SUPPORTED' },
          created_at: '2026-09-14T11:00:05Z',
        },
      ];

      vi.spyOn(conversationService, 'listMessages').mockResolvedValueOnce(messagesConv2);

      renderResearchChat('/chat/conv-2');

      await waitFor(() => {
        expect(screen.getAllByText('Nội dung Conversation 2 hoàn toàn khác').length).toBeGreaterThan(0);
      });

      expect(screen.queryByText('Nội dung Conversation 1')).not.toBeInTheDocument();
    });

    it('(E) Follow-up query in existing conversation reuses conversation_id without creating new conversation', async () => {
      const mockMessages = [
        {
          id: 'msg-1',
          role: 'user',
          content: 'Câu hỏi đầu tiên',
          created_at: '2026-09-14T10:00:00Z',
        },
        {
          id: 'msg-2',
          role: 'assistant',
          content: 'Trả lời đầu tiên',
          extra_metadata: { status: 'SUPPORTED' },
          created_at: '2026-09-14T10:00:05Z',
        },
      ];

      vi.spyOn(conversationService, 'listMessages').mockResolvedValueOnce(mockMessages);
      const createConvSpy = vi.spyOn(conversationService, 'createConversation');
      const askSpy = vi.spyOn(qaService, 'askQuestion').mockResolvedValueOnce(mockFinalAnswer);

      renderResearchChat('/chat/conv-active-456');

      await waitFor(() => {
        expect(screen.getAllByText('Câu hỏi đầu tiên').length).toBeGreaterThan(0);
      });

      const textarea = screen.getByTestId('question-textarea');
      fireEvent.change(textarea, { target: { value: 'Câu hỏi tiếp theo?' } });
      fireEvent.click(screen.getByTestId('btn-ask'));

      await waitFor(() => {
        expect(askSpy).toHaveBeenCalledTimes(1);
      });

      expect(createConvSpy).not.toHaveBeenCalled();
      expect(askSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          question: 'Câu hỏi tiếp theo?',
          conversation_id: 'conv-active-456',
        })
      );
    });

    it('(F) Ask API error retains existing history and preserves user input', async () => {
      const mockMessages = [
        {
          id: 'msg-1',
          role: 'user',
          content: 'Lịch sử trước đó',
          created_at: '2026-09-14T10:00:00Z',
        },
        {
          id: 'msg-2',
          role: 'assistant',
          content: 'Câu trả lời đã lưu',
          extra_metadata: { status: 'SUPPORTED' },
          created_at: '2026-09-14T10:00:05Z',
        },
      ];

      vi.spyOn(conversationService, 'listMessages').mockResolvedValueOnce(mockMessages);
      vi.spyOn(qaService, 'askQuestion').mockRejectedValueOnce(
        new ApiClientError('Không thể kết nối tới máy chủ.', 500)
      );

      renderResearchChat('/chat/conv-error-test');

      await waitFor(() => {
        expect(screen.getAllByText('Lịch sử trước đó').length).toBeGreaterThan(0);
      });

      const textarea = screen.getByTestId('question-textarea') as HTMLTextAreaElement;
      fireEvent.change(textarea, { target: { value: 'Câu hỏi gây lỗi' } });
      fireEvent.click(screen.getByTestId('btn-ask'));

      await waitFor(() => {
        expect(screen.getByTestId('qa-error-alert')).toBeInTheDocument();
      });

      // Existing turns should still be there!
      expect(screen.getAllByText('Lịch sử trước đó').length).toBeGreaterThan(0);
      expect(screen.getByText('Câu trả lời đã lưu')).toBeInTheDocument();
      // Failed input should be restored
      expect(textarea.value).toBe('Câu hỏi gây lỗi');
    });

    it('(G) Load history failure displays error notification', async () => {
      vi.spyOn(conversationService, 'listMessages').mockRejectedValueOnce(
        new ApiClientError('Cuộc trò chuyện không tồn tại.', 404)
      );

      renderResearchChat('/chat/conv-notfound-404');

      await waitFor(() => {
        expect(screen.getByTestId('qa-error-alert')).toBeInTheDocument();
      });

      expect(screen.getByText('Cuộc trò chuyện không tồn tại hoặc bạn không có quyền truy cập.')).toBeInTheDocument();
    });

    it('(H) Hydrated citations can be clicked to open Evidence Drawer with restored evidence', async () => {
      const mockMessages = [
        {
          id: 'msg-1',
          role: 'user',
          content: 'Việt Nam gia nhập WTO năm nào?',
          created_at: '2026-09-14T10:00:00Z',
        },
        {
          id: 'msg-2',
          role: 'assistant',
          content: 'Việt Nam chính thức gia nhập WTO [1].',
          extra_metadata: {
            status: 'SUPPORTED',
            evidence_coverage: 1.0,
            citations: mockFinalAnswer.citations,
            evidence: mockFinalAnswer.evidence,
            claims: mockFinalAnswer.claims,
            verification_summary: mockFinalAnswer.verification_summary,
          },
          created_at: '2026-09-14T10:00:05Z',
        },
      ];

      vi.spyOn(conversationService, 'listMessages').mockResolvedValueOnce(mockMessages);

      renderResearchChat('/chat/conv-evidence-drawer');

      await waitFor(() => {
        expect(screen.getByTestId('citation-btn-1')).toBeInTheDocument();
      });

      // Click citation [1]
      fireEvent.click(screen.getByTestId('citation-btn-1'));

      // Drawer opens
      await waitFor(() => {
        expect(screen.getByTestId('evidence-drawer')).toBeInTheDocument();
      });

      expect(screen.getByTestId('evidence-full-content')).toHaveTextContent(/Ngày 11-1-2007, Việt Nam chính thức trở thành thành viên thứ 150/i);
    });
  });

  describe('8. Router Navigation & API Error Semantics (CHAT-03.4)', () => {
    it('uses React Router navigate to transition from New Chat to /chat/:id without wiping in-flight turns', async () => {
      const askSpy = vi.spyOn(qaService, 'askQuestion').mockResolvedValueOnce(mockFinalAnswer);
      const createConvSpy = vi.spyOn(conversationService, 'createConversation').mockResolvedValueOnce({
        id: 'conv-nav-111',
        title: 'Cuộc trò chuyện mới',
        is_pinned: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });

      renderResearchChat('/');

      const textarea = screen.getByTestId('question-textarea');
      fireEvent.change(textarea, { target: { value: 'Hỏi câu đầu tiên' } });
      fireEvent.click(screen.getByTestId('btn-ask'));

      await waitFor(() => {
        expect(createConvSpy).toHaveBeenCalledTimes(1);
        expect(askSpy).toHaveBeenCalledTimes(1);
      });

      // After ask finishes, the turn is rendered and NOT wiped
      await waitFor(() => {
        expect(screen.getByTestId('chat-conversation-flow')).toBeInTheDocument();
        expect(screen.getAllByText('Hỏi câu đầu tiên').length).toBeGreaterThan(0);
      });
    });

    it('renders INSUFFICIENT_EVIDENCE as valid AI response turn without triggering error alert', async () => {
      const mockInsufficientAnswer: FinalAnswerResponse = {
        question: 'Câu hỏi không đủ bằng chứng?',
        answer: 'Thông tin trong các tài liệu kiểm chứng hiện tại không đủ để trả lời câu hỏi này một cách chắc chắn.',
        status: 'INSUFFICIENT_EVIDENCE',
        claims: [],
        evidence: [],
        citations: [],
        evidence_coverage: 0,
        verification_summary: {
          SUPPORTED: 0,
          PARTIALLY_SUPPORTED: 0,
          REFUTED: 0,
          NOT_ENOUGH_INFO: 0,
        },
        metadata: {},
      };

      vi.spyOn(conversationService, 'listMessages').mockResolvedValueOnce([]);
      const askSpy = vi.spyOn(qaService, 'askQuestion').mockResolvedValueOnce(mockInsufficientAnswer);

      renderResearchChat('/chat/conv-insufficient');

      const textarea = screen.getByTestId('question-textarea');
      // Wait until history loading resolves
      await waitFor(() => {
        expect(screen.queryByTestId('sidebar-history-loading')).not.toBeInTheDocument();
      });

      fireEvent.change(textarea, { target: { value: 'Câu hỏi không đủ bằng chứng?' } });
      fireEvent.click(screen.getByTestId('btn-ask'));

      await waitFor(() => {
        expect(askSpy).toHaveBeenCalledTimes(1);
        expect(screen.getByTestId('chat-conversation-flow')).toBeInTheDocument();
      });

      // Should NOT render error alert
      expect(screen.queryByTestId('qa-error-alert')).not.toBeInTheDocument();

      // Should render AI turn with INSUFFICIENT_EVIDENCE status
      expect(screen.getByText(/Thông tin trong các tài liệu kiểm chứng hiện tại không đủ/i)).toBeInTheDocument();
      expect(screen.getAllByText(/INSUFFICIENT_EVIDENCE/i).length).toBeGreaterThan(0);
    });

    it('handles unexpected HTTP 500 server error by showing error alert and preserving query', async () => {
      vi.spyOn(conversationService, 'listMessages').mockResolvedValueOnce([]);
      const askSpy = vi.spyOn(qaService, 'askQuestion').mockRejectedValueOnce(
        new ApiClientError('Đã xảy ra sự cố nội bộ khi xử lý câu hỏi. Vui lòng thử lại sau.', 500)
      );

      renderResearchChat('/chat/conv-server-500');

      const textarea = screen.getByTestId('question-textarea') as HTMLTextAreaElement;
      // Wait until initial loading finishes
      await waitFor(() => {
        expect(screen.queryByTestId('sidebar-history-loading')).not.toBeInTheDocument();
      });

      fireEvent.change(textarea, { target: { value: 'Câu hỏi kích hoạt lỗi 500' } });
      fireEvent.click(screen.getByTestId('btn-ask'));

      await waitFor(() => {
        expect(askSpy).toHaveBeenCalledTimes(1);
        expect(screen.getByTestId('qa-error-alert')).toBeInTheDocument();
      });

      // Friendly server error message is shown
      expect(screen.getByText('Máy chủ đang gặp sự cố khi xử lý câu hỏi. Vui lòng thử lại sau.')).toBeInTheDocument();
      // User query is restored in textarea
      expect(textarea.value).toBe('Câu hỏi kích hoạt lỗi 500');
    });
  });
});
