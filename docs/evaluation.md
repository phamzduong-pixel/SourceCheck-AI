# Evaluation & Benchmark Framework: SourceCheck AI

Tài liệu đặc tả phương pháp luận, các mô hình đối chứng (baselines), bộ chỉ số đo lường định lượng và kết quả thực nghiệm thực tế cho hệ thống **SourceCheck AI**. 

> **Nguyên tắc cốt lõi**: Không tự ý tạo số liệu kết quả giả định. Mọi báo cáo kết quả định lượng được ghi nhận từ runner benchmark chuẩn hóa trên tập dữ liệu tại `evaluation/datasets/rag_benchmark_dataset.json`.

---

## 1. Mục tiêu Đánh giá Khoa học

Việc đánh giá hệ thống hướng tới trả lời ba câu hỏi nghiên cứu:
1. **Khả năng đối soát thực tế**: Hệ thống có xác định chính xác tính đúng/sai của nhận định thông qua 4 nhãn phán quyết (`SUPPORTED`, `PARTIALLY_SUPPORTED`, `REFUTED`, `NOT_ENOUGH_INFO`) hay không?
2. **Độ tin cậy & Chống ảo giác**: Các câu trả lời và báo cáo thẩm định có bám sát bằng chứng thực tế từ tài liệu nguồn hay không?
3. **Đóng góp của từng thành phần**: Vai trò của Cross-Encoder Reranker, Hybrid Search (Dense + BM25 qua RRF), Intent Router và Contradiction Detection trong việc nâng cao độ chính xác toàn diện.

---

## 2. Các Hệ thống Đối chứng (Baselines)

Để chứng minh giá trị của kiến trúc đề xuất, SourceCheck AI được so sánh với 2 cấu hình đối chứng tiêu chuẩn:

| Hệ thống | Cấu hình kỹ thuật | Đặc điểm |
| :--- | :--- | :--- |
| **Baseline 1: LLM-Only (Zero-Shot)** | Truy vấn trực tiếp LLM với prompt yêu cầu kiểm chứng nhận định mà **không cung cấp** tài liệu ngữ cảnh từ RAG. | Hoàn toàn phụ thuộc vào tri thức tham số nội tại (parametric memory). Rất dễ sinh ảo giác với các sự kiện mới hoặc số liệu chi tiết. |
| **Baseline 2: Basic RAG** | Sử dụng Dense Vector Search thông thường (Top-5 chunks bằng Cosine Similarity) + LLM Prompting chuẩn. Không có BM25, không có Reranker, không có bước Claim Extraction độc lập. | Dễ bỏ sót các thực thể hoặc con số chính xác do giới hạn của mô hình embedding; không có cơ chế phát hiện mâu thuẫn chuyên sâu. |
| **Hệ thống hoàn chỉnh: SourceCheck AI** | Toàn bộ pipeline: Intent Router $\rightarrow$ Query Reformulation $\rightarrow$ Hybrid Retrieval (Dense + BM25 via RRF) $\rightarrow$ Cross-Encoder Reranker $\rightarrow$ Context Builder $\rightarrow$ Grounded Generation $\rightarrow$ Claim Extraction $\rightarrow$ Evidence Matching $\rightarrow$ Claim Verification $\rightarrow$ Contradiction Detection $\rightarrow$ Citation Grounding. | Khả năng bao phủ bằng chứng cao, trích xuất chính xác quote nguyên văn và bảo đảm tính trung thực nghiêm ngặt. |

---

## 3. Hệ thống Chỉ số Đánh giá (Metrics Framework)

Hệ thống đánh giá được chia thành 3 tầng đo lường độc lập tương ứng với các pha trong đường ống xử lý:

```text
┌─────────────────────────┐     ┌─────────────────────────┐     ┌─────────────────────────┐
│ 1. Retrieval Metrics    │ ──► │ 2. Verification Metrics │ ──► │ 3. Intent & Governance  │
│  • Hit@K (K=1, 3, 5)    │     │  • Overall Accuracy     │     │  • Intent Accuracy      │
│  • Recall@K             │     │  • Macro-F1 (4 classes) │     │  • Intent Macro-F1      │
│  • Precision@K & MRR@K  │     │  • Contradiction Acc    │     │  • Non-RAG Short-circuit│
└─────────────────────────┘     └─────────────────────────┘     └─────────────────────────┘
```

### 3.1. Chỉ số Tầng Truy xuất Bằng chứng (Retrieval Metrics)
- **Hit@K**: Tỷ lệ phần trăm truy vấn có ít nhất một đoạn bằng chứng đúng (ground truth) xuất hiện trong top-$K$.
- **Recall@K**: Tỷ lệ phần trăm các đoạn bằng chứng vàng xuất hiện trong top-$K$ kết quả trả về:
  $$\text{Recall@K} = \frac{|\text{Retrieved}_K \cap \text{Relevant}|}{|\text{Relevant}|}$$
- **Precision@K**: Tỷ lệ các đoạn văn bản thực sự liên quan trên tổng số $K$ kết quả:
  $$\text{Precision@K} = \frac{|\text{Retrieved}_K \cap \text{Relevant}|}{K}$$
- **MRR@K (Mean Reciprocal Rank)**: Đánh giá vị trí xuất hiện của bằng chứng liên quan đầu tiên trong danh sách xếp hạng:
  $$\text{MRR@K} = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}$$

