# Evaluation & Benchmark Plan: SourceCheck AI

Tài liệu đặc tả phương pháp luận, các mô hình đối chứng (baselines), bộ chỉ số đo lường định lượng và kế hoạch thực nghiệm phân rã (Ablation Study) cho hệ thống **SourceCheck AI**. 

> **Nguyên tắc cốt lõi**: Không tự ý tạo số liệu kết quả giả định. Mọi báo cáo kết quả định lượng chỉ được ghi nhận sau khi thực thi runner benchmark trên tập dữ liệu chuẩn trong thư mục `evaluation/`.

---

## 1. Mục tiêu Đánh giá Khoa học

Việc đánh giá hệ thống hướng tới trả lời ba câu hỏi nghiên cứu:
1. **Khả năng đối soát thực tế**: Hệ thống có vượt trội hơn so với các phương pháp LLM truyền thống (Zero-shot) và RAG thông thường (Basic RAG) trong việc xác định tính đúng/sai của thông tin hay không?
2. **Độ tin cậy & Chống ảo giác**: Các câu trả lời và báo cáo thẩm định có bám sát bằng chứng thực tế hay không?
3. **Đóng góp của từng thành phần**: Việc bổ sung Cross-Encoder Reranker, Hybrid Search và Contradiction Detection đóng góp cụ thể bao nhiêu phần trăm vào độ chính xác tổng thể?

---

## 2. Các Hệ thống Đối chứng (Baselines)

Để chứng minh giá trị của kiến trúc đề xuất, SourceCheck AI được đặt lên bàn cân so sánh với 2 hệ thống đối chứng tiêu chuẩn:

| Hệ thống | Cấu hình kỹ thuật | Đặc điểm |
| :--- | :--- | :--- |
| **Baseline 1: LLM-Only (Zero-Shot)** | Truy vấn trực tiếp LLM (GPT-4o / Claude / Llama-3) với prompt yêu cầu kiểm chứng nhận định mà **không cung cấp** tài liệu ngữ cảnh nào từ RAG. | Hoàn toàn phụ thuộc vào tri thức tham số nội tại (parametric memory). Rất dễ sinh ảo giác với các sự kiện mới hoặc số liệu chi tiết. |
| **Baseline 2: Basic RAG** | Sử dụng Dense Vector Search thông thường (Top-5 chunks bằng Cosine Similarity) + LLM Prompting chuẩn. Không có BM25, không có Reranker, không có bước Claim Extraction độc lập. | Dễ bỏ sót các thực thể hoặc con số chính xác do giới hạn của mô hình embedding; không có cơ chế phát hiện mâu thuẫn chuyên sâu. |
| **Hệ thống đề xuất: SourceCheck AI** | Toàn bộ pipeline: Claim Extraction $\rightarrow$ Hybrid Retrieval (Dense + BM25 via RRF) $\rightarrow$ Cross-Encoder Reranker $\rightarrow$ Entailment Reasoning $\rightarrow$ Contradiction Detection $\rightarrow$ Citation Grounding. | Khả năng bao phủ bằng chứng cao, trích xuất chính xác quote nguyên văn và bảo đảm tính trung thực nghiêm ngặt. |

---

## 3. Hệ thống Chỉ số Đánh giá (Metrics Framework)

Hệ thống đánh giá được chia thành 3 tầng đo lường độc lập tương ứng với các pha trong đường ống xử lý:

```text
┌─────────────────────────┐     ┌─────────────────────────┐     ┌─────────────────────────┐
│ 1. Retrieval Metrics    │ ──► │ 2. Verification Metrics │ ──► │ 3. Generation Metrics   │
│  • Recall@K             │     │  • Claim Verif. F1      │     │  • Faithfulness         │
│  • Precision@K          │     │  • Stance Accuracy      │     │  • Answer Correctness   │
│  • MRR@K & NDCG@K       │     │  • Evidence Coverage    │     │  • Unsupported Rate     │
└─────────────────────────┘     └─────────────────────────┘     └─────────────────────────┘
```

### 3.1. Chỉ số Tầng Truy xuất Bằng chứng (Retrieval Metrics)

Đo lường năng lực của tầng RAG trong việc tìm đúng các đoạn văn bản chứa bằng chứng chân thực:

- **Recall@K**: Tỷ lệ phần trăm các đoạn bằng chứng vàng (ground truth evidence) xuất hiện trong top-$K$ kết quả trả về của hệ thống.
  $$\text{Recall@K} = \frac{|\text{Retrieved}_K \cap \text{Relevant}|}{|\text{Relevant}|}$$
