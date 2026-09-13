# Software Architecture: SourceCheck AI

Tài liệu mô tả kiến trúc phần mềm tổng thể của hệ thống SourceCheck AI, phân tích chi tiết các tầng phân quyền trách nhiệm (Layered Architecture), luồng dữ liệu (Data Flow) và các nguyên lý thiết kế hệ thống.

---

## 1. Sơ đồ Phân tầng Kiến trúc (Layered Architecture)

Hệ thống được tổ chức theo mô hình phân tầng nghiêm ngặt (Strict Layered / Clean Architecture). Mỗi tầng chỉ phụ thuộc vào tầng bên dưới nó thông qua các giao diện trừu tượng (interfaces/abstractions):

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. PRESENTATION LAYER (Giao diện người dùng)                                │
│    ├── React 18 + TypeScript + Vite (Port 5173 with Reverse Proxy)          │
│    ├── Glassmorphism Design System (Frosted Glass, Ambient Glow Orbs)       │
│    ├── Auth State (AuthContext, useAuth, Token Persistence, SVG Eye Toggle) │
│    └── Components & Pages (LoginPage, RegisterPage, OAuthCallbackPage)      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTP / JSON REST (Proxied /api)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. API LAYER (Tầng giao tiếp & Điều phối mạng)                              │
│    ├── FastAPI App & Lifespan Event Management (Port 8000)                  │
│    ├── Routers: /auth, /documents, /search, /questions, /verify, /health    │
│    └── Security Dependencies (JWT Bearer, OAuth2, Request Validation)       │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Service Calls
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. SERVICE LAYER (Tầng nghiệp vụ trung tâm)                                 │
│    ├── AuthService & GoogleOAuthProvider (Local & OAuth 2.0 Auth)           │
│    ├── IngestionService (Coordination of Loading & Splitting)               │
│    ├── VerificationService (Claim Extraction, Matcher, Verifier, Stance)    │
│    ├── CitationService (Footnotes & Source Attribution)                     │
│    ├── GuardrailService (Faithfulness & Hallucination Mitigation)           │
│    └── QAService (End-to-End Pipeline Orchestrator)                         │
└───────────────────┬─────────────────────────────────────┬───────────────────┘
                    │                                     │
                    ▼                                     ▼
┌──────────────────────────────────────┐ ┌────────────────────────────────────┐
│ 4. AI / RAG LAYER                    │ │ 5. DATA ACCESS LAYER (Repositories)│
│    ├── LlamaIndex RAG Framework      │ │    ├── BaseRepository[Model]       │
│    ├── Hybrid Retriever (Dense+BM25) │ │    ├── DocumentRepository          │
│    ├── Cross-Encoder Reranker        │ │    ├── VerificationRepository      │
│    ├── LangChain LLM Orchestration   │ │    └── SQLAlchemy 2.0 AsyncSession │
│    └── Structured Output Enforcement │ └─────────────────┬──────────────────┘
└───────────────────┬──────────────────┘                   │
                    │                                      │
                    └──────────────────┬───────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 6. DATABASE & STORAGE LAYER (Tầng lưu trữ vật lý)                           │
│    ├── PostgreSQL 16 + pgvector (Primary Relational & Vector Storage)       │
│    ├── Local SQLite Engine (Automatic Resilient Fallback: sourcecheck.db)   │
│    └── Redis 7 (Cache, Task Queue & Rate-Limiting)                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Chi tiết Trách nhiệm Từng Phân tầng

### 2.1. Presentation Layer (Tầng Trình diễn)
- **Công nghệ**: React, Vite, TypeScript.
- **Trách nhiệm**:
  - Tiếp nhận tương tác từ người dùng, quản lý trạng thái UI cục bộ (Form state, Loading indicators).
  - Gửi yêu cầu qua HTTP Client (`axios` hoặc `fetch`) tới Backend API.
  - Hiển thị kết quả kiểm chứng trực quan: Thẻ trạng thái màu sắc theo phán quyết, trích dẫn có thể nhấp để xem tài liệu gốc, biểu đồ độ bao phủ bằng chứng.
- **Ranh giới**: Hoàn toàn không chứa logic AI, không truy vấn trực tiếp CSDL.

### 2.2. API Layer (Tầng Giao tiếp & Điều phối mạng)
- **Công nghệ**: FastAPI (Python 3.10+).
- **Trách nhiệm**:
  - Tiếp nhận các HTTP Request, kiểm tra tính hợp lệ của dữ liệu đầu vào thông qua Pydantic Schemas.
  - Quản lý phiên làm việc, bảo vệ endpoint bằng dependency injection (`get_current_active_user`, `OAuth2PasswordBearer`).
  - Phân luồng xử lý tới router tương ứng (`/auth`, `/documents`, `/search`, `/questions`, `/verify`).
  - Chuẩn hóa mã phản hồi HTTP (200, 201, 400, 401, 404, 500) và gói dữ liệu trong phong bì chuẩn `APIResponse`.
- **Ranh giới**: Không chứa thuật toán nghiệp vụ hoặc logic suy luận.

