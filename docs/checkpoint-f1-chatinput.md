# Checkpoint F1 — Research ChatInput

## Trạng thái

Đã hoàn thành ngày 28/09/2026. Đây là checkpoint focused cho lớp nhập liệu nghiên cứu trên frontend, kèm thay đổi tối thiểu để truyền trạng thái Search qua Q&A pipeline.

## Chức năng đã hoàn thành

### Composer và thao tác nhập

- Initial state compact; focus/typing chuyển sang expanded state.
- Textarea auto-resize.
- `Enter` submit; `Shift+Enter` tạo dòng mới.
- Khi request đang chạy, Send chuyển thành Stop.
- Toolbar flex ổn định, không overlap; mic nằm ngay bên trái Send.

### Tài liệu đính kèm

- Hỗ trợ PDF, DOCX và TXT.
- File picker mở từ nút `+`; drag & drop hiển thị overlay.
- File chip hiển thị tên và trạng thái `uploading`, `processing`, `ready`, `error`.
- File hợp lệ được upload qua `documentService.uploadDocument` và lấy `document_id` từ response.
- Q&A gửi một hoặc nhiều `document_ids`.
- Summary chỉ submit khi có đúng một document ở trạng thái ready.
- File không hợp lệ hoặc upload lỗi hiển thị thông báo rõ ràng.

### Search và grounding

Search không gọi internet/web search. Search sử dụng retrieval hiện có của SourceCheck:

```text
document scope → vector/BM25/hybrid retrieval → context → generation
              → claim verification → citation → output guardrail
```

Request Q&A truyền `search_enabled` và `document_ids`. Backend mặc định `search_enabled=True` để giữ backward compatibility. Khi tắt Search, pipeline vẫn retrieval grounded theo câu hỏi gốc nhưng không chạy contextual query rewrite.

### Voice input

- Dùng `SpeechRecognition` hoặc `webkitSpeechRecognition` nếu browser hỗ trợ.
- Ngôn ngữ ưu tiên `vi-VN`.
- Transcript được đưa vào textarea để người dùng kiểm tra/chỉnh sửa.
- Không tự động submit.
- Có trạng thái listening/error và fallback unsupported.

### Empty State và conversation layout

- Empty State căn giữa trong vùng `.app-content` theo cả hai chiều.
- Chiều cao empty workspace trừ đúng padding của content area, tránh scrollbar dư.
- Khi conversation bắt đầu, layout chuyển về conversation flow bình thường.
- Sticky composer có cùng chiều rộng và trục ngang với answer column sau avatar AI.
- Không thay đổi sidebar hoặc semantics Q&A/Summary.

## Contract chính

### Frontend request

```ts
interface QuestionRequest {
  question: string;
  task_type?: 'qa' | 'summary';
  search_mode?: 'hybrid' | 'vector' | 'bm25' | string;
  search_enabled?: boolean;
  document_ids?: string[];
  conversation_id?: string | null;
}
```

### Summary rule

```text
task_type=summary
+ exactly one ready document_id
→ document-grounded summary
```

## Module liên quan

- `frontend/src/components/chat/ResearchInputComposer.tsx`
- `frontend/src/pages/ResearchChatPage.tsx`
- `frontend/src/types/qa.ts`
- `frontend/src/services/documents.ts`
- `frontend/src/styles/chat.css`
- `backend/app/schemas/qa.py`
- `backend/app/api/routers/questions.py`
- `backend/app/services/qa/qa_service.py`
- `backend/app/services/qa/pipeline.py`

## Validation

- Focused frontend ChatInput/document scope/Summary tests: pass.
- Full frontend regression: `17 files / 198 tests passed`.
- Backend retrieval, document scope, verification và summary regression: `28 passed`.
- Frontend production build: pass.
- `git diff --check`: pass.

Backend test environment từng có lỗi khi đọc `DEBUG=release` từ `.env`; test được chạy lại bằng `DEBUG=false` tạm thời, không chỉnh `.env`.

## Ngoài phạm vi

- Không URL ingestion.
- Không web search.
- Không OCR/image analysis.
- Không TTS/audio backend.
- Không ownership/workspace.
- Không refactor kiến trúc Q&A/Summary.
- Chưa commit/push.