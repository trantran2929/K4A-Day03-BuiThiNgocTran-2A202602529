"""
🛠️ TOOL DEFINITIONS & EXECUTION BACKEND
Mã nguồn chứa danh sách Tool Schemas (JSON Schema) và Execution Layer phục vụ cho MCP Server.
"""

import json
from typing import Dict, Any

# ==============================================================================
# 1. KHAI BÁO TOOL SCHEMAS CHUẨN NATIVE JSON SCHEMA (TASK 1.2)
# ==============================================================================

TOOLS_SCHEMA = [
    # Tool 1: Đã được định nghĩa mẫu sẵn cho Học viên tham khảo
    {
        "name": "search_bus_route",
        "description": (
            "Tra cứu tuyến xe buýt phù hợp dựa theo điểm đi và điểm đến của hành khách." 
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "origin": {
                    "type": "string",
                    "minLength": 1,
                    "description": (
                         "Điểm xuất phát của hành khách, ví dụ: 'VinUni'."
                    )
                },
                "destination": {
                    "type": "string",
                    "minLength": 1,
                    "description": (
                        "Điểm đến của hành khách, ví dụ: 'Bến xe Mỹ Đình'."
                    )
                }
            },
            "required": ["origin", "destination"],
            "additionalProperties": False
        }
    },
    
# --------------------------------------------------------------------------
# TODO TOOL 2: ĐĂNG KÝ VÉ THÁNG VINBUS
# Các tham số:
# - full_name: Họ tên hành khách
# - phone: Số điện thoại
# - ticket_type: Loại vé tháng
# - route_id: Mã tuyến, bắt buộc với vé một tuyến
# --------------------------------------------------------------------------
    {
        "name": "register_monthly_pass",
        "description": (
            "Đăng ký vé tháng Vinbus sau khi hành khách đã cung cấp đủ thông tin."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "full_name": {
                    "type": "string",
                    "minLength": 1,
                    "description": (
                        "Họ và tên hành khách, ví dụ: 'Nguyễn Văn A'."
                    )
                },
                "phone": {
                    "type": "string",
                    "pattern": "^0[0-9]{9}$",
                    "description": (
                        "Số điện thoại hành khách."
                    )
                },
                "ticket_type": {
                    "type": "string",
                    "enum": ["one_route", "all_routes"],
                    "description": (
                        "Loại vé tháng: one_route là vé tháng một tuyến, "
                        "all_routes là vé tháng liên tuyến."
                    )
                },
                "route_id":{
                    "type": "string",
                    "pattern": "^[A-Z][0-9]{2}$",
                    "description": (
                        "Mã tuyến VinBus, ví dụ E01. "
                        "Bắt buộc khi ticket_type là one_route."
                    )
                }
            },
            "required": [
                "full_name", "phone", "ticket_type"
            ],
            "allOf": [
                {
                    "if": {
                        "properties": {
                            "ticket_type": {
                                "const": "one_route"
                            }
                        },
                        "required": ["ticket_type"]
                    },
                    "then": {
                        "required": ["route_id"]
                    }
                }
            ],
            "additionalProperties": False
        }
    }
]

# ==============================================================================
# 2. MÔ PHỎNG DỮ LIỆU & HÀM THỰC THI TOOL (EXECUTION LAYER)
# ==============================================================================

MOCK_DATABASE = [
    {
        "route_id": "E01",
        "route_name": "VinUni - Bến xe Mỹ Đình",
        "stops": ["VinUni", "Cầu Giấy", "Bến xe Mỹ Đình"],
        "operating_hours": "05:00 - 21:00",
        "frequency": "15 phút/lượt"
    },
    {
        "route_id": "E02",
        "route_name": "VinUni - Bến xe Giáp Bát",
        "stops": ["VinUni", "Ngã Tư Sở", "Bến xe Giáp Bát"],
        "operating_hours": "05:00 - 21:00",
        "frequency": "15 phút/lượt"
    },
    {
        "route_id": "E03",
        "route_name": "VinUni - Bến xe Yên Nghĩa",
        "stops": ["VinUni", "Hà Đông", "Bến xe Yên Nghĩa"],
        "operating_hours": "05:00 - 21:00",
        "frequency": "15 phút/lượt"
    }
]

MOCK_REGISTRATIONS = []

def normalize_text(value:str) -> str:
    """Chuẩn hóa chuỗi để so sánh không phân biệt chữ hoa, chữ thường."""
    return value.strip().casefold()

