import random
from datetime import date
from typing import TypedDict

from dateutil.relativedelta import relativedelta
from faker import Faker
from sqlalchemy import text

from db import get_session, DB
from enums import ABS_PRODUCT_TYPES, CURRENCIES, BRANCHES, ABS_ACCOUNT_STATUSES


class Client(TypedDict):
    client_id: int
    registration_date: date
    remain: int


type Clients = list[Client]


fake = Faker("ru_RU")

TOTAL_ACCOUNTS = 7000

PRODUCT_TYPE_WEIGHTS = [0.7, 0.2, 0.1]

CURRENCY_WEIGHTS = [0.8, 0.15, 0.05]

ACCOUNT_STATUS_WEIGHTS = [0.3, 0.7]

SALARY_ACCOUNT_WEIGHTS = [0.3, 0.7]

client_pool = []


def get_client_id(clients: Clients) -> Client:
    rand_client = random.choice(clients)

    while rand_client['remain'] <= 0:
        rand_client = random.choice(clients)

    rand_client['remain'] -= 1

    return rand_client


def generate_balance_by_product_type(product_type: str) -> int:

    if product_type == "current":
        zone = random.choices(
            ["low", "medium", "high"],
            weights=[0.70, 0.25, 0.05],
            k=1
        )[0]

        if zone == "low":
            amount = random.uniform(0, 150_000)
        elif zone == "medium":
            amount = random.uniform(150_000, 800_000)
        else:
            amount = random.uniform(800_000, 3_000_000)

    elif product_type == "savings":
        zone = random.choices(
            ["low", "medium", "high"],
            weights=[0.20, 0.55, 0.25],
            k=1
        )[0]

        if zone == "low":
            amount = random.uniform(50_000, 500_000)
        elif zone == "medium":
            amount = random.uniform(500_000, 3_000_000)
        else:
            amount = random.uniform(3_000_000, 10_000_000)

    elif product_type == "deposit":
        zone = random.choices(
            ["medium", "high", "very_high"],
            weights=[0.25, 0.50, 0.25],
            k=1
        )[0]

        if zone == "medium":
            amount = random.uniform(500_000, 3_000_000)
        elif zone == "high":
            amount = random.uniform(3_000_000, 12_000_000)
        else:
            amount = random.uniform(12_000_000, 40_000_000)

    else:
        raise ValueError(f"Unknown product type: {product_type}")

    return int(round(amount))

with get_session("abs") as session:
    client_rows: Clients = [
        {
            "client_id": row["client_id"],
            "registration_date": row["registration_date"],
            "remain": row["remain"],
        }
        for row in session.execute(
            text("""
                 SELECT client_id, registration_date::DATE AS registration_date, 6 AS remain
                 FROM clients
                 ORDER BY client_id
                 """)
        ).mappings().all()
    ]

    for _ in range(TOTAL_ACCOUNTS):

        client: Client = get_client_id(client_rows)

        product_type = random.choices(ABS_PRODUCT_TYPES, weights=PRODUCT_TYPE_WEIGHTS, k=1)[0]

        opened_date = fake.date_between_dates(
                date_start=client["registration_date"],
                date_end=date.today()
            )

        closed_date = random.choices([fake.date_between_dates(
                date_start= min(opened_date + relativedelta(months=1), date.today()),
                date_end=date.today()
            ), None], weights=[0.2, 0.8], k=1)[0]

        account_status = ABS_ACCOUNT_STATUSES[0]

        if closed_date is not None:
            account_status = random.choices(
                [ABS_ACCOUNT_STATUSES[1], ABS_ACCOUNT_STATUSES[2]],
                weights=ACCOUNT_STATUS_WEIGHTS,
                k=1
            )[0]

        row_to_insert = {
            "account_id": fake.uuid4().replace("-", ""),
            "client_id": client["client_id"],
            "product_type": product_type,
            "currency": random.choices(CURRENCIES, weights=CURRENCY_WEIGHTS, k=1)[0],
            "balance": generate_balance_by_product_type(product_type),
            "opened_date": opened_date,
            "closed_date": closed_date,
            "branch_code": random.choice(BRANCHES),
            "account_status": account_status,
            "is_salary_account": random.choices(
                [True, False],
                weights=SALARY_ACCOUNT_WEIGHTS,
                k=1
            )[0],
        }

        session.execute(
            text("""
                 INSERT INTO accounts (account_id,
                                       client_id,
                                       product_type,
                                       currency,
                                       balance,
                                       opened_date,
                                       closed_date,
                                       branch_code,
                                       account_status,
                                       is_salary_account)
                 VALUES (:account_id,
                         :client_id,
                         :product_type,
                         :currency,
                         :balance,
                         :opened_date,
                         :closed_date,
                         :branch_code,
                         :account_status,
                         :is_salary_account)
                 """),
            row_to_insert
        )

    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
