"""
🔌 MULTI-PROVIDER LLM ADAPTER (Google Gemini, OpenAI & Offline Mock)
Hỗ trợ Native Tool Calling và chuyển đổi linh hoạt qua biến môi trường LLM_PROVIDER.
"""

import re
import os
import sys
import json
from typing import Dict, Any, List
from click import prompt
from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()

class BaseLLMProvider:
    """Interface cơ sở cho các LLM Provider hỗ trợ Native Tool Calling"""
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        raise NotImplementedError


class MockOfflineProvider(BaseLLMProvider):
    """Offline Mock Provider dùng để kiểm thử không cần API Key."""

    def __init__(self):
        self.model_name = "Offline-Mock-Model-2026"

    def _is_route_query(self, prompt: str) -> bool:
        """Nhận diện yêu cầu tra cứu tuyến hoặc chuyến xe."""
        prompt_lower = prompt.casefold()

        route_keywords = [
            "tìm tuyến",
            "tìm chuyến",
            "tra cứu tuyến",
            "tra cứu chuyến",
            "lộ trình",
            "đi từ"
        ]

        return any(
            keyword in prompt_lower
            for keyword in route_keywords
        )

    def generate(
        self,
        prompt: str,
        system_prompt: str = ""
    ) -> str:
        prompt_lower = prompt.casefold()

        if self._is_route_query(prompt):
            return (
                "[Mock Chatbot Response]: "
                "Chatbot Baseline không có công cụ tra cứu "
                "dữ liệu tuyến xe VinBus."
            )

        if (
            "đăng ký" in prompt_lower
            and "vé tháng" in prompt_lower
        ):
            return (
                "[Mock Chatbot Response]: "
                "Chatbot Baseline không có công cụ "
                "đăng ký vé tháng VinBus."
            )

        return (
            "[Mock Chatbot Response]: "
            "VinBus là dịch vụ xe buýt điện. "
            "Đây là phản hồi mô phỏng ở chế độ offline."
        )

    def generate_with_tools(
        self,
        prompt: str,
        tools_schema: List[Dict[str, Any]],
        system_prompt: str = ""
    ) -> Dict[str, Any]:
        prompt_lower = prompt.casefold()

        if (
            "đăng ký" in prompt_lower
            and "vé tháng" in prompt_lower
        ):
            return self._handle_monthly_pass(prompt)

        if self._is_route_query(prompt):
            return self._handle_route_search(prompt)

        return {
            "type": "text",
            "content": (
                "[Mock Agent Response]: "
                "VinBus là dịch vụ xe buýt điện. "
                "Tôi có thể hỗ trợ tra cứu tuyến xe "
                "và đăng ký vé tháng."
            ),
            "thought": (
                "Đây là câu hỏi chung, không cần gọi Tool."
            )
        }

    def _handle_route_search(
        self,
        prompt: str
    ) -> Dict[str, Any]:
        match = re.search(
            r"từ\s+(.+?)\s+đến\s+(.+?)(?:[?.!]|$)",
            prompt,
            flags=re.IGNORECASE
        )

        if not match:
            return {
                "type": "text",
                "content": (
                    "Bạn vui lòng cung cấp đầy đủ "
                    "điểm đi và điểm đến."
                ),
                "thought": (
                    "Yêu cầu tra cứu còn thiếu điểm đi "
                    "hoặc điểm đến nên chưa gọi Tool."
                )
            }

        origin = match.group(1).strip()
        destination = match.group(2).strip()

        return {
            "type": "tool_call",
            "tool_name": "search_bus_route",
            "arguments": {
                "origin": origin,
                "destination": destination
            },
            "thought": (
                "Người dùng muốn tra cứu tuyến VinBus "
                "và đã cung cấp đủ điểm đi, điểm đến."
            )
        }

    def _handle_monthly_pass(
        self,
        prompt: str
    ) -> Dict[str, Any]:
        prompt_lower = prompt.casefold()

        ticket_type = (
            "all_routes"
            if "liên tuyến" in prompt_lower
            else "one_route"
        )

        phone_match = re.search(
            r"\b0\d{9}\b",
            prompt
        )

        route_match = re.search(
            r"\bE\d{2}\b",
            prompt,
            flags=re.IGNORECASE
        )

        name_match = re.search(
            r"\bcho\s+(.+?)(?:,\s*(?:số điện thoại|sđt)|$)",
            prompt,
            flags=re.IGNORECASE
        )

        missing_fields = []

        if not name_match:
            missing_fields.append("họ và tên")

        if not phone_match:
            missing_fields.append("số điện thoại")

        if (
            ticket_type == "one_route"
            and not route_match
        ):
            missing_fields.append("mã tuyến")

        if missing_fields:
            return {
                "type": "text",
                "content": (
                    "Bạn vui lòng bổ sung: "
                    + ", ".join(missing_fields)
                    + "."
                ),
                "thought": (
                    "Thông tin đăng ký chưa đầy đủ "
                    "nên chưa gọi Tool."
                )
            }

        arguments = {
            "full_name": name_match.group(1).strip(),
            "phone": phone_match.group(0),
            "ticket_type": ticket_type
        }

        if route_match:
            arguments["route_id"] = (
                route_match.group(0).upper()
            )

        return {
            "type": "tool_call",
            "tool_name": "register_monthly_pass",
            "arguments": arguments,
            "thought": (
                "Người dùng đã cung cấp đủ thông tin "
                "để đăng ký vé tháng VinBus."
            )
        }

