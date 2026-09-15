# TEAM — Day04, K4-L3B

**Làm nhóm.** Mỗi người tự viết và commit phần INDIVIDUAL của mình.

## Thông tin bài nộp

- Tên nhóm: 1Minh
- Người đại diện / MSSV: Võ Đức Tài / 2A202603007
- Tên repo: `K4-L3-DAY04-VoDucTai-2A202603007-PromptEngineeringToolCalling`
- URL repo, nhánh nộp, commit chốt: `https://github.com/HydrogenDrinker/K4-L3B-Day04-VoDucTai-2A202603007-Prompt-Engineering-Tool-Calling-Labs`
- Deadline áp dụng và link thông báo đổi hạn nếu có: 23:59 ngày 15/09/2026

## Thành viên

| Họ và tên | MSSV | GitHub | Vai trò và công việc | File/commit/PR |
|---|---|---|---|---|
| Võ Đức Tài | 2A202603007 | https://github.com/HydrogenDrinker | Trưởng nhóm / Toàn bộ phần việc | system_prompt.md, tools.yaml, eval_group.json, REPORT.md, chat.py |

## Nhận xét chung

- Kết quả và bằng chứng: Tiến trình cải tiến rõ ràng có bằng chứng run JSON thật và version_log.csv: v0 đạt 21/30 (70%) $\rightarrow$ v1 đạt 28/30 (93.33%) $\rightarrow$ v2 đạt 30/30 (100%) $\rightarrow$ v3 đạt 30/30 (100%). Bộ test case nhóm tự viết đạt 10/10 (100%). Bộ kiểm thử an toàn adversarial đạt 10/12 (83.33%).
- Thay đổi hiệu quả nhất: Thêm quy tắc xử lý thiếu thông tin (`clarify` dạng text/choice), thiết lập confirmation boundary nghiêm ngặt (hủy xác nhận cũ khi payload thay đổi), và hướng dẫn rõ ràng việc không hỏi lại khi người dùng đã chỉ định explicit `staging` / `production`.
- Giới hạn còn lại: Một số tình huống tấn công có mã XML/HTML giả lập (`<assistant>`) cần có thêm bước làm sạch dữ liệu đầu vào (input sanitization) ở tầng code ứng dụng.
- Cách phân công và tích hợp: Nhóm 1 thành viên tự lực triển khai toàn bộ luồng, thiết lập chu trình khoa học: phân tích lỗi $\rightarrow$ đặt giả thuyết $\rightarrow$ sửa đổi artifact $\rightarrow$ chạy eval $\rightarrow$ đo lường đối chiếu.

## INDIVIDUAL

### Võ Đức Tài — 2A202603007

- Phần việc và file/commit/PR: Phân tích 9 ca thất bại của v0; thiết kế và hoàn thiện `system_prompt.md`, `tools.yaml` qua các vòng v1–v3; tự soạn 10 ca kiểm thử (5 single + 5 multi) trong `eval_group.json`; sửa lỗi Unicode stdout trong `chat.py` và sinh transcript thực tế; hoàn thành `REPORT.md` và `version_log.csv`.
- Quyết định, khó khăn và cách xử lý: Ở vòng v1, sau khi thêm quy tắc môi trường mơ hồ, model bị over-triggering (hỏi lại clarify cả khi người dùng đã nói rõ staging). Quyết định xử lý: tinh chỉnh mô tả trong cả prompt và schema tools ở v2 để làm rõ "chỉ hỏi lại khi môi trường lạ/không xác định", đưa kết quả lên tuyệt đối 30/30.
- Điều đã học: Hiểu sâu sắc cơ chế định tuyến tool calling của mô hình ngôn ngữ lớn, kỹ thuật prompt engineering phân tách ranh giới hành động nhạy cảm, và tầm quan trọng của việc đánh giá dựa trên evidence thay vì đoán mò.
- AI/công cụ đã dùng và cách kiểm tra: Antigravity IDE, Python 3.10 (conda vin_lab03), OpenRouter API (gpt-4o-mini). Kiểm tra 100% bằng script `run_eval.py` tự động và live chat CLI.
- Thời điểm đã tự nộp URL repo chung trên VLearn: Đã kiểm tra và nộp trước 23:59 ngày 15/09/2026.
