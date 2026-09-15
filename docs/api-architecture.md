# API Architecture & Conventions: SourceCheck AI

Tài liệu định hướng kiến trúc, tiêu chuẩn thiết kế và quy ước giao tiếp API cho hệ thống **SourceCheck AI**. Tài liệu này đóng vai trò là kim chỉ nam cho việc phát triển và tích hợp giữa Frontend, Backend và các dịch vụ bên thứ ba.

---

## 1. Nguyên tắc Thiết kế Cốt lõi (Core Principles)

1. **Chuẩn RESTful**: Đặt tên tài nguyên bằng danh từ số nhiều (plural nouns), đại diện cho các thực thể dữ liệu rõ ràng. Sử dụng đúng phương thức HTTP:
   - `GET`: Truy xuất dữ liệu (an toàn, không thay đổi trạng thái server - idempotent).
   - `POST`: Tạo mới tài nguyên hoặc kích hoạt tác vụ tính toán phức tạp.
   - `PUT`: Cập nhật toàn bộ tài nguyên.
   - `PATCH`: Cập nhật một phần tài nguyên.
   - `DELETE`: Xóa tài nguyên.
2. **Phiên bản hóa rõ ràng (API Versioning)**: Mọi endpoint phục vụ nghiệp vụ đều bắt đầu bằng tiền tố `/api/v1/` để đảm bảo tính tương thích ngược khi nâng cấp hệ thống trong tương lai.
3. **Định dạng dữ liệu JSON đồng nhất**: Mọi Request Payload và Response Body đều sử dụng chuẩn `application/json` với mã hóa UTF-8.
4. **Không trạng thái (Statelessness)**: Mỗi request phải chứa đầy đủ thông tin cần thiết (headers, authentication tokens) để server xử lý độc lập.

---

## 2. Cấu trúc Phong bì Phản hồi Chuẩn (Unified Response Envelope)

Mọi phản hồi từ Backend đều được đóng gói trong một schema duy nhất `APIResponse[T]` để đảm bảo tính nhất quán cho phía Frontend khi phân tích kết quả:

### 2.1. Phản hồi Thành công (Success Response)
```json
{
  "success": true,
  "data": {
    "id": "a3b8e7c1-23d4-4f56-8a90-123456789abc",
    "status": "COMPLETED"
  },
  "message": "Operation completed successfully.",
  "error": null
}
```

### 2.2. Phản hồi Thất bại (Error Response)
```json
{
  "success": false,
  "data": null,
  "message": "Validation failed for the submitted input text.",
  "error": {
    "code": "VALIDATION_ERROR",
    "details": {
      "field": "text",
      "reason": "String should have at least 5 characters"
    }
  }
}
```

### 2.3. Phản hồi Phân trang (Paginated Response Envelope)
Đối với các danh sách dài (như lịch sử kiểm chứng, danh mục tài liệu), dữ liệu trong trường `data` tuân theo chuẩn `PaginatedResponse`:
```json
{
  "success": true,
  "data": {
    "items": [ ... ],
    "total": 120,
    "page": 1,
    "page_size": 20,
    "total_pages": 6
  },
  "message": null,
  "error": null
}
```

---

## 3. Quy ước Mã Trạng thái HTTP (HTTP Status Codes)

| Mã trạng thái | Tên quy ước | Ý nghĩa áp dụng trong SourceCheck AI |
| :--- | :--- | :--- |
| **200 OK** | Thành công | Yêu cầu truy vấn hoặc xử lý thành công (GET, POST xử lý dữ liệu). |
| **201 Created** | Đã tạo mới | Tài liệu hoặc phiên kiểm chứng mới được lưu trữ thành công. |
| **400 Bad Request** | Yêu cầu không hợp lệ | Dữ liệu đầu vào sai cấu trúc hoặc không thỏa mãn ràng buộc schema. |
| **401 Unauthorized** | Chưa xác thực | Thiếu token hoặc token xác thực không hợp lệ/hết hạn. |
| **403 Forbidden** | Không có quyền | Người dùng không có quyền truy cập vào tài nguyên được yêu cầu. |
| **404 Not Found** | Không tìm thấy | Bản ghi (document_id, request_id) không tồn tại trong cơ sở dữ liệu. |
| **422 Unprocessable Entity**| Lỗi kiểm định dữ liệu | FastAPI/Pydantic validation error khi request body thiếu trường bắt buộc. |
| **429 Too Many Requests** | Vượt quá giới hạn | Người dùng gọi API vượt quá hạn mức rate-limiting cho phép. |
| **500 Internal Error** | Lỗi máy chủ | Lỗi ngoại lệ chưa được xử lý hoặc dịch vụ bên ngoài (LLM/Vector DB) gặp sự cố. |

---

## 4. Định hướng Cấu trúc Nhóm Endpoints (Endpoint Roadmap)

