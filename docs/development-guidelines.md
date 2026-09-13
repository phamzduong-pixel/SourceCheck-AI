# Development Guidelines: SourceCheck AI

Tài liệu quy chuẩn kỹ thuật và hướng dẫn phát triển dành cho toàn bộ thành viên tham gia xây dựng mã nguồn dự án **SourceCheck AI**. Việc tuân thủ các nguyên tắc này là bắt buộc nhằm đảm bảo mã nguồn luôn trong sạch, dễ bảo trì, dễ kiểm thử và có khả năng mở rộng bền vững.

---

## 1. Quy chuẩn Đặt tên (Naming Conventions)

### 1.1. Python (Backend & Evaluation)
- **Tệp và Thư mục (Files & Directories)**: Sử dụng `snake_case` hoàn toàn bằng chữ thường (Ví dụ: `verification_service.py`, `claim_extractor.py`).
- **Lớp (Classes)**: Sử dụng `PascalCase` (Ví dụ: `VerificationService`, `HybridRetriever`, `DocumentChunk`).
- **Hàm và Phương thức (Functions & Methods)**: Sử dụng `snake_case` bắt đầu bằng động từ hành động (Ví dụ: `extract_claims()`, `verify_claim()`, `get_by_id()`).
- **Biến và Thuộc tính (Variables & Attributes)**: Sử dụng `snake_case` có ngữ nghĩa rõ ràng (Ví dụ: `confidence_score`, `raw_content`).
- **Hằng số (Constants)**: Sử dụng `UPPER_SNAKE_CASE` (Ví dụ: `API_V1_PREFIX`, `DEFAULT_CHUNK_SIZE`).

### 1.2. TypeScript / React (Frontend)
- **Components & Layouts**: Sử dụng `PascalCase` cho cả tên file và tên component (Ví dụ: `ClaimCard.tsx`, `VerificationView.tsx`).
- **Hooks**: Sử dụng `camelCase` bắt đầu bằng tiền tố `use` (Ví dụ: `useFactCheck.ts`, `useDebounce.ts`).
- **Services & Utils**: Sử dụng `camelCase` (Ví dụ: `apiClient.ts`, `formatDate.ts`).
- **Types & Interfaces**: Sử dụng `PascalCase` (Ví dụ: `VerificationResult`, `ClaimItem`).

### 1.3. API & Endpoints
- **Đường dẫn (URL Paths)**: Sử dụng danh từ số nhiều, chữ thường và dấu gạch nối (kebab-case) nếu cần:
  - `/api/v1/documents`
  - `/api/v1/search/hybrid`
  - `/api/v1/verify/extract-claims`
- **Trường dữ liệu JSON (Payloads & Responses)**: Luôn sử dụng `snake_case` đồng nhất (Ví dụ: `{"claim_text": "...", "confidence_score": 0.95}`).

---

## 2. Quy chuẩn Cấu trúc Thư mục & Phân định Trách nhiệm (Folder & File Responsibility)

### 2.1. Nguyên tắc Đơn trách nhiệm (Single Responsibility Principle - SRP)
- Mỗi file hoặc module chỉ chịu trách nhiệm cho một khía cạnh nghiệp vụ duy nhất.
- **Tuyệt đối không tạo các file "nhồi nhét"**: Nghiêm cấm tạo các file gom tụ nhiều trách nhiệm như `ai_service.py`, `sourcecheck_service.py`, hoặc `rag_service.py`.
- Khi một file có nguy cơ vượt quá 300 dòng mã hoặc chứa nhiều hơn một trách nhiệm rõ ràng, lập tức phân tách thành các module con.

