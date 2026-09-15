# Features Specification: SourceCheck AI

Tài liệu đặc tả toàn bộ danh mục tính năng của hệ thống SourceCheck AI. Mỗi tính năng được mô tả chuẩn mực bao gồm: Tên chức năng, Mục đích, Dữ liệu đầu vào (Input), Kết quả đầu ra (Output), Tác nhân (Actor), Luồng hoạt động chính (Main Flow) và Ghi chú.

---

## 1. Nhóm chức năng Người dùng & Xác thực (User & Authentication)

### 1.1. Đăng ký & Đăng nhập người dùng (User Auth & Google OAuth - Full-Stack Completed)
- **Mục đích**: Cung cấp cơ chế định danh người dùng an toàn bằng Email + Mật khẩu và đăng nhập xã hội qua **Google OAuth 2.0 (OpenID Connect)**, cấp phát JWT access token và bảo vệ các API nghiệp vụ.
- **Input**:
  - Email + Password (đăng nhập truyền thống).
  - Google OAuth Code + State (đăng nhập Google, không yêu cầu nhập mật khẩu Gmail vào SourceCheck AI).
- **Output**: Access Token (SourceCheck JWT Bearer thời hạn 24 giờ), Thông tin hồ sơ người dùng (`UserResponse` bảo mật, không lộ mật khẩu hay token thứ ba).
- **Actor**: Người dùng cuối, Nhà nghiên cứu, Quản trị viên.
- **API Endpoints**:
  - `POST /api/v1/auth/register`: Đăng ký tài khoản (băm mật khẩu an toàn bằng `bcrypt`, chống trùng lặp email).
  - `POST /api/v1/auth/login`: Xác thực thông tin đăng nhập và sinh JWT token (`sub`, `email`, `role`, `exp`).
  - `GET /api/v1/auth/google/login`: Khởi tạo luồng xác thực Google OAuth 2.0 kèm CSRF state token.
  - `GET /api/v1/auth/google/callback`: Đổi authorization code lấy identity từ Google, tự động tìm/tạo/liên kết tài khoản an toàn và cấp phát SourceCheck JWT.
  - `GET /api/v1/auth/me`: Lấy thông tin tài khoản hiện tại qua header `Authorization: Bearer <token>`.
  - `POST /api/v1/questions/ask`: Được bảo vệ nghiêm ngặt bằng token xác thực (chặn 401 Unauthorized nếu thiếu hoặc sai token).
- **Frontend UI & Components**:
  - `LoginPage.tsx` & `RegisterPage.tsx`: Thiết kế phong cách Glassmorphism mờ cao cấp (`backdrop-filter: blur(24px)`), ô nhập bán trong suốt, nút con mắt SVG (`EyeIcon.tsx`) bật/tắt mật khẩu.
  - `GoogleButton.tsx`: Nút đăng nhập Google với logo SVG 4 màu và spinner trạng thái.
  - `OAuthCallbackPage.tsx`: Nhận redirect từ Google (`/auth/callback`), tự động đổi mã lấy token và chuyển hướng tới Authenticated Workspace (`/`).
  - `AppLayout.tsx`, `Sidebar.tsx`, `Header.tsx`: Khung ứng dụng hoàn chỉnh, hỗ trợ Light & Dark Mode, menu người dùng floating popup, chuyển đổi độc lập ngôn ngữ UI (vi/en) và ngôn ngữ AI (vi/en).
  - `ResearchChatPage.tsx` & `chat.css`: Giao diện Main Research Chat phong cách Graylight/ChatGPT tối giản, hỗ trợ multi-turn follow-up với conversation context, câu hỏi nối tiếp (với conversation_id), hiển thị trạng thái loading, xử lý `INSUFFICIENT_EVIDENCE` mượt mà và trích dẫn/bằng chứng độc lập theo từng lượt.
  - Custom Scrollbar: Thanh cuộn hiện đại toàn hệ thống (`16px`, `#888888` thumb, `#555555` hover, `border-radius: 10px`, nền trong suốt) bám sát lề phải màn hình.
  - `vite.config.ts`: Cấu hình Reverse Proxy chuyển tiếp `/api` sang FastAPI backend (Port 8000).

---

## 2. Nhóm chức năng Kho tri thức (Knowledge Base)

