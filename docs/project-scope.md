# Project Scope & Roadmap: SourceCheck AI

Tài liệu xác định ranh giới phạm vi phát triển của dự án **SourceCheck AI**. Hệ thống được chia thành 3 giai đoạn rõ ràng: **Giai đoạn MVP (Khả thi tối thiểu)**, **Giai đoạn Advanced (Nâng cao)**, và **Giai đoạn Future (Tương lai dài hạn)**.

---

## 1. Giai đoạn MVP (Minimum Viable Product - Sản phẩm Khả thi Tối thiểu)

Mục tiêu của giai đoạn MVP là đưa hệ thống vào trạng thái hoạt động đầu cuối (end-to-end executable) với các tính năng thiết yếu nhất để xác minh tính khả thi của giải pháp:

### 1.1. Các tính năng bắt buộc trong MVP:
- **Kiến trúc mã nguồn chuẩn hóa**: Toàn bộ khung thư mục Frontend, Backend, Evaluation và Docs được hoàn thiện và kiểm tra toàn vẹn.
- **Nạp tài liệu cơ bản (Basic Document Ingestion)**: Cho phép tải lên văn bản thuần hoặc file TXT đơn giản, cắt đoạn (chunking) theo kích thước cố định.
- **Truy xuất vector cơ bản (Basic Dense Vector Search)**: Lập chỉ mục tài liệu vào vector database và truy xuất Top-K đoạn gần nhất dựa trên Cosine Similarity.
- **Bóc tách nhận định đơn giản (Single/Multi Claim Extraction)**: Tiếp nhận đoạn văn ngắn và tách ra các câu trần thuật sự thật.
- **Thẩm định nhận định (Basic Claim Verification)**: Gọi mô hình LLM với prompt có cấu trúc để gán nhãn Đúng / Sai / Chưa rõ kèm theo lời giải thích ngắn.
- **Giao diện Web tối giản (Minimalist Frontend UI)**: Giao diện cho phép nhập văn bản, bấm nút "Kiểm chứng" và hiển thị danh sách nhận định kèm thẻ màu trạng thái.
- **Báo cáo kết quả cơ bản**: Hiển thị bảng tổng hợp phán quyết và nguồn tài liệu được dùng.

### 1.2. Giới hạn trong giai đoạn MVP:
- Chỉ hỗ trợ văn bản tiếng Việt và tiếng Anh tiêu chuẩn.
- Chưa xử lý các tệp định dạng phức tạp như tệp bảng tính Excel hay tài liệu scan dạng ảnh.
- Chưa yêu cầu hệ thống tài khoản người dùng bắt buộc (cho phép tra cứu tự do ở chế độ guest).

---

## 2. Giai đoạn Advanced (Nâng cấp Chuyên sâu & Nghiên cứu Khoa học)

Giai đoạn này tập trung vào việc tối ưu hóa độ chính xác, đưa các kỹ thuật hiện đại vào vận hành thực tế và thực hiện các bài đo lường định lượng:

### 2.1. Các tính năng thuộc giai đoạn Advanced:
- **Tìm kiếm lai kết hợp (Hybrid Search with RRF)**: Kết hợp đồng thời Dense Vector Search và Sparse BM25 Search để giải quyết triệt để bài toán tìm kiếm số liệu, tên riêng và ngày tháng.
- **Tái xếp hạng nâng cao (Cross-Encoder Reranking)**: Bổ sung mô hình Cross-Encoder để lọc sạch các đoạn văn trôi nổi, nâng cao độ chính xác của ngữ cảnh cung cấp cho LLM.
- **Phát hiện mâu thuẫn đa chiều (Contradiction Detection)**: 
  - Nhận diện mâu thuẫn nội tại trong chính bài viết của người dùng.
  - Nhận diện xung đột thông tin giữa các nguồn tài liệu báo chí khác nhau.
- **Gắn nguồn trích dẫn nguyên văn (Citation Grounding & Footnotes)**: Tự động trích xuất chính xác câu văn làm căn cứ trong tài liệu gốc và định dạng danh mục tham khảo chuẩn hóa.
- **Hàng rào chống ảo giác (Faithfulness Guardrail)**: Tự động chấm điểm độ trung thực của câu trả lời trước khi gửi về client, ngăn chặn việc mô hình tự bịa đặt thông tin.
- **Framework Đánh giá & Benchmark Tự động**: Tích hợp các bộ dữ liệu thử nghiệm chuẩn, tự động đo lường Recall@K, Precision@K, Claim Verification F1 và lưu vết kết quả Ablation Study.
- **Quản lý phiên làm việc & Lịch sử cá nhân**: Đăng ký/đăng nhập JWT và lưu vết toàn bộ các lần kiểm chứng trong PostgreSQL.

---

## 3. Giai đoạn Future (Tầm nhìn Mở rộng Dài hạn)

Các tính năng mang tính đột phá và mở rộng quy mô ứng dụng cho doanh nghiệp, cơ quan báo chí và cộng đồng:

### 3.1. Các tính năng định hướng Tương lai:
- **Thẩm định Đa phương tiện (Multimodal Fact-Checking)**:
  - Kiểm chứng thông tin trong hình ảnh (nhận diện ảnh đã qua Photoshop/ghép nối).
  - Phân tích và kiểm chứng thông tin trong video ngắn (TikTok, YouTube Shorts, Reels) bằng cách chuyển đổi âm thanh sang văn bản (Whisper) kết hợp trích xuất khung hình.
- **Tiện ích Mở rộng Trình duyệt (Browser Extension)**:
  - Cho phép người dùng bôi đen đoạn văn bản trên bất kỳ trang web hoặc mạng xã hội nào và nhấp chuột phải để kiểm chứng ngay lập tức mà không cần chuyển tab.
- **Tích hợp Mạng lưới Thẩm định Toàn cầu (Global Fact-Checking Integration)**:
  - Đồng bộ và kết nối với cơ sở dữ liệu của các tổ chức kiểm chứng quốc tế thông qua chuẩn ClaimReview (Schema.org / Google Fact Check Tools API).
- **Môi trường Cộng tác Toà soạn (Editorial Collaboration Workspace)**:
  - Cung cấp không gian làm việc số cho các nhà báo và ban biên tập: Phân quyền duyệt bài nhiều cấp, ghi chú nội bộ, và xuất báo cáo đối soát dạng PDF có chứng chỉ số.
- **Hệ thống Crawler Tự động & Cảnh báo Sớm (Real-time Trend Verification)**:
  - Tự động theo dõi các chủ đề nóng trên mạng xã hội, phát hiện các thông tin sai lệch đang có xu hướng lan rộng và cảnh báo sớm cho cơ quan quản lý.
