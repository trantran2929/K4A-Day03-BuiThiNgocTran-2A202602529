import json
import streamlit as st

from app import run_react_agent, save_waterfall_trace, run_baseline_chatbot
from mcp_server import MCPVinBusServer
from providers import get_llm_provider


st.set_page_config(
    page_title="Trợ lý VinBus",
    page_icon="🚌",
    layout="wide"
)


@st.cache_resource
def initialize_services():
    """Khởi tạo Provider và MCP Server một lần."""
    provider = get_llm_provider()
    mcp_server = MCPVinBusServer()
    return provider, mcp_server


def extract_final_answer(trace_logs: list) -> str:
    """Lấy Final Answer cuối cùng từ Waterfall Trace."""
    for event in reversed(trace_logs):
        if event.get("action_type") == "FINAL_ANSWER":
            return event.get(
                "output",
                "Không nhận được câu trả lời."
            )

    return "Không nhận được câu trả lời từ Agent."

def extract_called_tools(trace_logs: list) -> list:
    """Lấy danh sách Tool được ReAct Agent gọi."""

    return [
        event.get("tool_name")
        for event in trace_logs
        if (
            event.get("action_type")
            == "TOOL_EXECUTION"
            and event.get("tool_name")
        )
    ]

def extract_usage(trace_logs: list) -> dict:
    """Lấy usage của lần gọi LLM trong trace, không cộng trùng."""
    for event in trace_logs:
        usage = event.get("usage")
        if usage:
            return {
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
                "model": event.get("model", "unknown")
            }

    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "model": getattr(provider, "model_name", "unknown")
    }


def estimate_cost_usd(usage: dict):
    """Ước tính chi phí text cho model có bảng giá đã cấu hình."""
    prices = {
        "gpt-4o-mini": {
            "input": 0.15,
            "output": 0.60
        }
    }
    price = prices.get(usage.get("model"))
    if not price:
        return None

    return (
        usage.get("input_tokens", 0) * price["input"]
        + usage.get("output_tokens", 0) * price["output"]
    ) / 1_000_000


def render_trace(trace_logs: list):
    """Hiển thị Thought, Action và Observation."""

    if not trace_logs:
        st.info("Chưa có dữ liệu Waterfall Trace.")
        return

    for event in trace_logs:
        action_type = event.get(
            "action_type",
            "UNKNOWN"
        )
        step = event.get("step", "?")

        with st.container(border=True):
            st.markdown(
                f"**Bước {step} — {action_type}**"
            )

            thought = event.get("thought")
            if thought:
                st.markdown(f"🧠 **Thought:** {thought}")

            tool_name = event.get("tool_name")
            if tool_name:
                st.markdown(
                    f"🛠️ **Tool:** `{tool_name}`"
                )

            arguments = event.get("arguments")
            if arguments is not None:
                st.markdown("**Arguments:**")
                st.json(arguments)

            observation = event.get("observation")
            if observation is not None:
                st.markdown("👁️ **Observation:**")
                st.json(observation)

            output = event.get("output")
            if output:
                st.markdown("🏁 **Output:**")
                st.write(output)

            latency = event.get("latency_ms")
            if latency is not None:
                st.caption(f"Latency: {latency} ms")


provider, mcp_server = initialize_services()


if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Xin chào! Tôi là Trợ lý Dịch vụ "
                "Khách hàng VinBus. Tôi có thể hỗ trợ "
                "tra cứu tuyến xe và đăng ký vé tháng."
            )
        }
    ]

if "latest_baseline" not in st.session_state:
    st.session_state.latest_baseline = None

if "latest_trace" not in st.session_state:
    st.session_state.latest_trace = []


if "latest_usage" not in st.session_state:
    st.session_state.latest_usage = None


with st.sidebar:
    st.title("🚌 VinBus Assistant")

    st.markdown("### Trạng thái hệ thống")

    st.success(
        f"Provider: {provider.__class__.__name__}"
    )

    st.info(
        f"MCP Server: {mcp_server.server_name}"
    )

    st.markdown("### Chọn chế độ")

    selected_mode = st.radio(
        "Kiến trúc xử lý:",
        options=[
            "Chatbot Baseline",
            "ReAct Agent + MCP"
        ],
        index=0,
        help=(
            "Baseline không sử dụng Tool. "
            "ReAct Agent có thể gọi MCP Server."
        )
    )

    st.markdown("### Câu hỏi gợi ý")

    if st.button(
        "Tra cứu VinUni → Mỹ Đình",
        use_container_width=True
    ):
        st.session_state.suggested_prompt = (
            "Tìm tuyến VinBus từ VinUni "
            "đến Bến xe Mỹ Đình."
        )

    if st.button(
        "Đăng ký vé tuyến E01",
        use_container_width=True
    ):
        st.session_state.suggested_prompt = (
            "Đăng ký vé tháng một tuyến E01 "
            "cho Nguyễn Văn An, "
            "số điện thoại 0912345678."
        )

    if st.button(
        "Đăng ký vé liên tuyến",
        use_container_width=True
    ):
        st.session_state.suggested_prompt = (
            "Đăng ký vé tháng liên tuyến "
            "cho Trần Thị Bình, "
            "số điện thoại 0987654321."
        )

    st.divider()

    if st.button(
        "🗑️ Xóa lịch sử",
        use_container_width=True
    ):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "Lịch sử đã được xóa. "
                    "Tôi có thể giúp gì cho bạn?"
                )
            }
        ]
        st.session_state.latest_baseline = None
        st.session_state.latest_trace = []
        st.session_state.latest_usage = None
        st.rerun()


st.title(
    "🚌 Trợ lý Dịch vụ Khách hàng VinBus"
)