### 2.1. Quản lý Kho tri thức theo Chủ đề (Knowledge Domain Management)
- **Mục đích**: Phân nhóm dữ liệu tri thức theo các lĩnh vực chuyên biệt (Y tế, Kinh tế, Chính sách công, Khoa học công nghệ).
- **Input**: Tên chủ đề, mô tả, danh mục từ khóa ưu tiên.
- **Output**: Bản ghi không gian tri thức (Knowledge Domain) mới được tạo.
- **Actor**: Quản trị viên, Nhà nghiên cứu.
- **Luồng chính**:
  1. Người dùng chọn tạo mới Không gian tri thức.
  2. Thiết lập các tham số tìm kiếm và nguồn tin cậy liên quan đến lĩnh vực.
  3. Hệ thống cấu hình không gian vector và chỉ mục phù hợp.
- **Ghi chú**: Giúp giới hạn phạm vi tìm kiếm bằng chứng, nâng cao độ chính xác theo ngữ cảnh ngành.

---

## 3. Nhóm chức năng Quản lý Tài liệu Tri thức (Document Knowledge Base — FE-04.5A & BE-04.5B)

### 3.1. Tiếp nhận & Tải lên tài liệu (Document Ingestion & Parsing)
- **Mục đích**: Nạp tài liệu tri thức mới (PDF, DOCX, TXT) vào kho tri thức làm nguồn đối chứng thẩm định.
- **Input**: Tệp tài liệu định dạng `.pdf`, `.docx`, `.txt` (kèm xác thực MIME type và kích thước).
- **Output**: Bản ghi `Document` trong CSDL kèm danh sách `DocumentChunk` đã qua làm sạch và chunking.
- **Actor**: Nhà nghiên cứu, Quản trị viên.
- **Luồng chính**:
  1. Người dùng mở `DocumentUploadModal.tsx` tại giao diện `/documents`, chọn file và bấm Upload.
  2. Backend nhận file qua API `POST /api/v1/documents/upload`.
  3. `IngestionService` tự động nhận diện định dạng, chạy parser tương ứng (`PdfParser`, `DocxParser`, `TxtParser`).
  4. `TextCleaner` chuẩn hóa Unicode NFKC và loại bỏ ký tự điều khiển.
  5. `MetadataExtractor` tính mã băm SHA-256, đếm số trang, số từ, kích thước byte.
  6. `SentenceSplitter` phân đoạn và lưu trữ vào CSDL kèm cập nhật vector embeddings.

### 3.2. Quản lý, Xem chi tiết Chunks & Xóa tài liệu (Document Life-cycle)
- **Mục đích**: Xem danh sách tài liệu thật từ backend, kiểm tra các chunks văn bản và xóa tài liệu khi cần.
- **Input**: `document_id`.
- **Output**: Thông tin chi tiết tài liệu và danh sách chunks trong `DocumentDetailDrawer.tsx`.
- **API Endpoints**:
  - `GET /api/v1/documents`: Liệt kê tài liệu.
  - `GET /api/v1/documents/{document_id}`: Lấy chi tiết tài liệu kèm chunks.
  - `DELETE /api/v1/documents/{document_id}`: Xóa tài liệu và toàn bộ chunks liên quan.
- **Frontend UI**: `DocumentsPage.tsx`, hỗ trợ Search/Filter, Refresh, Empty/Loading/Error state, và hộp thoại xác nhận xóa an toàn.

---

## 4. Nhóm chức năng Tìm kiếm & Khám phá Truy xuất (Search & Retrieval Explorer — FE-04.6B & BE-04.6A)

### 4.1. Khám phá Truy xuất Độc lập (Search / Retrieval Explorer — `/search`)
- **Mục đích**: Cho phép người dùng trực tiếp kiểm tra và quan sát pipeline retrieval của hệ thống một cách minh bạch.
- **Input**: Câu truy vấn tìm kiếm độc lập, chế độ tìm kiếm (`hybrid`, `vector`, `bm25`), `top_k`.
- **Output**: Danh sách kết quả retrieval kèm phân rã chi tiết điểm số và thứ hạng.
- **API Endpoint**: `POST /api/v1/search`.
- **Frontend UI**: `SearchExplorerPage.tsx` và `RetrievalDetailsDrawer.tsx`.

