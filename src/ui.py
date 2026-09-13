import json
import streamlit as st

from app import run_react_agent, save_waterfall_trace
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


if "latest_trace" not in st.session_state:
    st.session_state.latest_trace = []


with st.sidebar:
    st.title("🚌 VinBus Assistant")

    st.markdown("### Trạng thái hệ thống")

    st.success(
        f"Provider: {provider.__class__.__name__}"
    )

    st.info(
        f"MCP Server: {mcp_server.server_name}"
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
        st.session_state.latest_trace = []
        st.rerun()


st.title("🚌 Trợ lý Dịch vụ Khách hàng VinBus")

st.caption(
    "Tra cứu lộ trình tuyến xe buýt điện "
    "và đăng ký vé tháng."
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
            with st.spinner(
                "Trợ lý VinBus đang xử lý..."
            ):
                try:
                    trace_logs = run_react_agent(
                        prompt,
                        provider,
                        mcp_server
                    )

                    final_answer = extract_final_answer(
                        trace_logs
                    )

                    save_waterfall_trace(trace_logs)

                    st.markdown(final_answer)

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": final_answer
                    })

                    st.session_state.latest_trace = (
                        trace_logs
                    )

                except Exception as error:
                    error_message = (
                        "Không thể xử lý yêu cầu: "
                        f"{str(error)}"
                    )

                    st.error(error_message)

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_message
                    })


with trace_column:
    st.subheader("Waterfall Trace")

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
            label="⬇️ Tải Waterfall Trace",
            data=trace_json,
            file_name="trace_waterfall.json",
            mime="application/json",
            use_container_width=True
        )