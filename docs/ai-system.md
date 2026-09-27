# AI System Architecture: SourceCheck AI

Tài liệu kỹ thuật trung tâm mô tả toàn bộ kiến trúc, công nghệ, giải thuật và đường ống (pipeline) xử lý trí tuệ nhân tạo của hệ thống **SourceCheck AI**.

---

## 1. Mục tiêu AI (AI Objectives)

Trọng tâm của hệ thống AI trong SourceCheck AI là **Tính chính xác dựa trên bằng chứng (Evidence-Grounded Accuracy)** và **Khả năng giải thích minh bạch (Explainability)**.

Khác với các hệ thống sinh văn bản tự do hoặc các tác nhân tự trị (Autonomous/ReAct Agents) vốn có tính bất định cao (non-deterministic) và dễ rơi vào vòng lặp suy diễn sai, SourceCheck AI được xây dựng theo mô hình **Đường ống có kiểm soát chặt chẽ (Deterministic Multi-Stage Pipeline)** với kiến trúc 4 pha nền tảng:

$$\mathbf{Retrieve} \longrightarrow \mathbf{Generate} \longrightarrow \mathbf{Verify} \longrightarrow \mathbf{Cite}$$

Hệ thống đặt ra 3 nguyên tắc bất biến:
1. **Không suy đoán ngoài tài liệu**: Mọi khẳng định phải bắt nguồn trực tiếp từ dữ liệu chứng minh được truy xuất.
2. **Không ảo giác (Zero Hallucination Tolerance)**: Áp dụng cơ chế Guardrail kiểm tra độ trung thực (Faithfulness) trước khi phát hành câu trả lời.
3. **Phân tách công việc rõ ràng**: Sử dụng **LlamaIndex** làm xương sống cho Data & RAG Layer, và **LangChain** cho LLM Orchestration & Structured Output.

---

## 2. Kiến trúc tổng quan đường ống AI (13-Stage Pipeline Architecture)

