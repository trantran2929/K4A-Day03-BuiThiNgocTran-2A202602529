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
from typing import Callable, Optional
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
    OBSERVATION_SYNTHESIS_PROMPT,
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


def run_baseline_chatbot(
    user_query: str,
    provider
) -> dict:
    """
    Chạy Chatbot Baseline chỉ bằng LLM.

    Chatbot không nhận Tool Schema và không gọi MCP Server.
    """

    print(
        f"\n💬 [CHATBOT BASELINE] "
        f"Câu hỏi: {user_query}"
    )

    start_time = time.time()

    response = provider.generate(
        user_query,
        system_prompt=CHATBOT_BASELINE_PROMPT
    )

    latency_ms = round(
        (time.time() - start_time) * 1000,
        2
    )

    result = {
        "mode": "CHATBOT_BASELINE",
        "query": user_query,
        "output": response,
        "tool_called": False,
        "latency_ms": latency_ms,
        "model": getattr(
            provider,
            "model_name",
            provider.__class__.__name__
        )
    }

    print(f"🤖 Chatbot phản hồi:\n{response}")
    print("🛠️ Tool được gọi: Không")
    print(f"⏱️ Latency: {latency_ms} ms")

    return result

def extract_final_answer(trace_logs: list) -> str:
    """Lấy câu trả lời cuối cùng từ trace của ReAct Agent."""

    for event in reversed(trace_logs):
        if event.get("action_type") == "FINAL_ANSWER":
            return event.get(
                "output",
                "Không có câu trả lời."
            )

    return "Không tìm thấy Final Answer trong trace."

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

def synthesize_observation_with_llm(
    provider,
    user_query: str,
    tool_name: str,
    arguments: dict,
    observation: dict
) -> tuple[str, str]:
    """
    Gửi Observation trở lại LLM để tạo Final Answer.

    Trả về:
    - final_answer: câu trả lời cuối.
    - synthesis_source: nguồn tổng hợp.
    """

    observation_prompt = (
        "YÊU CẦU BAN ĐẦU CỦA NGƯỜI DÙNG:\n"
        f"{user_query}\n\n"
        "CÔNG CỤ ĐÃ GỌI:\n"
        f"{tool_name}\n\n"
        "THAM SỐ GỌI CÔNG CỤ:\n"
        f"{json.dumps(arguments, ensure_ascii=False, indent=2)}"
        "\n\n"
        "OBSERVATION TỪ MCP SERVER:\n"
        f"{json.dumps(observation, ensure_ascii=False, indent=2)}"
        "\n\n"
        "Hãy tạo câu trả lời cuối cùng cho người dùng."
    )

    try:
        llm_answer = provider.generate(
            observation_prompt,
            system_prompt=OBSERVATION_SYNTHESIS_PROMPT
        )

        error_markers = [
            "[OpenAI Exception]",
            "[Gemini Exception]",
            "[OpenAI Error]",
            "[Gemini Error]"
        ]

        has_provider_error = any(
            marker in llm_answer
            for marker in error_markers
        )

        if (
            not llm_answer
            or not llm_answer.strip()
            or has_provider_error
        ):
            fallback_answer = build_final_answer(
                tool_name,
                observation
            )

            return (
                fallback_answer,
                "DETERMINISTIC_FALLBACK"
            )

        return (
            llm_answer.strip(),
            "LLM_OBSERVATION_SYNTHESIS"
        )

    except Exception:
        fallback_answer = build_final_answer(
            tool_name,
            observation
        )

        return (
            fallback_answer,
            "DETERMINISTIC_FALLBACK"
        )
    
