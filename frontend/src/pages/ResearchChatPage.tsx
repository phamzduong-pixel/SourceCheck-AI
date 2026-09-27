/**
 * ResearchChatPage: Central Research Chat Assistant Workspace for SourceCheck AI (FE-CHAT-01).
 * Features Perplexity-style research assistant workflow with transparent evidence citations,
 * claims breakdown, evidence coverage, multi-turn conversation flow, and docked follow-up composer.
 */

import React, { useState, useEffect, useRef, useContext } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import conversationService from '../services/conversations';
import { qaService } from '../services/qa';
import { verificationService } from '../services/verification';
import { FinalAnswerResponse, CitationItem, QuestionRequest } from '../types/qa';
import { VerificationResultResponse } from '../types/verification';
import { ApiClientError } from '../services/apiClient';
import { AnswerRenderer } from '../components/qa/AnswerRenderer';
import { EvidenceCoverageCard } from '../components/qa/EvidenceCoverageCard';
import { ClaimList } from '../components/qa/ClaimList';
import { EvidenceDrawer } from '../components/qa/EvidenceDrawer';
import { ResearchInputComposer, ResearchSubmitOptions } from '../components/chat/ResearchInputComposer';
import { VerificationResultCard } from '../components/qa/VerificationResultCard';
import { useAIPreferences } from '../hooks/useAIPreferences';
import { AuthContext } from '../context/AuthContext';
import '../styles/qa.css';
import '../styles/chat.css';

export interface ChatTurn {
  id: string;
  question: string;
  response: FinalAnswerResponse;
  timestamp: string;
  verificationReport?: VerificationResultResponse;
}