def execute_search_bus_route(
    origin: str,
    destination: str
) -> str:
    """Tra cứu tuyến VinBus có chứa điểm đi và điểm đến đúng thứ tự."""

    if not origin.strip() or not destination.strip():
        return json.dumps({
            "status": "INVALID_INPUT",
            "message": "Điểm đi và điểm đến không được để trống."
        }, ensure_ascii=False)

    normalized_origin = normalize_text(origin)
    normalized_destination = normalize_text(destination)
    matched_routes = []

    for route in MOCK_DATABASE:
        normalized_stops = [
            normalize_text(stop)
            for stop in route["stops"]
        ]

        if (
            normalized_origin in normalized_stops
            and normalized_destination in normalized_stops
        ):
            origin_index = normalized_stops.index(normalized_origin)
            destination_index = normalized_stops.index(
                normalized_destination
            )

            if origin_index < destination_index:
                journey_stops = route["stops"][
                    origin_index:destination_index + 1
                ]

                matched_routes.append({
                    "route_id": route["route_id"],
                    "route_name": route["route_name"],
                    "origin": origin,
                    "destination": destination,
                    "journey_stops": journey_stops,
                    "operating_hours": route["operating_hours"],
                    "frequency": route["frequency"]
                })

    if matched_routes:
        return json.dumps({
            "status": "SUCCESS",
            "message": (
                f"Tìm thấy {len(matched_routes)} tuyến phù hợp."
            ),
            "data": matched_routes
        }, ensure_ascii=False)

    return json.dumps({
        "status": "NOT_FOUND",
        "message": (
            f"Không tìm thấy tuyến VinBus trực tiếp "
            f"từ '{origin}' đến '{destination}'."
        )
    }, ensure_ascii=False)

def is_valid_phone(phone: str) -> bool:
    """Kiểm tra số điện thoại Việt Nam ở mức cơ bản."""
    normalized_phone = phone.strip().replace(" ", "")

    return (
        normalized_phone.isdigit()
        and normalized_phone.startswith("0")
        and len(normalized_phone) == 10
    )

def execute_register_monthly_pass(
    full_name: str,
    phone: str,
    ticket_type: str,
    route_id: str = ""
) -> str:
    """Mô phỏng đăng ký vé tháng VinBus."""

    full_name = full_name.strip()
    phone = phone.strip().replace(" ", "")
    ticket_type = ticket_type.strip().lower()
    route_id = route_id.strip().upper()

    if not full_name:
        return json.dumps({
            "status": "INVALID_INPUT",
            "message": "Họ và tên không được để trống."
        }, ensure_ascii=False)

    if not is_valid_phone(phone):
        return json.dumps({
            "status": "INVALID_INPUT",
            "message": (
                "Số điện thoại phải gồm 10 chữ số "
                "và bắt đầu bằng số 0."
            )
        }, ensure_ascii=False)

    if ticket_type not in ["one_route", "all_routes"]:
        return json.dumps({
            "status": "INVALID_INPUT",
            "message": (
                "Loại vé phải là 'one_route' hoặc 'all_routes'."
            )
        }, ensure_ascii=False)

    if ticket_type == "one_route":
        if not route_id:
            return json.dumps({
                "status": "INVALID_INPUT",
                "message": (
                    "Vé một tuyến yêu cầu cung cấp mã tuyến."
                )
            }, ensure_ascii=False)

        valid_route_ids = {
            route["route_id"]
            for route in MOCK_DATABASE
        }

        if route_id not in valid_route_ids:
            return json.dumps({
                "status": "NOT_FOUND",
                "message": (
                    f"Không tìm thấy tuyến có mã '{route_id}'."
                )
            }, ensure_ascii=False)

    registration_id = (
        f"VB-{len(MOCK_REGISTRATIONS) + 1:04d}"
    )

    registration = {
        "registration_id": registration_id,
        "full_name": full_name,
        "phone": phone,
        "ticket_type": ticket_type,
        "route_id": route_id if route_id else None,
        "application_status": "RECEIVED"
    }

    MOCK_REGISTRATIONS.append(registration)

    return json.dumps({
        "status": "SUCCESS",
        "registration_id": registration_id,
        "message": "Đăng ký vé tháng VinBus thành công.",
        "data": registration
    }, ensure_ascii=False)

# Router gọi tool thực tế
TOOL_ROUTER = {
    "search_bus_route": execute_search_bus_route,
    "register_monthly_pass": execute_register_monthly_pass
}

def dispatch_tool_call(
    tool_name: str,
    arguments: Dict[str, Any]
) -> str:
    """Chuyển yêu cầu gọi tool đến hàm thực thi tương ứng."""

    if tool_name not in TOOL_ROUTER:
        return json.dumps({
            "status": "UNKNOWN_TOOL",
            "error": f"Tool '{tool_name}' không tồn tại."
        }, ensure_ascii=False)

    try:
        return TOOL_ROUTER[tool_name](**arguments)
    except TypeError as error:
        return json.dumps({
            "status": "INVALID_ARGUMENTS",
            "error": str(error)
        }, ensure_ascii=False)
    except Exception as error:
        return json.dumps({
            "status": "EXECUTION_ERROR",
            "error": str(error)
        }, ensure_ascii=False)