def run_react_agent(
    user_query: str,
    provider,
    mcp_server: MCPVinBusServer,
    event_callback: Optional[Callable[[dict], None]] = None
) -> list:
    """
    [REACT AGENT LOOP] Thực thi vòng lặp Thought -> Action -> Observation với MCP Server
    Trả về danh sách trace log của phiên thực thi.
    """
    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")
    
    step = 0
    trace_logs = []
    tools_list = mcp_server.list_tools()

    def emit(stage: str, message: str, **details):
        """Phát sự kiện tiến trình cho giao diện nếu có callback."""
        if event_callback:
            event_callback({
                "stage": stage,
                "message": message,
                **details
            })
    
    while step < MAX_ITERATIONS:
        step += 1
        step_start_time = time.time()
        print(f"\n--- 🔄 Vòng lặp ReAct Loop (Step {step}/{MAX_ITERATIONS}) ---")
        
        # Gọi LLM với Native Tool Calling Specs
        llm_response = provider.generate_with_tools(user_query, tools_list, system_prompt=REACT_AGENT_SYSTEM_PROMPT)
        latency_ms = round((time.time() - step_start_time) * 1000, 2)
        
        thought = llm_response.get("thought", "Đang suy luận...")
        print(f"🧠 [Thought]: {thought}")
        usage = llm_response.get("usage", {})
        model_name = llm_response.get(
            "model",
            getattr(provider, "model_name", "unknown")
        )
        emit(
            "reasoning",
            thought,
            usage=usage,
            model=model_name
        )
        
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
                "latency_ms": latency_ms,
                "model": model_name,
                "usage": usage
            })
            emit("final", final_content)
            break
            
        # Trường hợp 2: LLM đề xuất gọi Tool (Action)
        elif llm_response.get("type") == "tool_call":
            tool_name = llm_response.get("tool_name")
            arguments = llm_response.get("arguments", {})
            
            print(f"🛠️ [Action Proposed]: {tool_name}({arguments})")
            emit(
                "action",
                f"Gọi công cụ {tool_name}",
                tool_name=tool_name,
                arguments=arguments
            )
            
            # Thực thi Tool qua MCP Server
            mcp_result = (
                mcp_server.call_tool(tool_name, arguments)
                or {}
            )
            obs_data = mcp_result.get("result", {})
            
            synthesis_source = "NO_DATA"
            synthesis_latency_ms = 0.0

            if not obs_data:
                print(
                    "👁️ [Observation từ MCP Server]: {}"
                )

                print(
                    "⚠️ MCP Server chưa trả về dữ liệu."
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
                    f"👁️ [Observation từ MCP Server]: "
                    f"{obs_str}"
                )

                synthesis_start_time = time.time()

                (
                    final_answer,
                    synthesis_source
                ) = synthesize_observation_with_llm(
                    provider=provider,
                    user_query=user_query,
                    tool_name=tool_name,
                    arguments=arguments,
                    observation=obs_data
                )

                synthesis_latency_ms = round(
                    (
                        time.time()
                        - synthesis_start_time
                    ) * 1000,
                    2
                )
            emit(
                "observation",
                (
                    "Công cụ trả trạng thái "
                    f"{obs_data.get('status', 'NO_DATA')}"
                    if obs_data
                    else "Công cụ không trả dữ liệu"
                ),
                observation=obs_data
            )
            
            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "TOOL_EXECUTION",
                "thought": thought,
                "tool_name": tool_name,
                "arguments": arguments,
                "observation": obs_data,
                "decision_latency_ms": latency_ms,
                "model": model_name,
                "usage": usage
            })
            
            # Kết thúc vòng lặp sau khi hoàn tất Observation và xuất Final Answer
            print(f"🧠 [Thought]: Đã nhận được dữ liệu từ MCP Server. Tổng hợp kết quả phản hồi.")
            print(f"🏁 [Final Answer]: {final_answer}")

            final_status = obs_data.get(
                "status",
                "NO_DATA"
            ) if obs_data else "NO_DATA"

            if synthesis_source == "LLM_OBSERVATION_SYNTHESIS":
                final_thought = (
                    "Đã gửi Observation từ MCP Server "
                    "trở lại LLM để tổng hợp câu trả lời "
                    f"với trạng thái {final_status}."
                )
            elif synthesis_source == "DETERMINISTIC_FALLBACK":
                final_thought = (
                    "LLM không thể tổng hợp Observation. "
                    "Hệ thống đã sử dụng bộ tổng hợp dự phòng "
                    f"với trạng thái {final_status}."
                )
            else:
                final_thought = (
                    "MCP Server không trả về dữ liệu để "
                    "tổng hợp câu trả lời."
                )
            trace_logs.append({
                "step": step + 1,
                "query": user_query,
                "action_type": "FINAL_ANSWER",
                "thought": final_thought,
                "output": final_answer,
                "synthesis_source": synthesis_source,
                "synthesis_latency_ms": synthesis_latency_ms,
                "model": model_name
            })
            emit("final", final_answer)
            break

    return trace_logs