### 4.2. Phân rã Điểm số & Thứ hạng Minh bạch (Score & Rank Inspection)
- **Thông tin hiển thị cho từng chunk kết quả**:
  - `Final Rank` & `Content` trích đoạn văn bản.
  - `Dense Vector Rank` (Thứ hạng tìm kiếm ngữ nghĩa).
  - `BM25 Rank` (Thứ hạng tìm kiếm từ khóa/thực thể).
  - `RRF Score` (Điểm số hợp nhất Reciprocal Rank Fusion với $k=60$).
  - `Reranker Score` (Điểm tương quan ngữ cảnh sâu từ Cross-Encoder `bge-reranker-base`).
  - Metadata: Tên tài liệu, trang, tác giả, ngày nạp.
- **Ngăn trượt chi tiết (`RetrievalDetailsDrawer`)**: Minh họa trực quan từng bước của retrieval pipeline và thời gian thực thi (Latency).

---

## 5. Nhóm chức năng Trợ lý Tra cứu Nghiên cứu (Research Chat Assistant & Grounded Q&A)

### 5.1. Không gian Tra cứu Nghiên cứu Trung tâm (Main Research Chat Workspace — `/chat` hoặc `/`)
- **Mục đích**: Đóng vai trò là màn hình làm việc chính phong cách Perplexity, tối ưu cho tra cứu thông tin có căn cứ.
- **Input**: Câu hỏi hoặc chủ đề tra cứu của người dùng.
- **Output**:
  - Lời chào khởi đầu (Welcome State) kèm gợi ý chủ đề (Prompt Starters).
  - Khung trả lời từ AI kèm hệ thống chú thích nguồn tương tác (`[1]`, `[2]`).
  - Thẻ phân tích nhận định thành phần (`Claims Breakdown`).
  - Thẻ định lượng độ bao phủ bằng chứng (`Evidence Coverage Card`).
  - Ngăn trượt tra cứu bằng chứng chi tiết (`EvidenceDrawer`).
  - Khung nhập liệu đa lượt cố định ở đáy màn hình (`chat-sticky-composer`).
- **Actor**: Người dùng cuối, Nhà nghiên cứu.

### 5.2. Nhận diện Ý định Người dùng (Intent Router — Deterministic Greeting & Identity Bypass)
- **Mục đích**: Tự động nhận diện và phản hồi tức thì các câu chào hỏi (`hello`, `xin chào`, `hi`) hoặc câu hỏi danh tính (`bạn là ai`, `SourceCheck AI là gì`) mà không cần kích hoạt RAG pipeline.
- **Cơ chế**: Áp dụng bộ lọc mẫu tất định (deterministic regex matcher), triệt tiêu độ trễ và ngăn chặn phản hồi nhầm `INSUFFICIENT_EVIDENCE`.

### 5.3. Viết lại Truy vấn Ngữ cảnh (Contextual Query Rewriting)
- **Mục đích**: Giải quyết hiện tượng đồng tham chiếu (coreference) trong hội thoại đa lượt (ví dụ: *"Ai là tác giả của nghiên cứu đó?"*).
- **Cơ chế**: Tự động kết hợp ngữ cảnh lượt hỏi trước để tái tạo truy vấn độc lập hoàn chỉnh trước khi đưa vào bộ tìm kiếm lai.

### 5.4. Nền tảng Lưu trữ Lịch sử Hội thoại (Conversation History — CHAT-02.1)
- **Mục đích**: Lưu vết các phiên tra cứu và tin nhắn của từng người dùng, hỗ trợ hội thoại đa phiên và đối soát lại kết quả lịch sử.
- **Input**: `user_id`, `conversation_id`, `role` (`user`/`assistant`), `content`, `extra_metadata` (chứa trích dẫn, claims, coverage).
- **Output**: Dữ liệu thực thể `Conversation` và `Message` được lưu trữ toàn vẹn trong cơ sở dữ liệu.
- **Actor**: Hệ thống backend.
- **Cơ chế**:
  - Phân cấp `User` -> `Conversation` -> `Message` với `CASCADE DELETE` triệt để.
  - Phân định quyền sở hữu dữ liệu (Ownership Isolation) theo từng `user_id`.
  - Quản lý lược đồ cơ sở dữ liệu qua Alembic Migration `003_add_conversations_and_messages.py`.

---

## 5.5. Nhóm chức năng Bảng điều khiển Tổng quan (System Dashboard — FE-04.9 & BE-04.9)