### 2.2. Phân định Trách nhiệm theo Tầng (Backend)
- `core/`: Chỉ chứa cấu hình hệ thống, logging, exceptions dùng chung và bảo mật cơ bản. **Tuyệt đối không đưa business logic vào core**.
- `models/`: Chỉ chứa các SQLAlchemy ORM models đại diện cho bảng CSDL quan hệ.
- `schemas/`: Chỉ chứa các Pydantic models phục vụ request/response validation và structured outputs. **Không trộn SQLAlchemy model với API schema**.
- `repositories/`: Chỉ chứa các câu truy vấn cơ sở dữ liệu (SELECT, INSERT, UPDATE). Không chứa logic suy luận AI.
- `services/`: Chứa toàn bộ nghiệp vụ. Mỗi tiểu lĩnh vực được tách vào một thư mục con riêng:
  - `services/ingestion/`: Tải và cắt văn bản.
  - `services/retrieval/`: Tìm kiếm vector, BM25 và hybrid.
  - `services/reranking/`: Xếp hạng lại bằng chứng.
  - `services/generation/`: Quản lý prompt và gọi LLM.
  - `services/verification/`: Bóc tách nhận định, đối soát, kiểm tra mâu thuẫn.
  - `services/citation/`: Định vị nguồn trích dẫn và tạo chú thích.
  - `services/guardrail/`: Kiểm tra độ trung thực và chống prompt injection.
- `api/routers/`: Chỉ tiếp nhận HTTP request, gọi service tương ứng và trả về `APIResponse`. Không viết thuật toán bên trong router.

---

## 3. Phong cách Mã nguồn (Code Style & Quality)

### 3.1. Python
- Tuân thủ nghiêm ngặt tiêu chuẩn **PEP 8**.
- **Type Hints là bắt buộc**: Mọi định nghĩa hàm đều phải khai báo kiểu dữ liệu cho tham số đầu vào và kiểu trả về (type annotations).
  ```python
  async def verify_claim(self, claim: ExtractedClaim, hits: List[SearchHit]) -> VerifiedClaimItem:
  ```
- Định dạng code bằng `black` và sắp xếp import bằng `isort` hoặc `ruff`.
- Không để lại code thừa, import không sử dụng, hoặc biến không dùng (no unused variables).

### 3.2. TypeScript / Frontend
- Tuân thủ chế độ kiểm tra nghiêm ngặt: `"strict": true` trong `tsconfig.json`.
- Tránh sử dụng kiểu `any`. Mọi dữ liệu trao đổi với API đều phải được định nghĩa interface trong `src/types/`.

---

## 4. Xử lý Lỗi & Ngoại lệ (Error Handling)

- Không bao giờ sử dụng khối `except Exception: pass` mà bỏ qua lỗi.
- Định nghĩa các lớp ngoại lệ nghiệp vụ thừa kế từ `SourceCheckException` trong `app/core/exceptions.py`.
- Tầng API sử dụng Exception Handlers tập trung để chuyển đổi các Domain Exceptions thành mã phản hồi HTTP có cấu trúc rõ ràng trong `APIResponse`:
  ```json
  {
    "success": false,
    "data": null,
    "message": "Chi tiết thông điệp lỗi thân thiện với người dùng",
    "error": {
      "code": "ENTITY_NOT_FOUND",
      "details": { "entity_id": "..." }
    }
  }
  ```

---

## 5. Quy chuẩn Kiểm thử (Testing Standards)

Mã nguồn mới chỉ được coi là hoàn thiện khi có bài kiểm thử đi kèm:
- **Unit Tests (`backend/tests/`)**:
  - Kiểm tra từng hàm/lớp độc lập.
  - Khi kiểm thử các dịch vụ phụ thuộc vào LLM hoặc Vector DB bên ngoài, **bắt buộc phải mock** (sử dụng `unittest.mock` hoặc `pytest-mock`) để bài test chạy nhanh và không tốn chi phí API token.
- **Lệnh chạy test chuẩn**:
  ```bash
  cd backend
  pytest tests/ -v
  ```
- Đảm bảo 100% test case trong bộ kiểm thử đều vượt qua trước khi tích hợp vào nhánh chính.

---

## 6. Quy chuẩn Tài liệu hóa (Documentation Standards)

- Mọi hàm public và class đều phải có **Docstrings** mô tả ngắn gọn mục đích, tham số và kết quả trả về.
- Khi có bất kỳ sự thay đổi nào về kiến trúc, lược đồ CSDL hoặc danh mục API, người phát triển có trách nhiệm cập nhật đồng bộ các tài liệu tương ứng trong thư mục `docs/`.
- Không lưu các ghi chú tạm thời, thông tin nhạy cảm (API Keys, mật khẩu) trong mã nguồn hoặc tài liệu.