- **Precision@K**: Tỷ lệ các đoạn văn bản thực sự liên quan trên tổng số $K$ kết quả trả về.
  $$\text{Precision@K} = \frac{|\text{Retrieved}_K \cap \text{Relevant}|}{K}$$
- **MRR@K (Mean Reciprocal Rank)**: Đánh giá vị trí xuất hiện của bằng chứng liên quan đầu tiên trong danh sách xếp hạng.

### 3.2. Chỉ số Tầng Thẩm định & Phán quyết (Verification Metrics)

Đo lường độ chính xác của logic suy luận và gán nhãn:

- **Claim Verification F1-Score**: Điểm F1 trung bình (Macro-F1) qua 3 nhãn phán quyết chính (`SUPPORTED`, `REFUTED`, `NOT_ENOUGH_INFO`):
  $$F_1 = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$$
- **Evidence Coverage**: Tỷ lệ phần trăm nhận định có ít nhất một bằng chứng hợp lệ hỗ trợ:
  $$\text{Evidence Coverage} = \frac{\text{Số Claim có bằng chứng xác đáng}}{\text{Tổng số Claim cần kiểm chứng}}$$
- **Unsupported Claim Rate (UCR)**: Tỷ lệ các nhận định bị kết luận mà không có bằng chứng kèm theo (Mục tiêu của SourceCheck AI là đưa chỉ số này tiệm cận $0\%$).

### 3.3. Chỉ số Tầng Tạo lập & Ngôn ngữ (Generation & Grounding Metrics)

Đo lường chất lượng của bản tóm tắt và lời giải thích:

- **Faithfulness (Độ trung thực)**: Tỷ lệ các câu khẳng định trong bản giải thích có thể suy ra được từ bằng chứng đã cung cấp (đo lường tự động thông qua Ragas framework). Ngăn ngừa việc mô hình tự ý bổ sung kiến thức ngoài.
- **Answer Correctness**: So sánh mức độ tương đồng ngữ nghĩa giữa câu kết luận của hệ thống với câu giải thích chuẩn mực do chuyên gia biên soạn (Ground Truth Reference).
- **Citation Precision / Recall**: Đánh giá tính chính xác của các thẻ trích dẫn `[1]`, `[2]` được chèn trong văn bản.

---

## 4. Kế hoạch Thử nghiệm Phân rã (Ablation Study Plan)

Để phân tích sâu vai trò của từng thành phần kỹ thuật, các kịch bản thực nghiệm sau sẽ được thiết lập:

| Thử nghiệm | Mô tả cấu hình biến thiên | Mục tiêu đo lường |
| :--- | :--- | :--- |
| **Ablation 1: Reranker Effect** | So sánh pipeline khi **BẬT** vs **TẮT** Cross-Encoder Reranker. | Đo lường mức tăng của Precision@K và Claim Verification F1 khi có tầng tái xếp hạng sâu. |
| **Ablation 2: Retrieval Mode** | So sánh 3 chế độ: (1) Dense Vector Only, (2) BM25 Only, (3) Hybrid RRF. | Chứng minh ưu thế vượt trội của Hybrid Search đối với các thực thể số và tên riêng. |
| **Ablation 3: Claim Decomposition** | So sánh việc đưa cả bài văn dài vào prompt vs bóc tách từng Claim độc lập. | Định lượng mức độ cải thiện tính bao phủ bằng chứng và giảm thiểu bỏ sót thông tin. |
| **Ablation 4: Contradiction Check** | So sánh độ chính xác tổng thể khi có và không có bộ phát hiện mâu thuẫn chéo. | Đánh giá khả năng phát hiện tin tức ngụy tạo tinh vi chứa thông tin tự triệt tiêu. |

---

## 5. Quy trình Thực thi Thực nghiệm (Execution Protocol)

1. **Chuẩn bị Dữ liệu (Datasets)**: Sử dụng các tập dữ liệu kiểm chứng chuẩn hóa (như FEVER, MultiFC, hoặc tập dữ liệu tin tức tiếng Việt do nhóm nghiên cứu biên soạn) đặt trong `evaluation/datasets/`.
2. **Chạy Thực nghiệm Độc lập (Independent Run)**: Thực thi runner scripts trong `evaluation/experiments/` để gọi pipeline với các cấu hình định trước.
3. **Thu thập & Ghi nhận (Result Logging)**: Mọi kết quả định lượng, tham số mô hình, độ trễ phản hồi (latency tính bằng giây) và ma trận nhầm lẫn (Confusion Matrix) được lưu trữ nguyên vẹn dưới định dạng JSON/CSV trong thư mục `evaluation/results/`.
