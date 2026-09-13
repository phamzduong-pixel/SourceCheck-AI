# Evaluation Framework

Thư mục phục vụ công tác nghiên cứu, thực nghiệm, benchmark, evaluation và ablation study cho hệ thống SourceCheck AI.

## Cấu trúc thư mục

- `datasets/`: Chứa các bộ dữ liệu thẩm định thực tế (ground-truth datasets, test claims, reference evidence).
- `baselines/`: Các mô hình nền tảng, mô hình đối chứng dùng để so sánh hiệu năng (zero-shot LLM, standard BM25, standard RAG).
- `metrics/`: Mã nguồn tính toán các chỉ số đo lường hiệu năng (Accuracy, Precision, Recall, F1, Faithfulness, Citation Precision).
- `experiments/`: Kịch bản và cấu hình chạy các bài thử nghiệm, kiểm tra độ ổn định và ablation study.
- `results/`: Kết quả đầu ra từ các lần chạy benchmark, báo cáo so sánh định lượng và log thực nghiệm.
