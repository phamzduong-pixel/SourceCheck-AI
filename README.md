# SourceCheck AI

**Hệ thống thẩm định thông tin và đối soát nguồn tự động (Automated Fact-Checking & Source Verification System)**

[![Backend Tests](https://img.shields.io/badge/Backend%20Tests-146%20Passed-brightgreen)](#)
[![Frontend Tests](https://img.shields.io/badge/Frontend%20Tests-16%20Passed-brightgreen)](#)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](#)
[![React](https://img.shields.io/badge/React-18%20%2B%20TypeScript-61dafb)](#)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688)](#)

---

## 1. Tổng quan dự án

**SourceCheck AI** là nền tảng phân tích, bóc tách và thẩm định tính xác thực của thông tin dựa trên AI và các nguồn dữ liệu tin cậy. Hệ thống hoạt động theo nguyên tắc cốt lõi **Retrieve $\rightarrow$ Generate $\rightarrow$ Verify $\rightarrow$ Cite $\rightarrow$ Guardrail**, triệt tiêu hiện tượng ảo giác (hallucination) của LLM bằng cách gắn chặt mọi kết luận vào các đoạn trích dẫn (verbatim quotes) và nguồn dữ liệu kiểm chứng được.

---

## 2. Trạng thái hiện tại của hệ thống (Current System State)

Hệ thống đã hoàn thành toàn bộ cốt lõi Backend AI Pipeline và nền tảng Frontend Authentication:

### 2.1. Đường ống Trí tuệ Nhân tạo (Core AI Pipeline)
- **Document Ingestion & Chunking**: Hỗ trợ nạp đa định dạng (PDF, DOCX, TXT), làm sạch Unicode NFKC, trích xuất mã SHA-256 metadata và chia đoạn (Sentence Window / Fixed Chunking).
- **Hybrid Retrieval & Reranking**: Kết hợp tìm kiếm vector dense (PostgreSQL `pgvector` / Embeddings) và tìm kiếm từ khóa sparse (BM25), hợp nhất qua thuật toán Reciprocal Rank Fusion (RRF) và tinh lọc bằng mô hình Cross-Encoder (`bge-reranker-base`).
- **Claim Extraction**: Tự động bóc tách văn bản/câu trả lời thành các nhận định sự kiện (claims) độc lập, có thể kiểm chứng.
- **Evidence Matching**: Ánh xạ từng claim với các đoạn bằng chứng tương quan dựa trên độ tương đồng ngữ nghĩa và điểm số reranking.
- **Claim Verification & Contradiction Detection**: Đánh giá lập trường từng claim theo 4 trạng thái (`SUPPORTED`, `PARTIALLY_SUPPORTED`, `REFUTED`, `NOT_ENOUGH_INFO`), phát hiện xung đột chéo giữa các nguồn tài liệu và đo lường độ phủ bằng chứng (Evidence Coverage).
- **Citation Service & Grounding**: Tạo hệ thống chú thích nguồn có cấu trúc (Footnotes, Verbatim Quotes, Source URLs, Stances).
- **Input & Output Guardrails**: Kiểm định tính trung thực (Faithfulness Check), ngăn chặn rò rỉ dữ liệu hoặc trích dẫn nguồn giả mạo.
- **End-to-End Q&A Pipeline Orchestration**: Điều phối toàn bộ quy trình xử lý câu hỏi và xuất báo cáo kiểm chứng hoàn chỉnh.

### 2.2. Hệ thống Xác thực & Bảo mật (Authentication & Security)
- **Email + Password Authentication**: Đăng ký tài khoản mới (băm mật khẩu an toàn bằng `bcrypt`), đăng nhập và cấp phát SourceCheck JWT Token thời hạn 24 giờ.
- **Google OAuth 2.0 (OpenID Connect)**: Hỗ trợ đăng nhập xã hội qua Google, chống tấn công CSRF bằng signed state token (HMAC-SHA256), liên kết an toàn với tài khoản người dùng (`email_verified`).
- **Endpoint Protection**: Bảo vệ các API nghiệp vụ (`/questions/ask`, `/auth/me`) thông qua dependency injection.
- **Database Engine & Fallback**: Hỗ trợ PostgreSQL + `pgvector` cho production và tự động fallback sang SQLite (`sourcecheck.db`) trong môi trường local development khi chưa cấu hình PostgreSQL server.

### 2.3. Giao diện Người dùng (Frontend UI)
- **Phong cách Glassmorphism hiện đại**: Thiết kế thẻ kính mờ cao cấp (`backdrop-filter: blur(24px) saturate(180%)`), nền pastel nhạt chuyển sắc động với các khối sáng trôi nhẹ (ambient floating glow orbs), ô nhập liệu bán trong suốt có viền phát sáng khi focus.
- **Nút đăng nhập Google đa màu**: Tích hợp SVG chuẩn Google, hiệu ứng nhấc nhẹ và trạng thái loading trực quan.
- **Trang xử lý OAuth Callback**: Tự động nhận mã ủy quyền từ Google, trao đổi lấy JWT và xử lý thân thiện khi người dùng hủy bỏ (`error=access_denied`).
- **Kiểm soát hiển thị mật khẩu tối ưu**: Nút con mắt SVG mở/đóng (`EyeIcon.tsx`), triệt tiêu xung đột với icon mặc định của trình duyệt (`::-ms-reveal`).
- **Cấu hình Reverse Proxy**: Vite server chuyển tiếp tự động các request `/api` sang backend FastAPI (port 8000).

---

## 3. Cấu trúc thư mục dự án

```text
SourceCheck-AI/
├── frontend/                     # Giao diện người dùng (React 18 + TypeScript + Vite)
│   ├── src/
│   │   ├── components/auth/      # GoogleButton, EyeIcon, ProtectedRoute
│   │   ├── context/              # AuthContext (quản lý state đăng nhập toàn cục)
│   │   ├── hooks/                # useAuth hook
│   │   ├── pages/                # LoginPage, RegisterPage, OAuthCallbackPage, Workspace
│   │   ├── services/             # auth.ts (gọi API backend & xử lý JWT)
│   │   ├── styles/               # auth.css (Hệ thống thiết kế Glassmorphism)
│   │   ├── types/                # TypeScript interfaces
│   │   └── test/                 # Test suite Vitest (16 unit & integration tests)
│   └── vite.config.ts            # Cấu hình Vite & API reverse proxy
│
├── backend/                      # Ứng dụng backend xử lý nghiệp vụ (FastAPI)
│   ├── alembic/                  # Database schema migrations
│   ├── app/
│   │   ├── api/                  # API routers (auth, questions, documents, search, health)
│   │   ├── core/                 # config, database, security, logging
│   │   ├── models/               # SQLAlchemy models (User, Document, Claim, Citation, etc.)
│   │   ├── schemas/              # Pydantic schemas (Request & Response models)
│   │   └── services/             # Core business & AI modules:
│   │       ├── auth_service.py   # Quản lý đăng ký, đăng nhập & liên kết tài khoản
│   │       ├── oauth/            # GoogleOAuthProvider & BaseOAuthProvider
│   │       ├── ingestion/        # Parsers, cleaners & splitters
│   │       ├── retrieval/        # Dense, sparse & hybrid retrievers
│   │       ├── reranking/        # Cross-encoder rerankers
│   │       ├── generation/       # LLM generation & answer assembler
│   │       ├── verification/     # Claim extraction, matcher, verifier, contradiction
│   │       ├── citation/         # Footnotes formatting & source grounding
│   │       ├── guardrail/        # Faithfulness & safety guardrails
│   │       └── qa/               # End-to-end QAService & Pipeline orchestration
│   └── tests/                    # Test suite Pytest (146 unit & integration tests)
│
├── docs/                         # Tài liệu kiến trúc và hướng dẫn kỹ thuật chi tiết
├── evaluation/                   # Môi trường benchmark & ablation study
├── .env.example                  # Mẫu cấu hình biến môi trường
└── README.md                     # Tài liệu tổng quan
```

---

## 4. Khởi động nhanh (Quick Start)

### 4.1. Yêu cầu môi trường
- **Python**: $\ge$ 3.10
- **Node.js**: $\ge$ 18.x
- **Trình quản lý gói**: `npm` và `pip`

### 4.2. Khởi chạy Backend
```bash
cd backend
# Cài đặt dependencies (nếu chưa có)
pip install -r requirements.txt

# Khởi chạy server FastAPI với Uvicorn (Port 8000)
uvicorn app.main:app --reload
```

### 4.3. Khởi chạy Frontend
```bash
cd frontend
# Cài đặt dependencies (nếu chưa có)
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

*(Bạn cũng có thể tạo tài khoản mới tại `http://localhost:5173/register` hoặc đăng nhập bằng Google)*

---

## 5. Kết quả Kiểm thử & Đóng gói (Test & Build Metrics)

- **Backend Pytest**: **146 / 146 tests passed** (100% pass rate trên 16 test modules).
- **Frontend Vitest**: **16 / 16 tests passed** (Bao gồm form validation, toggle password, OAuth callback, router protection).
- **Frontend Production Build**: `npm run build` biên dịch thành công với **0 lỗi TypeScript**.

---

## 6. Danh mục Tài liệu Kỹ thuật Chi tiết

Để tìm hiểu sâu hơn về từng phân hệ, vui lòng đọc các tài liệu chuyên đề trong thư mục `docs/`:
- [System Overview](docs/system-overview.md) — Kiến trúc tổng thể và luồng vận hành toàn hệ thống.
- [AI System Architecture](docs/ai-system.md) — Đặc tả chi tiết các giải thuật và tầng AI/RAG Pipeline.
- [Software Architecture](docs/software-architecture.md) — Phân tích phân tầng phần mềm và các mẫu thiết kế.
- [Database Architecture](docs/database-architecture.md) — Thiết kế cơ sở dữ liệu quan hệ và vector embeddings.
- [API Architecture & Endpoints](docs/api-architecture.md) — Quy ước giao tiếp RESTful và danh mục API endpoints.
- [Features Specification](docs/features.md) — Đặc tả chi tiết các nhóm chức năng của hệ thống.
- [Evaluation & Benchmark Plan](docs/evaluation.md) — Kế hoạch thực nghiệm và bộ chỉ số khoa học.
- [Development Guidelines](docs/development-guidelines.md) — Quy chuẩn lập trình và quy trình phát triển.