```text
               ┌────────────────────────────────────────────────────────┐
               │                  User Input (Text / Query)             │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. INTENT ROUTING (Deterministic Regex / Keyword Intent Classifier)                    │
│    ├── GREETING / IDENTITY ──► Phản hồi xã giao / danh tính tức thì (Bypass RAG)       │
│    └── KNOWLEDGE_QUERY     ──► Tiếp tục đường ống RAG kiểm chứng chuyên sâu            │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 2. INPUT GUARDRAIL & QUERY REWRITING                                                   │
│    ├── Input Guardrail (Kiểm tra an toàn, chống prompt injection, cô lập untrusted)    │
│    └── Contextual Query Rewriter (Giải quyết tham chiếu ngữ cảnh trong hội thoại đa lượt)│
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 3. HYBRID RETRIEVAL & RERANKING                                                        │
│    ├── Dense Vector Retrieval (PostgreSQL + pgvector / HNSW Semantic Search)           │
│    ├── Sparse Lexical Retrieval (BM25 Keyword Matching)                                │
│    ├── Hybrid Search Fusion (Reciprocal Rank Fusion - RRF k=60)                        │
│    └── Cross-Encoder Reranking (BGE-Reranker-Base: Đo tương quan sâu câu hỏi - passage)│
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 4. EVIDENCE SUFFICIENCY & CONTEXT BUILDING                                             │
│    ├── Evidence Sufficiency Check (Ngắt an toàn nếu không tìm thấy bằng chứng hợp lệ)  │
│    └── Structured Context Builder (Lắp ghép top-k bằng chứng có đánh số [E1], [E2])    │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 5. GROUNDED GENERATION & FACT-CHECKING REASONING                                       │
│    ├── Grounded LLM Generation (LangChain Prompting + Structured Pydantic Output)      │
│    ├── Claim Extraction (Bóc tách câu trả lời thành các mệnh đề sự thật độc lập)      │
│    ├── Evidence Matching (Ánh xạ từng Claim với bằng chứng liên quan)                  │
│    ├── Claim Verification (Suy luận Stance: SUPPORTED / REFUTED / NOT_ENOUGH_INFO)     │
│    └── Contradiction Detection (Nhận diện mâu thuẫn nội tại và xung đột đa nguồn)      │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 6. CITATION & OUTPUT GUARDRAIL                                                         │
│    ├── Footnote Citation Grounding (Định vị đoạn trích nguyên văn quote và URL nguồn)  │
│    ├── Evidence Coverage Calculation (Đo lường định lượng tỷ lệ bằng chứng phủ)       │
│    └── Output Faithfulness Guardrail (Kiểm định tính trung thực cuối cùng)             │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Tầng Dữ liệu & RAG (Data & RAG Layer - Powered by LlamaIndex)

LlamaIndex được lựa chọn làm nền tảng chính cho việc quản lý dữ liệu, phân mảnh, nhúng vector và kết nối kho tri thức.

### 3.1. Tiếp nhận & Tiền xử lý tài liệu (Document Ingestion Pipeline)

Hệ thống triển khai pipeline xử lý tài liệu chuẩn hóa 5 bước độc lập, phân tách trách nhiệm cao:

$$\mathbf{Document\ File} \longrightarrow \mathbf{Parse} \longrightarrow \mathbf{Clean} \longrightarrow \mathbf{Extract\ Metadata} \longrightarrow \mathbf{Chunk} \longrightarrow \mathbf{Store}$$

1. **Định dạng tài liệu được hỗ trợ (Supported Parsers)**:
   - **PDF (`PdfParser`)**: Sử dụng thư viện `pypdf`, đọc theo trang (page-by-page), giữ nguyên chỉ số trang thực tế 1-indexed (`page_number`), đồng thời trích xuất các thuộc tính PDF header (Title, Author, Subject, Creator).
   - **Plain Text (`TxtParser`)**: Hỗ trợ cơ chế đa bảng mã (UTF-8, UTF-8-SIG, Latin-1, CP1252, ISO-8859-1) với chế độ fallback an toàn `replace`.
   - **DOCX (`DocxParser`)**: Sử dụng thư viện `python-docx`, trích xuất toàn diện các đoạn văn (paragraphs) cùng dữ liệu bảng biểu (tables), bảo toàn cấu trúc văn bản hành chính/báo cáo và thông tin metadata (Title, Author, Subject).

2. **Làm sạch văn bản tất định (Deterministic Text Cleaning - `TextCleaner`)**:
   - Chuẩn hóa Unicode theo chuẩn **NFKC** nhằm đồng nhất ký tự tiếng Việt có dấu.
   - Loại bỏ các ký tự điều khiển không in được (ASCII control characters `\x00-\x08`, `\x0B-\x0C`, `\x0E-\x1F`, `\x7F-\x9F`), bảo toàn ký tự thụt dòng và xuống dòng chuẩn.
   - Chuyển đổi mọi định dạng ngắt dòng (`\r\n`, `\r`) về định dạng chuẩn `\n`.
   - Thu gọn các khoảng trắng ngang liên tiếp (consecutive spaces/tabs) và giới hạn tối đa 2 ký tự xuống dòng liên tiếp (`\n\n`), bảo đảm tính thẩm mỹ và cô đọng ngữ nghĩa.

3. **Trích xuất Metadata chuẩn hóa (`MetadataExtractor`)**:
   - Tính toán mã băm toàn vẹn **SHA-256** của file gốc nhằm hỗ trợ kiểm tra tính xác thực và chống trùng lặp dữ liệu.
   - Thống kê chính xác: `file_size_bytes`, `page_count`, `word_count`, `char_count`, và nhãn thời gian nạp `ingested_at` (ISO 8601 UTC).
   - Kết hợp metadata từ cấu trúc file (Title/Author) cùng metadata tùy chỉnh từ người dùng (`source_id`, `source_url`, `publisher`).

### 3.2. Chiến lược phân mảnh (Chunking Strategies)

Các bộ phân đoạn hoạt động theo nguyên tắc **bảo toàn số trang gốc (page retention)** và xác định chính xác vị trí ký tự bắt đầu/kết thúc (`char_start`, `char_end`) trên từng chunk:

1. **Fixed-Size Chunking with Overlap (`FixedSizeChunker`)**:
   - Cấu hình tập trung tại `app/core/config.py`: `DEFAULT_CHUNK_SIZE = 500`, `DEFAULT_CHUNK_OVERLAP = 50`.
   - Duyệt tuần tự theo từng trang (`PageContent`), tự động căn lề ngắt đoạn theo ranh giới từ vựng (whitespace) ở 30% cuối của chunk để tránh cắt đôi từ.
   - Gắn `page_number`, `token_count` ước lượng, và vị trí ký tự vào `chunk_metadata`.
2. **Sentence-Window Chunking (`SentenceWindowChunker`)**:
   - Cấu hình tập trung: `DEFAULT_SENTENCE_WINDOW_SIZE = 3`.
   - Sử dụng regex nhận diện câu tinh vi, phân biệt các dấu chấm kết thúc câu với các từ viết tắt phổ biến (như `e.g.`, `Dr.`, `U.S.`).
   - Mỗi chunk tập trung vào một câu đơn (`content`), đồng thời đóng gói ngữ cảnh mở rộng gồm 3 câu trước và 3 câu sau vào trường `chunk_metadata["window"]`. Phục vụ tối ưu cho tác vụ trích xuất Claim và đối chiếu chứng cứ.

### 3.3. Lưu trữ giao dịch (Transactional Persistence - `IngestionService`)
- Điều phối toàn bộ quy trình upload/ingest trong một giao dịch cơ sở dữ liệu (`AsyncSession` transaction) duy nhất.
- Tự động rollback nếu xảy ra bất kỳ lỗi định dạng, lỗi đọc file hay vi phạm ràng buộc dữ liệu.
- Lưu trữ vào bảng `documents` và hàng loạt bản ghi con trong bảng `document_chunks`.
- Trường `DocumentChunk.embedding` được để `None` một cách chủ đích tại pha này, tách biệt hoàn toàn pha Ingestion và pha Vector Encoding tiếp theo.


### 3.4. Mô hình Nhúng & Tầng Trừu tượng hóa Embedding (Embedding Abstraction Layer)

Hệ thống thiết kế tầng trừu tượng hóa độc lập tại `app/services/embedding/`, loại bỏ hoàn toàn việc hard-code embedding provider vào pipeline:

```text
backend/app/services/embedding/
├── base.py                 # BaseEmbeddingProvider (interface, dimension validation)
├── providers/
│   ├── openai_provider.py  # OpenAI text-embedding-3-small (REST API qua httpx async)
│   ├── mock_provider.py    # MockDeterministicEmbeddingProvider (chuẩn hóa L2 norm)
│   └── __init__.py         # Provider registry & get_embedding_provider() factory
├── embedding_service.py    # EmbeddingService (điều phối batch chunk vectorization)
└── __init__.py
```

1. **Nguyên tắc cấu hình tập trung**:
   - `settings.EMBEDDING_DIM`: Mặc định 1536 chiều, đồng bộ tuyệt đối giữa cấu hình Pydantic, cột `DocumentChunk.embedding` (pgvector), và các embedding provider.
   - `settings.EMBEDDING_PROVIDER`: Cấu hình qua `.env` (hỗ trợ `openai`, `mock`, ...). Cơ chế Graceful Fallback tự động chuyển sang mock provider nếu thiếu `OPENAI_API_KEY` trong môi trường dev/testing.
2. **Lưu trữ Vector (`DocumentChunk.embedding`)**:
   - `EmbeddingService.embed_chunks_and_persist`: Chuyển đổi danh sách chunks thành vector theo lô (`EMBEDDING_BATCH_SIZE = 64`) và cập nhật vào PostgreSQL qua giao dịch `AsyncSession`.
   - `EmbeddingService.embed_document_pending_chunks`: Tự động tìm các chunk có `embedding IS NULL` để vector hóa.

### 3.5. Tìm kiếm Ngữ nghĩa pgvector (Dense Semantic Vector Retrieval)

Tầng truy xuất vector ngữ nghĩa được triển khai độc lập tại `app/services/retrieval/vector_search.py` (`PgVectorRetriever`) phối hợp cùng `DocumentRepository.search_vector`:

$$\mathbf{User\ Query} \xrightarrow{\quad\text{embed\_query}\quad} \vec{q} \in \mathbb{R}^{1536} \xrightarrow{\quad\text{pgvector\ (<=>)}\quad} \mathbf{Top\text{-}K\ Chunks} \xrightarrow{\quad\text{join}\quad} \mathbf{Doc\ +\ Source}$$

1. **Toán tử khoảng cách Cosine trên PostgreSQL**:
   - Sử dụng toán tử khoảng cách cosine của pgvector:
     $$\text{distance} = \vec{q} \mathbin{\Longleftrightarrow} \vec{d}$$
   - Điểm tương đồng ngữ nghĩa chuẩn hóa:
     $$\text{similarity\_score} = 1.0 - \text{distance}$$
2. **Truy xuất liên kết toàn vẹn (Full Relation Traversal)**:
   - Câu truy vấn tự động `JOIN` giữa `DocumentChunk` $\rightarrow$ `Document` $\rightarrow$ `Source` để SearchHit trả về đầy đủ: `chunk_id`, `document_id`, `source_id`, `source_title`, `source_url`, `page_number`, `publisher`, `score`, và metadata.
3. **Phân tách tầng rõ rệt**:
   - Router `POST /api/v1/search/vector` và `POST /api/v1/search` chỉ tiếp nhận request và ủy nhiệm cho `RetrievalService`. Tuyệt đối không chứa câu lệnh SQL thô trong router.


### 3.6. Tìm kiếm Từ khóa BM25 (Sparse Lexical Search)

Tầng tìm kiếm từ khóa được thiết kế tại `app/services/retrieval/bm25_search.py` (`BM25Retriever`):
- Sử dụng giải thuật **Lucene BM25** với công thức hàm IDF bảo đảm luôn dương:
  $$\text{IDF}(q) = \ln\left(1 + \frac{N - n(q) + 0.5}{n(q) + 0.5}\right)$$
- **Tối ưu hóa từ khóa đặc biệt**: Bộ tách từ (`tokenize`) giữ nguyên các mã định danh kỹ thuật, điều luật hành chính (ví dụ `15/2020/NĐ-CP`), tên viết tắt dịch bệnh (`COVID-19`, `SARS-CoV-2`), số liệu phần trăm (`4.5%`, `5.2%`) và tên riêng thực thể.
- Bổ sung điểm thưởng cho các cụm từ khớp chính xác nguyên văn (exact phrase boost).

### 3.7. Tìm kiếm Lai (Hybrid Search) & Hợp nhất Thứ hạng RRF (Reciprocal Rank Fusion)

Module `app/services/retrieval/hybrid_search.py` (`HybridRetriever`) thực thi song song hai kênh tìm kiếm và kết hợp thông qua Reciprocal Rank Fusion:

```text
Query
  ↓
Vector Search ──┐
                ├── RRF → Hybrid Candidates
BM25 Search ────┘
                     ↓
              Cross-Encoder
                Reranking
                     ↓
              Top-K Evidence
