"""
🚀 CORE AGENT APPLICATION (DAY 03: CHATBOT VS REACT AGENT)
Thực thi so sánh giữa Chatbot Baseline (Cấp 2) và ReAct Agent kết nối MCP Server (Cấp 3).

So sánh:
1. Chatbot Baseline không có công cụ.
2. ReAct Agent sử dụng Native Tool Calling và MCP Server.

Nghiệp vụ:
- Tra cứu lộ trình tuyến xe VinBus.
- Đăng ký vé tháng VinBus.
"""

import json
import os
import sys
import time
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from mcp_server import MCPVinBusServer
from prompts import (
    CHATBOT_BASELINE_PROMPT,
    REACT_AGENT_SYSTEM_PROMPT,
    MAX_ITERATIONS
)
from providers import get_llm_provider

load_dotenv()

def load_test_cases():
    """Tải danh sách 5 test cases từ config/test_cases.json hoặc config/test_cases.example.json"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")
    if not os.path.exists(config_path):
        example_path = os.path.join(base_dir, "config", "test_cases.example.json")
        if os.path.exists(example_path):
            print("⚠️ [CONFIG NOTICE]: Chưa thấy file 'config/test_cases.json'. Đang dùng mẫu 'config/test_cases.example.json'.")
            print("👉 Hãy chạy: copy config/test_cases.example.json config/test_cases.json và viết test cases theo đề tài của bạn!\n")
            config_path = example_path
        else:
            config_path = "test_cases.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_waterfall_trace(trace_data: list):
    """Ghi vết log Waterfall Trace Log ra file docs/trace_waterfall.json"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    trace_path = os.path.join(docs_dir, "trace_waterfall.json")
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(trace_data, f, ensure_ascii=False, indent=2)
    print(f"📊 [OBSERVABILITY]: Đã lưu {len(trace_data)} sự kiện Waterfall Trace tại '{trace_path}'!")


def run_baseline_chatbot(user_query: str, provider):
    """Chạy Chatbot gốc (Cấp 2) không có công cụ gọi Tool"""
    print(f"\n💬 [CHATBOT BASELINE] Câu hỏi: {user_query}")
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    print(f"🤖 Chatbot phản hồi:\n{response}")

def build_final_answer(tool_name: str, observation: dict) -> str:
    """Tổng hợp Observation của MCP Server thành câu trả lời VinBus."""

    status = observation.get("status")

    if status == "SUCCESS":
        if tool_name == "search_bus_route":
            routes = observation.get("data", [])

            if not routes:
                return "Không tìm thấy tuyến VinBus phù hợp."

            answer_lines = [
                observation.get(
                    "message",
                    f"Tìm thấy {len(routes)} tuyến phù hợp."
                )
            ]

            for route in routes:
                stops = " → ".join(
                    route.get("journey_stops", [])
                )

                answer_lines.append(
                    (
                        f"- Tuyến {route.get('route_id', '')}: "
                        f"{route.get('route_name', '')}\n"
                        f"  Lộ trình: {stops}\n"
                        f"  Giờ hoạt động: "
                        f"{route.get('operating_hours', 'Chưa có dữ liệu')}\n"
                        f"  Tần suất: "
                        f"{route.get('frequency', 'Chưa có dữ liệu')}"
                    )
                )

            return "\n".join(answer_lines)

        if tool_name == "register_monthly_pass":
            registration = observation.get("data", {})

            ticket_labels = {
                "one_route": "Vé tháng một tuyến",
                "all_routes": "Vé tháng liên tuyến"
            }

            ticket_type = registration.get("ticket_type", "")
            ticket_label = ticket_labels.get(
                ticket_type,
                ticket_type
            )

            route_id = registration.get("route_id")
            route_text = (
                f"\nTuyến đăng ký: {route_id}"
                if route_id
                else ""
            )

            return (
                f"{observation.get('message', 'Đăng ký thành công.')}\n"
                f"Mã hồ sơ: "
                f"{observation.get('registration_id', '')}\n"
                f"Hành khách: "
                f"{registration.get('full_name', '')}\n"
                f"Loại vé: {ticket_label}"
                f"{route_text}\n"
                f"Trạng thái: "
                f"{registration.get('application_status', '')}"
            )

        return observation.get(
            "message",
            "Công cụ đã xử lý yêu cầu thành công."
        )

    if status == "NOT_FOUND":
        return observation.get(
            "message",
            "Không tìm thấy dữ liệu phù hợp."
        )

    if status in [
        "INVALID_INPUT",
        "INVALID_ARGUMENTS"
    ]:
        return observation.get(
            "message",
            observation.get(
                "error",
                "Thông tin đầu vào chưa hợp lệ."
            )
        )

    if status == "UNKNOWN_TOOL":
        return observation.get(
            "error",
            "Agent đã yêu cầu một công cụ không tồn tại."
        )

    if status == "EXECUTION_ERROR":
        return (
            "Không thể xử lý yêu cầu do lỗi công cụ: "
            f"{observation.get('error', 'Không xác định')}"
        )

    return (
        "Phản hồi từ công cụ: "
        f"{json.dumps(observation, ensure_ascii=False)}"
    )