### 5.5.1. Thống kê Hoạt động Toàn diện (`DashboardPage.tsx`)
- **Mục đích**: Cung cấp bức tranh toàn cảnh về hoạt động và độ tin cậy của toàn bộ hệ thống.
- **Input**: Dữ liệu tổng hợp từ endpoint `GET /api/v1/dashboard/stats`.
- **Output**:
  - Thẻ chỉ số tổng quan: Tổng số Tài liệu (Documents), Tổng số Câu hỏi (Questions), Tổng số Hội thoại (Conversations), Tổng số Lượt kiểm chứng (Fact-Checks).
  - Biểu đồ phân bố phán quyết (Verdict Distribution): Số lượng và tỷ lệ % của `SUPPORTED`, `REFUTED`, `PARTIALLY_SUPPORTED`, `NOT_ENOUGH_INFO`.
  - Thẻ truy cập nhanh tới các không gian chức năng chính.
- **Actor**: Người dùng, Quản trị viên.

---

## 6. Nhóm chức năng Bằng chứng (Evidence Extraction & Matching)

### 6.1. Ánh xạ Bằng chứng theo Nhận định (Evidence Matching)
- **Mục đích**: Liên kết từng câu nhận định cụ thể với các đoạn văn bản đóng vai trò là bằng chứng trực tiếp.
- **Input**: Danh sách các nhận định (claims), danh sách ứng viên bằng chứng đã truy xuất.
- **Output**: Cặp (Claim, Evidence) kèm điểm tương quan ngữ nghĩa.
- **Actor**: Hệ thống.
- **Luồng chính**: Lọc bỏ các đoạn văn bản không liên quan trực tiếp đến khẳng định trọng tâm của claim.
- **Ghi chú**: Mỗi claim có thể liên kết với một hoặc nhiều bằng chứng.

### 6.2. Tính toán Độ bao phủ Bằng chứng (Evidence Coverage Analysis)
- **Mục đích**: Đo lường định lượng xem có bao nhiêu phần trăm nhận định trong văn bản đã tìm được căn cứ xác minh.
- **Input**: Danh sách các nhận định đã được đối chiếu.
- **Output**: Tỉ lệ phần trăm bao phủ (Coverage Rate), số lượng nhận định thiếu nguồn.
- **Actor**: Hệ thống.
- **Luồng chính**: Tổng hợp số claim có bằng chứng hợp lệ trên tổng số claim cần kiểm tra.
- **Ghi chú**: Giúp người dùng biết được độ tin cậy của toàn bộ bài viết dựa trên mức độ đầy đủ của dữ liệu.

---

## 7. Nhóm chức năng Trích dẫn (Citation Grounding)

### 7.1. Định vị Trích dẫn Chính xác (Citation Anchor Grounding)
- **Mục đích**: Gắn kết luận của hệ thống với đoạn trích nguyên văn (quote) trong tài liệu gốc.
- **Input**: Nhận định đã kiểm chứng, bằng chứng đối chiếu.
- **Output**: Đoạn văn bản trích dẫn nguyên gốc, tên tài liệu, tác giả, đường link tham khảo.
- **Actor**: Hệ thống.
- **Luồng chính**: Thuật toán quét và trích xuất đúng câu mang thông tin mấu chốt làm căn cứ kết luận.
- **Ghi chú**: Ngăn ngừa trường hợp dẫn link nguồn chung chung mà không chỉ ra người đọc cần nhìn vào dòng nào.

### 7.2. Định dạng Danh mục Tham khảo (Footnote & References Formatting)
- **Mục đích**: Trình bày chú thích khoa học (inline numbers `[1]`, `[2]`) ở cuối báo cáo.
- **Input**: Danh sách bằng chứng đã dùng trong báo cáo.
- **Output**: Bảng danh mục tài liệu tham khảo theo định dạng chuẩn (Markdown / Web UI).
- **Actor**: Hệ thống.
- **Luồng chính**: Đánh số thứ tự các trích dẫn xuất hiện trong bài và tạo danh mục tra cứu cuối trang.
- **Ghi chú**: Tương thích với các định dạng hiển thị web và xuất bản tài liệu PDF.

---

## 8. Nhóm chức năng Thẩm định Nhận định (Claim Verification)

### 8.1. Tự động bóc tách nhận định (Claim Extraction)
- **Mục đích**: Phân tách văn bản phức tạp của người dùng thành các mệnh đề sự kiện đơn lẻ, độc lập, có thể kiểm chứng.
- **Input**: Văn bản đoạn tin tức hoặc status mạng xã hội.
- **Output**: Danh sách các claims độc lập (loại bỏ quan điểm chủ quan, câu cảm thán).
- **Actor**: Hệ thống.
- **Luồng chính**:
  1. Phân tích ngữ pháp và cấu trúc ngữ nghĩa của đoạn văn bản.
  2. Bóc tách từng phát biểu mang tính khẳng định sự thật khách quan.
  3. Chuẩn hóa câu văn để có thể hiểu độc lập mà không cần đọc cả bài dài.
