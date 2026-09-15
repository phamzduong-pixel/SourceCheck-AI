# System Overview: SourceCheck AI

Tài liệu tổng quan giới thiệu toàn bộ kiến trúc, mục tiêu, giá trị và mô hình vận hành của dự án **SourceCheck AI**. Đây là tài liệu khởi đầu dành cho mọi thành viên đội ngũ phát triển, hội đồng nghiên cứu và người dùng kỹ thuật để nắm bắt bức tranh toàn cảnh của hệ thống.

---

## 1. Mục tiêu hệ thống (System Objectives)

**SourceCheck AI** là hệ thống thẩm định tính xác thực của thông tin và đối soát nguồn dữ liệu tự động (Automated Fact-Checking & Source Verification System). Hệ thống hướng tới ba mục tiêu chiến lược:

1. **Thẩm định thông tin tự động và chuẩn xác**: Giảm thiểu thời gian rà soát thông tin từ nhiều giờ làm việc thủ công xuống còn vài giây với độ chính xác cao.
2. **Minh bạch và có khả năng kiểm chứng (Explainable & Verifiable AI)**: Không đưa ra câu trả lời dưới dạng một chiếc "hộp đen". Mọi kết luận (Đúng / Sai / Một phần đúng / Chưa đủ căn cứ) đều phải được dẫn chứng bằng đoạn trích nguyên văn (verbatim quotes) và liên kết nguồn xác thực.
3. **Giảm thiểu ảo giác của AI (Hallucination Mitigation)**: Áp dụng cơ chế kiểm soát nghiêm ngặt (Guardrails & Faithfulness Verification) để đảm bảo mô hình chỉ kết luận dựa trên bằng chứng thu thập được, triệt tiêu hiện tượng mô hình tự bịa đặt thông tin.

---

## 2. Vấn đề cần giải quyết (Problem Statement)

Trong kỷ nguyên số, thông tin sai lệch (disinformation/misinformation) và tin giả (fake news) lan truyền với tốc độ chóng mặt trên các nền tảng mạng xã hội và báo chí, gây ra những hệ lụy nghiêm trọng:
- **Khối lượng thông tin khổng lồ**: Con người không đủ thời gian và nhân lực để kiểm chứng từng tin tức lan truyền.
- **Hiện tượng ảo giác của LLM truyền thống**: Người dùng có xu hướng hỏi các mô hình AI tạo sinh thông thường, nhưng các mô hình này thường tạo ra các câu trả lời nghe có vẻ thuyết phục nhưng chứa đựng số liệu hoặc sự kiện sai sự thật (hallucination), thiếu trích dẫn nguồn có thể kiểm tra chéo.
- **Thiếu tính đối soát đa nguồn**: Các công cụ tìm kiếm hiện nay chỉ trả về danh sách liên kết trang web rời rạc, buộc người đọc phải tự đọc, tự phân tích và tự tổng hợp kết luận.

SourceCheck AI ra đời nhằm lấp đầy khoảng trống này bằng cách tự động hóa quy trình: **Tiếp nhận $\rightarrow$ Tách nhận định $\rightarrow$ Tìm kiếm bằng chứng đa nguồn $\rightarrow$ Đối soát mâu thuẫn $\rightarrow$ Kết luận kèm trích dẫn**.

---

## 3. Đối tượng sử dụng (Target Users)

Hệ thống được thiết kế phục vụ ba nhóm đối tượng chính:

| Nhóm người dùng | Nhu cầu chính | Giá trị SourceCheck AI mang lại |
| :--- | :--- | :--- |
| **Người dùng phổ thông & Độc giả** | Kiểm tra nhanh các bài đăng trên mạng xã hội, tin đồn, tin nhắn lan truyền. | Nhận ngay phán quyết nhanh, rõ ràng, dễ hiểu cùng liên kết tới các nguồn báo chí chính thống. |
| **Nhà báo, Phóng viên & Biên tập viên** | Đối soát số liệu, trích dẫn phát ngôn của nhân vật trước khi xuất bản tin tức. | Bóc tách từng nhận định (claims), tự động truy xuất tài liệu lưu trữ, tiết kiệm thời gian biên tập. |
| **Chuyên viên nghiên cứu & Tổ chức Fact-Checking** | Nghiên cứu sâu về các nguồn tin, phân tích mâu thuẫn giữa các bên, lưu vết bằng chứng. | Cung cấp báo cáo thẩm định chi tiết, phân tích độ bao phủ bằng chứng và cho phép benchmark định lượng. |

---

## 4. Giá trị cốt lõi (Core Values)