def run_react_agent(user_query: str, provider, mcp_server: MCPVinBusServer) -> list:
    """
    [REACT AGENT LOOP] Thực thi vòng lặp Thought -> Action -> Observation với MCP Server
    Trả về danh sách trace log của phiên thực thi.
    """
    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")
    
    step = 0
    trace_logs = []
    tools_list = mcp_server.list_tools()
    
    while step < MAX_ITERATIONS:
        step += 1
        step_start_time = time.time()
        print(f"\n--- 🔄 Vòng lặp ReAct Loop (Step {step}/{MAX_ITERATIONS}) ---")
        
        # Gọi LLM với Native Tool Calling Specs
        llm_response = provider.generate_with_tools(user_query, tools_list, system_prompt=REACT_AGENT_SYSTEM_PROMPT)
        latency_ms = round((time.time() - step_start_time) * 1000, 2)
        
        thought = llm_response.get("thought", "Đang suy luận...")
        print(f"🧠 [Thought]: {thought}")
        
        # Trường hợp 1: LLM quyết định trả lời bằng văn bản trực tiếp
        if llm_response.get("type") == "text":
            final_content = llm_response.get("content", "")
            print(f"🏁 [Final Answer]: {final_content}")
            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "FINAL_ANSWER",
                "thought": thought,
                "output": final_content,
                "latency_ms": latency_ms
            })
            break
            
        # Trường hợp 2: LLM đề xuất gọi Tool (Action)
        elif llm_response.get("type") == "tool_call":
            tool_name = llm_response.get("tool_name")
            arguments = llm_response.get("arguments", {})
            
            print(f"🛠️ [Action Proposed]: {tool_name}({arguments})")
            
            # Thực thi Tool qua MCP Server
            mcp_result = (
                mcp_server.call_tool(tool_name, arguments)
                or {}
            )
            obs_data = mcp_result.get("result", {})
            
            if not obs_data:
                print("👁️ [Observation từ MCP Server]: {}")
                print(
                    "⚠️ MCP Server chưa trả về dữ liệu. "
                    "Hãy hoàn thiện call_tool() trong src/mcp_server.py."
                )
                final_answer = (
                    "Chưa thể xử lý yêu cầu vì MCP Server "
                    "không trả về dữ liệu."
                )
            else:
                obs_str = json.dumps(
                    obs_data,
                    ensure_ascii=False
                )
                print(
                    f"👁️ [Observation từ MCP Server]: {obs_str}"
                )

                final_answer = build_final_answer(
                    tool_name,
                    obs_data
                )
            
            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "TOOL_EXECUTION",
                "tool_name": tool_name,
                "arguments": arguments,
                "observation": obs_data,
                "latency_ms": latency_ms
            })
            
            # Kết thúc vòng lặp sau khi hoàn tất Observation và xuất Final Answer
            print(f"🧠 [Thought]: Đã nhận được dữ liệu từ MCP Server. Tổng hợp kết quả phản hồi.")
            print(f"🏁 [Final Answer]: {final_answer}")

            final_status = obs_data.get(
                "status",
                "NO_DATA"
            ) if obs_data else "NO_DATA"

            final_thought = (
                "Đã tổng hợp phản hồi từ MCP Server "
                f"với trạng thái {final_status}."
            )
            trace_logs.append({
                "step": step + 1,
                "query": user_query,
                "action_type": "FINAL_ANSWER",
                "thought": final_thought,
                "output": final_answer,
                "latency_ms": 10.0
            })
            break

    return trace_logs