### 2.3. Service Layer (Tầng Nghiệp vụ)
- **Công nghệ**: Thuần Python (Pure Python Services).
- **Trách nhiệm**:
  - Hiện thực hóa các quy tắc nghiệp vụ cốt lõi của SourceCheck AI.
  - Quản lý định danh người dùng & OAuth: `AuthService` xử lý đăng ký tài khoản (băm mật khẩu bằng `bcrypt`), xác thực thông tin đăng nhập, liên kết an toàn tài khoản Google OAuth (`GoogleOAuthProvider`, `BaseOAuthProvider`) và cấp phát SourceCheck JWT token.
  - Đóng vai trò nhạc trưởng (orchestrator): Ví dụ, `VerificationService` nhận text $\rightarrow$ gọi `ClaimExtractor` $\rightarrow$ gọi `EvidenceMatcher` $\rightarrow$ gọi `ClaimVerifier` $\rightarrow$ gọi `ContradictionDetector` $\rightarrow$ gọi `CitationService`.
- **Ranh giới**: Không phụ thuộc vào giao thức HTTP hay khung web FastAPI; có thể dễ dàng gọi từ CLI hoặc Celery task.

### 2.4. AI / RAG Layer (Tầng Trí tuệ Nhân tạo & Truy xuất)
- **Công nghệ**: LlamaIndex (Data/Index), LangChain (Prompt/LLM), HuggingFace Transformers (Rerankers).
- **Trách nhiệm**:
  - Quản lý index vector và tìm kiếm lai BM25 + Dense vector.
  - Thực hiện tái xếp hạng bằng chứng bằng mô hình Cross-Encoder.
  - Kết nối tới LLM Providers (OpenAI, Anthropic, Local LLMs) qua lớp trừu tượng `BaseLLMProvider`.
  - Ép kiểu kết quả sinh từ LLM vào các định dạng có cấu trúc chặt chẽ (Pydantic).
- **Ranh giới**: Tách biệt hoàn toàn với tầng truy cập cơ sở dữ liệu quan hệ.

### 2.5. Data Access Layer (Tầng Truy cập Dữ liệu)
- **Công nghệ**: SQLAlchemy 2.0 Async, Repository Pattern.
- **Trách nhiệm**:
  - Trừu tượng hóa các câu lệnh truy vấn SQL (SELECT, INSERT, UPDATE, DELETE).
  - Quản lý Session và Transaction của cơ sở dữ liệu.
  - Chuyển đổi giữa các bản ghi cơ sở dữ liệu (ORM Models) và các đối tượng nghiệp vụ.
- **Ranh giới**: Các tầng trên (Services) chỉ gọi các phương thức như `get_by_id()`, `create()` mà không cần viết câu lệnh SQL thuần.

### 2.6. Database & Storage Layer (Tầng Lưu trữ Vật lý)
- **Công nghệ**: PostgreSQL, Vector DB, Redis.
- **Trách nhiệm**: Đảm bảo tính toàn vẹn dữ liệu (ACID), khả năng lưu trữ bền vững và tốc độ tìm kiếm vector mili-giây.

---

## 3. Luồng Dữ liệu Điển hình: Quy trình Thẩm định (Verification Data Flow)

Dưới đây là hành trình của một request kiểm chứng từ lúc người dùng gửi tới khi nhận kết quả:

```text
User 
 │  1. POST /api/v1/verify { "text": "..." }
 ▼
[API Router: verification.py]
 │  2. Validate Pydantic Schema
 │  3. Resolve VerificationService via Dependency Injection
 ▼
[VerificationService]
 │  4. Gọi ClaimExtractor: Tách text thành [Claim 1, Claim 2]
 │  5. Với mỗi Claim:
 │      a. Gọi RetrievalService: Chạy Hybrid Search (Vector + BM25)
 │      b. Gọi RerankService: Chấm điểm lại bằng Cross-Encoder
 │      c. Gọi ClaimVerifier: LLM suy luận ra Verdict + Quote
 │  6. Gọi ContradictionDetector: Kiểm tra mâu thuẫn giữa các Claim
 │  7. Gọi FaithfulnessChecker: Kiểm tra ảo giác
 │  8. Gọi CitationService: Đánh số trích dẫn [1], [2]
 │  9. Gọi VerificationRepository: Lưu kết quả vào PostgreSQL
 ▼
[API Router: verification.py]
 │  10. Đóng gói vào APIResponse[VerificationResultResponse]
 ▼
User (Nhận JSON & Render giao diện trực quan)
```

---

## 4. Nguyên tắc Thiết kế & Đảm bảo Chất lượng

1. **Single Responsibility Principle (SRP)**: Mỗi class, file hoặc package chỉ chịu trách nhiệm cho một khía cạnh duy nhất.
2. **Dependency Inversion (DIP)**: Các module cấp cao không phụ thuộc vào chi tiết cài đặt của module cấp thấp; cả hai đều phụ thuộc vào abstractions (Ví dụ: `LLMService` gọi `BaseLLMProvider`).
3. **Stateless Backend**: Máy chủ Backend không lưu trạng thái phiên làm việc trong bộ nhớ tiến trình (process memory), cho phép triển khai nhiều replicas sau bộ cân bằng tải (Load Balancer).
4. **Graceful Error Handling**: Mọi ngoại lệ domain đều được bắt và định dạng thành mã lỗi JSON chuẩn, không làm lộ stack trace nội bộ ra client.
