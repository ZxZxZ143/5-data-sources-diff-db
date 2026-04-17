import datetime
import random
import uuid
from typing import TypedDict

from faker import Faker
from sqlalchemy import text

from db import get_session
from enums import ABS_TRX_TYPES, ABS_TRANSACTION_STATUSES, CITIES


class Account(TypedDict):
    account_id: str
    opened_date: datetime.date
    closed_date: datetime.date
    currency: str


type Accounts = list[Account]

fake = Faker("ru_RU")

TOTAL_TRX = 30000

TRX_TYPES_WEIGHTS = [0.2, 0.35, 0.35, 0.1]

TRANSACTION_STATUSES_WEIGHTS = [
    .9,
    .03,
    .07,
]

PURCHASE_MCC_CODES = [
    "5411",
    "5499",
    "5812",
    "5814",
    "5912",
    "5999",
    "5732",
    "5541",
]

CASH_MCC_CODES = [
    "6011",
]

SERVICE_MCC_CODES = [
    "4814",
    "4900",
    "9399",
]

MERCHANT_NAMES = [
    "Magnum",
    "Small",
    "Technodom",
    "Sulpak",
    "Mechta",
    "Burger King",
    "KFC",
    "Dodo Pizza",
    "Starbucks",
    "Invivo",
    "Meloman",
]

EMPLOYER_NAMES = [
    'TOO "Tech Solutions"',
    'TOO "Digital Trade"',
    'AO "Banking Group"',
    'TOO "Retail Service"',
    'TOO "Logistics KZ"',
]

ATM_NAMES = [
    "ATM Halyk",
    "ATM Kaspi",
    "ATM Freedom Bank",
    "ATM Jusan",
    "ATM CenterCredit",
]

SERVICE_NAMES = [
    "Beeline",
    "Kcell",
    "Activ",
    "Kazakhtelecom",
    "Alseco",
    "Kaspi Pay",
]


def generate_counterparty_fields(trx_type: str) -> dict:
    if trx_type == "transfer":
        return {
            "counterparty_account": uuid.uuid4().hex[:20],
            "counterparty_name": fake_name(),
        }

    if trx_type == "credit":
        source = random.choices(
            ["salary", "refund", "topup"],
            weights=[0.5, 0.2, 0.3],
            k=1
        )[0]

        if source == "salary":
            return {
                "counterparty_account": uuid.uuid4().hex[:20],
                "counterparty_name": random.choice(EMPLOYER_NAMES),
            }

        if source == "refund":
            return {
                "counterparty_account": None,
                "counterparty_name": random.choice(MERCHANT_NAMES),
            }

        return {
            "counterparty_account": None,
            "counterparty_name": "Cash-in / Пополнение",
        }

    if trx_type == "debit":
        debit_kind = random.choices(
            ["merchant", "service"],
            weights=[0.75, 0.25],
            k=1
        )[0]

        if debit_kind == "merchant":
            return {
                "counterparty_account": None,
                "counterparty_name": random.choice(MERCHANT_NAMES),
            }

        return {
            "counterparty_account": None,
            "counterparty_name": random.choice(SERVICE_NAMES),
        }

    if trx_type == "cash_withdrawal":
        return {
            "counterparty_account": None,
            "counterparty_name": random.choice(ATM_NAMES),
        }

    raise ValueError(f"Unknown trx_type: {trx_type}")


def fake_name() -> str:
    first_names = [fake.first_name() for _ in range(100)]
    last_names = [fake.last_name() for _ in range(100)]
    return f"{random.choice(first_names)} {random.choice(last_names)}"

def generate_channel_by_trx_type(trx_type: str) -> str:
    channel_rules = {
        "credit": {
            "channels": ["mobile_app", "web", "atm", "branch", "terminal"],
            "weights": [0.35, 0.20, 0.20, 0.15, 0.10],
        },
        "debit": {
            "channels": ["terminal", "mobile_app", "web", "branch"],
            "weights": [0.55, 0.20, 0.20, 0.05],
        },
        "transfer": {
            "channels": ["mobile_app", "web", "branch", "terminal"],
            "weights": [0.60, 0.25, 0.10, 0.05],
        },
        "cash_withdrawal": {
            "channels": ["atm", "branch"],
            "weights": [0.90, 0.10],
        },
    }

    rule = channel_rules[trx_type]

    return random.choices(
        rule["channels"],
        weights=rule["weights"],
        k=1
    )[0]


def generate_mcc_code(trx_type: str) -> str | None:
    if trx_type == "debit":
        return random.choice(PURCHASE_MCC_CODES)

    if trx_type == "cash_withdrawal":
        return random.choice(CASH_MCC_CODES)

    if trx_type == "credit":
        return None

    if trx_type == "transfer":
        return None

    return None