- **Ghi chú**: Đây là bước mở đầu quan trọng nhất của quy trình kiểm chứng.

### 8.2. Suy luận & Gán nhãn Phán quyết (Stance & Verdict Assignment)
- **Mục đích**: Xác định tính đúng/sai của nhận định dựa trên bằng chứng đã tìm được.
- **Input**: Từng nhận định kèm bằng chứng tương ứng.
- **Output**: Phán quyết (SUPPORTED, REFUTED, PARTIALLY_SUPPORTED, NOT_ENOUGH_INFO) cùng điểm tin cậy (Confidence Score) và lời giải thích lập luận.
- **Actor**: Hệ thống (LLM Reasoning Engine).
- **Luồng chính**: Mô hình đối chiếu claim với bằng chứng theo nguyên tắc logic suy diễn và gán nhãn phán quyết.
- **Ghi chú**: Luôn có phần giải thích tóm tắt logic dẫn tới phán quyết.

---

## 9. Nhóm chức năng Phát hiện Mâu thuẫn (Contradiction Detection)

### 9.1. Phát hiện Mâu thuẫn Nội tại (Internal Contradiction Detection)
- **Mục đích**: Cảnh báo khi văn bản đầu vào tự chứa các tuyên bố trái ngược nhau (ví dụ: đoạn đầu nói tăng trưởng, đoạn sau nói sụt giảm cùng một chỉ số).
- **Input**: Danh sách các claims bóc tách từ cùng một văn bản.
- **Output**: Cảnh báo mâu thuẫn kèm chỉ dẫn các câu đối chọi nhau.
- **Actor**: Hệ thống.
- **Luồng chính**: So khớp chéo giữa các mệnh đề trong cùng văn bản đầu vào.
- **Ghi chú**: Hỗ trợ đắc lực cho các biên tập viên phát hiện lỗi logic trong bản thảo.

### 9.2. Phát hiện Xung đột Bằng chứng Đa nguồn (Source Contradiction Detection)
- **Mục đích**: Cảnh báo khi hai nguồn tài liệu uy tín đưa ra hai con số hoặc hai sự kiện trái chiều về cùng một nhận định.
- **Input**: Tập bằng chứng từ nhiều nguồn khác nhau.
- **Output**: Thông báo sự kiện đang có tranh cãi, hiển thị quan điểm của cả 2 phía.
- **Actor**: Hệ thống.
- **Luồng chính**: Đối chiếu stance giữa các bằng chứng độc lập, nếu có cả bằng chứng ủng hộ lẫn bác bỏ thì kích hoạt cờ tranh chấp.
- **Ghi chú**: Không ép buộc kết luận Đúng/Sai khi bản thân các nguồn thông tin trên thực tế chưa thống nhất.

---

## 10. Nhóm chức năng Báo cáo Kiểm chứng (Verification Report)

### 10.1. Tổng hợp Báo cáo Thẩm định (Fact-Check Summary)
- **Mục đích**: Trình bày tổng thể kết quả kiểm tra theo dạng Dashboard trực quan.
- **Input**: Kết quả của toàn bộ pipeline kiểm chứng.
- **Output**: Báo cáo tổng thể với phán quyết chung (Chính xác, Sai lệch, Trộn lẫn, Chưa rõ), danh sách nhận định kèm nhãn màu sắc, và biểu đồ tỷ lệ bao phủ.
- **Actor**: Người dùng cuối.
- **Luồng chính**: Render kết quả trên giao diện web ngay sau khi pipeline hoàn tất.
- **Ghi chú**: Cung cấp góc nhìn từ tóm tắt nhanh cho độc giả phổ thông đến chi tiết chuyên sâu cho chuyên gia.

