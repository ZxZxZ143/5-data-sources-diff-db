import csv
import random
import uuid
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import text

from db import get_session
from enums import INVESTIGATION_STATUSES

OUTPUT_FILE = Path("C:/Users/kyrlu/PycharmProjects/data_sources/data/aml/aml_alerts.csv")


def load_transactions(session) -> list[dict[str, Any]]:
    rows = session.execute(
        text("""
            SELECT
                t.trx_id,
                a.client_id,
                t.trx_datetime,
                t.posting_date::date AS posting_date,
                t.trx_type::text AS trx_type,
                t.amount,
                t.currency::text AS currency,
                t.channel::text AS channel,
                t.status::text AS status,
                t.counterparty_name,
                t.reference
            FROM transactions t
            JOIN accounts a
              ON a.account_id = t.account_id
            ORDER BY t.trx_id
        """)
    ).mappings().all()

    if not rows:
        raise ValueError("В transactions нет данных")

    return [
        {
            "trx_id": row["trx_id"],
            "client_id": row["client_id"],
            "trx_datetime": row["trx_datetime"],
            "posting_date": row["posting_date"],
            "trx_type": row["trx_type"],
            "amount": Decimal(str(row["amount"])),
            "currency": row["currency"],
            "channel": row["channel"],
            "status": row["status"],
            "counterparty_name": row["counterparty_name"],
            "reference": row["reference"],
        }
        for row in rows
    ]


def detect_rule(tx: dict[str, Any]) -> tuple[str, str] | None:
    trx_type = tx["trx_type"]
    amount = tx["amount"]
    currency = tx["currency"]
    channel = tx["channel"]
    status = tx["status"]

    if trx_type == "cash_withdrawal" and amount >= Decimal("150000"):
        return "large_cash_withdrawal", random.choices(
            ["high", "critical"],
            weights=[0.75, 0.25],
            k=1
        )[0]

    if trx_type == "transfer" and amount >= Decimal("1000000"):
        return "high_value_transfer", random.choices(
            ["high", "critical"],
            weights=[0.45, 0.55],
            k=1
        )[0]

    if currency in ("USD", "EUR") and amount >= Decimal("250000"):
        return "high_value_fx_transaction", random.choices(
            ["medium", "high", "critical"],
            weights=[0.30, 0.55, 0.15],
            k=1
        )[0]

    if trx_type == "debit" and channel in ("mobile_app", "web") and amount >= Decimal("350000"):
        return "large_digital_payment", random.choices(
            ["medium", "high"],
            weights=[0.70, 0.30],
            k=1
        )[0]

    if status == "reversed" and amount >= Decimal("300000"):
        return "reversed_large_transaction", random.choices(
            ["medium", "high"],
            weights=[0.65, 0.35],
            k=1
        )[0]

    return None


def should_create_alert(rule_name: str, risk_level: str) -> bool:
    if rule_name == "large_cash_withdrawal":
        return random.choices([True, False], weights=[0.70, 0.30], k=1)[0]

    if rule_name == "high_value_transfer":
        return random.choices([True, False], weights=[0.82, 0.18], k=1)[0]

    if rule_name == "high_value_fx_transaction":
        return random.choices([True, False], weights=[0.58, 0.42], k=1)[0]

    if rule_name == "large_digital_payment":
        return random.choices([True, False], weights=[0.40, 0.60], k=1)[0]

    if rule_name == "reversed_large_transaction":
        return random.choices([True, False], weights=[0.52, 0.48], k=1)[0]

    if risk_level == "critical":
        return random.choices([True, False], weights=[0.85, 0.15], k=1)[0]

    return random.choices([True, False], weights=[0.50, 0.50], k=1)[0]


def generate_alert_date(tx: dict[str, Any]) -> date:
    base_date = tx["posting_date"] or tx["trx_datetime"].date()
    delay_days = random.choices([0, 1, 2, 3, 5], weights=[0.25, 0.35, 0.20, 0.15, 0.05], k=1)[0]
    return min(base_date + timedelta(days=delay_days), date.today())


def generate_investigation_status(risk_level: str) -> str:
    if risk_level == "critical":
        return random.choices(
            INVESTIGATION_STATUSES,
            weights=[0.10, 0.28, 0.35, 0.22, 0.05],
            k=1
        )[0]

    if risk_level == "high":
        return random.choices(
            INVESTIGATION_STATUSES,
            weights=[0.14, 0.34, 0.18, 0.20, 0.14],
            k=1
        )[0]

    return random.choices(
        INVESTIGATION_STATUSES,
        weights=[0.18, 0.32, 0.06, 0.12, 0.32],
        k=1
    )[0]


def generate_comment(
    rule_name: str,
    risk_level: str,
    investigation_status: str,
    tx: dict[str, Any]
) -> str:
    amount = f"{tx['amount']}"
    counterparty = tx["counterparty_name"] or "unknown counterparty"

    if investigation_status == "new":
        return f"Автоматическое срабатывание по правилу {rule_name}. Требуется первичная проверка операции на сумму {amount}."

    if investigation_status == "in_review":
        return f"Операция на сумму {amount} направлена на проверку. Контрагент: {counterparty}. Уровень риска: {risk_level}."

    if investigation_status == "escalated":
        return f"Кейс эскалирован в compliance по правилу {rule_name}. Необходим углублённый анализ клиента и источника средств."

    if investigation_status == "closed_true_positive":
        return f"Подозрительная активность подтверждена. Срабатывание по правилу {rule_name}, операция требует AML-контроля."

    return f"Проверка завершена. Существенных отклонений не выявлено, алерт признан false positive по правилу {rule_name}."


def build_alert(tx: dict[str, Any], rule_name: str, risk_level: str) -> dict[str, Any]:
    investigation_status = generate_investigation_status(risk_level)

    return {
        "alert_id": uuid.uuid4().hex,
        "trx_id": tx["trx_id"],
        "client_id": tx["client_id"],
        "alert_date": generate_alert_date(tx).isoformat(),
        "rule_name": rule_name,
        "risk_level": risk_level,
        "investigation_status": investigation_status,
        "analyst_comment": generate_comment(
            rule_name=rule_name,
            risk_level=risk_level,
            investigation_status=investigation_status,
            tx=tx
        ),
    }


def write_csv(file_path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("Нет данных для записи в CSV")

    fieldnames = [
        "alert_id",
        "trx_id",
        "client_id",
        "alert_date",
        "rule_name",
        "risk_level",
        "investigation_status",
        "analyst_comment",
    ]

    with file_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


with get_session("abs") as session:
    transactions = load_transactions(session)

    alerts: list[dict[str, Any]] = []
    used_trx_ids: set[int] = set()

    for tx in transactions:
        if tx["trx_id"] in used_trx_ids:
            continue

        detected = detect_rule(tx)

        if detected is None:
            continue

        rule_name, risk_level = detected

        if not should_create_alert(rule_name, risk_level):
            continue

        alerts.append(build_alert(tx, rule_name, risk_level))
        used_trx_ids.add(tx["trx_id"])

    if not alerts:
        raise ValueError("Не удалось сгенерировать ни одного AML-алерта")

    write_csv(OUTPUT_FILE, alerts)

    print(f"Готово: {OUTPUT_FILE}")
    print(f"Сгенерировано AML alerts: {len(alerts)}")