export const ResearchChatPage: React.FC = () => {
  const { t, setActiveChatTitle, showSources, showVerification } = useAIPreferences();
  const authContext = useContext(AuthContext);
  const user = authContext?.user;

  // Multi-turn conversation state
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const params = useParams<{ conversationId: string }>();
  const navigate = useNavigate();
  const justCreatedConvIdRef = useRef<string | null>(null);
  const [question, setQuestion] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isHistoryLoading, setIsHistoryLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [turns, setTurns] = useState<ChatTurn[]>([]);

  // Evidence Drawer state
  const [activeCitation, setActiveCitation] = useState<CitationItem | null>(null);
  const [activeEvidenceTurnId, setActiveEvidenceTurnId] = useState<string | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);

  const inputRef = useRef<HTMLTextAreaElement>(null);
  const flowEndRef = useRef<HTMLDivElement>(null);
  const isNearBottomRef = useRef<boolean>(true);
  const userJustSubmittedRef = useRef<boolean>(false);
  const requestSequenceRef = useRef(0);
  const pendingQuestionRef = useRef('');

  // Monitor viewport scroll position to prevent disruptive auto-scroll when user is reading higher up
  useEffect(() => {
    const checkScrollPosition = () => {
      const scrollY = window.scrollY || document.documentElement.scrollTop;
      const windowHeight = window.innerHeight;
      const documentHeight = document.documentElement.scrollHeight;
      // User is considered near bottom if within 220px of the page bottom
      isNearBottomRef.current = documentHeight - (scrollY + windowHeight) < 220;
    };

    window.addEventListener('scroll', checkScrollPosition, { passive: true });
    return () => window.removeEventListener('scroll', checkScrollPosition);
  }, []);

  // Helper: Convert raw backend messages into structured ChatTurn items
  const mapMessagesToTurns = (messages: any[]): ChatTurn[] => {
    const turnsList: ChatTurn[] = [];
    let currentTurnUser: { id: string; question: string; timestamp: string } | null = null;

    for (const msg of messages) {
      if (msg.role === 'user') {
        currentTurnUser = {
          id: `turn-${msg.id || Date.now()}`,
          question: msg.content,
          timestamp: msg.created_at
            ? new Date(msg.created_at).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
            : '',
        };
      } else if (msg.role === 'assistant' && currentTurnUser) {
        const meta = msg.extra_metadata || {};
        const response: FinalAnswerResponse = {
          question: currentTurnUser.question,
          answer: msg.content,
          status: meta.status || 'SUPPORTED',
          claims: Array.isArray(meta.claims) ? meta.claims : [],
          evidence: Array.isArray(meta.evidence) ? meta.evidence : [],
          citations: Array.isArray(meta.citations) ? meta.citations : [],
          evidence_coverage: typeof meta.evidence_coverage === 'number' ? meta.evidence_coverage : 0,
          verification_summary: meta.verification_summary || {},
          metadata: meta.metadata || {},
        };

        turnsList.push({
          id: currentTurnUser.id,
          question: currentTurnUser.question,
          response,
          timestamp: currentTurnUser.timestamp || (msg.created_at
            ? new Date(msg.created_at).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
            : ''),
        });
        currentTurnUser = null;
      }
    }

    // Edge case: if a dangling user turn exists without an assistant answer
    if (currentTurnUser) {
      turnsList.push({
        id: currentTurnUser.id,
        question: currentTurnUser.question,
        response: {
          question: currentTurnUser.question,
          answer: '...',
          status: 'SUPPORTED',
          claims: [],
          evidence: [],
          citations: [],
          evidence_coverage: 0,
          verification_summary: {},
          metadata: {},
        },
        timestamp: currentTurnUser.timestamp,
      });
    }

    return turnsList;
  };

  // Reset conversation to fresh welcome state
  const handleResetChat = () => {
    justCreatedConvIdRef.current = null;
    requestSequenceRef.current += 1;
    setTurns([]);
    setQuestion('');
    setError(null);
    setIsLoading(false);
    setIsHistoryLoading(false);
    setIsDrawerOpen(false);
    setActiveCitation(null);
    setActiveEvidenceTurnId(null);
    setActiveConversationId(null);
    setActiveChatTitle(null);
    if (params.conversationId) {
      navigate('/', { replace: true });
    }
    setTimeout(() => {
      inputRef.current?.focus();
    }, 50);
  };

  // Keep activeChatTitle in sync with current conversation turns
  useEffect(() => {
    if (turns.length > 0) {
      const firstQ = turns[0].question;
      const title = firstQ.length > 48 ? `${firstQ.slice(0, 48)}...` : firstQ;
      setActiveChatTitle(title);
    } else {
      setActiveChatTitle(null);
    }
  }, [turns, setActiveChatTitle]);

  // Clean up activeChatTitle when unmounting ResearchChatPage
  useEffect(() => {
    return () => {
      setActiveChatTitle(null);
    };
  }, [setActiveChatTitle]);

  // Listen for external New Chat requests (e.g., from Sidebar '+ Tra cứu mới' button)
  useEffect(() => {
    const onNewChatEvent = () => {
      handleResetChat();
    };

    window.addEventListener('sourcecheck:new-chat', onNewChatEvent);
    return () => {
      window.removeEventListener('sourcecheck:new-chat', onNewChatEvent);
    };
  }, []);

  // Conversation Isolation & Hydration: Triggered whenever URL param conversationId changes
  useEffect(() => {
    const convoId = params.conversationId;
    if (convoId) {
      setActiveConversationId(convoId);

      // If this navigation was triggered by creating a new conversation in-flight,
      // preserve the current in-flight turns instead of wiping and re-fetching
      if (justCreatedConvIdRef.current === convoId) {
        justCreatedConvIdRef.current = null;
        return;
      }

      // Clear previous conversation turns to prevent state bleed
      setTurns([]);
      setError(null);
      setIsHistoryLoading(true);

      conversationService
        .listMessages(convoId)
        .then((messages) => {
          if (Array.isArray(messages)) {
            const parsedTurns = mapMessagesToTurns(messages);
            setTurns(parsedTurns);
          }
        })
        .catch((err: any) => {
          if (err instanceof ApiClientError) {
            if (err.statusCode === 404) {
              setError('Cu\u1ed9c tr\u00f2 chuy\u1ec7n kh\u00f4ng t\u1ed3n t\u1ea1i ho\u1eb7c b\u1ea1n kh\u00f4ng c\u00f3 quy\u1ec1n truy c\u1eadp.');
            } else if (err.statusCode === 401) {
              setError('Phi\u00ean l\u00e0m vi\u1ec7c \u0111\u00e3 h\u1ebft h\u1ea1n. Vui l\u00f2ng \u0111\u0103ng nh\u1eadp l\u1ea1i \u0111\u1ec3 ti\u1ebfp t\u1ee5c.');
            } else {
              setError(err.message || '\u0110\u00e3 x\u1ea3y ra l\u1ed7i trong qu\u00e1 tr\u00ecnh x\u1eed l\u00fd c\u00e2u h\u1ecfi.');
            }
          } else {
            setError(err?.message || '\u0110\u00e3 x\u1ea3y ra l\u1ed7i kh\u00f4ng x\u00e1c \u0111\u1ecbnh.');
          }
        })
        .finally(() => {
          setIsHistoryLoading(false);
        });
    } else {
      // If we navigate away to /chat or /, reset active conversation state
      setActiveConversationId(null);
      setTurns([]);
      setError(null);
      setIsHistoryLoading(false);
    }
  }, [params.conversationId]);

  // Handle Question Submission
  const handleAsk = async (
    queryText?: string,
    options: ResearchSubmitOptions = { taskType: 'qa', documentIds: [], searchEnabled: true },
  ) => {
    const textToSubmit = (queryText ?? question).trim();
    if (!textToSubmit || isLoading || isHistoryLoading) return;

    const requestSequence = requestSequenceRef.current + 1;
    requestSequenceRef.current = requestSequence;
    pendingQuestionRef.current = textToSubmit;
    userJustSubmittedRef.current = true;
    setIsLoading(true);
    setError(null);
    setQuestion('');

    let targetConvId = activeConversationId;

    if (!targetConvId) {
      try {
        const initialTitle =
          textToSubmit.length > 48 ? textToSubmit.slice(0, 48) + '...' : textToSubmit;
        const newConv = await conversationService.createConversation(initialTitle);
        if (requestSequence !== requestSequenceRef.current) return;
        if (newConv?.id) {
          targetConvId = newConv.id;
          setActiveConversationId(targetConvId);
          justCreatedConvIdRef.current = targetConvId;
          window.dispatchEvent(new CustomEvent('sourcecheck:refresh-conversations'));
          navigate('/chat/' + targetConvId, { replace: true });
        }
      } catch (convErr: any) {
        console.warn('Could not create conversation, proceeding with stateless request', convErr);
      }
    }

    if (requestSequence !== requestSequenceRef.current) return;

    const request: QuestionRequest = {
      question: textToSubmit,
      top_k: 5,
      search_mode: 'hybrid',
      search_enabled: options.searchEnabled,
      conversation_id: targetConvId,
    };
    if (options.taskType === 'summary') {
      request.task_type = 'summary';
      request.document_ids = options.documentIds;
    } else if (options.documentIds.length > 0) {
      request.document_ids = options.documentIds;
    }

    try {
      const response = await qaService.askQuestion(request);
      if (requestSequence !== requestSequenceRef.current) return;

      const responseConversationId = response.metadata?.conversation_id;
      if (!targetConvId && responseConversationId) {
        targetConvId = String(responseConversationId);
        setActiveConversationId(targetConvId);
        justCreatedConvIdRef.current = targetConvId;
        navigate('/chat/' + targetConvId, { replace: true });
        window.dispatchEvent(new CustomEvent('sourcecheck:refresh-conversations'));
      }

      const newTurn: ChatTurn = {
        id: 'turn-' + Date.now(),
        question: textToSubmit,
        response,
        timestamp: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
      };

      setTurns((prev) => [...prev, newTurn]);

      const requestId = response.metadata?.request_id || response.metadata?.verification_result_id;
      if (typeof requestId === 'string' && requestId) {
        verificationService.getVerificationReport(requestId)
          .then((verificationReport) => {
            setTurns((prev) => prev.map((turn) => (
              turn.id === newTurn.id ? { ...turn, verificationReport } : turn
            )));
          })
          .catch(() => undefined);
      }

      window.dispatchEvent(new CustomEvent('sourcecheck:refresh-conversations'));
    } catch (err: any) {
      if (requestSequence !== requestSequenceRef.current) return;
      if (err instanceof ApiClientError) {
        if (err.statusCode === 401) {
          setError('Phi\u00ean l\u00e0m vi\u1ec7c \u0111\u00e3 h\u1ebft h\u1ea1n. Vui l\u00f2ng \u0111\u0103ng nh\u1eadp l\u1ea1i \u0111\u1ec3 ti\u1ebfp t\u1ee5c.');
        } else if (err.statusCode === 404) {
          setError('Cu\u1ed9c tr\u00f2 chuy\u1ec7n kh\u00f4ng t\u1ed3n t\u1ea1i ho\u1eb7c b\u1ea1n kh\u00f4ng c\u00f3 quy\u1ec1n truy c\u1eadp.');
        } else if (err.statusCode === 422) {
          setError(err.message || '\u0110\u00e3 x\u1ea3y ra l\u1ed7i trong qu\u00e1 tr\u00ecnh x\u1eed l\u00fd c\u00e2u h\u1ecfi.');
        } else if (err.statusCode >= 500) {
          setError('M\u00e1y ch\u1ee7 \u0111ang g\u1eb7p s\u1ef1 c\u1ed1 khi x\u1eed l\u00fd c\u00e2u h\u1ecfi. Vui l\u00f2ng th\u1eed l\u1ea1i sau.');
        } else if (err.statusCode === 0) {
          setError('Kh\u00f4ng th\u1ec3 k\u1ebft n\u1ed1i \u0111\u1ebfn m\u00e1y ch\u1ee7. Vui l\u00f2ng ki\u1ec3m tra l\u1ea1i m\u1ea1ng.');
        } else {
          setError(err.message || '\u0110\u00e3 x\u1ea3y ra l\u1ed7i trong qu\u00e1 tr\u00ecnh x\u1eed l\u00fd c\u00e2u h\u1ecfi.');
        }
      } else {
        setError(err?.message || '\u0110\u00e3 x\u1ea3y ra l\u1ed7i kh\u00f4ng x\u00e1c \u0111\u1ecbnh.');
      }
      setQuestion(textToSubmit);
    } finally {
      if (requestSequence === requestSequenceRef.current) {
        setIsLoading(false);
      }
    }
  };

  const handleStop = () => {
    if (!isLoading) return;
    requestSequenceRef.current += 1;
    setQuestion(pendingQuestionRef.current);
    setIsLoading(false);
  };
  // Smart Auto-Follow: only scroll to bottom if user just submitted or was already near bottom
  useEffect(() => {
    if (turns.length === 0) return;
    if (userJustSubmittedRef.current || isNearBottomRef.current) {
      userJustSubmittedRef.current = false;
      const timeoutId = setTimeout(() => {
        if (typeof flowEndRef.current?.scrollIntoView === 'function') {
          flowEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
      }, 60);
      return () => clearTimeout(timeoutId);
    }
  }, [turns.length]);




  // Open Evidence Drawer when citation clicked
  const handleCitationClick = (citation: CitationItem, turnId?: string) => {
    setActiveCitation(citation);
    setActiveEvidenceTurnId(turnId || (turns.length > 0 ? turns[turns.length - 1].id : null));
    setIsDrawerOpen(true);
  };

  // Find active evidence in corresponding turn
  const currentTurn = turns.find((t) => t.id === activeEvidenceTurnId) || turns[turns.length - 1];
  const activeEvidence = currentTurn?.response?.evidence?.find(
    (ev) => ev.evidence_id === activeCitation?.evidence_id
  );

  const hasTurns = turns.length > 0;
  const userInitials =
    user?.full_name
      ?.split(' ')
      .filter(Boolean)
      .map((n) => n[0])
      .slice(0, 2)
      .join('')
      .toUpperCase() || 'U';

  return (
    <div
      className={`qa-container research-chat-workspace ${!hasTurns ? 'is-empty' : ''}`}
      data-testid="qa-page"
    >
      {/* Hidden reset button to support direct component test harness */}
      <button
        type="button"
        style={{ display: 'none' }}
        onClick={handleResetChat}
        data-testid="btn-reset-chat"
        aria-label="Tra cứu mới"
      />


      {/* Empty / Welcome State (Initial Research Landing) */}
      {!hasTurns && !isLoading && (
        <div className="chat-welcome-container qa-empty-state" data-testid="qa-empty-state">
          <div className="chat-welcome-icon" aria-hidden="true">
            <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              <path d="m9 12 2 2 4-4" />
            </svg>
          </div>

          <h1 className="chat-welcome-title">
            {t('chat.welcomeTitle')}
          </h1>

          <p className="chat-welcome-subtitle">
            {t('chat.welcomeSubtitle')}
          </p>

          {/* Centered Research Composer */}
          <div className="chat-welcome-composer-wrapper">
            <ResearchInputComposer
              value={question}
              onChange={setQuestion}
              onSubmit={(options) => handleAsk(undefined, options)}
              onStop={handleStop}
              isLoading={isLoading}
              disabled={isHistoryLoading}
              variant="welcome"
            />
          </div>
        </div>
      )}

      {/* Error Alert */}
      {error && (
        <div className="qa-error-alert" role="alert" data-testid="qa-error-alert" style={{ marginBottom: '1rem' }}>
          <span>{error}</span>
          <button
            type="button"
            onClick={() => setError(null)}
            style={{ background: 'none', border: 'none', color: '#991b1b', cursor: 'pointer', fontWeight: 'bold' }}
            aria-label="Đóng thông báo lỗi"
          >
            ✕
          </button>
        </div>
      )}

      {/* Conversation Flow (Multi-turn dialogue) */}
      {hasTurns && (
        <div className="chat-conversation-flow" data-testid="chat-conversation-flow">
          {turns.map((turn, turnIdx) => {
            const isLatest = turnIdx === turns.length - 1;
            const res = turn.response;
            const statusClass = (res.status || 'supported').toLowerCase();

            return (
              <div key={turn.id} className="chat-turn" data-testid={`chat-turn-${turnIdx}`}>
                {/* User Question Turn */}
                <div className="chat-turn-user" data-testid={`chat-turn-user-${turnIdx}`}>
                  <div className="chat-user-avatar" title={user?.full_name || 'User'}>
                    {userInitials}
                  </div>
                  <div className="chat-user-bubble">
                    <div className="chat-user-header">
                      {t('chat.userLabel')} • {turn.timestamp}
                    </div>
                    <p className="chat-user-text">{turn.question}</p>
                  </div>
                </div>

                {/* Grounded AI Response Turn */}
                <div className="chat-turn-ai" data-testid={`chat-turn-ai-${turnIdx}`}>
                  <div className="chat-ai-avatar" title="SourceCheck AI">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                      <path d="m9 12 2 2 4-4" />
                    </svg>
                  </div>

                  <div className="chat-ai-body">
                    {/* Main Answer Container */}
                    <div
                      className="qa-answer-container"
                      data-testid={isLatest ? 'qa-answer-container' : `qa-answer-container-${turnIdx}`}
                    >
                      <div className="qa-answer-card">
                        <div className="answer-card-header">
                          <h2 className="answer-card-title">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                              <path d="m9 12 2 2 4-4" />
                            </svg>
                            <span>{t('qa.answerTitle')}</span>
                          </h2>

                          <span
                            className={`status-pill ${statusClass}`}
                            data-testid={isLatest ? 'answer-status-pill' : undefined}
                          >
                            ● {res.status}
                          </span>
                        </div>

                        {/* Grounded Answer with Citations */}
                        <AnswerRenderer
                          answerText={res.answer}
                          citations={showSources ? res.citations || [] : []}
                          onCitationClick={(cit) => handleCitationClick(cit, turn.id)}
                          showCitations={showSources}
                        />
                      </div>

                      {/* Evidence Coverage */}
                      {showVerification && typeof res.evidence_coverage === 'number' && (
                        <EvidenceCoverageCard
                          coverage={res.evidence_coverage}
                          status={res.status}
                          summary={res.verification_summary}
                        />
                      )}

                      {/* Claims Breakdown */}
                      {showVerification && res.claims && res.claims.length > 0 && (
                        <ClaimList
                          claims={res.claims}
                          citations={showSources ? res.citations || [] : []}
                          onCitationClick={(cit) => handleCitationClick(cit, turn.id)}
                        />
                      )}

                      {showVerification && turn.verificationReport && (
                        <VerificationResultCard report={turn.verificationReport} />
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Loading Indicator State */}
      {isLoading && (
        <div className="qa-loading-card research-chat-loading" data-testid="qa-loading-state" role="status" aria-live="polite">
          <div className="research-loading-dots" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
          <p className="qa-loading-text">{t('qa.loadingTitle')}</p>
        </div>
      )}

      <div ref={flowEndRef} />

      {/* Sticky Bottom Docked Composer (Visible when conversation is active) */}
      {hasTurns && (
        <div className="chat-sticky-composer" data-testid="question-composer">
          <ResearchInputComposer
            value={question}
            onChange={setQuestion}
            onSubmit={(options) => handleAsk(undefined, options)}
            onStop={handleStop}
            isLoading={isLoading}
            disabled={isHistoryLoading}
            variant="sticky"
          />
        </div>
      )}
      {/* Evidence Drawer */}
      <EvidenceDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        citation={activeCitation}
        evidence={activeEvidence}
      />
    </div>
  );
};