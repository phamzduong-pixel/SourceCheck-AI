# SourceCheck AI — Demo Verification Scenarios

## Demo source

Use the existing seeded source from the verification E2E fixture:

- **Title:** Báo cáo Kinh tế - Xã hội 2023
- **Publisher:** Tổng cục Thống kê
- **Source URL:** `https://gso.gov.vn/gdp-2023`
- **Content:** “Theo Tổng cục Thống kê, tăng trưởng GDP Việt Nam năm 2023 đạt 5.05%. Kim ngạch xuất nhập khẩu hàng hóa năm 2023 đạt 683 tỷ USD.”
- **Evidence location:** one ingested passage (chunk 0); page number is not supplied by the API for this mock source.

The passage provides two independently verifiable facts: GDP growth (5.05%) and 2023 goods import/export turnover (683 billion USD).

## Five demo questions

| # | Question | Expected scenario | Evidence to inspect |
|---|---|---|---|
| 1 | Tăng trưởng GDP Việt Nam năm 2023 đạt bao nhiêu phần trăm? | `SUPPORTED` | Quote containing “5.05%”; source title and URL; citation `[1]`. |
| 2 | Kim ngạch xuất nhập khẩu hàng hóa năm 2023 đạt bao nhiêu? | `SUPPORTED` | Quote containing “683 tỷ USD”; the same source, with a real citation. |
| 3 | GDP năm 2023 đạt 5.05% và kim ngạch xuất nhập khẩu đạt 700 tỷ USD, đúng không? | `PARTIALLY_SUPPORTED` | GDP portion supported; the 700 billion USD portion is not supported by the passage. Inspect claim-to-evidence mapping and coverage. |
| 4 | GDP Việt Nam năm 2023 đạt 12.5%, đúng không? | `REFUTED` | Evidence quote states 5.05%, contradicting 12.5%; inspect the refuting evidence and citation. |
| 5 | Tăng trưởng GDP năm 2023 — hãy kiểm tra claim không có trong tài liệu | `NOT_ENOUGH_INFO` | The retrieved source does not support the fixture claim; no fabricated citation or quote; coverage reflects missing evidence. |

## What to verify in the UI/API

For every request, inspect the answer, extracted claims, claim verdict, claim-to-evidence mapping, citation quote/source, evidence coverage, and `request_id`. Then open `/api/v1/verify/{request_id}` and confirm the persisted report matches the answer response. In the Chat UI, confirm the same claims, verdicts, citations, quotes, source URL, and coverage are rendered.

## Validation note

The existing end-to-end test executes ingestion → `/questions/ask` → persistence → `/verify/{request_id}` with the source above and validates answer, claims, evidence, citation, coverage, and persisted provenance. The deterministic local mock provider is intentionally conservative: it can produce grounded/insufficient answers, while `REFUTED` and mixed `PARTIALLY_SUPPORTED` outcomes are also covered by the existing claim-verifier and guardrail tests. No verdict is hardcoded in the frontend or production pipeline.
