# 📊 BÁO CÁO THU HOẠCH NGHIỆM THU BÀI LAB 3 (BƯỚC 3 — SUBMISSION ARTIFACT)

> **Họ và Tên Học viên:** Bùi Thị Ngọc Trân 
> **Mã Sinh Viên / Mã Học viên:** 2A202602529  
> **Chủ đề Lựa chọn:** Trợ lý Dịch vụ Khách hàng VinBus

---

## 1. BẢNG CHẤM ĐIỂM AGENTIC FIT SCORING MATRIX (ĐÁNH GIÁ CHỦ ĐỀ)

| Tiêu chí Đánh giá | Mức độ (1 - 5) | Giải trình chi tiết lý do chọn điểm |
| :--- | :---: | :--- |
| **1. Multi-step Reasoning** | 4/ 5 | Agent phải nhận diện ý định của hành khách, kiểm tra các thông tin bắt buộc, lựa chọn công cụ phù hợp, xử lý kết quả Observation và tổng hợp câu trả lời cuối cùng. |
| **2. Tool Interaction** | 5/ 5 | Hệ thống cần tương tác với MCP Server để tra cứu tuyến xe hoặc đăng ký vé tháng. Chatbot Baseline không thể thực hiện các nghiệp vụ này vì không được cung cấp Tool. |
| **3. Dynamic Decision** | 4/ 5 | Agent phải quyết định gọi search_bus_route hoặc register_monthly_pass tùy theo yêu cầu. Các tham số cũng thay đổi động: vé một tuyến cần route_id, còn vé liên tuyến không cần route_id. |
| **4. Long Horizon Goal** | 3/ 5 | Agent phải duy trì mục tiêu từ yêu cầu ban đầu đến khi nhận Observation và trả kết quả, nhưng nghiệp vụ hiện tại thường chỉ kéo dài một đến hai bước xử lý. |
| **TỔNG ĐIỂM AGENTIC FIT** | **16/ 20** | *Bài toán phù hợp triển khai Agentic System vì tổng điểm lớn hơn 12/20.* |

---

## 2. TRÍCH XUẤT KẾT QUẢ WATERFALL TRACE LOG (SAU KHI CHẠY TEST SUITE TRÊN API THẬT)

> ⚠️ **YÊU CẦU NGHIỆM THU:** Mở tệp `.env` điền `GEMINI_API_KEY` (hoặc `OPENAI_API_KEY`) để kết nối LLM thật trước khi thực thi `python src/app.py --all`. Bài nộp chỉ dùng Mock Offline Provider sẽ không đạt điểm nghiệm thực tế.

Dán 1 đoạn trích xuất log tiêu biểu từ file `docs/trace_waterfall.json` sinh ra từ phản hồi LLM API thật:

```json
[
  {
    "step": 1,
    "query": "Đăng ký vé tháng một tuyến E01 cho Nguyễn Văn An, số điện thoại 0912345678.",
    "action_type": "TOOL_EXECUTION",
    "thought": "OpenAI quyết định gọi công cụ 'register_monthly_pass' với tham số: {\"full_name\": \"Nguyễn Văn An\", \"phone\": \"0912345678\", \"ticket_type\": \"one_route\", \"route_id\": \"E01\"}",
    "tool_name": "register_monthly_pass",
    "arguments": {
      "full_name": "Nguyễn Văn An",
      "phone": "0912345678",
      "ticket_type": "one_route",
      "route_id": "E01"
    },
    "observation": {
      "status": "SUCCESS",
      "registration_id": "VB-0001",
      "message": "Đăng ký vé tháng VinBus thành công.",
      "data": {
        "registration_id": "VB-0001",
        "full_name": "Nguyễn Văn An",
        "phone": "0912345678",
        "ticket_type": "one_route",
        "route_id": "E01",
        "application_status": "RECEIVED"
      }
    },
    "latency_ms": 1135.91,
    "model": "gpt-4o-mini",
    "usage": {
      "input_tokens": 820,
      "output_tokens": 39,
      "total_tokens": 859
    }
  }
]
```
### Nhận xét Waterfall Trace

Agent đã nhận diện đúng yêu cầu đăng ký vé tháng một tuyến và ánh xạ cụm từ “một tuyến” thành `ticket_type="one_route"`. Agent lựa chọn Tool `register_monthly_pass`, truyền đầy đủ họ tên, số điện thoại và mã tuyến E01. MCP Server trả về Observation có trạng thái `SUCCESS` và mã hồ sơ `VB-0001`. Kết quả cho thấy Native Tool Calling đã được thực hiện bằng OpenAI `gpt-4o-mini`, với token usage được ghi nhận trong trace. Sau khi MCP Server trả về Observation, Agent gửi yêu cầu ban đầu, tên Tool, arguments và Observation trở lại LLM để tổng hợp Final Answer. Nếu lượt tổng hợp gặp lỗi, hệ thống sử dụng `build_final_answer()` làm phương án dự phòng. Trace ghi riêng thời gian quyết định Tool và thời gian tổng hợp câu trả lời.

---

## 3. TỔNG KẾT KẾT QUẢ NGHIỆM THU & NỘP BÀI

- [x] Đã điền API Key thật trong `.env` và xác nhận Agent chạy mượt mà trên LLM API thật (Gemini/OpenAI).
- **Tổng số Test Cases đã chạy thành công:** 5 / 5 test cases.
- **Số lượt gọi Tool qua MCP Server chính xác:** 4 lượt.
- **Kết quả đẩy Repo nộp bài:** [x] Đã Commit và Push mã nguồn thành công lên GitHub cá nhân.

---

> ✅ **HOÀN TẤT NỘP BÀI:** Sao chép đường link GitHub Repository cá nhân của bạn và dán vào ô nộp bài trên hệ thống LMS VLearn để hoàn tất Bài Lab 3!