def generate_amount(trx_type: str) -> int:

    if trx_type == "debit":
        zone = random.choices(
            ["small", "medium", "large"],
            weights=[0.65, 0.30, 0.05],
            k=1
        )[0]

        if zone == "small":
            amount = random.uniform(500, 15_000)
        elif zone == "medium":
            amount = random.uniform(15_000, 120_000)
        else:
            amount = random.uniform(120_000, 600_000)

    elif trx_type == "credit":
        zone = random.choices(
            ["small", "medium", "large"],
            weights=[0.35, 0.45, 0.20],
            k=1
        )[0]

        if zone == "small":
            amount = random.uniform(1_000, 30_000)
        elif zone == "medium":
            amount = random.uniform(30_000, 250_000)
        else:
            amount = random.uniform(250_000, 1_500_000)

    elif trx_type == "transfer":
        zone = random.choices(
            ["small", "medium", "large"],
            weights=[0.30, 0.50, 0.20],
            k=1
        )[0]

        if zone == "small":
            amount = random.uniform(2_000, 50_000)
        elif zone == "medium":
            amount = random.uniform(50_000, 400_000)
        else:
            amount = random.uniform(400_000, 2_000_000)

    elif trx_type == "cash_withdrawal":
        zone = random.choices(
            ["small", "medium", "large"],
            weights=[0.45, 0.45, 0.10],
            k=1
        )[0]

        if zone == "small":
            amount = random.uniform(1_000, 20_000)
        elif zone == "medium":
            amount = random.uniform(20_000, 100_000)
        else:
            amount = random.uniform(100_000, 500_000)

    else:
        raise ValueError(f"Unknown trx_type: {trx_type}")

    return int(round(amount, 2))

def generate_reference(trx_type: str, counterparty_name: str | None) -> str | None:
    if trx_type == "debit":
        return f"Оплата покупки в {counterparty_name}"
    if trx_type == "transfer":
        return f"Перевод {counterparty_name}"
    if trx_type == "cash_withdrawal":
        return f"Снятие наличных в {counterparty_name}"
    if trx_type == "credit":
        return f"Зачисление от {counterparty_name}"

    return None

def generate_posting_date(trx_datetime):
    if random.random() < 0.85:
        return trx_datetime.date()
    return (trx_datetime + datetime.timedelta(days=1)).date()

with get_session("abs") as session:
    accounts: Accounts = [
        {
            "account_id": row["account_id"],
            "opened_date": row["opened_date"],
            "closed_date": row["closed_date"],
            "currency": row["currency"],
        }
        for row in session.execute(
            text("""
                 SELECT account_id, currency, opened_date, closed_date
                 FROM accounts
                 """
                 )).mappings().all()
    ]

    for _ in range(TOTAL_TRX):

        account: Account = random.choice(accounts)

        trx_type = random.choices(ABS_TRX_TYPES, weights=TRX_TYPES_WEIGHTS, k=1)[0]

        channel = generate_channel_by_trx_type(trx_type)

        trx_datetime = fake.date_time_between(
            start_date=account["opened_date"],
            end_date=datetime.date.today() if account["closed_date"] is None else account["closed_date"],
        )

        counterparty = generate_counterparty_fields(trx_type)

        status = random.choices(ABS_TRANSACTION_STATUSES, weights=TRANSACTION_STATUSES_WEIGHTS, k=1)[0]

        posting_date = generate_posting_date(trx_datetime)

        row_to_insert = {
            "account_id": account["account_id"],
            "trx_datetime": trx_datetime,
            "trx_type": trx_type,
            "amount": generate_amount(trx_type),
            "currency": account["currency"],
            "counterparty_account": counterparty["counterparty_account"],
            "counterparty_name": counterparty["counterparty_name"],
            "reference": generate_reference(trx_type, counterparty["counterparty_name"]),
            "channel": generate_channel_by_trx_type(trx_type),
            "posting_date": posting_date,
            "status": status,
            "mcc_code": generate_mcc_code(trx_type),
            "city": random.choice(CITIES),
        }

        session.execute(
            text("""
                 INSERT INTO transactions (account_id,
                                               trx_datetime,
                                               trx_type,
                                               amount,
                                               currency,
                                               counterparty_account,
                                               counterparty_name,
                                               reference,
                                               channel,
                                               posting_date,
                                               status,
                                               mcc_code,
                                               city)
                 VALUES (:account_id,
                         :trx_datetime,
                         :trx_type,
                         :amount,
                         :currency,
                         :counterparty_account,
                         :counterparty_name,
                         :reference,
                         :channel,
                         :posting_date,
                         :status,
                         :mcc_code,
                         :city)
                 """),
            row_to_insert
        )

    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
