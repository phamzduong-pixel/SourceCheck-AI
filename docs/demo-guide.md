# Demo Guide & Presentation Script: SourceCheck AI

Tài liệu kịch bản trình diễn (Live Demo Walkthrough) từng bước cho hội đồng đánh giá và người sử dụng hệ thống **SourceCheck AI**.

---

## 1. Chuẩn bị Môi trường Demo (Pre-requisites)

### Khởi động Hệ thống
1. **Backend** (Port 8000):
   ```bash
   cd backend
   uvicorn app.main:app --reload --port 8000
   ```
2. **Frontend** (Port 5173):
   ```bash
   cd frontend
   npm run dev
   ```

### Tài khoản Demo Seed
* **URL**: `http://localhost:5173/login`
* **Email**: `demo@sourcecheck.ai`
* **Mật khẩu**: `Password123!`

---

## 2. Kịch bản Trình diễn 8 Bước (8-Step Demo Flow)

```text
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ 1. Login     │ ──► │ 2. Documents │ ──► │ 3. RAG Q&A   │ ──► │ 4. Multi-turn│
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                                       │
┌──────────────┐     ┌──────────────┐     ┌──────────────┐             ▼
│ 8. Greeting  │ ◄── │ 7. Search    │ ◄── │ 6. Fact-Check│ ◄── ┌──────────────┐
│  (Intent)    │     │  (Explorer)  │     │  (Workspace) │     │ 5. Insuff.   │
└──────────────┘     └──────────────┘     └──────────────┘     │  Evidence    │
                                                               └──────────────┘
```

---

### Bước 1: Đăng nhập & Khám phá Giao diện (Login & App Shell)
* **Thao tác**: Truy cập `http://localhost:5173/login`, đăng nhập với tài khoản `demo@sourcecheck.ai`.
* **Điểm nhấn**:
  * Giao diện phong cách **Matte Charcoal Dark Aesthetic** lấy cảm hứng từ DeepSeek và ChatGPT/Perplexity.
  * Hỗ trợ chuyển đổi **Light Mode / Dark Mode** tức thì trên Header.
  * Tùy chọn độc lập giữa **Ngôn ngữ Giao diện (UI)** và **Ngôn ngữ Trả lời của AI**.
  * Chuyển hướng trực tiếp vào **Dashboard** (`/dashboard`) với các thống kê thời gian thực: Tổng số tài liệu, hội thoại, câu hỏi, thẩm định.

---

### Bước 2: Quản lý Kho Tri thức & Tải tài liệu (Document Management)
* **Thao tác**: Điều hướng sang menu **Documents** (`/documents`).
* **Hành động**: Nhấn nút **Upload Document**, chọn tệp tài liệu mẫu (PDF, DOCX hoặc TXT).
* **Điểm nhấn**:
  * Ingestion Pipeline tự động làm sạch Unicode NFKC, bóc tách cấu trúc và phân mảnh (chunking).
  * Nhấn vào một tài liệu để mở Drawer xem chi tiết Metadata (SHA-256, Word count, Page count) và danh sách từng Chunk đã được lập chỉ mục.

---

### Bước 3: Đặt câu hỏi có Bằng chứng (Grounded RAG Q&A)
* **Thao tác**: Điều hướng sang **Research Chat** (`/chat` hoặc `/`).
* **Hành động**: Nhập câu hỏi vào khung soạn thảo:
  > *"Tăng trưởng GDP của Việt Nam năm 2023 đạt bao nhiêu phần trăm theo số liệu chính thức?"*
* **Điểm nhấn**:
  * Giao diện hội thoại cân đối (Balanced Left-Rail Alignment), câu hỏi và câu trả lời AI thẳng hàng nhau dọc theo trục lề trái.
  * Thanh Header cố định (`Sticky Top Header`) tự động hiển thị tên tóm tắt cuộc hội thoại kèm badge `● Grounded` và nút **"+ Tra cứu mới"** luôn đứng yên trên đỉnh màn hình khi cuộn trang.
  * Hệ thống thực thi **Hybrid Search (Dense Vector + BM25)** kết hợp **Reciprocal Rank Fusion (RRF)** và **Cross-Encoder Reranker**.
  * Câu trả lời được tổng hợp ngắn gọn kèm các thẻ trích dẫn footnote `[1]`, `[2]`.
  * Nhấn vào `[1]` để mở **Evidence Drawer** bên phải, xem trực tiếp đoạn trích dẫn nguyên văn (verbatim snippet), điểm liên quan và nguồn tài liệu gốc.
  * Thẻ **Evidence Coverage** hiển thị tỷ lệ phần trăm nhận định được bảo chứng (100%).

---

### Bước 4: Hỏi nối tiếp đa lượt (Multi-turn Follow-up with Context)
* **Thao tác**: Tiếp tục tại cuộc hội thoại trên, nhập câu hỏi ngắn:
  > *"Còn kim ngạch xuất nhập khẩu thì sao?"*
* **Điểm nhấn**:
  * Module **Contextual Query Rewriter** tự động nhận diện từ khóa anaphoric ("Còn... thì sao") và tái tạo truy vấn độc lập: *"Năm 2023 kim ngạch xuất nhập khẩu Việt Nam đạt bao nhiêu?"*.
  * Câu trả lời lượt 2 được lưu nối tiếp vào lịch sử hội thoại (`/conversations`), hoàn toàn cô lập theo tài khoản người dùng.
  * Nút **"+ Tra cứu mới"** trên Header cho phép reset phiên trò chuyện tức thì để bắt đầu chủ đề mới.