```

1. **Công thức RRF (Fusion Ranking)**:
   $$\text{RRF\_Score}(d) = \sum_{m \in \{\text{vector}, \text{bm25}\}} \frac{w_m}{k + \text{Rank}_m(d)}$$
   - $k$: Hằng số làm mượt (mặc định $k = 60$).
   - $\text{Rank}_m(d)$: Thứ hạng (1-indexed) của chunk $d$ trong danh sách trả về của retriever $m$.
   - $w_{\text{dense}} = 1.0, w_{\text{sparse}} = 1.0$: Trọng số đóng góp của từng kênh.
2. **Khử trùng lặp (Deduplication) & Tích lũy điểm**:
   - Nếu một đoạn văn xuất hiện ở cả hai bảng xếp hạng (vừa tương đồng ngữ nghĩa, vừa chứa đúng từ khóa kỹ thuật), điểm RRF của chunk đó được cộng dồn, đưa chunk đó lên đầu danh sách ứng viên.
   - Mỗi chunk xuất hiện duy nhất 1 lần trong tập kết quả, đi kèm thông số phân rã `vector_rank` và `bm25_rank` trong metadata.

### 3.8. Tái xếp hạng bằng chứng (Cross-Encoder Reranking - Second-Stage Relevance Ranking)

Tầng tái xếp hạng được thiết kế độc lập tại `app/services/reranking/`:

```text
backend/app/services/reranking/
├── base.py                   # BaseReranker (interface trừu tượng cho phép thay thế model)
├── cross_encoder_reranker.py # CrossEncoderReranker (hỗ trợ mô hình neural + fallback tất định)
└── reranking_service.py      # RerankingService (điều phối chấm điểm & sắp xếp)
```

1. **Nguyên tắc phân tách trách nhiệm**:
   - **RRF = Fusion Ranking**: Tìm kiếm và tổng hợp các ứng viên tiềm năng (Candidate Generation) từ không gian vector và từ khóa.
   - **Cross-Encoder = Second-Stage Relevance Ranking**: Nhận đồng thời cặp `(Query, Candidate Passage)`, thực hiện cross-attention sâu giữa từng từ trong câu truy vấn và văn bản đoạn trích để tính điểm tương quan thực tế (Relevance Score $[0.0, 1.0]$).
   - **Tính tất định cao (Deterministic Pipeline)**: Toàn bộ quá trình từ Search $\rightarrow$ RRF $\rightarrow$ Rerank vận hành tuần tự, minh bạch và có thể tái lập kết quả, **tuyệt đối không phải là AI Agent hay vòng lặp suy diễn tự trị (ReAct loop)**.
2. **Cấu hình tập trung**:
   - Model được cấu hình tập trung qua `settings.RERANKER_MODEL` (mặc định `BAAI/bge-reranker-base`), `settings.RERANKER_PROVIDER`, và `settings.RERANKER_ENABLED` trong `app/core/config.py`, không hard-code trong mã nguồn service.
   - Cơ chế Fallback an toàn tự động kích hoạt bộ tính điểm cross-scoring tất định nếu môi trường chưa tải được trọng số mô hình hoặc chạy offline/testing.

### 3.9. Sàng lọc Bằng chứng & Xây dựng Ngữ cảnh (Evidence Selection & Context Building)

Sau khi hoàn thành tái xếp hạng (Cross-Encoder Reranking), kết quả được đưa qua tầng sàng lọc và đóng gói ngữ cảnh tại `app/services/retrieval/`:

```text
backend/app/services/retrieval/
├── evidence_selector.py # EvidenceSelector: Lọc top-K, khử trùng lặp (exact ID + Jaccard)
├── context_builder.py   # ContextBuilder: Định danh chuẩn hóa E1, E2, mapping, token budgeting
└── schemas.py           # EvidenceItem, StructuredContext, SourceInfo
```

1. **Nguyên tắc nền tảng**:
   - **Retrieval chỉ cung cấp bằng chứng**: Context Builder tuyệt đối không sinh thêm thông tin mới, không suy diễn hay thay đổi nội dung văn bản gốc của các đoạn trích.
   - **Tách biệt với LLM Generation**: Bước này hoàn thiện khâu chuẩn bị dữ liệu có cấu trúc cho LLM Generation nhưng chưa gọi LLM.
2. **Sàng lọc & Khử trùng lặp (`EvidenceSelector`)**:
   - Lọc theo ngưỡng điểm tối thiểu (`min_score`).
   - Loại bỏ trùng lặp tuyệt đối theo định danh chunk (`chunk_id`).
   - Khử trùng lặp nội dung cận kề (near-duplicate text) thông qua chỉ số tương đồng từ vựng Jaccard (ngưỡng mặc định `dedup_threshold = 0.85`), xử lý triệt để hiện tượng câu trùng do sliding window overlap.
   - Bảo toàn trật tự xếp hạng sau rerank của các ứng viên.
3. **Đóng gói Ngữ cảnh có cấu trúc (`ContextBuilder`)**:
   - Gán mã định danh ổn định (`E1`, `E2`, ...) cho từng đoạn bằng chứng.
   - Lưu trữ ánh xạ tường minh $O(1)$ (`evidence_map: Dict[str, EvidenceItem]`) từ `evidence_id` $\rightarrow$ `chunk_id`, `document_id`, `source_id`, `source_title`, `source_url`, `page_number` để phục vụ trực tiếp cho tầng Citation Grounding và Claim Verification phía sau mà không cần truy vấn ngược lại database.
   - Quản lý ngân sách token (`max_tokens`) và cắt tỉa tất định để ngăn tràn context window hoặc giảm hiện tượng "Lost in the Middle".
   - Định dạng khối ngữ cảnh chuẩn mực:
     ```text
     [E1]
     Nguồn: Tổng cục Thống kê (https://gso.gov.vn/...) [Trang 12]
     Độ liên quan: 0.9420
     Nội dung: "Tăng trưởng GDP cả năm 2023 ước đạt 5.05% so với năm trước..."

     [E2]
     Nguồn: Báo Tuổi Trẻ (https://tuoitre.vn/...)
     Độ liên quan: 0.8850
     Nội dung: "Tổng kim ngạch xuất nhập khẩu hàng hóa năm 2023 đạt 683 tỷ USD..."
     ```
   - Xử lý an toàn khi danh sách ứng viên trống (`total_evidence = 0`, thông báo `"No relevant evidence found."`, không gây crash hệ thống).



---

## 4. Tầng Sinh văn bản & Cấu trúc hóa Đầu ra (LLM Generation Layer)

Tầng LLM Generation tại `app/services/generation/` có nhiệm vụ tiếp nhận câu hỏi và khối ngữ cảnh bằng chứng có cấu trúc từ Prompt 11 để tổng hợp câu trả lời khách quan, trung thực:

```text
backend/app/services/generation/
├── base.py                 # BaseLLMProvider (abstract interface)
├── llm_provider.py         # OpenAILLMProvider (httpx async + json_schema) & MockLLMProvider
├── prompt_templates.py     # Tách biệt hoàn toàn prompt templates khỏi service code
├── schemas.py              # GeneratedAnswer, GenerationResponse, GenerationStatus
├── generation_service.py   # GenerationService (điều phối prompt, gọi model, validate ID)
└── __init__.py
```

### 4.1. Vai trò của LLM trong SourceCheck AI
- **Chỉ đảm nhận vai trò Generation (Sinh câu trả lời)**: LLM tuyệt đối **không phải là agent tự trị tìm kiếm thông tin** và **chưa chịu trách nhiệm đưa ra phán quyết thẩm định tính đúng/sai cuối cùng** của nhận định (nhiệm vụ này thuộc về Tầng Thẩm định Chuyên biệt - Verification Domain ở giai đoạn tiếp theo).
- **Phụ thuộc 100% vào Bằng chứng (Strict Grounding)**: Toàn bộ thông tin đầu vào của LLM bắt buộc phải đến từ chuỗi `Hybrid Search -> Reranking -> Evidence Selection -> Context Builder`. LLM không được sử dụng tri thức tiềm ẩn (internal pre-trained knowledge) hay suy diễn ngoài phạm vi các đoạn trích `[E1], [E2]...`.

### 4.2. Bảo đảm cấu trúc đầu ra (Structured Output Enforcement)
Đầu ra của LLM được ràng buộc nghiêm ngặt theo schema tối thiểu:
```json
{
  "answer": "string",
  "status": "SUPPORTED" | "INSUFFICIENT_EVIDENCE",
  "evidence_ids": ["E1", "E2"]
}
```
1. **Trạng thái `INSUFFICIENT_EVIDENCE`**:
   - Nếu ngữ cảnh bằng chứng rỗng, không đủ dữ liệu, hoặc không liên quan đến câu hỏi, mô hình bắt buộc phải gán `status = "INSUFFICIENT_EVIDENCE"`, trả về thông báo không đủ căn cứ và danh sách `evidence_ids = []`.
   - **Tối ưu Fast-path**: Nếu Context Builder trả về `total_evidence == 0`, `GenerationService` lập tức trả về kết quả `INSUFFICIENT_EVIDENCE` mà không cần gọi API của LLM, tiết kiệm chi phí và giảm độ trễ tối đa.
2. **Khử ảo giác mã định danh (Evidence ID Sanitization)**:
   - `GenerationService` đối chiếu danh sách `evidence_ids` do LLM trả về với tập định danh thực tế trong `StructuredContext.evidence_map`. Mọi mã định danh do LLM tự bịa ra sẽ bị loại bỏ.
   - Nếu mô hình chọn nhãn `SUPPORTED` nhưng không đưa ra được bất kỳ mã bằng chứng hợp lệ nào, hệ thống tự động hạ nhãn xuống `INSUFFICIENT_EVIDENCE`.

### 4.3. Lớp trừu tượng hóa Provider & Khả năng chịu lỗi (Resilience & Abstraction)
1. **Cấu hình độc lập**:
   - Provider và Model được lấy từ biến môi trường qua `settings.LLM_PROVIDER` (mặc định `openai`), `settings.LLM_MODEL` (`gpt-4o-mini`), `settings.LLM_TIMEOUT_SECONDS` (30.0s), `settings.LLM_TEMPERATURE` (0.0). Tuyệt đối không hard-code API key trong mã nguồn.
2. **Graceful Fallback & An toàn hệ thống**:
   - Nếu thiếu `OPENAI_API_KEY`, hệ thống tự động chuyển đổi an toàn sang `MockLLMProvider` phục vụ unit testing và môi trường phát triển offline.
   - Xử lý bao quát các lỗi: `httpx.TimeoutException`, lỗi kết nối mạng, HTTP $4xx/5xx$, và lỗi cú pháp JSON. Trả về payload an toàn với nhãn `INSUFFICIENT_EVIDENCE`, đảm bảo backend không bao giờ bị crash.


---

## 5. Tầng Thẩm định Chuyên biệt (Verification Domain - Trọng tâm SourceCheck AI)

Đây là thành phần khác biệt nhất của SourceCheck AI so với các hệ thống RAG hỏi đáp thông thường. Toàn bộ logic được tách riêng trong `services/verification/`.

### 5.1. Bóc tách Nhận định (Claim Extraction - Cầu nối trung gian giữa Generation và Verification)

**Claim Extraction đóng vai trò là bước trung gian then chốt giữa Generation (Prompt 12) và Evidence Verification (Prompt 14+)**:

```text
Question
   ↓
Retrieval & Reranking
   ↓
Evidence Context
   ↓
LLM Generation
   ↓
Synthesized Answer
   ↓
Claim Extraction (Rule-based / LLM-based)
   ↓
[Claim 1, Claim 2, Claim 3, ...] (Kiểm chứng độc lập ở bước tiếp theo)
```

Tầng Claim Extraction được thiết kế tại `backend/app/services/verification/`:
```text
backend/app/services/verification/
├── base.py                 # BaseClaimExtractor (interface trừu tượng cho Rule-based & LLM-based)
├── claim_extractor.py      # RuleBasedClaimExtractor, LLMClaimExtractor, ClaimExtractor (facade)
├── prompt_templates.py     # Prompt tách nhận định độc lập, cấm ý kiến chủ quan
└── schemas.py              # ClaimItem (claim_id, text, order, verifiable), ClaimExtractionResponse
```

1. **Nguyên tắc phân rã nhận định (Atomicity & Fidelity)**:
   - Một câu phức chứa nhiều thông tin thực tế sẽ được tách thành các mệnh đề độc lập (atomic claims).
     - *Ví dụ*: `"SIC đào tạo AI và IoT. Chương trình kéo dài 6 tháng."`
     - $\rightarrow$ `Claim 1`: `"SIC đào tạo AI."`
     - $\rightarrow$ `Claim 2`: `"SIC đào tạo IoT."`
     - $\rightarrow$ `Claim 3`: `"Chương trình kéo dài 6 tháng."`
   - **Bảo toàn ý nghĩa gốc**: Không tự ý thêm bớt chi tiết, không đưa tri thức bên ngoài vào.
   - **Bảo toàn thứ tự xuất hiện (`order: 1, 2, 3...`)**: Giữ nguyên trật tự thời gian và luồng lập luận của câu trả lời.
   - **Loại bỏ ý kiến chủ quan / lời chào hỏi**: Chỉ trích xuất các mệnh đề có khả năng kiểm chứng được (check-worthy, verifiable factual propositions).
2. **Kiến trúc đa chiến lược (Multi-strategy Abstraction & Fallback)**:
   - `LLMClaimExtractor`: Sử dụng mô hình ngôn ngữ lớn kết hợp Structured Output Schema để nhận diện ngữ nghĩa phức tạp và giải quyết đại từ nhân xưng.
   - `RuleBasedClaimExtractor`: Giải thuật tách câu và liên từ (`và`, `đồng thời`, `and`,...) tất định, bảo vệ hệ thống không crash khi chạy offline hoặc gặp sự cố mạng/timeout.
   - Mỗi claim trích xuất ra sẽ được đưa vào làm đầu vào độc lập cho các bộ kiểm chứng (`ClaimVerifier`, `EvidenceMatcher`) ở giai đoạn tiếp theo.


### 5.2. Ánh xạ Bằng chứng (Evidence Matching - Sàng lọc Ứng viên Bằng chứng cho từng Claim)

> [!IMPORTANT]
> **Evidence Matching không phải là Verification.**
> 
> Tầng này CHỈ trả lời câu hỏi:
> *"Bằng chứng nào có liên quan đến claim này và có khả năng chứa thông tin kiểm chứng?"*
> 
> Còn câu hỏi:
> *"Bằng chứng có thực sự chứng minh (SUPPORTED) hoặc bác bỏ (REFUTED) claim hay không?"*
> sẽ được giải quyết chuyên biệt tại **Prompt 15 — Claim Verification & Contradiction Detection**.

```text
Answer
   ↓
Claim Extraction
   ↓
Claim 1 ──→ [Evidence Matching] ──→ Candidates [E1, E2] (Relevance Score)
Claim 2 ──→ [Evidence Matching] ──→ Candidates [E1, E3]
Claim 3 ──→ [Evidence Matching] ──→ Candidates [E4]
```

1. **Nguyên tắc hoạt động của `EvidenceMatcher`**:
   - Nhận danh sách `ClaimItem` cùng tập bằng chứng đã chọn lọc (`StructuredContext` / `EvidenceItem`s).
   - Sử dụng Cross-Encoder Reranking kết hợp tính tương đồng ngữ nghĩa/từ vựng giữa `claim.text` và `evidence.content` để tính toán `relevance_score` chính xác.
   - Sắp xếp các ứng viên giảm dần theo điểm tương quan, lọc bỏ các bằng chứng dưới ngưỡng (`min_score`).
   - Một claim có thể liên kết với nhiều evidence candidate, và một evidence có thể được dùng chung cho nhiều claim độc lập.
2. **Cấu trúc Dữ liệu & Tính Truy vết (Provenance Guarantee)**:
   - Output có cấu trúc chặt chẽ (`MatchedEvidenceCandidate`):
     ```json
     {
       "claim_id": "claim_1",
       "evidence_id": "E1",
       "chunk_id": "uuid-...",
       "document_id": "uuid-...",
       "source_id": "uuid-...",
       "source_title": "...",
       "source_url": "...",
       "content": "...",
       "relevance_score": 0.9125,
       "relation": "UNCLEAR",
       "rank": 1
     }
     ```
   - Bảo toàn chuỗi liên kết: `Question` $\rightarrow$ `Answer` $\rightarrow$ `Claim` $\rightarrow$ `Evidence` (`chunk_id`, `document_id`, `source_id`, `source_url`), làm cơ sở vững chắc cho bước phán quyết Stance (Prompt 15) và hiển thị Citation (Prompt 16).


### 5.3. Thẩm định & Xác định Lập trường (Claim Verification - Powered by ClaimVerifier)

```text
Claim
  ↓
Matched Evidence Candidates
  ↓
Verification
  ├── SUPPORTED           (Bằng chứng trực tiếp khẳng định)
  ├── PARTIALLY_SUPPORTED (Khẳng định một phần, chi tiết/phạm vi chưa đầy đủ)
  ├── REFUTED             (Bằng chứng trực tiếp bác bỏ/mâu thuẫn)
  └── NOT_ENOUGH_INFO     (Không đủ dữ liệu kiểm chứng)
        ↓
Contradiction Detection
        ↓
Verification Report
```

> [!IMPORTANT]
> **Điểm khác biệt cốt lõi giữa RAG thông thường và SourceCheck AI**:
> - **Retrieval**: Chỉ tìm kiếm các đoạn văn bản có khả năng liên quan (Candidate Generation & Reranking).
> - **Verification**: Thẩm định thực nghiệm xem các đoạn bằng chứng đó **có thực sự hỗ trợ hay bác bỏ** nhận định hay không.

1. **Nguyên tắc thẩm định độc lập**:
   - `ClaimVerifier` nhận từng cặp `(ClaimItem, List[MatchedEvidenceCandidate])`.
   - Mô hình (LLM hoặc Engine tất định) **chỉ được phép sử dụng thông tin trong bằng chứng đã cung cấp**. Tuyệt đối cấm sử dụng tri thức tiềm ẩn để suy đoán.
   - Đầu ra cấu trúc hóa nghiêm ngặt (`ClaimVerificationResult`):
     - `claim_id`: Định danh nhận định.
     - `verdict`: Nhãn phán quyết (`SUPPORTED`, `PARTIALLY_SUPPORTED`, `REFUTED`, `NOT_ENOUGH_INFO`).
     - `confidence`: Điểm số chắc chắn của phán quyết thẩm định ($\in [0.0, 1.0]$), **tuyệt đối không gọi đây là Answer Accuracy**.
     - `supporting_evidence_ids`: Danh sách ID bằng chứng ủng hộ (ví dụ `["E1"]`).
     - `refuting_evidence_ids`: Danh sách ID bằng chứng phản bác (ví dụ `["E2"]`).
     - `explanation`: Lời giải thích ngắn gọn, trích dẫn trực tiếp mã bằng chứng.
2. **Khả năng chịu lỗi & Graceful Fallback**:
   - Nếu danh sách bằng chứng rỗng $\rightarrow$ Trả về ngay `NOT_ENOUGH_INFO` với `confidence = 0.0`.
   - Nếu LLM gặp sự cố timeout hoặc lỗi provider $\rightarrow$ Tự động chuyển tiếp sang heuristic engine, bảo đảm backend luôn vận hành liên tục.

### 5.4. Phát hiện Mâu thuẫn (Contradiction Detection - Powered by ContradictionDetector)

Module `ContradictionDetector` rà soát 2 cấp độ mâu thuẫn dữ liệu:
1. **Mâu thuẫn Nhận định - Bằng chứng (Claim Refutation Conflict)**:
   - Phát hiện khi bằng chứng bác bỏ trực tiếp nhận định của người dùng/LLM (`verdict == REFUTED`).
2. **Xung đột Đa nguồn Bằng chứng (Cross-Source Evidence Conflict)**:
   - Phát hiện khi hai bằng chứng từ hai nguồn khác nhau cùng tham chiếu một fact nhưng đưa ra số liệu/năm xung đột:
     - *Ví dụ*: Nhận định *"Sự kiện X diễn ra vào năm 2026."*
     - Nguồn A (`[E1]`): *"Sự kiện X diễn ra vào năm 2026."*
     - Nguồn B (`[E2]`): *"Sự kiện X diễn ra vào năm 2025."*
     - $\rightarrow$ `ContradictionDetector` lập tức gắn cờ `CROSS_SOURCE_CONFLICT` giữa `[E1]` và `[E2]`.
   - **Nguyên tắc công bằng**: Hệ thống ghi nhận xung đột đa nguồn, không tự ý chọn một nguồn là đúng chỉ vì nguồn đó xuất hiện trước.

### 5.5. Độ bao phủ Bằng chứng (Evidence Coverage - Powered by EvidenceCoverageCalculator)

Đo lường định lượng mức độ đầy đủ của bằng chứng trên toàn bộ câu trả lời:

$$\text{Evidence Coverage} = \frac{\text{Số lượng claim được kiểm chứng (SUPPORTED + PARTIALLY\_SUPPORTED + REFUTED)}}{\text{Tổng số claim có thể kiểm chứng}}$$

> [!NOTE]
> Chỉ số này đo lường **mức độ bao phủ và đầy đủ của kho dữ liệu kiểm chứng**, **tuyệt đối không gọi đây là "độ chính xác của câu trả lời" (Answer Accuracy)**.


---

## 6. Hàng rào Kiểm soát & Tổng hợp Phản hồi (Guardrails & Final Answer Assembly)

> [!IMPORTANT]
> **Nguyên tắc thiết kế tối thượng của Guardrail**:
> **Guardrail là lớp kiểm soát cuối cùng, không phải nguồn tri thức.**
> 
> SourceCheck AI vận hành như một **deterministic pipeline có guardrail nghiêm ngặt**, tuyệt đối **không phải là Autonomous Agent/ReAct** hay Blackbox LLM tự trị. Mô hình ngôn ngữ chỉ đóng vai trò hỗ trợ phân tích và tổng hợp dưới sự giám sát và chế tài toàn diện của các thuật toán tất định (deterministic algorithms).

### 6.1. Kiến trúc Pipeline Chính Thức (Official End-to-End Pipeline)

```text
Retrieve
   ↓
Generate
   ↓
Verify
   ↓
Cite
   ↓
Guardrail
   ↓
Final Answer
```

```text
backend/app/services/guardrail/
├── input_guardrail.py      # Kiểm soát đầu vào, chống Prompt Injection, cô lập dữ liệu tài liệu
├── output_guardrail.py     # Thẩm tra toàn vẹn đầu ra (claim, citation, evidence grounding)
├── guardrail_service.py    # Điều phối tổng thể các hàng rào an toàn
├── schemas.py              # GuardrailStatus, InputValidationResult, OutputValidationResult
└── __init__.py

backend/app/services/generation/
└── answer_assembler.py     # Đóng gói và giải quyết trạng thái phản hồi cuối cùng (FinalAnswerResponse)
```

---

### 6.2. Hàng rào Đầu vào (Input Guardrail - Powered by `InputGuardrail`)

Thực hiện kiểm tra an ninh trước khi kích hoạt bất kỳ tác vụ truy xuất (retrieval) hoặc gọi mô hình (LLM):
1. **Kiểm tra tính hợp lệ của câu hỏi**:
   - Chặn lập tức các câu hỏi rỗng, chỉ chứa khoảng trắng (`empty/whitespace query`).
   - Giới hạn độ dài tối đa (`max_question_length = 2000` ký tự), ngăn chặn tấn công từ chối dịch vụ (DoS) hoặc tràn context buffer.
2. **Phát hiện & Chặn đứng Prompt Injection / Jailbreak**:
   - Quét qua tập luật regex biểu thức chính quy nhận diện các mẫu câu tấn công:
     - *"Ignore all previous instructions"*, *"Disregard rules"*
     - *"Reveal/print system prompt"*, *"Developer mode"*
     - *"DAN mode"*, *"Act as an unrestricted AI"*
   - Khi phát hiện mã độc, trả về trạng thái `BLOCKED` ngay tại cửa ngõ đầu vào, không tiêu tốn tài nguyên hệ thống.
3. **Cô lập Bằng chứng là Dữ liệu Thụ động Không Tin cậy (Untrusted Passive Data)**:
   - Toàn bộ nội dung tài liệu (`document_chunk` / `evidence_content`) được coi là **untrusted data**.
   - Áp dụng kỹ thuật trung hòa thẻ chỉ thị (`[untrusted_system_tag]`) và đóng gói trong khối phân định `<evidence_data id="...">...</evidence_data>`, bảo đảm các chỉ thị tiềm ẩn trong văn bản tài liệu **không bao giờ được thực thi như system instructions**.

---

### 6.3. Gắn nguồn Trích dẫn Trực tiếp (Citation Grounding - Powered by `CitationService`)

Tầng Citation Service được triển khai tại `backend/app/services/citation/` nhằm liên kết các nhận định đã được kiểm chứng với bằng chứng thực nghiệm và tài liệu gốc trong cơ sở tri thức:

```text
Claim Verification
       ↓
Verified Evidence
       ↓
Citation Mapping
       ↓
[1] [2] [3]
```

```text
backend/app/services/citation/
├── base.py                 # BaseCitationService (abstract interface)
├── citation_grounder.py    # extract_verbatim_quote (trích dẫn nguyên văn) & find_quote_anchor
├── citation_formatter.py   # CitationFormatter (định dạng entry, danh mục footnotes, inline tags)
├── citation_service.py     # CitationService (điều phối trích dẫn, deduplicate footnote_index)
├── schemas.py              # CitationStance, CitationItem, FormattedCitationEntry, CitationSummary
└── __init__.py
```

> [!IMPORTANT]
> **Nguyên tắc cốt lõi: Tuyệt đối không để LLM tự bịa citation**:
> - **Nguồn gốc dữ liệu**: Toàn bộ Citation được sinh trực tiếp từ dữ liệu `EvidenceItem` và `DocumentChunk` đã được lưu trữ trong hệ thống (Knowledge Base), **tuyệt đối không phải do LLM tự suy diễn hoặc tự sinh link**.
> - **Trích dẫn nguyên văn (`quote`)**: Được trích xuất bằng thuật toán đối chiếu chuỗi con chính xác (`extract_verbatim_quote`) từ nội dung bằng chứng thực tế (`evidence_content`), hoàn toàn không qua sinh văn bản của LLM để triệt tiêu nguy cơ ảo giác trích dẫn.

1. **Chuỗi truy vết nguồn gốc (Full Provenance Traceability)**:
   $$\mathbf{Answer} \longrightarrow \mathbf{Claim} \longrightarrow \mathbf{Citation} \longrightarrow \mathbf{Evidence} \longrightarrow \mathbf{Document} \longrightarrow \mathbf{Source}$$
   - Mỗi `CitationItem` bao gồm đầy đủ các trường:
     - `citation_id`: UUID duy nhất của trích dẫn.
     - `claim_id`: ID nhận định được trích dẫn.
     - `evidence_id` / `chunk_id`: Định danh đoạn bằng chứng hoặc chunk cơ sở.
     - `document_id`: Định danh tài liệu chứa đoạn trích.
     - `source_name` / `source_url`: Tên nguồn xuất bản và đường link xác thực (hoặc dự phòng an toàn nếu metadata bị thiếu).
     - `quote`: Đoạn văn bản nguyên văn được trích từ tài liệu.
     - `stance`: Lập trường của bằng chứng đối với nhận định (`SUPPORTS`, `REFUTES`, hoặc `CONTEXT`).
     - `footnote_index`: Số thứ tự chú thích chân trang tuần tự (`1`, `2`, `3`, ...).

2. **Khử trùng lặp chú thích chân trang (Footnote Deduplication)**:
   - Khi cùng một đoạn bằng chứng (`chunk_id` hoặc `evidence_id`) được sử dụng để chứng minh cho nhiều nhận định khác nhau, hệ thống tái sử dụng cùng một `footnote_index` (ví dụ cùng trích dẫn `[1]`).
   - Danh mục Footnotes ở cuối tài liệu chỉ hiển thị duy nhất một mục chú thích cho mỗi đoạn trích, giữ bài viết gọn gàng, chuẩn mực học thuật.

3. **Định dạng hiển thị chuẩn khoa học (Citation Formatter)**:
   - Thẻ trích dẫn trong dòng (inline tags): `[1]`, `[2]`, `[1][2]`.
   - Danh mục tài liệu tham khảo (Footnotes section):
     - Định dạng: `[index] Source Name — Document Title (URL)`
     - Đoạn trích nguyên văn: `> "quote..."`
     - Kèm theo nhãn lập trường (`[SUPPORTS]`, `[REFUTES]`) và chỉ số liên quan (`Relevance: 0.95`).
   - Xử lý linh hoạt khi thiếu URL hoặc metadata: Tự động dự phòng về `"Internal Knowledge Base"` hoặc `"Document <ID>"` mà không làm gián đoạn hệ thống.

---

### 6.4. Hàng rào Đầu ra (Output Guardrail - Powered by `OutputGuardrail`)

Trước khi dữ liệu rời khỏi backend để đến tay người dùng, `OutputGuardrail` thực hiện kiểm định nghiêm ngặt tính toàn vẹn và mức độ đáng tin cậy:
1. **Tính hoàn chỉnh của thẩm định nhận định (Claim Verification Completeness)**:
   - Mọi claim trích xuất từ câu trả lời **bắt buộc phải có phán quyết thẩm định tương ứng** (`ClaimVerificationResult`). Tuyệt đối không cho phép tồn tại claim "bị bỏ quên" hoặc chưa qua kiểm chứng.
2. **Tính xác thực của trích dẫn (Citation-to-Evidence Integrity)**:
   - Mọi `citation.evidence_id` hoặc `chunk_id` phải tồn tại trong tập bằng chứng thực tế được truy xuất (`valid_evidence_ids`).
   - Cấm triệt để việc sinh ra các ID bằng chứng hoặc URL ảo tưởng không có trong cơ sở tri thức.
3. **Tính nhất quán giữa trạng thái tổng thể và phán quyết thành phần**:
   - Nếu câu trả lời gắn nhãn `SUPPORTED` nhưng danh mục thẩm định không có bất kỳ claim nào đạt `SUPPORTED` $\rightarrow$ Đánh dấu vi phạm nghiêm trọng.
4. **Chế tài xử lý vi phạm**:
   - Khi phát hiện vi phạm tính toàn vẹn dữ liệu, phương thức `apply_final_guardrail` tự động chuyển đổi phản hồi sang trạng thái `BLOCKED` kèm danh sách vi phạm chi tiết trong `metadata`, ngăn chặn thông tin sai lệch đến người dùng.

---

### 6.5. Đóng gói & Định dạng Phản hồi Thống nhất (`AnswerAssembler`)

Tổng hợp kết quả từ mọi tầng thành đối tượng `FinalAnswerResponse` chuẩn hóa:
```json
{
  "question": "GDP Việt Nam năm 2023 tăng trưởng bao nhiêu?",
  "answer": "Tăng trưởng GDP Việt Nam năm 2023 đạt 5.05%.",
  "status": "SUPPORTED",
  "claims": [
    {
      "claim_id": "claim_1",
      "text": "Tăng trưởng GDP Việt Nam năm 2023 đạt 5.05%.",
      "order": 1,
      "verifiable": true
    }
  ],
  "evidence": [
    {
      "evidence_id": "E1",
      "chunk_id": "chunk-uuid-1",
      "content": "Tăng trưởng GDP năm 2023 ước đạt 5.05%...",
      "score": 0.9450
    }
  ],
  "citations": [
    {
      "citation_id": "cit-uuid-1",
      "claim_id": "claim_1",
      "evidence_id": "E1",
      "source_name": "Tổng cục Thống kê",
      "source_url": "https://gso.gov.vn/...",
      "quote": "Tăng trưởng GDP năm 2023 ước đạt 5.05%...",
      "stance": "SUPPORTS",
      "footnote_index": 1
    }
  ],
  "evidence_coverage": 1.0,
  "verification_summary": {
    "SUPPORTED": 1,
    "PARTIALLY_SUPPORTED": 0,
    "REFUTED": 0,
    "NOT_ENOUGH_INFO": 0
  },
  "metadata": {}
}
```

#### Xử lý Trường hợp Không đủ Bằng chứng (`INSUFFICIENT_EVIDENCE` Policy)
- Khi truy xuất không tìm thấy tài liệu phù hợp hoặc kết quả thẩm định là `NOT_ENOUGH_INFO`:
  - **Tuyệt đối cấm LLM suy đoán hoặc bịa câu trả lời**.
  - Hệ thống trả về trạng thái `INSUFFICIENT_EVIDENCE` với thông báo rõ ràng:
    > *"Thông tin trong các tài liệu kiểm chứng hiện tại không đủ để trả lời câu hỏi này một cách chắc chắn."*
  - `claims: []`, `evidence: []`, `citations: []`, `evidence_coverage: 0.0`.


---

## 7. Pipeline Đầu Cuối (Core RAG + Verification End-to-End Pipeline)

Được triển khai tại `backend/app/services/qa/` (`pipeline.py`, `qa_service.py`, `intent_router.py`, `query_rewriter.py`), đây là **hạt nhân xử lý hoàn chỉnh của Core Backend**, tích hợp toàn bộ các thành phần AI modular thành một chuỗi xử lý thống nhất:

```text
                  User Question
                        │
                        ▼
               [ 1. Intent Router ] ──► (GREETING/IDENTITY: Phản hồi tức thì)
                        │ (KNOWLEDGE_QUERY)
                        ▼
              [ 2. Input Guardrail ]
                        │
                        ▼
          [ 3. Contextual Query Rewriter ]
                        │
                        ▼
             ┌─ Dense Vector Search ─┐
             │                       ├─► [ 5. Reciprocal Rank Fusion (RRF) ]
             └─ Sparse BM25 Search ──┘
                        │
                        ▼
           [ 6. Cross-Encoder Reranking ]
                        │
                        ▼
         [ 7. Evidence Sufficiency Check ] ──► (Thiếu: Safe Insufficient Response)
                        │ (Đủ bằng chứng)
                        ▼
        [ 8. Context Builder & Generation ]
                        │
                        ▼
             [ 9. Claim Extraction ]
                        │
                        ▼
             [ 10. Evidence Matching ]
                        │
                        ▼
            [ 11. Claim Verification ]
                        │
                        ▼
          [ 12. Contradiction & Coverage ]
                        │
                        ▼
         [ 13. Citation & Output Guardrail ]
                        │
                        ▼
                   Final Answer
```

> [!IMPORTANT]
> **Khẳng định Bản chất Kiến trúc**:
> **SourceCheck AI là một deterministic pipeline có các thành phần AI được kiểm soát, tuyệt đối không phải Autonomous Agent/ReAct.**
> Mọi bước từ truy xuất, thẩm định, phát hiện mâu thuẫn đến tạo trích dẫn đều vận hành theo quy trình tuyến tính, kiểm soát chặt chẽ bằng thuật toán tất định, đảm bảo tính tái lập (reproducibility), loại trừ rủi ro vòng lặp vô tận (infinite loops) và triệt tiêu khả năng phát tán thông tin giả mạo.

### 7.1. Cấu trúc Điều phối & Dịch vụ (`QAPipeline` & `QAService`)
```text
backend/app/services/qa/
├── intent_router.py   # IntentRouter: Phân loại deterministic Greeting / Identity / Knowledge Query
├── query_rewriter.py  # QueryRewriter: Viết lại query đa lượt giải quyết tham chiếu ngữ cảnh
├── pipeline.py        # QAPipeline: Điều phối 13 bước từ Question đến Final Answer
├── qa_service.py      # QAService: Facade xử lý exception an toàn và lưu trữ CSDL quan hệ
└── __init__.py
```

1. **Chuỗi 13 Bước Thực thi Tuyến tính**:
   1. `Intent Router`: Nhận diện các intent xã giao hoặc định danh cơ bản để phản hồi trực tiếp, tối ưu hóa độ trễ và tránh truy xuất RAG không cần thiết.
   2. `Input Guardrail`: Kiểm tra độ an toàn, chống prompt injection, cô lập tài liệu (Untrusted Data).
   3. `Contextual Query Rewriter`: Tự động nhận diện đại từ/thay thế ngữ cảnh trong hội thoại đa lượt và viết lại thành truy vấn độc lập.
   4. `Hybrid Search`: Kết hợp đồng thời Vector Search (pgvector) + BM25 Search.
   5. `Reciprocal Rank Fusion (RRF)`: Hợp nhất danh sách thứ hạng với tham số tiêu chuẩn $k=60$.
   6. `Cross-Encoder Reranking`: Sắp xếp lại danh sách đoạn trích theo mức độ liên quan ngữ nghĩa chuyên sâu (`bge-reranker-base`).
   7. `Evidence Sufficiency & Selection`: Đánh giá ngưỡng bao phủ bằng chứng; ngắt an toàn và trả về phản hồi chuẩn nếu không đủ cơ sở dữ liệu.
   8. `Context Builder & LLM Generation`: Đóng gói `StructuredContext` kèm mã định danh `[E1], [E2]` và sinh câu trả lời bám sát bằng chứng.
   9. `Claim Extraction`: Tách câu trả lời thành danh sách các mệnh đề độc lập có thể kiểm chứng.
   10. `Evidence Matching`: Ánh xạ các đoạn bằng chứng tiềm năng cho từng nhận định.
   11. `Claim Verification`: Đánh giá lập trường thực nghiệm (`SUPPORTED`, `PARTIALLY_SUPPORTED`, `REFUTED`, `NOT_ENOUGH_INFO`).
   12. `Contradiction Detection & Coverage`: Quét phát hiện mâu thuẫn nhận định, xung đột dữ liệu chéo và đo lường tỷ lệ bao phủ bằng chứng.
   13. `Citation Service & Output Guardrail`: Trích xuất chuỗi trích dẫn nguyên văn, đánh số chú thích chân trang tuần tự (`[1]`, `[2]`), và thẩm tra độ trung thực (Faithfulness) cuối cùng.

2. **Lưu vết Quan hệ (Relational Provenance Traceability)**:
   $$\mathbf{Question} \longrightarrow \mathbf{Answer} \longrightarrow \mathbf{Claim} \longrightarrow \mathbf{VerificationResult} \longrightarrow \mathbf{Evidence} \longrightarrow \mathbf{Citation} \longrightarrow \mathbf{Source}$$
   - Tự động lưu trữ vào PostgreSQL/SQLite khi có session hoạt động, bảo đảm không tạo bản ghi trùng lặp và liên kết chặt chẽ mọi mắt xích kiểm chứng.

---

## 8. Phân định Hệ thống Hiện tại & Định hướng Mở rộng Tương lai

| Tiêu chí | Hệ thống Hiện tại (Current Production Implementation) | Đề xuất Mở rộng Tương lai (Future Research Extension) |
| :--- | :--- | :--- |
| **Mô hình Điều phối** | 13-stage Deterministic Pipeline (Kiểm soát chặt chẽ, 100% tái lập) | Dynamic Multi-Agent Routing / Adaptive Graph RAG |
| **Nguồn Dữ liệu** | Internal Verified Knowledge Base (PDF, DOCX, TXT via pgvector + BM25) | Web Search APIs (Tavily/Google) + Social Media Feeds Real-time Ingestion |
| **Intent Classifier** | Deterministic Regex & Pattern Matcher (Zero latency, 100% precision) | Fine-tuned SLM Classifier / Zero-shot Intent Router |
| **Reranking** | Local Cross-Encoder (`bge-reranker-base`) | Cohere Rerank v3 API / ColBERTv2 late-interaction |
| **Lưu trữ Hội thoại** | Relational User-Conversation-Message Schema với Cascade Delete | Hierarchical Memory Tree / Long-term Vector Memory |

---

## 9. Tích hợp Đánh giá Định lượng (Evaluation Alignment)

Pipeline AI được kết nối trực tiếp với bộ benchmark khoa học trong thư mục `evaluation/`:
- **Bộ dữ liệu chuẩn hóa**: 28 ca thực nghiệm bao phủ đầy đủ các trường hợp: có bằng chứng đầy đủ, thiếu bằng chứng (`INSUFFICIENT_EVIDENCE`), có mâu thuẫn chéo giữa các nguồn tài liệu (`CONTRADICTION`), và các query xã giao (`GREETING/IDENTITY`).
- **Kết quả thực tế**: Đạt độ chính xác 100% (28/28 cases passed), Hit@1 = 1.0, Recall@1 = 1.0, Verification Accuracy = 1.0, và Intent Routing Accuracy = 1.0. Chi tiết xem tại [Evaluation Report](docs/evaluation.md).


---

## Current implementation status

Các thành phần user-facing hiện đã được nối với pipeline verification thực tế:

- Luồng hỏi đáp đi qua retrieval, generation, claim extraction, evidence matching, claim-level verification, coverage và citation trước khi hiển thị kết quả.
- Verdict tổng thể được lưu riêng với verdict của từng claim; khi đọc lại qua `GET /api/v1/verify/{request_id}`, các claim vẫn giữ đúng trạng thái `SUPPORTED`, `PARTIALLY_SUPPORTED`, `REFUTED` hoặc `NOT_ENOUGH_INFO`.
- Evidence và citation được lấy từ dữ liệu backend; quote, source URL, document và page chỉ được hiển thị khi có dữ liệu thật.
- Evidence Coverage lấy từ kết quả verification, không được frontend tự tính lại.
- Verification History đọc các báo cáo đã persistence qua `GET /api/v1/verify/history` và cho phép mở lại báo cáo theo `request_id`.
- Các thay đổi Profile/Settings, Sidebar và presentation không thay đổi ClaimVerifier, evidence matching, coverage calculation, retrieval strategy hoặc LLM provider.

### Local database compatibility

Database SQLite fallback được khởi tạo trước khi các trường profile được bổ sung có thể thiếu `avatar_url` hoặc `phone_number`. Vì `create_all` không thay đổi bảng đã tồn tại, startup hiện kiểm tra và thêm các cột nullable còn thiếu trước khi thực hiện truy vấn user. Đây là lớp tương thích cho môi trường local; môi trường quản lý bằng Alembic sử dụng migration `004_add_user_profile_fields`.

### Validation reference

- Authentication tests: `14 passed`.
- Legacy SQLite profile-schema test: `2 passed` trong focused database run.
- Local demo login sau compatibility check: HTTP `200`.

Chi tiết user flow và giới hạn sản phẩm được ghi tại [Current Completion Status](current-status.md).
---

## 10. Research ChatInput và Document-Scoped Request Contract (Checkpoint F1)

Phần nhập liệu nghiên cứu hiện tại là lớp frontend điều phối request, không phải một retrieval engine riêng. Component chính là `frontend/src/components/chat/ResearchInputComposer.tsx`, được dùng bởi `ResearchChatPage` cho cả empty state và conversation mode.

### 10.1. Request flow

```text
ChatInput
  ├─ attachment upload → document_id
  ├─ task_type: qa | summary
  ├─ document_ids: selected ready documents
  ├─ search_enabled
  └─ question
       ↓
ResearchChatPage
       ↓
POST /api/v1/questions/ask
       ↓
QuestionRequest → QAService → QAPipeline
```

`task_type=qa` là mặc định để bảo toàn backward compatibility. `task_type=summary` yêu cầu đúng một `document_id`; Summary không đi qua top-k semantic/BM25 retrieval mà dùng document-wide summary flow đã triển khai ở E1-E3.

### 10.2. Attachment scope

- Chỉ nhận PDF, DOCX và TXT ở ChatInput.
- Upload dùng API tài liệu hiện có và lấy `document_id` từ response.
- Chỉ attachment ở trạng thái `ready` mới được đưa vào `document_ids`.
- Q&A có thể gửi nhiều document; Summary chỉ được gửi một document.
- Backend validate scope trước khi pipeline chạy.
- Retrieval, context builder, evidence matcher, claim verifier, citation service và output guardrail tiếp tục dùng cùng document scope.

### 10.3. Search control

Search control không mở rộng ra web search hoặc URL ingestion. Nó điều khiển hành vi trong retrieval pipeline hiện có:

- Search bật: giữ `search_mode=hybrid`, dùng Vector Search + BM25 + RRF + reranking.
- Search tắt: vẫn giữ grounded retrieval với câu hỏi gốc để không phá Q&A backward compatibility, nhưng bỏ contextual query rewrite.
- `search_enabled` mặc định là `true` ở backend schema.
- Khi có `document_ids`, cả hai nhánh Vector/BM25 vẫn bị filter theo scope trước khi context và verification.

Vì vậy Search không bypass các bước generation, claim extraction, verification, citation hoặc output guardrail.

### 10.4. Voice và interaction guardrails

- Web Speech API ưu tiên `vi-VN`; transcript chỉ cập nhật textarea.
- Không tự động submit transcript.
- Enter submit; Shift+Enter newline.
- Khi request chạy, Send chuyển thành Stop; attachment và voice controls bị disable khi không phù hợp.
- Browser không hỗ trợ Speech Recognition thì hiển thị fallback rõ ràng.

### 10.5. Layout states

- Empty State căn giữa theo vùng `.app-content`, dùng chiều cao thực tế đã trừ padding của content để tránh scrollbar dư.
- Khi có message, workspace chuyển về conversation flow; sticky composer căn theo answer column sau avatar AI.
- Toolbar là flex row độc lập, icon không wrap/overlap; mic luôn nằm cạnh Send.
- Light/Dark mode và responsive desktop/mobile được giữ nguyên.

### 10.6. Validation reference

- Focused frontend ChatInput/scope/Summary tests: pass.
- Full frontend regression: 17 test files, 198 tests pass.
- Backend retrieval/document-scope/verification/summary regression: 28 tests pass.
- Production build: pass.
- `git diff --check`: pass.

Phạm vi F1 không bao gồm web search, OCR, image analysis, URL ingestion, TTS, ownership/workspace hoặc thay đổi kiến trúc verification/citation.