if __name__ == "__main__":
    print("==========================================================")
    print("🚌 TRỢ LÝ DỊCH VỤ KHÁCH HÀNG VINBUS")
    print("CHATBOT BASELINE VS REACT AGENT")
    print("==========================================================")
    
    provider = get_llm_provider()
    mcp_server = MCPVinBusServer()
    
    print(f"🔌 LLM Provider: {provider.__class__.__name__}")
    print(f"🌐 MCP Server: {mcp_server.server_name}\n")
    
    tests = load_test_cases()
    print(f"✅ Đã tải thành công {len(tests)} Test Cases thử nghiệm.\n")
    
    if "--interactive" in sys.argv:
        print("🎮 [INTERACTIVE MODE] Trò chuyện với trợ lý VinBus:")
        print("💡 Gợi ý câu hỏi:")
        print(
            "   - Câu hỏi chung: "
            "'VinBus sử dụng loại phương tiện nào?'"
        )
        print(
            "   - Tra cứu tuyến: "
            "'Tìm tuyến từ VinUni đến Bến xe Mỹ Đình'"
        )
        print(
            "   - Đăng ký vé: "
            "'Đăng ký vé tháng một tuyến E01 cho "
            "Nguyễn Văn An, số điện thoại 0912345678'"
        )
        print("   - Gõ 'exit' hoặc 'quit' để kết thúc.\n")
        while True:
            try:
                user_input = input("👤 Hành khách hỏi: ").strip()
                if not user_input or user_input.lower() in ["exit", "quit"]:
                    print("\n👋 Cảm ơn bạn đã sử dụng trợ lý VinBus.")
                    break
                logs = run_react_agent(user_input, provider, mcp_server)
                save_waterfall_trace(logs)
            except (KeyboardInterrupt, EOFError):
                print("\n👋 Đã thoát phiên tương tác.")
                break
    elif "--all" in sys.argv:
        print("🚀 [TEST SUITE MODE] Kiểm tra 5 Test Cases:")
        completed_count = 0
        todo_count = 0
        all_traces = []
        
        for tc in tests:
            print(f"\n==================================================")
            print(f"🧪 [{tc['id']}] Loại test: {tc['type']} (Độ phức tạp: {tc['complexity']})")
            print(f"📌 Kỳ vọng: {tc['expected_behavior']}")
            
            if tc["question"].strip().startswith("TODO"):
                print(f"⏸️ [CHƯA KÍCH HOẠT - ĐANG LÀ TODO]:")
                print(f"   {tc['question']}")
                print(f"   👉 Hãy mở file 'config/test_cases.json' để viết câu hỏi thực tế cho Test Case này!")
                todo_count += 1
            else:
                logs = run_react_agent(tc["question"], provider, mcp_server)
                all_traces.extend(logs)
                completed_count += 1
                
        print(f"\n==================================================")
        print(f"📊 [KẾT QUẢ TEST SUITE]: Đã thực thi {completed_count}/{len(tests)} Test Cases | {todo_count} Test Cases đang chờ điền câu hỏi (TODO)")
        if all_traces:
            save_waterfall_trace(all_traces)
        print(f"💡 Để trò chuyện trực tiếp từng câu: Chạy 'python src/app.py --interactive'")
    else:
        # Chế độ mặc định khi chỉ gõ 'python src/app.py'
        print("ℹ️ HƯỚNG DẪN SỬ DỤNG CHƯƠNG TRÌNH:")
        print("  1. Chat trực tiếp liên tục:   python src/app.py --interactive")
        print("  2. Chạy toàn bộ Test Cases:    python src/app.py --all\n")
        
        sample_query = tests[1]["question"]

        print(
            "--- 🏁 DEMO TEST CASE TRA CỨU TUYẾN VINBUS ---"
        )

        logs = run_react_agent(
            sample_query,
            provider,
            mcp_server
        )

        save_waterfall_trace(logs)

        print(
            "\n💡 Chạy 'python src/app.py --interactive' "
            "để trò chuyện trực tiếp."
        )
        