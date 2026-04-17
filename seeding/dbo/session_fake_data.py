import json
import random
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TypedDict, Any

from faker import Faker
from sqlalchemy import text

from db import get_session
from enums import DEVICE_TYPES, APP_VERSIONS_WEB, APP_VERSIONS_MOBILE, CITIES, LOGIN_FAILURE_REASONS

fake = Faker("ru_RU")

TOTAL_SESSIONS = 5000

SESSIONS_FILE = Path("C:/Users/kyrlu/PycharmProjects/data_sources/data/dbo/dbo_sessions.json")

DEVICE_TYPE_WEIGHTS = [0.45, 0.30, 0.25]

APP_VERSION_WEIGHTS_MOBILE = [0.05, 0.10, 0.18, 0.24, 0.25, 0.18]

APP_VERSION_WEIGHTS_WEB = [0.20, 0.35, 0.45]


class ClientRow(TypedDict):
    client_id: int
    registration_date: date


def load_clients(session) -> list[ClientRow]:
    rows = session.execute(
        text("""
            SELECT
                client_id,
                registration_date::date AS registration_date
            FROM clients
            ORDER BY client_id
        """)
    ).mappings().all()

    if not rows:
        raise ValueError("В abs.clients нет данных")

    return [
        {
            "client_id": row["client_id"],
            "registration_date": row["registration_date"],
        }
        for row in rows
    ]


def choose_client_weights(clients: list[ClientRow]) -> list[float]:
    today = date.today()
    weights: list[float] = []

    for client in clients:
        months_since_registration = max(
            0,
            (today.year - client["registration_date"].year) * 12
            + (today.month - client["registration_date"].month)
        )

        if months_since_registration >= 36:
            weights.append(1.8)
        elif months_since_registration >= 12:
            weights.append(1.2)
        else:
            weights.append(0.7)

    return weights


def generate_device_type() -> str:
    return random.choices(DEVICE_TYPES, weights=DEVICE_TYPE_WEIGHTS, k=1)[0]


def generate_app_version(device_type: str) -> str:
    if device_type == "web":
        return random.choices(APP_VERSIONS_WEB, weights=APP_VERSION_WEIGHTS_WEB, k=1)[0]

    return random.choices(APP_VERSIONS_MOBILE, weights=APP_VERSION_WEIGHTS_MOBILE, k=1)[0]


def generate_login_time(registration_date: date) -> datetime:
    start_date = max(registration_date, date.today() - timedelta(days=365))
    return fake.date_time_between_dates(
        datetime_start=datetime.combine(start_date, datetime.min.time()),
        datetime_end=datetime.combine(date.today(), datetime.max.time()),
    )


def generate_success(device_type: str) -> bool:
    if device_type == "web":
        return random.choices([True, False], weights=[0.90, 0.10], k=1)[0]

    return random.choices([True, False], weights=[0.94, 0.06], k=1)[0]


def generate_logout_time(login_time: datetime, success: bool) -> datetime | None:
    if not success:
        return None

    session_minutes = random.choices(
        [1, 3, 5, 10, 15, 25, 40, 60, 90],
        weights=[0.03, 0.07, 0.12, 0.20, 0.22, 0.16, 0.10, 0.07, 0.03],
        k=1
    )[0]

    return login_time + timedelta(
        minutes=session_minutes,
        seconds=random.randint(5, 59)
    )


def generate_ip() -> str:
    return fake.ipv4_public()


def generate_city() -> str:
    return random.choice(CITIES)


def build_session_record(client: ClientRow) -> dict[str, Any]:
    device_type = generate_device_type()
    successful_login = generate_success(device_type)
    login_time = generate_login_time(client["registration_date"])
    logout_time = generate_logout_time(login_time, successful_login)

    return {
        "session_id": uuid.uuid4().hex,
        "client_id": client["client_id"],
        "login_time": login_time.isoformat(),
        "logout_time": logout_time.isoformat() if logout_time else None,
        "device_type": device_type,
        "app_version": generate_app_version(device_type),
        "ip_address": generate_ip(),
        "city": generate_city(),
        "successful_login": successful_login,
        "failure_reason": None if successful_login else random.choice(LOGIN_FAILURE_REASONS),
    }


def write_json_file(file_path: Path, data: list[dict[str, Any]]) -> None:
    file_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


with get_session("abs") as session:
    clients = load_clients(session)

    client_weights = choose_client_weights(clients)

    sessions: list[dict[str, Any]] = []

    for _ in range(TOTAL_SESSIONS):
        client = random.choices(clients, weights=client_weights, k=1)[0]
        sessions.append(build_session_record(client))

    write_json_file(SESSIONS_FILE, sessions)