st.caption(
    "Chọn Chatbot Baseline hoặc ReAct Agent + MCP "
    "trong thanh bên để xử lý câu hỏi."
)


chat_column, trace_column = st.columns(
    [3, 2],
    gap="large"
)


with chat_column:
    st.subheader("Hội thoại")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


suggested_prompt = st.session_state.pop(
    "suggested_prompt",
    None
)

user_prompt = st.chat_input(
    "Ví dụ: Tìm tuyến từ VinUni đến Bến xe Mỹ Đình"
)

prompt = user_prompt or suggested_prompt


if prompt:
    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with chat_column:
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            final_answer = None
            error_message = None

            with st.status(
                "Đang phân tích yêu cầu...",
                expanded=True
            ) as live_status:
                def show_live_event(event: dict):
                    stage = event.get("stage")
                    message = event.get("message", "")

                    if stage == "reasoning":
                        live_status.write(
                            f"🧠 Suy luận tóm tắt: {message}"
                        )
                    elif stage == "action":
                        live_status.write(
                            f"🛠️ {message}: "
                            f"`{event.get('arguments', {})}`"
                        )
                    elif stage == "observation":
                        observation = event.get(
                            "observation",
                            {}
                        )
                        live_status.write(
                            f"👁️ {message}"
                        )
                        live_status.json(observation)
                    elif stage == "final":
                        live_status.write(
                            "🏁 Đã tổng hợp câu trả lời."
                        )

                try:
                    baseline_result = None
                    trace_logs = []
                    final_answer = None

                    # Chế độ 1: Chỉ chạy Chatbot Baseline
                    if selected_mode == "Chatbot Baseline":
                        live_status.write(
                            "💬 Đang chạy Chatbot Baseline..."
                        )

                        baseline_result = run_baseline_chatbot(
                            prompt,
                            provider
                        )

                        final_answer = baseline_result.get(
                            "output",
                            "Không có câu trả lời."
                        )

                        st.session_state.latest_baseline = (
                            baseline_result
                        )
                        st.session_state.latest_trace = []
                        st.session_state.latest_usage = None

                    # Chế độ 2: Chạy ReAct Agent + MCP
                    else:
                        live_status.write(
                            "🤖 Đang chạy ReAct Agent + MCP..."
                        )

                        trace_logs = run_react_agent(
                            prompt,
                            provider,
                            mcp_server,
                            event_callback=show_live_event
                        )

                        final_answer = extract_final_answer(
                            trace_logs
                        )

                        save_waterfall_trace(trace_logs)

                        st.session_state.latest_baseline = None
                        st.session_state.latest_trace = trace_logs
                        st.session_state.latest_usage = (
                            extract_usage(trace_logs)
                        )

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": (
                            f"**Chế độ: {selected_mode}**\n\n"
                            f"{final_answer}"
                        )
                    })

                    live_status.update(
                        label=f"Hoàn tất — {selected_mode}",
                        state="complete",
                        expanded=False
                    )

                except Exception as error:
                    error_message = (
                        "Không thể xử lý yêu cầu: "
                        f"{str(error)}"
                    )

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_message
                    })
                    live_status.update(
                        label="Xử lý thất bại",
                        state="error",
                        expanded=True
                    )

            if final_answer:
                st.markdown(
                    f"**Chế độ: {selected_mode}**"
                )

                st.markdown(final_answer)

                if selected_mode == "Chatbot Baseline":
                    st.caption(
                        "🛠️ Chatbot Baseline không sử dụng Tool"
                    )

                else:
                    called_tools = extract_called_tools(
                        trace_logs
                    )

                    if called_tools:
                        st.caption(
                            "🛠️ MCP Tool: "
                            f"{', '.join(called_tools)}"
                        )
                    else:
                        st.caption(
                            "🛠️ Agent xác định không cần gọi Tool"
                        )

            elif error_message:
                st.error(error_message)

with trace_column:
    st.subheader("🔍 MCP Waterfall Trace")

    if selected_mode == "Chatbot Baseline":
        st.info(
            "Chatbot Baseline không có Waterfall Trace "
            "vì không gọi Tool hoặc MCP Server."
        )

    else:
        st.caption(
            "Thought → Action → Observation "
            "của ReAct Agent + MCP."
        )

        usage = st.session_state.latest_usage

        if usage:
            st.markdown(
                "#### Token của câu hỏi gần nhất"
            )

            input_col, output_col, total_col = (
                st.columns(3)
            )

            input_col.metric(
                "Input",
                usage.get("input_tokens", 0)
            )

            output_col.metric(
                "Output",
                usage.get("output_tokens", 0)
            )

            total_col.metric(
                "Tổng",
                usage.get("total_tokens", 0)
            )

            st.caption(
                f"Model: "
                f"{usage.get('model', 'unknown')}"
            )

            estimated_cost = estimate_cost_usd(
                usage
            )

            if estimated_cost is not None:
                st.caption(
                    "Chi phí ước tính: "
                    f"${estimated_cost:.8f} USD"
                )
            else:
                st.caption(
                    "Chưa cấu hình bảng giá "
                    "cho model này."
                )

        with st.expander(
            "Xem Thought → Action → Observation",
            expanded=True
        ):
            render_trace(
                st.session_state.latest_trace
            )

        if st.session_state.latest_trace:
            trace_json = json.dumps(
                st.session_state.latest_trace,
                ensure_ascii=False,
                indent=2
            )

            st.download_button(
                label="⬇️ Tải MCP Waterfall Trace",
                data=trace_json,
                file_name="trace_waterfall.json",
                mime="application/json",
                use_container_width=True
            )
