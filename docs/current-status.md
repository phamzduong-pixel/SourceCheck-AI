# SourceCheck AI — Current Completion Status

> Cập nhật: 27/09/2026

Tài liệu này ghi lại trạng thái user-facing và các phần đã hoàn thiện trong các checkpoint gần đây. Đây là bản tóm tắt vận hành; mô tả kỹ thuật chi tiết vẫn nằm trong các tài liệu kiến trúc tương ứng.

## 1. Luồng người dùng chính

Luồng demo hiện có thể thực hiện theo chuỗi:

`Đăng nhập → Upload tài liệu → Tài liệu sẵn sàng → Hỏi đáp → Verification → Claims/Verdict → Evidence/Citation → Coverage → Tra cứu lại lịch sử`

- Hỗ trợ upload PDF, DOCX và TXT qua Documents.
- Chat sử dụng câu trả lời và dữ liệu nguồn thật từ backend.
- Verification hiển thị verdict tổng thể và verdict riêng của từng claim: `SUPPORTED`, `PARTIALLY_SUPPORTED`, `REFUTED`, `NOT_ENOUGH_INFO`.
- Evidence/Citation hiển thị quote, document/source, URL và page number khi backend cung cấp; metadata thiếu được bỏ qua một cách an toàn.
- Evidence Coverage lấy trực tiếp từ backend, không được tính lại ở frontend.
- Citation tương tác mở đúng evidence liên quan; `/api/v1/verify/{request_id}` trả lại báo cáo đã lưu.

## 2. Lịch sử và điều hướng

- `GET /api/v1/verify/history` cung cấp các lần kiểm chứng gần đây của user hiện tại.
- Verification History có loading, empty, error và trạng thái báo cáo không còn dữ liệu.
- Sidebar có thể thu gọn/mở rộng; khi thu gọn vẫn giữ các icon chính và tooltip.
- Lịch sử hội thoại được chia thành `Đã ghim` và `Lịch sử`; pin/unpin chuyển item giữa hai nhóm.
- Profile menu có các action Hồ sơ, Cài đặt và Đăng xuất.
- Modal xóa hội thoại được căn giữa viewport và vẫn giữ confirmation trước thao tác phá hủy.

## 3. Hồ sơ người dùng và Cài đặt

### Hồ sơ

- Hiển thị avatar, tên hiển thị và email tài khoản hiện tại.
- Cho phép chọn avatar, đổi tên và thêm/sửa số điện thoại.
- Email được xem là thông tin tài khoản và không cho chỉnh sửa trong UI.
- Thay đổi hồ sơ được lưu qua `PATCH /api/v1/auth/me` và được phản ánh lại trong Sidebar/Profile menu.
- Có feedback thành công/lỗi và trạng thái đang lưu.

### Cài đặt

- Theme: Sáng/Tối.
- Ngôn ngữ giao diện: VI/EN.
- Ngôn ngữ trả lời AI: VI/EN.
- Cỡ chữ: Nhỏ/Vừa/Lớn.
- Bật/tắt hiển thị nguồn/dẫn chứng và thông tin kiểm chứng.
- Các preference giao diện được lưu cục bộ và giữ lại sau refresh.
- TTS không được phát triển thêm; trang Cài đặt chỉ phản ánh các chức năng âm thanh nếu runtime hiện tại có hỗ trợ.
- Xóa lịch sử server/database không được giả lập bằng localStorage; nếu chưa có API phù hợp, UI hiển thị rõ là chưa khả dụng.

## 4. Xác thực và database local

- Tài khoản demo: `demo@sourcecheck.ai` / `Password123!`.
- Email/password login và Google OAuth hiện có vẫn dùng cùng authentication architecture.
- Đã xử lý lỗi login HTTP 500 trên database SQLite local cũ: `create_all` không tự thêm cột mới, nên startup hiện kiểm tra và bổ sung các cột profile nullable còn thiếu (`avatar_url`, `phone_number`) trước khi truy vấn user.
- Login local đã xác nhận trả HTTP 200 sau khi schema được nâng tương thích.
- Migration production tương ứng vẫn là `004_add_user_profile_fields`; không thay đổi verification algorithm hoặc pipeline.

## 5. Validation gần nhất

- Focused database compatibility tests: `2 passed`.
- Backend authentication tests: `14 passed`.
- Direct local login check: HTTP `200`.
- Không có thay đổi frontend trong bản sửa lỗi server gần nhất nên không chạy lại frontend build cho bản sửa đó.

## 6. Phạm vi không thay đổi

Các cập nhật trên không thay đổi Claim Extraction, Claim Verifier, evidence matching, citation logic, coverage calculation, RAG/retrieval pipeline, database architecture hoặc LLM provider. Không commit/push trong checkpoint này.