- **Nguyên tắc "Retrieve $\rightarrow$ Generate $\rightarrow$ Verify $\rightarrow$ Cite"**: Không phụ thuộc vào trí nhớ nội tại của mô hình ngôn ngữ lớn (parametric memory), mà phụ thuộc vào bằng chứng thực tế truy xuất được (non-parametric evidence).
- **Phát hiện mâu thuẫn (Contradiction Detection)**: Khả năng nhận diện những điểm bất đồng giữa nội dung người dùng nhập vào với tài liệu chuẩn, hoặc giữa các nguồn tin trái chiều với nhau.
- **Kiến trúc mô-đun hóa cao (Modular Architecture)**: Các tầng Ingestion, Retrieval, Verification và Generation độc lập, cho phép nâng cấp từng cấu phần (ví dụ đổi vector database, đổi LLM provider) mà không làm gián đoạn toàn hệ thống.

---

## 5. Luồng hoạt động tổng thể (End-to-End Workflow)

Quy trình xử lý một yêu cầu kiểm chứng trong SourceCheck AI diễn ra theo đường ống tất định 13 giai đoạn:

```text
[ Người dùng / Giao diện Web ]
              │ (Nhập câu hỏi / văn bản / tài liệu)
              ▼
[ 1. Intent Router ] ──────────────► GREETING / IDENTITY ──► Phản hồi xã giao ngay lập tức (Bypass RAG)
              │ (KNOWLEDGE_QUERY)
              ▼
[ 2. Input Guardrail ] ────────────► Kiểm tra an toàn, chống prompt injection & bảo mật
              │
              ▼
[ 3. Contextual Query Rewriter ] ──► Viết lại query đa lượt giải quyết tham chiếu ngữ cảnh
              │
              ▼
[ 4. Hybrid Retrieval ] ───────────► Dense Vector (pgvector) + Sparse Lexical (BM25)
              │
              ▼
[ 5. Reciprocal Rank Fusion (RRF) ]► Hợp nhất danh sách thứ hạng (k=60)
              │
              ▼
[ 6. Cross-Encoder Reranking ] ────► Tinh lọc & chấm điểm tương quan ngữ cảnh (bge-reranker-base)
              │
              ▼
[ 7. Evidence Sufficiency ] ───────► Đánh giá ngưỡng bằng chứng (Thiếu -> Safe Insufficient Response)
              │ (Đủ bằng chứng)
              ▼
[ 8. Context & LLM Generation ] ───► Lắp ghép Structured Context [E1], [E2] & sinh câu trả lời
              │
              ▼
[ 9. Claim Extraction ] ───────────► Bóc tách văn bản thành các nhận định sự thật độc lập
              │
              ▼
[ 10. Evidence Matching ] ─────────► Ánh xạ từng claim với đoạn bằng chứng liên quan
              │
              ▼
[ 11. Claim Verification ] ────────► Phán quyết: SUPPORTED / PARTIALLY_SUPPORTED / REFUTED / NOT_ENOUGH_INFO
              │
              ▼
[ 12. Contradiction & Coverage ] ──► Phát hiện mâu thuẫn đa nguồn & tính tỷ lệ bao phủ bằng chứng
              │
              ▼
[ 13. Citation & Output Guardrail ]► Gắn số chú thích [1], [2], quote nguyên văn & xuất bản kết quả
```

---

## 6. Các thành phần chính của hệ thống

1. **Frontend (`frontend/`)**: Giao diện web người dùng xây dựng trên nền React 18, Vite và TypeScript:
   - **Research Chat Assistant (`/chat` hoặc `/`)**: Giao diện tra cứu phong cách Perplexity, hỗ trợ hội thoại đa lượt, ngăn minh chứng trượt (Evidence Drawer), phân rã luận điểm và đo lường độ phủ bằng chứng.
   - **Fact-Checking Workspace (`/fact-check`)**: Không gian kiểm chứng chuyên sâu văn bản, hiển thị phán quyết 4 trạng thái, lập trường và cảnh báo mâu thuẫn chéo.
   - **Search / Retrieval Explorer (`/search`)**: Công cụ tra cứu retrieval độc lập, minh bạch hóa điểm số BM25, Dense Vector, RRF và Cross-Encoder.
   - **Document Knowledge Base (`/documents`)**: Quản lý nạp, xem và xóa tài liệu tri thức nội bộ (PDF, DOCX, TXT).
   - **System Dashboard (`/dashboard`)**: Tổng quan số liệu thực tế về Documents, Questions, Conversations, Verifications và phân bố phán quyết.
   - **Design System & Theme**: Thiết kế hiện đại hỗ trợ chuyển đổi Light Mode & Dark Mode Matte Charcoal.