class GeminiProvider(BaseLLMProvider):
    """Google Gemini Provider (Native Tool Calling với Google GenAI SDK)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gemini-2.5-flash"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            return "[Gemini Error]: Chưa cấu hình GEMINI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            contents = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = client.models.generate_content(model=self.model_name, contents=contents)
            return response.text
        except Exception as e:
            return f"[Gemini Exception]: {str(e)}"

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            print("ℹ️ [Gemini Provider]: Chưa tìm thấy GEMINI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)
        
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            
            # Chuẩn hóa function declarations cho Gemini SDK
            function_declarations = []
            for tool in tools_schema:
                # Bỏ qua các tool schema chưa được định nghĩa hoàn chỉnh
                if not tool.get("name") or not tool.get("parameters"):
                    continue
                function_declarations.append({
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {})
                })

            config = types.GenerateContentConfig(
                system_instruction=system_prompt if system_prompt else None,
                tools=[{"function_declarations": function_declarations}] if function_declarations else None,
                temperature=0.2
            )

            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )

            # Kiểm tra xem Gemini có trả về Tool Call không
            if response.function_calls:
                call = response.function_calls[0]
                args = dict(call.args) if hasattr(call, 'args') and call.args else {}
                return {
                    "type": "tool_call",
                    "tool_name": call.name,
                    "arguments": args,
                    "thought": f"Gemini quyết định gọi công cụ '{call.name}' với tham số: {json.dumps(args, ensure_ascii=False)}"
                }
            else:
                return {
                    "type": "text",
                    "content": response.text or "",
                    "thought": "Gemini phản hồi trực tiếp bằng văn bản (không cần gọi công cụ)."
                }

        except Exception as e:
            print(f"⚠️ [Gemini API Warning]: Không thể kết nối live API ({str(e)}). Tự động fallback về Mock.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Provider (Native Tool Calling với OpenAI SDK)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gpt-4o-mini"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            return "[OpenAI Error]: Chưa cấu hình OPENAI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(model=self.model_name, messages=messages)
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"[OpenAI Exception]: {str(e)}"

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            print("ℹ️ [OpenAI Provider]: Chưa tìm thấy OPENAI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)

            tools = []
            for tool in tools_schema:
                if not tool.get("name"):
                    continue
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {})
                    }
                })

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None
            )

            msg = response.choices[0].message
            if msg.tool_calls:
                call = msg.tool_calls[0]
                args = json.loads(call.function.arguments) if call.function.arguments else {}
                return {
                    "type": "tool_call",
                    "tool_name": call.function.name,
                    "arguments": args,
                    "thought": f"OpenAI quyết định gọi công cụ '{call.function.name}' với tham số: {json.dumps(args, ensure_ascii=False)}"
                }
            else:
                return {
                    "type": "text",
                    "content": msg.content or "",
                    "thought": "OpenAI phản hồi trực tiếp bằng văn bản (không cần gọi công cụ)."
                }
        except Exception as e:
            print(f"⚠️ [OpenAI API Warning]: Không thể kết nối live API ({str(e)}). Tự động fallback về Mock.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)


def get_llm_provider() -> BaseLLMProvider:
    """Factory function khởi tạo Provider theo LLM_PROVIDER env variable"""
    provider_type = os.getenv("LLM_PROVIDER", "gemini").lower()
    
    if provider_type == "gemini":
        key = os.getenv("GEMINI_API_KEY")
        if key and key != "your_gemini_api_key_here":
            return GeminiProvider()
        else:
            return MockOfflineProvider()
    elif provider_type == "openai":
        key = os.getenv("OPENAI_API_KEY")
        if key and key != "your_openai_api_key_here":
            return OpenAIProvider()
        else:
            return MockOfflineProvider()
    elif provider_type == "mock":
        return MockOfflineProvider()
    else:
        return MockOfflineProvider()
