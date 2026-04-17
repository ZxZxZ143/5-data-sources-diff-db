import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from enums import TRANSFER_BANKS, UTILITY_PROVIDERS, GENERIC_ERROR_TEXTS, TRANSFER_ERROR_TEXTS, UTILITY_ERROR_TEXTS, \
    EVENT_TYPES

SESSIONS_FILE = Path("C:/Users/kyrlu/PycharmProjects/data_sources/data/dbo/dbo_sessions.json")
EVENTS_FILE = Path("C:/Users/kyrlu/PycharmProjects/data_sources/data/dbo/dbo_events.json")

EVENT_TYPE_WEIGHTS = [0.50, 0.28, 0.22]

def read_json_file(file_path: Path) -> list[dict[str, Any]]:
    if not file_path.exists():
        raise FileNotFoundError(f"Файл не найден: {file_path}")

    with file_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Ожидался JSON-массив в файле {file_path}")

    return data


def write_json_file(file_path: Path, data: list[dict[str, Any]]) -> None:
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_dt(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def random_time_between(start: datetime, end: datetime) -> datetime:
    if end <= start:
        return start

    delta_seconds = int((end - start).total_seconds())
    offset = random.randint(0, delta_seconds)
    return start + timedelta(seconds=offset)


def generate_event_id() -> str:
    return uuid.uuid4().hex


def generate_login_event(session_row: dict[str, Any]) -> dict[str, Any]:
    successful_login = bool(session_row["successful_login"])

    return {
        "event_id": generate_event_id(),
        "session_id": session_row["session_id"],
        "event_time": session_row["login_time"],
        "event_type": "login",
        "event_data": {
            "device_type": session_row.get("device_type"),
            "app_version": session_row.get("app_version"),
            "ip_address": session_row.get("ip_address"),
            "city": session_row.get("city"),
        },
        "success": successful_login,
        "error_text": None if successful_login else session_row.get("failure_reason") or "Login failed",
    }


def generate_event_data(event_type: str) -> dict[str, Any]:
    if event_type == "view_balance":
        return {
            "currency": random.choice(["KZT", "USD", "EUR"]),
            "account_type": random.choice(["current", "savings", "deposit"]),
        }

    if event_type == "make_transfer":
        return {
            "amount": round(random.uniform(1000, 500000), 2),
            "currency": random.choice(["KZT", "USD"]),
            "target_bank": random.choice(TRANSFER_BANKS),
            "transfer_type": random.choice(["by_phone", "by_card", "by_account"]),
        }

    if event_type == "pay_utility":
        return {
            "provider": random.choice(UTILITY_PROVIDERS),
            "amount": round(random.uniform(500, 50000), 2),
            "category": random.choice(["mobile", "internet", "water", "electricity"]),
        }

    if event_type == "logout":
        return {
            "reason": "user_action",
        }

    return {}


def generate_event_result(event_type: str) -> tuple[bool, str | None]:
    if event_type == "view_balance":
        success = random.choices([True, False], weights=[0.98, 0.02], k=1)[0]
        return success, None if success else random.choice(GENERIC_ERROR_TEXTS)

    if event_type == "make_transfer":
        success = random.choices([True, False], weights=[0.90, 0.10], k=1)[0]
        return success, None if success else random.choice(TRANSFER_ERROR_TEXTS)

    if event_type == "pay_utility":
        success = random.choices([True, False], weights=[0.93, 0.07], k=1)[0]
        return success, None if success else random.choice(UTILITY_ERROR_TEXTS)

    if event_type == "logout":
        return True, None

    return True, None


def generate_action_events(session_row: dict[str, Any]) -> list[dict[str, Any]]:
    login_dt = parse_dt(session_row["login_time"])
    logout_dt = parse_dt(session_row["logout_time"])

    if login_dt is None:
        return []

    if logout_dt is None or logout_dt <= login_dt:
        logout_dt = login_dt + timedelta(minutes=5)

    actions_count = random.choices(
        [1, 2, 3, 4, 5],
        weights=[0.14, 0.26, 0.28, 0.20, 0.12],
        k=1
    )[0]

    chosen_types = random.choices(
        EVENT_TYPES,
        weights=EVENT_TYPE_WEIGHTS,
        k=actions_count
    )

    event_times = sorted(
        random_time_between(login_dt + timedelta(seconds=5), logout_dt - timedelta(seconds=5))
        for _ in range(actions_count)
    )

    events: list[dict[str, Any]] = []

    for event_type, event_dt in zip(chosen_types, event_times):
        success, error_text = generate_event_result(event_type)

        events.append(
            {
                "event_id": generate_event_id(),
                "session_id": session_row["session_id"],
                "event_time": event_dt.isoformat(),
                "event_type": event_type,
                "event_data": generate_event_data(event_type),
                "success": success,
                "error_text": error_text,
            }
        )

    events.append(
        {
            "event_id": generate_event_id(),
            "session_id": session_row["session_id"],
            "event_time": logout_dt.isoformat(),
            "event_type": "logout",
            "event_data": generate_event_data("logout"),
            "success": True,
            "error_text": None,
        }
    )

    return events


def build_events(sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []

    for session_row in sessions:
        events.append(generate_login_event(session_row))

        if bool(session_row["successful_login"]):
            events.extend(generate_action_events(session_row))

    events.sort(key=lambda item: (item["event_time"], item["session_id"]))
    return events


def main():
    sessions = read_json_file(SESSIONS_FILE)
    events = build_events(sessions)
    write_json_file(EVENTS_FILE, events)

    print(f"Готово: {EVENTS_FILE}")
    print(f"Прочитано сессий: {len(sessions)}")
    print(f"Сгенерировано событий: {len(events)}")


if __name__ == "__main__":
    main()