Hệ thống phân chia toàn bộ API thành 6 nhóm router độc lập:

### 4.0. Authentication & User Management (`/api/v1/auth`)
- Mục đích: Đăng ký tài khoản, xác thực danh tính người dùng và cấp phát JWT token bảo mật.
- Endpoints cốt lõi:
  - `POST /api/v1/auth/register`: Đăng ký tài khoản người dùng mới (email + password).
    - **Request Body**:
      ```json
      {
        "email": "user@example.com",
        "password": "SecurePassword123",
        "full_name": "Nguyễn Văn A"
      }
      ```
    - **Response Body (`APIResponse[UserResponse]`)**:
      ```json
      {
        "success": true,
        "data": {
          "id": "c1f2b3a4-1234-5678-9abc-def012345678",
          "email": "user@example.com",
          "full_name": "Nguyễn Văn A",
          "role": "user",
          "is_active": true,
          "created_at": "2026-09-14T08:00:00Z"
        },
        "message": "Đăng ký tài khoản thành công."
      }
      ```
  - `POST /api/v1/auth/login`: Xác thực thông tin đăng nhập và cấp phát Bearer JWT token.
    - **Request Body**:
      ```json
      {
        "email": "user@example.com",
        "password": "SecurePassword123"
      }
      ```
    - **Response Body (`APIResponse[TokenResponse]`)**:
      ```json
      {
        "success": true,
        "data": {
          "access_token": "eyJhbGciOi...",
          "token_type": "bearer",
          "expires_in": 86400
        },
        "message": "Đăng nhập thành công."
      }
      ```
  - `GET /api/v1/auth/me`: Truy xuất thông tin profile của người dùng đang đăng nhập.
    - **Header**: `Authorization: Bearer <access_token>`
    - **Response Body (`APIResponse[UserResponse]`)**: Trả về dữ liệu an toàn, không chứa mật khẩu hay chuỗi băm `hashed_password`.
  - `GET /api/v1/auth/google/login`: Khởi tạo luồng xác thực Google OAuth 2.0.
    - **Query params**: `redirect: bool` (mặc định `false`; nếu `true` chuyển hướng HTTP 307 tới Google Consent).
    - **Response Body (`APIResponse[GoogleLoginResponse]`)**: Trả về `authorization_url` và mã chống CSRF `state`.
  - `GET /api/v1/auth/google/callback`: Nhận authorization code từ Google và cấp phát SourceCheck JWT.
    - **Query params**: `code: string`, `state: string`, `error?: string`.
    - **Xử lý an toàn**: Kiểm tra CSRF `state`, đối soát danh tính qua Google userinfo, liên kết tài khoản an toàn nếu email đã verified, không merge tùy tiện khi có xung đột.
    - **Response Body (`APIResponse[TokenResponse]`)**: Cấp phát SourceCheck JWT access token chuẩn bearer.

### 4.1. Health & Diagnostics (`/health`, `/ready`)
- Mục đích: Phục vụ giám sát hệ thống, bộ cân bằng tải và container orchestrator (Docker/Kubernetes).
- Endpoints định hướng:
  - `GET /health`: Liveness probe (trạng thái sống của tiến trình FastAPI).
  - `GET /ready`: Readiness probe (trạng thái kết nối Database, Redis, Vector DB).

### 4.2. Document Management (`/api/v1/documents`)
- Mục đích: Nạp và quản lý các nguồn tài liệu trong kho tri thức phục vụ đối soát.
- Endpoints định hướng:
  - `POST /api/v1/documents/ingest`: Tải lên văn bản/URL, phân tách chunks và lưu trữ.
  - `GET /api/v1/documents`: Liệt kê danh sách tài liệu trong hệ thống (có phân trang).
  - `GET /api/v1/documents/{document_id}`: Xem chi tiết tài liệu và danh sách chunks.
  - `DELETE /api/v1/documents/{document_id}`: Xóa tài liệu khỏi CSDL và Vector Store.

### 4.3. Search & Retrieval (`/api/v1/search`)
- Mục đích: Cung cấp khả năng tìm kiếm độc lập phục vụ kiểm tra hoặc tích hợp ngoài.
- Endpoints định hướng:
  - `POST /api/v1/search/hybrid`: Tìm kiếm lai kết hợp Dense Vector + BM25 bằng RRF.
  - `POST /api/v1/search/vector`: Tìm kiếm thuần theo độ tương đồng ngữ nghĩa.
  - `POST /api/v1/search/bm25`: Tìm kiếm thuần theo từ khóa/thực thể cố định.