2. **Backend API (`backend/app/api/`)**: Cung cấp các RESTful API phân tách theo domain nghiệp vụ (`auth`, `documents`, `search`, `questions`, `verify`, `dashboard`, `health`) với FastAPI, bảo vệ qua JWT Bearer token.
3. **Core Services (`backend/app/services/`)**:
   - `auth_service.py` & `oauth/`: Đăng ký, xác thực, liên kết tài khoản và trao đổi token Google OAuth an toàn.
   - `ingestion/`: Tải, làm sạch Unicode NFKC và phân tách tài liệu nguồn (Sentence Window, Fixed Size) từ PDF, DOCX, TXT.
   - `retrieval/`: Công cụ tìm kiếm lai (Hybrid Search: Dense Vector + BM25) kết hợp LlamaIndex và RRF fusion.
   - `reranking/`: Mô hình Cross-Encoder (`bge-reranker-base`) định lượng độ tương quan ngữ cảnh.
   - `generation/`: Quản lý prompt và điều phối LLM thông qua LangChain, ép kiểu đầu ra có cấu trúc.
   - `verification/`: Trái tim nghiệp vụ của SourceCheck AI (`ClaimExtractor`, `EvidenceMatcher`, `ClaimVerifier`, `ContradictionDetector`).
   - `citation/`: Hệ thống định vị nguồn, trích dẫn nguyên văn và chú thích bằng chứng có cấu trúc (`[1]`, `[2]`).
   - `guardrail/`: Hàng rào kiểm soát ảo giác (Faithfulness Check) và an toàn thông tin.
   - `qa/`: Điều phối toàn bộ quy trình Q&A (`IntentRouter`, `QueryRewriter`, `QAPipeline`, `QAService`).
   - `dashboard/`: Cung cấp thống kê tổng hợp vận hành hệ thống (`DashboardService`).
4. **Database & Storage Layer**:
   - *PostgreSQL + pgvector*: Lưu trữ thực thể dữ liệu quan hệ (Người dùng, Hội thoại, Tin nhắn, Tài liệu, Nhận định, Bằng chứng) và vector embeddings.
   - *Local SQLite Fallback*: Tự động khởi tạo và chuyển tiếp dữ liệu nội bộ (`sourcecheck.db`) khi chạy local development.
   - *Redis*: Lưu trữ bộ đệm và rate-limiting.
5. **Evaluation Framework (`evaluation/`)**: Hệ thống thực nghiệm đo lường 28 ca benchmark định lượng độc lập, kiểm thử Hit@K, Recall@K, Verification Accuracy/Macro-F1, và Intent Routing Accuracy.

---

## 7. Mối quan hệ giữa Frontend, Backend, AI, Database và Evaluation

```text
┌─────────────────────────────────────────────────────────────┐
│                   Frontend (React + Vite)                   │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / JSON API
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend API (FastAPI)                    │
│   ├── Dependencies Injection                                │
│   └── Business Domain Routers                               │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
               ▼                              ▼
┌──────────────────────────────┐ ┌────────────────────────────┐
│      Database & Storage      │ │         AI Services        │
│  ├── PostgreSQL (Relational) │ │  ├── Ingestion & Chunking  │
│  ├── Vector DB (Embeddings)  │ │  ├── LlamaIndex Retrieval  │
│  └── Redis (Cache & Session) │ │  ├── LangChain Generation  │
└──────────────▲───────────────┘ │  └── Verification Pipeline │
               │                 └────────────▲───────────────┘
               │                              │
               └──────────────┬───────────────┘
                              │
               ┌──────────────┴──────────────┐
               │    Evaluation Framework     │
               │  ├── Ground Truth Datasets  │
               │  ├── Baseline Comparisons   │
               │  └── Quantitative Metrics   │
               └─────────────────────────────┘
```

- **Frontend** chỉ giao tiếp trực tiếp với **Backend API**, hoàn toàn không nhận biết cấu trúc DB hoặc chi tiết LLM.
- **Backend API** chuyển tiếp yêu cầu đến các **Services**, đóng vai trò điều phối.
- **AI Services** tương tác với **Database** (đọc/ghi tài liệu, truy xuất vector) và các nhà cung cấp **LLM Providers**.
- **Evaluation Framework** là môi trường độc lập, có quyền truy cập vào cả tập dữ liệu chuẩn lẫn API nội bộ của Backend để thực hiện các bài benchmark khoa học và ablation study nhằm cải tiến thuật toán.

---

## 8. Sơ đồ tài liệu dự án (Documentation Map)

Để tìm hiểu sâu hơn về từng khía cạnh, vui lòng xem các tài liệu chuyên đề:
- [Features Specification](features.md): Chi tiết toàn bộ danh mục chức năng của hệ thống.
- [AI System Architecture](ai-system.md): Toàn bộ thiết kế kỹ thuật của RAG, Verification và LLM Pipeline.
- [Software Architecture](software-architecture.md): Phân tầng phần mềm và luồng dữ liệu kiến trúc.
- [Database Architecture](database-architecture.md): Mô hình dữ liệu và lược đồ cơ sở dữ liệu.
- [API Architecture](api-architecture.md): Định hướng thiết kế và quy ước API RESTful.
- [Evaluation Plan](evaluation.md): Phương pháp luận và bộ chỉ số benchmark khoa học.
- [Project Scope](project-scope.md): Phân định phạm vi MVP, giai đoạn nâng cao và tương lai.
- [Development Guidelines](development-guidelines.md): Quy chuẩn viết mã, tổ chức thư mục và nguyên tắc kỹ thuật.
