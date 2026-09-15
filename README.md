# SourceCheck AI

**Hệ thống thẩm định thông tin và đối soát nguồn tự động (Automated Fact-Checking & Source Verification System)**

[![Backend Tests](https://img.shields.io/badge/Backend%20Tests-249%2B%20Passed-brightgreen)](#)
[![Frontend Tests](https://img.shields.io/badge/Frontend%20Tests-166%20Passed-brightgreen)](#)
[![Evaluation Benchmark](https://img.shields.io/badge/Evaluation-28%2F28%20Passed%20(100%25)-brightgreen)](#)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](#)
[![React](https://img.shields.io/badge/React-18%20%2B%20TypeScript-61dafb)](#)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688)](#)

---

## 1. Tổng quan dự án

**SourceCheck AI** là nền tảng phân tích, bóc tách và thẩm định tính xác thực của thông tin dựa trên AI và các nguồn dữ liệu tin cậy. Hệ thống hoạt động theo nguyên tắc cốt lõi **Retrieve $\rightarrow$ Generate $\rightarrow$ Verify $\rightarrow$ Cite $\rightarrow$ Guardrail**, triệt tiêu hoàn toàn hiện tượng ảo giác (hallucination) của LLM bằng cách gắn chặt mọi kết luận vào các đoạn trích dẫn nguyên văn (verbatim quotes) và nguồn dữ liệu kiểm chứng được.

Hệ thống được thiết kế theo mô hình **Đường ống tất định 13 giai đoạn (13-Stage Deterministic Pipeline)**, hoàn toàn không phụ thuộc vào các tác nhân tự trị (Autonomous / ReAct Agents) thiếu ổn định.

```text
User Input / Query
       │
       ▼
[ 1. Intent Router ] ──────────────► [ GREETING / IDENTITY ] ──► Phản hồi xã giao ngay lập tức (Bypass RAG)
       │ (KNOWLEDGE_QUERY)
       ▼
[ 2. Input Guardrail ] ────────────► Kiểm tra an toàn / prompt injection
       │
       ▼
[ 3. Contextual Query Rewriter ] ──► Viết lại query đa lượt dựa trên lịch sử hội thoại
       │
       ▼
[ 4. Hybrid Retrieval ] ───────────► Dense Vector (pgvector) + Sparse Lexical (BM25)
       │
       ▼
[ 5. Reciprocal Rank Fusion (RRF) ]► Hợp nhất thứ hạng đa kênh
       │
       ▼
[ 6. Cross-Encoder Reranking ] ────► Tinh lọc & tính điểm tương quan ngữ cảnh (bge-reranker-base)
       │
       ▼
[ 7. Evidence Sufficiency ] ───────► Đánh giá ngưỡng bằng chứng (Thiếu -> Safe Insufficient Evidence Response)
       │ (Đủ bằng chứng)
       ▼
[ 8. Context Building & Generation]► LangChain + Structured Pydantic Output
       │
       ▼
[ 9. Claim Extraction ] ───────────► Bóc tách các nhận định sự thật độc lập
       │
       ▼
[ 10. Evidence Matching ] ─────────► Ánh xạ từng claim với passage liên quan
       │
       ▼
[ 11. Claim Verification ] ────────► Suy luận phán quyết: SUPPORTED / PARTIALLY_SUPPORTED / REFUTED / NOT_ENOUGH_INFO
       │
       ▼
[ 12. Contradiction & Coverage ] ──► Phát hiện xung đột đa nguồn & đo lường tỷ lệ bao phủ bằng chứng
       │
       ▼
[ 13. Citation & Output Guardrail ]► Đánh số chú thích [1], [2], gắn trích dẫn nguyên văn & xuất bản
```

---

## 2. Các Phân hệ Chức năng Chính (System Modules)

### 2.1. Không gian Tra cứu Nghiên cứu (Research Chat Assistant — `/chat` hoặc `/`)
- **Tra cứu tức thì & Gợi ý chủ đề**: Giao diện hội thoại thông minh phong cách ChatGPT / DeepSeek / Perplexity với các thẻ gợi ý câu hỏi mẫu (Prompt Starters).
- **Trải nghiệm Hội thoại Đỉnh cao (Balanced Chat UX)**: Căn chỉnh trục dọc thẳng hàng tuyệt đối (balanced left-rail) giữa tin nhắn người dùng và phản hồi AI với avatar 34x34px, khung chat tối đa 820px, loại bỏ hoàn toàn hiện tượng lệch mép.
- **Sticky Top Header & Tên cuộc trò chuyện**: Thanh Header cố định ở trên cùng viewport (`position: sticky; top: 0;`), tự động hiển thị tên tóm tắt cuộc trò chuyện kèm badge `● Grounded` và nút **"+ Tra cứu mới"** luôn đứng yên khi cuộn qua các câu trả lời dài.
- **Hội thoại Đa lượt (Multi-turn Conversation)**: Lưu trữ lịch sử `User -> Conversation -> Message`, tự động viết lại câu hỏi nối tiếp thông qua **Contextual Query Rewriter**.
- **Ngăn Minh chứng Trượt (Evidence Drawer)**: Chú thích số tương tác `[1]`, `[2]`, bấm để mở ngăn trượt bên phải hiển thị trích dẫn nguyên văn, nguồn xuất bản, URL và độ tương đồng ngữ nghĩa.
- **Phân rã Luận điểm & Độ phủ Bằng chứng (Claims Breakdown & Coverage)**: Trực quan hóa từng nhận định thành phần và tỷ lệ phần trăm dữ liệu được bảo chứng.
- **Intent Router**: Tự động nhận diện và phản hồi tức thì các câu chào hỏi (`hello`, `xin chào`) hoặc câu hỏi danh tính (`bạn là ai`) mà không kích hoạt RAG.
- **Giao diện Tối giản Graylight / Matte Charcoal**: Tông màu xám than sang trọng, hỗ trợ chuyển đổi mượt mà Light Mode (`#f9f9fb`) và Dark Mode (`#212121`).

### 2.2. Không gian Thẩm định Chuyên sâu (Fact-Checking Workspace — `/fact-check`)
- **Quy trình Kiểm chứng Đa tầng**: Tiếp nhận văn bản/tin tức phức tạp, tự động bóc tách các claims độc lập và truy vấn kho tri thức đối soát chéo.
- **Phán quyết theo Luận điểm (Stance Badging)**: Gán nhãn 4 phán quyết rõ ràng (`SUPPORTED`, `PARTIALLY_SUPPORTED`, `REFUTED`, `NOT_ENOUGH_INFO`).
- **Cảnh báo Mâu thuẫn (Contradiction Alerts)**: Phát hiện và cảnh báo trực quan các điểm bất đồng hoặc xung đột thông tin giữa các tài liệu đối chứng.

### 2.3. Khám phá Truy xuất & Xếp hạng (Search / Retrieval Explorer — `/search`)
- **Quan sát Minh bạch Pipeline Truy xuất**: Cho phép nhập query độc lập để kiểm tra kết quả retrieval của hệ thống.
- **Chi tiết Điểm số & Thứ hạng**: Hiển thị phân rã chi tiết thứ hạng BM25 rank, Dense Vector rank, RRF score, Cross-Encoder reranker score và final rank.

### 2.4. Quản lý Tài liệu Tri thức (Document Knowledge Base — `/documents`)
- **Nạp Đa Định dạng**: Hỗ trợ tải lên tài liệu PDF, DOCX, TXT với quy trình parse, clean Unicode NFKC, trích xuất SHA-256 hash và chunking tự động.
- **Quản lý Vòng đời**: Danh sách tài liệu thật từ backend, xem chi tiết metadata/chunks và xóa tài liệu.

### 2.5. Tổng quan Hệ thống (Dashboard — `/dashboard`)
- **Số liệu Vận hành Thực tế**: Thống kê tổng số Documents, Questions, Conversations, Verifications, tỷ lệ phân bố phán quyết (Verdict distribution) và biểu đồ hoạt động.

---

## 3. Cấu trúc Thư mục Dự án

```text
SourceCheck-AI/
├── frontend/                     # Giao diện người dùng (React 18 + TypeScript + Vite)
│   ├── src/
│   │   ├── components/           # UI components (auth, layout, qa, factCheck, documents, search, dashboard)
│   │   ├── context/              # AuthContext, AIPreferencesContext
│   │   ├── hooks/                # useAuth, useAIPreferences hooks
│   │   ├── i18n/                 # Đa ngôn ngữ độc lập: UI (vi/en) & AI Model (vi/en)
│   │   ├── pages/                # ResearchChatPage, FactCheckPage, DocumentsPage, SearchExplorerPage, DashboardPage, LoginPage, RegisterPage
│   │   ├── services/             # apiClient, auth, qa, verification, documents, search, dashboard, system
│   │   ├── styles/               # Theme tokens & stylesheet cho từng phân hệ (layout, chat, documents, dashboard, search, factcheck)
│   │   └── test/                 # 166 unit & integration tests (Vitest)
│   └── vite.config.ts            # Cấu hình Vite & API reverse proxy
│
├── backend/                      # Ứng dụng backend xử lý nghiệp vụ (FastAPI)
│   ├── alembic/                  # Database schema migrations
│   ├── app/
│   │   ├── api/                  # API routers (auth, questions, verify, documents, search, dashboard, health)
│   │   ├── core/                 # config, database, security, logging
│   │   ├── models/               # SQLAlchemy models (User, Conversation, Message, Document, Claim, Citation, etc.)
│   │   ├── schemas/              # Pydantic schemas (Conversation, Question, Verify, Document, Search, etc.)
│   │   └── services/             # Core business & AI modules:
│   │       ├── auth_service.py   # Quản lý đăng ký, đăng nhập & liên kết OAuth
│   │       ├── ingestion/        # Parsers (PDF, DOCX, TXT), cleaners & splitters
│   │       ├── retrieval/        # Dense (pgvector), sparse (BM25) & hybrid retrievers (RRF)
│   │       ├── reranking/        # Cross-encoder rerankers (bge-reranker-base)
│   │       ├── generation/       # LLM generation & context builder
│   │       ├── verification/     # Claim extraction, matcher, verifier, contradiction
│   │       ├── citation/         # Footnotes formatting & source grounding
│   │       ├── guardrail/        # Faithfulness & safety guardrails
│   │       └── qa/               # Intent router, query rewriter, QAService orchestration
│   └── tests/                    # 249+ unit & integration tests (Pytest)
│
├── docs/                         # Tài liệu kiến trúc và hướng dẫn kỹ thuật chi tiết
│   ├── demo-guide.md             # Kịch bản demo 8 bước hoàn chỉnh
│   ├── evaluation.md             # Báo cáo thực nghiệm & bộ chỉ số khoa học
│   ├── ai-system.md              # Đặc tả chi tiết đường ống AI 13 giai đoạn
│   ├── software-architecture.md  # Kiến trúc phân tầng và thiết kế phần mềm
│   ├── system-overview.md        # Tổng quan toàn diện hệ thống
│   ├── database-architecture.md  # Mô hình cơ sở dữ liệu quan hệ & vector
│   └── api-architecture.md       # Đặc tả các REST API endpoints
├── evaluation/                   # Bộ benchmark kiểm thử 28 ca đánh giá định lượng
├── .env.example                  # Mẫu cấu hình biến môi trường chuẩn
└── README.md                     # Tài liệu tổng quan
```

---

## 4. Khởi động Nhanh (Quick Start)

### 4.1. Yêu cầu môi trường
- **Python**: $\ge$ 3.10
- **Node.js**: $\ge$ 18.x
- **Trình quản lý gói**: `npm` và `pip`

### 4.2. Khởi chạy Backend
```bash
cd backend
# Cài đặt dependencies
pip install -r requirements.txt

# Khởi chạy server FastAPI với Uvicorn (Port 8000)
uvicorn app.main:app --reload
```

### 4.3. Khởi chạy Frontend
```bash
cd frontend
# Cài đặt dependencies
npm install

# Khởi chạy dev server Vite (Port 5173)
npm run dev
```

### 4.4. Tài khoản Demo có sẵn (Seed Account)
Hệ thống tự động kích hoạt tài khoản demo sẵn sàng để đăng nhập và trải nghiệm:
- **URL đăng nhập**: `http://localhost:5173/login`
- **Email**: `demo@sourcecheck.ai`
- **Mật khẩu**: `Password123!`
- **Họ tên**: `Demo User`
- **Vai trò**: `researcher`

### 4.5. Hướng dẫn Trình diễn Demo (Live Demo Script)
Xem chi tiết kịch bản 8 bước trình diễn sản phẩm tại: [Demo Presentation Guide](docs/demo-guide.md).

---

## 5. Kết quả Thực nghiệm & Kiểm thử (Verification & Metrics)

### 5.1. Automated Test Suites
- **Frontend Test Suite**: **166 / 166 tests passed (100%)** trên 9 test suites (`apiClient`, `chat`, `qa`, `auth`, `factCheck`, `layout`, `documents`, `search`, `dashboard`).
- **Frontend Production Build**: `tsc && vite build` hoàn thành với **0 lỗi TypeScript / lint**.
- **Backend Test Suite**: **249+ tests passed** trên toàn bộ các domain AI, Q&A, Ingestion, Retrieval, Verification, Conversation, Search, và Auth.

### 5.2. RAG & Verification Benchmark Results (`evaluation/run_evaluation.py`)
- **Tổng số ca thực nghiệm**: 28 test cases.
- **Tỷ lệ vượt qua**: **28 / 28 cases passed (100%)**.
- **Retrieval Hit@1 / Hit@3**: **1.000 / 1.000**.
- **Retrieval Recall@1 / Recall@3**: **1.000 / 1.000**.
- **Verification Accuracy / Macro-F1**: **1.000 / 1.000** trên 4 nhãn (`SUPPORTED`, `PARTIALLY_SUPPORTED`, `REFUTED`, `NOT_ENOUGH_INFO`).
- **Intent Router Accuracy**: **1.000** (Greeting & Identity classification).
- **Zero Hallucination Tolerance**: 100% các câu hỏi thiếu bằng chứng được trả về thông báo an toàn giải thích rõ ràng lý do.

---

## 6. Danh mục Tài liệu Kỹ thuật Chi tiết

Để tìm hiểu sâu hơn về từng phân hệ, vui lòng đọc các tài liệu chuyên đề trong thư mục `docs/`:
- [Demo Presentation Guide](docs/demo-guide.md) — Kịch bản demo 8 bước chi tiết cho thuyết trình và nghiệm thu.
- [Evaluation & Benchmark Report](docs/evaluation.md) — Báo cáo thực nghiệm định lượng và kết quả kiểm thử khoa học.
- [System Overview](docs/system-overview.md) — Kiến trúc tổng thể và luồng vận hành toàn hệ thống.
- [AI System Architecture](docs/ai-system.md) — Đặc tả chi tiết các giải thuật và tầng AI/RAG Pipeline 13 giai đoạn.
- [Software Architecture](docs/software-architecture.md) — Phân tích phân tầng phần mềm và các mẫu thiết kế.
- [Database Architecture](docs/database-architecture.md) — Thiết kế cơ sở dữ liệu quan hệ và vector embeddings.
- [API Architecture & Endpoints](docs/api-architecture.md) — Quy ước giao tiếp RESTful và danh mục API endpoints.
- [Features Specification](docs/features.md) — Đặc tả chi tiết các nhóm chức năng của hệ thống.
- [Development Guidelines](docs/development-guidelines.md) — Quy chuẩn lập trình và quy trình phát triển.

## Current completion status

- **Conversations authentication**: Conversation requests send Authorization: Bearer access_token. Existing token-expiration handling remains unchanged.
- **Conversation history**: GET /api/v1/conversations/ returns only conversations owned by the current user. Greetings such as hello create or reuse a conversation and persist both user and assistant messages.
- **Conversation lifecycle**: opening Chat, loading the Sidebar, and refreshing do not create a conversation. A conversation appears after a real user message; create, reload, and delete remain synchronized between UI and backend.
- **Test isolation**: conversation tests use an isolated SQLite in-memory database/session override and do not write to the development database. Existing test data was cleaned by test title/user; database backups are retained when recovery is needed.
- **Search /search**: the form is user-facing (Evidence Exploration (Vietnamese: evidence exploration)). Retrieval strategy remains backend-controlled; Hybrid Search, BM25, RRF, reranking, and scores are available only in Retrieval Details.
- **UI localization**: typed vi/en dictionaries cover navigation, Sidebar, Chat input and keyboard hints, Search, Documents, Verification, auth, theme/language controls, and Dashboard. Technical terms remain unchanged where appropriate.
- **Dashboard**: statistics come from dashboardService.getStats(). Refresh requests the Dashboard API again and updates statistics, verification distribution, and recent activity.

Frontend validation: cd frontend; run the focused Vitest command documented above, followed by npm run build.