### 4.4. Question Answering (`/api/v1/questions`)
- Mục đích: Cung cấp tính năng hỏi đáp có cơ sở dữ liệu (Grounded Q&A) và thẩm tra thực nghiệm qua pipeline AI 13 bước.
- **Yêu cầu bảo mật**: Bắt buộc phải có `Authorization: Bearer <access_token>` hợp lệ. Nếu thiếu hoặc token sai/hết hạn $\rightarrow$ trả về `401 Unauthorized`.
- Endpoints cốt lõi:
  - `POST /api/v1/questions/ask`: Đặt câu hỏi và nhận câu trả lời đã thẩm định kèm bằng chứng và trích dẫn chuẩn hóa.
    - **Header**: `Authorization: Bearer <access_token>` (Bắt buộc)
    - **Request Body**:
      ```json
      {
        "question": "Tăng trưởng GDP Việt Nam năm 2023 là bao nhiêu?",
        "top_k": 5,
        "search_mode": "hybrid"
      }
      ```
    - **Response Body (`APIResponse[FinalAnswerResponse]`)**:
      ```json
      {
        "success": true,
        "data": {
          "question": "Tăng trưởng GDP Việt Nam năm 2023 là bao nhiêu?",
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
              "content": "Tăng trưởng GDP cả năm 2023 của Việt Nam ước đạt 5.05%...",
              "score": 0.95
            }
          ],
          "citations": [
            {
              "citation_id": "cit-uuid-1",
              "claim_id": "claim_1",
              "evidence_id": "E1",
              "source_name": "Tổng cục Thống kê",
              "source_url": "https://gso.gov.vn/gdp-2023",
              "quote": "Tăng trưởng GDP cả năm 2023 của Việt Nam ước đạt 5.05%...",
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
          "metadata": {
            "footnotes_text": "[1] Tổng cục Thống kê (https://gso.gov.vn/gdp-2023)"
          }
        },
        "message": null,
        "error": null
      }
      ```
    - **Chế độ phản hồi an toàn**:
      - Nếu câu hỏi rỗng/prompt injection: Trả về trạng thái `status: "BLOCKED"`.
      - Nếu không có tài liệu: Trả về trạng thái `status: "INSUFFICIENT_EVIDENCE"`.
      - Tuyệt đối không để lộ exception stack trace của server ra client.


### 4.5. Fact-Checking Verification (`/api/v1/verify`)
- Mục đích: Đường ống thẩm định cốt lõi của SourceCheck AI.
- Endpoints:
  - `POST /api/v1/verify`: Kích hoạt toàn bộ quy trình: Bóc tách claim $\rightarrow$ Tìm kiếm bằng chứng $\rightarrow$ Phán quyết $\rightarrow$ Phát hiện mâu thuẫn $\rightarrow$ Gắn trích dẫn.
  - `POST /api/v1/verify/extract-claims`: Endpoint độc lập chỉ bóc tách các câu nhận định từ văn bản.
  - `GET /api/v1/verify/{request_id}`: Tra cứu lại báo cáo kết quả kiểm chứng đã thực hiện trước đó.
  - `GET /api/v1/verify/history`: Lấy danh sách lịch sử kiểm chứng của người dùng hiện tại.

### 4.6. Conversation History Management (`/api/v1/conversations`)
- Mục đích: Quản lý lịch sử hội thoại của người dùng, cô lập quyền sở hữu theo `user_id`, hỗ trợ cascade delete.
- Endpoints:
  - `GET /api/v1/conversations`: Liệt kê danh sách hội thoại của người dùng đã xác thực.
  - `POST /api/v1/conversations`: Tạo phiên hội thoại mới.
  - `GET /api/v1/conversations/{conversation_id}`: Lấy chi tiết lịch sử tin nhắn của một hội thoại.
  - `DELETE /api/v1/conversations/{conversation_id}`: Xóa hội thoại và toàn bộ tin nhắn liên quan (`CASCADE DELETE`).

### 4.7. System Dashboard & Analytics (`/api/v1/dashboard`)
- Mục đích: Cung cấp số liệu thống kê tổng hợp thực tế về hệ thống cho người dùng và quản trị viên.
- Endpoints:
  - `GET /api/v1/dashboard/stats`: Trả về tổng số documents, questions, conversations, verifications và phân bố phán quyết (`SUPPORTED`, `REFUTED`, `PARTIALLY_SUPPORTED`, `NOT_ENOUGH_INFO`).

---

## 5. Quy chuẩn Đặt tên & Định dạng (Naming Conventions)

- **URL Paths**: Dùng chữ thường (lowercase) và dấu gạch nối (kebab-case) nếu cần (Ví dụ: `/extract-claims`).
- **JSON Fields**: Dùng kiểu `snake_case` cho cả request body và response body (Ví dụ: `source_url`, `confidence_score`, `claim_text`).
- **HTTP Headers**: Sử dụng chuẩn `Kebab-Case` (Ví dụ: `Authorization: Bearer <token>`, `Content-Type: application/json`).