---

### Bước 5: Câu hỏi ngoài miền / Thiếu bằng chứng (Insufficient Evidence Handling)
* **Thao tác**: Nhập câu hỏi không có trong kho tri thức:
  > *"Tỷ lệ lạm phát trên sao Hỏa vào năm 2099 là bao nhiêu?"*
* **Điểm nhấn**:
  * Tầng **Evidence Sufficiency & Output Guardrail** phát hiện không có bằng chứng hợp lệ.
  * Hệ thống trả về thông báo an toàn: *"Tài liệu kiểm chứng hiện tại không đủ cơ sở để trả lời"*, triệt tiêu 100% ảo giác (Zero Hallucination).

---

### Bước 6: Không gian Thẩm định Chuyên sâu (Fact-Checking Workspace)
* **Thao tác**: Điều hướng sang **Fact-Checking** (`/fact-check`).
* **Hành động**: Dán đoạn văn bản cần kiểm chứng hoặc chọn **Sample Claim**:
  > *"Tăng trưởng GDP Việt Nam năm 2023 đạt 12.5% và Việt Nam nhập siêu 50 tỷ USD."*
* **Điểm nhấn**:
  * Hệ thống bóc tách thành các Claims độc lập và đối soát chéo.
  * Hiển thị bảng kết quả với nhãn phán quyết rõ ràng:
    * Claim 1: `REFUTED` (do số liệu thực tế là 5.05%).
    * Claim 2: `REFUTED` (do thực tế là xuất siêu 28 tỷ USD).
  * Cờ cảnh báo **Contradiction / Conflict Indicator** màu đỏ nổi bật cùng danh sách bằng chứng đối lập (`REFUTES`).

---

### Bước 7: Trực quan hóa Truy xuất (Search / Retrieval Explorer)
* **Thao tác**: Điều hướng sang **Search** (`/search`).
* **Hành động**: Nhập truy vấn tìm kiếm độc lập: *"Reciprocal Rank Fusion BM25 Vector"* và chọn chế độ `Hybrid`.
* **Điểm nhấn**:
  * Hiển thị bảng đối soát truy xuất: Xếp hạng Dense Vector, xếp hạng BM25, điểm số tổng hợp RRF Score và điểm Cross-Encoder Rerank.
  * Cho phép kỹ sư và người thẩm định kiểm tra độ trong suốt (explainability) của thuật toán retrieval.

---

### Bước 8: Xử lý Hội thoại Xã giao ngoài RAG (Deterministic Intent Router)
* **Thao tác**: Quay lại **Research Chat** (`/chat`), gửi câu chào:
  > *"Xin chào bạn"* hoặc *"Bạn là ai?"*
* **Điểm nhấn**:
  * Nhánh **Intent Router** nhận diện tức thì pattern ngữ pháp quy tắc (`GREETING` / `IDENTITY` / `SMALLTALK`).
  * Trả lời ngay phản hồi mẫu định sẵn mà không cần tốn chi phí gọi Vector Embedding, Hybrid Search hay LLM Generation.

---

## 3. Tổng kết Trình diễn (Summary Takeaways)
1. **Kiến trúc chặt chẽ**: Pipeline 13 bước tất định, không dựa vào Agent tự do bất định.
2. **Minh bạch & Đáng tin cậy**: Mọi nhận định đều có trích dẫn footnote `[1]`, `[2]` mở trực tiếp bằng chứng.
3. **Hiệu năng & Tiết kiệm**: Intent Router loại bỏ truy vấn thừa; Hybrid RRF + Reranker cho độ chính xác Hit@1 = 100%.
4. **Trải nghiệm người dùng cao cấp**: Giao diện hoàn thiện Light/Dark Mode, không còn bất kỳ placeholder nào.

## 4. Profile & Settings trong demo

Sau khi đăng nhập, mở User/Profile menu để kiểm tra:

1. **Hồ sơ**: chọn avatar, đổi tên hiển thị hoặc cập nhật số điện thoại rồi lưu. Email hiện tại chỉ đọc.
2. **Cài đặt**: đổi Sáng/Tối, VI/EN, cỡ chữ và bật/tắt nguồn hoặc thông tin kiểm chứng. Refresh trang để xác nhận các preference giao diện được giữ lại.
3. **Sidebar**: thử thu gọn/mở rộng, pin một cuộc hội thoại và xác nhận item chuyển giữa `Đã ghim` và `Lịch sử`.

## 5. Kiểm tra khi login local báo lỗi máy chủ

Nếu database SQLite local được tạo từ phiên bản cũ, hãy khởi động lại backend từ thư mục `backend` để startup compatibility check bổ sung các profile column còn thiếu. Tài khoản demo hợp lệ là:

- Email: `demo@sourcecheck.ai`
- Mật khẩu: `Password123!`

Không cần tạo lại user hoặc sửa frontend để xử lý lỗi schema này. Nếu dùng database được quản lý bằng Alembic, chạy migration `004_add_user_profile_fields` trước khi thử lại.