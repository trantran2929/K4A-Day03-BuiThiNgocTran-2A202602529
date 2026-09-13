"""
🔌 MODEL CONTEXT PROTOCOL (MCP) SERVER MODULE
Mô phỏng kiến trúc MCP Server (Client-Server Architecture) cung cấp công cụ chuẩn hóa.
"""

import json
import sys
from typing import Dict, Any, List
from tools import TOOLS_SCHEMA, dispatch_tool_call

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

class MCPVinBusServer:
    """
    Giả lập MCP Server tuân thủ chuẩn giao thức Model Context Protocol
    """
    def __init__(self, server_name: str = "vinbus-customer-service-mcp-server"):
        self.server_name = server_name
        self.version = "2026.1.0"
        
    def list_tools(self) -> List[Dict[str, Any]]:
        """Trả về danh sách các Tools chuẩn giao thức MCP"""
        return TOOLS_SCHEMA
        
    def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Thực thi tool và đóng gói kết quả theo JSON-RPC 2.0.
        """

        try:
            result_json = dispatch_tool_call(
                tool_name,
                arguments
            )

            content = json.loads(result_json)

            return {
                "jsonrpc": "2.0",
                "server": self.server_name,
                "tool": tool_name,
                "result": content
            }

        except json.JSONDecodeError as error:
            return {
                "jsonrpc": "2.0",
                "server": self.server_name,
                "tool": tool_name,
                "result": {
                    "status": "EXECUTION_ERROR",
                    "error": (
                        "Tool trả về dữ liệu JSON không hợp lệ: "
                        f"{str(error)}"
                    )
                }
            }

        except Exception as error:
            return {
                "jsonrpc": "2.0",
                "server": self.server_name,
                "tool": tool_name,
                "result": {
                    "status": "EXECUTION_ERROR",
                    "error": str(error)
                }
            }


if __name__ == "__main__":
    print("==========================================================")
    print("MCP SERVER — VINBUS CUSTOMER SERVICE")
    print("==========================================================")

    server = MCPVinBusServer()
    tools = server.list_tools()

    print(
        f"✅ Khởi tạo thành công: "
        f"{server.server_name} "
        f"(Version: {server.version})"
    )
    print(
        f"📦 Số lượng Tools công bố: {len(tools)}"
    )

    print("\nDanh sách công cụ:")
    for tool in tools:
        print(f"- {tool.get('name')}")

    print("\nKiểm tra tra cứu tuyến:")
    route_result = server.call_tool(
        "search_bus_route",
        {
            "origin": "VinUni",
            "destination": "Bến xe Mỹ Đình"
        }
    )
    print(
        json.dumps(
            route_result,
            ensure_ascii=False,
            indent=2
        )
    )

    print("\nKiểm tra đăng ký vé tháng:")
    registration_result = server.call_tool(
        "register_monthly_pass",
        {
            "full_name": "Nguyễn Văn An",
            "phone": "0912345678",
            "ticket_type": "one_route",
            "route_id": "E01"
        }
    )
    print(
        json.dumps(
            registration_result,
            ensure_ascii=False,
            indent=2
        )
    )