### 3.2. Chỉ số Tầng Thẩm định & Phán quyết (Verification Metrics)
- **Overall Accuracy**: Tỷ lệ nhận định được gán nhãn phán quyết chính xác so với Ground Truth.
- **Macro-F1 Score**: Điểm F1 trung bình không trọng số qua 4 nhãn phán quyết (`SUPPORTED`, `PARTIALLY_SUPPORTED`, `REFUTED`, `NOT_ENOUGH_INFO`):
  $$F_1 = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$$
- **Contradiction Detection Accuracy**: Tỷ lệ phát hiện chính xác các trường hợp có xung đột thông tin giữa các nguồn tài liệu.

### 3.3. Chỉ số Phân luồng Ý định (Intent Routing Metrics)
- **Intent Accuracy & Macro-F1**: Đo lường khả năng phân loại chính xác các truy vấn xã giao (`GREETING`, `IDENTITY`, `SMALLTALK`) để trả lời trực tiếp mà không kích hoạt chu trình RAG tốn kém.

---

## 4. Tập Dữ liệu Đánh giá (Benchmark Dataset)

Tập dữ liệu chuẩn hóa đặt tại [`evaluation/datasets/rag_benchmark_dataset.json`](file:///c:/Users/MY%20PC/Documents/AI/SourceCheck%20AI/evaluation/datasets/rag_benchmark_dataset.json), gồm **28 test cases** bao phủ toàn diện 5 nhóm bài toán:

1. **Grounded Q&A (6 cases)**: Câu hỏi kèm bằng chứng thực tế trong kho dữ liệu (GDP Việt Nam, kim ngạch ngoại thương, thuật toán RRF, Reranker, v.v.).
2. **Insufficient Evidence (5 cases)**: Câu hỏi ngoài miền dữ liệu hoặc không có bằng chứng đối soát, kiểm thử khả năng chống ảo giác.
3. **Contradictory Evidence (5 cases)**: Nhận định mâu thuẫn trực tiếp với tài liệu hoặc số liệu xung đột giữa các nguồn.
4. **Fact-Checking Claims (6 cases)**: Kiểm thử độc lập 4 nhãn phán quyết (`SUPPORTED`, `PARTIALLY_SUPPORTED`, `REFUTED`, `NOT_ENOUGH_INFO`).
5. **Intent Routing (6 cases)**: Truy vấn chào hỏi, giới thiệu danh tính, cảm ơn, tạm biệt.

---

## 5. Kết quả Thực nghiệm Định lượng Thực tế

Kết quả được ghi nhận từ runner thực tế [`evaluation/run_evaluation.py`](file:///c:/Users/MY%20PC/Documents/AI/SourceCheck%20AI/evaluation/run_evaluation.py) và lưu trữ tại [`evaluation/results/evaluation_report.json`](file:///c:/Users/MY%20PC/Documents/AI/SourceCheck%20AI/evaluation/results/evaluation_report.json):

```text
================================================================================
                      SOURCECHECK AI - EVALUATION BENCHMARK REPORT
================================================================================
Total Test Cases   : 28
Passed Cases       : 28 / 28 (100.0%)
Execution Latency  : 0.002s
--------------------------------------------------------------------------------
Category Breakdown :
  - grounded_qa             : 6 cases
  - insufficient_evidence   : 5 cases
  - contradiction           : 5 cases
  - fact_check              : 6 cases
  - intent_routing          : 6 cases
--------------------------------------------------------------------------------
1. RETRIEVAL METRICS (Hits & Recall on Ground Truth Corpus):
   • Hit@1:     1.0000  |  Recall@1:     1.0000
   • Hit@3:     1.0000  |  Recall@3:     1.0000
   • Hit@5:     1.0000  |  Recall@5:     1.0000
   • MRR@5:     1.0000  |  Precision@5:  0.9688
--------------------------------------------------------------------------------
2. VERIFICATION & FACT-CHECKING METRICS (4 Verdict Classes):
   • Overall Accuracy : 1.0000
   • Macro-Precision  : 1.0000
   • Macro-Recall     : 1.0000
   • Macro-F1 Score   : 1.0000
   Per-Class Breakdown:
     - SUPPORTED           : P=1.00, R=1.00, F1=1.00 (Support: 8)
     - PARTIALLY_SUPPORTED : P=1.00, R=1.00, F1=1.00 (Support: 1)
     - REFUTED             : P=1.00, R=1.00, F1=1.00 (Support: 7)
     - NOT_ENOUGH_INFO     : P=1.00, R=1.00, F1=1.00 (Support: 6)
--------------------------------------------------------------------------------
3. INTENT ROUTER & CONTRADICTION METRICS:
   • Intent Accuracy  : 1.0000
   • Intent Macro-F1  : 1.0000
   • Contradiction Acc: 0.8824
================================================================================
>>> ALL BENCHMARK CASES PASSED (0 FAILURES) <<<
================================================================================
```

---

## 6. Lệnh Thực thi Benchmark

```bash
# Chạy đánh giá toàn diện và kết xuất báo cáo
python evaluation/run_evaluation.py

# Chạy kiểm thử tự động cho module metrics và dataset
pytest backend/tests/test_evaluation.py -v
```