### 10.2. Xuất bản & Chia sẻ Kết quả (Export & Share)
- **Mục đích**: Chia sẻ báo cáo kết quả kiểm chứng cho cộng đồng hoặc tải về để lưu trữ hồ sơ.
- **Input**: Mã yêu cầu kiểm chứng (`request_id`), định dạng xuất (Link công khai / Markdown / PDF).
- **Output**: Đường link chia sẻ hoặc tệp báo cáo hoàn chỉnh.
- **Actor**: Người dùng.
- **Luồng chính**: Người dùng bấm "Chia sẻ" hoặc "Xuất báo cáo", hệ thống đóng gói nội dung và tạo định dạng tương ứng.
- **Ghi chú**: Đường link công khai ở chế độ chỉ đọc (read-only).

---

## 11. Nhóm chức năng Đánh giá & Thử nghiệm (Evaluation Framework)

### 11.1. Chạy Đánh giá Tự động (Automated Benchmark Runner)
- **Mục đích**: Đo lường hiệu năng của hệ thống trên các tập dữ liệu thẩm định tiêu chuẩn (Ground Truth Datasets).
- **Input**: Bộ dataset thử nghiệm, cấu hình tham số mô hình (top-k, reranker on/off, hybrid weight).
- **Output**: Bảng số liệu định lượng về Precision, Recall, F1, Faithfulness.
- **Actor**: Kỹ sư AI, Nhà nghiên cứu.
- **Luồng chính**: Runner nạp tập claims mẫu, kích hoạt pipeline và so sánh phán quyết của hệ thống với nhãn chuẩn của con người.
- **Ghi chú**: Chạy định kỳ sau mỗi lần cập nhật thuật toán để tránh hiện tượng suy giảm hiệu năng (regression).

### 11.2. Thử nghiệm Bóc tách Thành phần (Ablation Study Logging)
- **Mục đích**: Định lượng đóng góp thực tế của từng mô-đun (Reranker, BM25, Multi-query) đối với chất lượng tổng thể.
- **Input**: Danh sách các cấu hình biến thiên (Ví dụ: tắt Reranker, chỉ dùng Vector Search).
- **Output**: Bảng so sánh chéo hiệu năng giữa các biến thể.
- **Actor**: Nhà nghiên cứu.
- **Luồng chính**: Tự động chạy lần lượt các cấu hình và lưu log chi tiết vào `evaluation/results/`.
- **Ghi chú**: Phục vụ công tác báo cáo khoa học và tối ưu hóa tài nguyên phần cứng.

---

## 12. Nhóm chức năng Quản trị Hệ thống (Administration)

### 12.1. Giám sát Sức khỏe & Tải hệ thống (System Health & Monitoring)
- **Mục đích**: Theo dõi trạng thái hoạt động của các dịch vụ phụ thuộc (Database, Redis, Vector DB, LLM API).
- **Input**: Các tín hiệu heartbeat từ endpoint `/health` và `/ready`.
- **Output**: Bảng điều khiển trạng thái (Uptime, Latency, Error Rate).
- **Actor**: Quản trị viên hệ thống (DevOps/Admin).
- **Luồng chính**: Cơ chế monitoring tự động gọi các probe định kỳ để cảnh báo sự cố.
- **Ghi chú**: Giúp phát hiện sớm khi tài khoản API bên ngoài hết hạn mức hoặc database bị gián đoạn kết nối.

## 13. Current user-flow completion status

### 9.1 Conversation and history

- Conversation APIs require a Bearer access token and enforce user ownership.
- The GREETING path persists a conversation, user message, canned response, and assistant message.
- The Sidebar displays backend data for the current user and does not create conversations when Chat is opened or refreshed.
- Automated conversation tests use an isolated test database/session and do not pollute the development database.

### 9.2 User interface

- Search Explorer uses Evidence Exploration (Vietnamese: evidence exploration). Hybrid/Dense/BM25, Top-K, and reranker are not user-facing form inputs; technical details remain in Retrieval Details.
- Conversation context actions use consistent UI icons instead of emoji; destructive delete styling is preserved.
- Chat input uses a soft default border and light gray hover/focus states without a heavy focus ring.
- UI language uses typed vi/en dictionaries for text, placeholders, tooltips, titles, aria labels, keyboard hints, loading/error/empty states, auth, Search, Documents, Verification, and Dashboard.
- Dashboard statistics are API-backed; refresh reuses the dashboard service and updates all related data blocks.

### 9.3 Validation and boundaries

- Frontend builds are validated with tsc && vite build.
- Focused tests cover Chat, Sidebar, Search, Documents, Verification, auth, Dashboard, and conversation persistence/isolation.
- These updates do not change the RAG pipeline, verification algorithms, or authentication architecture.