def run_comparison(
    user_query: str,
    provider,
    mcp_server: MCPVinBusServer
) -> dict:
    """
    Chạy cùng một câu hỏi qua:
    1. Chatbot Baseline không có Tool.
    2. ReAct Agent có Native Tool Calling và MCP Server.
    """

    print("\n" + "=" * 60)
    print("📊 SO SÁNH CHATBOT BASELINE VS REACT AGENT + MCP")
    print("=" * 60)
    print(f"📌 Câu hỏi: {user_query}")

    baseline_result = run_baseline_chatbot(
        user_query,
        provider
    )

    agent_trace = run_react_agent(
        user_query,
        provider,
        mcp_server
    )

    agent_answer = extract_final_answer(
        agent_trace
    )

    tool_events = [
        event
        for event in agent_trace
        if event.get("action_type") == "TOOL_EXECUTION"
    ]

    tools_called = [
        event.get("tool_name")
        for event in tool_events
    ]

    comparison = {
        "query": user_query,
        "baseline": baseline_result,
        "react_mcp_agent": {
            "mode": "REACT_MCP_AGENT",
            "output": agent_answer,
            "tool_called": len(tool_events) > 0,
            "tools": tools_called,
            "trace": agent_trace
        }
    }

    print("\n" + "-" * 60)
    print("📋 KẾT QUẢ SO SÁNH")
    print("-" * 60)

    print("\n💬 CHATBOT BASELINE")
    print(f"Câu trả lời: {baseline_result['output']}")
    print("Tool: Không")

    print("\n🤖 REACT AGENT + MCP")
    print(f"Câu trả lời: {agent_answer}")
    print(
        "Tool: "
        + (
            ", ".join(tools_called)
            if tools_called
            else "Không cần gọi Tool"
        )
    )

    return comparison


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

    if "--compare" in sys.argv:
        print(
            "📊 [COMPARE MODE] "
            "Chatbot Baseline vs ReAct Agent + MCP"
        )

        all_comparisons = []
        all_agent_traces = []

        for tc in tests:
            if tc["question"].strip().startswith("TODO"):
                continue

            print("\n" + "=" * 60)
            print(f"🧪 [{tc['id']}] {tc['question']}")

            comparison = run_comparison(
                tc["question"],
                provider,
                mcp_server
            )

            comparison["test_case_id"] = tc["id"]
            comparison["expected_behavior"] = (
                tc["expected_behavior"]
            )

            all_comparisons.append(comparison)

            all_agent_traces.extend(
                comparison["react_mcp_agent"]["trace"]
            )

        if all_agent_traces:
            save_waterfall_trace(all_agent_traces)

        base_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )

        comparison_path = os.path.join(
            base_dir,
            "docs",
            "comparison_results.json"
        )

        with open(
            comparison_path,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                all_comparisons,
                file,
                ensure_ascii=False,
                indent=2
            )

        print(
            "\n✅ Đã lưu kết quả so sánh tại "
            f"{comparison_path}"
        )

    elif "--interactive" in sys.argv:
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
        print("  3. So sánh hai kiến trúc:      python src/app.py --compare")
        
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
        
