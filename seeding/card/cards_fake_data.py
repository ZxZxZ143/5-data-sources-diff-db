import hashlib
import random
from datetime import date
from decimal import Decimal
from typing import TypedDict

from dateutil.relativedelta import relativedelta
from faker import Faker
from sqlalchemy import text

from db import get_session, DB
from enums import CARD_PRODUCTS, CARD_TYPES, CARD_PAYMENT_SYSTEMS, CARD_STATUSES

fake_ru = Faker("ru_RU")
fake_en = Faker("en_US")

TOTAL_CARDS = 7000

class AccountRow(TypedDict):
    client_id: int
    account_id: str
    opened_date: date
    closed_date: date | None
    is_salary_account: bool
    remain: int


def load_accounts(session) -> list[AccountRow]:
    rows = session.execute(
        text("""
            SELECT
                client_id,
                account_id,
                opened_date::date AS opened_date,
                closed_date::date AS closed_date,
                is_salary_account
            FROM accounts
            WHERE product_type = 'current'
            ORDER BY account_id
        """)
    ).mappings().all()

    accounts: list[AccountRow] = []

    for row in rows:
        remain = 2 if row["is_salary_account"] else random.choices(
            [1, 2],
            weights=[0.85, 0.15],
            k=1
        )[0]

        accounts.append(
            {
                "client_id": row["client_id"],
                "account_id": row["account_id"],
                "opened_date": row["opened_date"],
                "closed_date": row["closed_date"],
                "is_salary_account": row["is_salary_account"],
                "remain": remain,
            }
        )

    return accounts


def get_account(accounts: list[AccountRow]) -> AccountRow:
    available_accounts = [account for account in accounts if account["remain"] > 0]

    account = random.choice(available_accounts)
    account["remain"] -= 1
    return account


def generate_card_product(is_salary_account: bool) -> str:
    if is_salary_account:
        return random.choices(
            CARD_PRODUCTS,
            weights=[0.55, 0.30, 0.15],
            k=1
        )[0]

    return random.choices(
        CARD_PRODUCTS,
        weights=[0.70, 0.22, 0.08],
        k=1
    )[0]


def generate_card_type(is_salary_account: bool) -> str:
    if is_salary_account:
        return CARD_TYPES[0]

    return random.choices(
        CARD_TYPES,
        weights=[0.88, 0.12],
        k=1
    )[0]


def generate_payment_system() -> str:
    return random.choices(
        CARD_PAYMENT_SYSTEMS,
        weights=[0.55, 0.45],
        k=1
    )[0]


def generate_issue_date(opened_date: date, closed_date: date | None) -> date:
    end_date = min(closed_date or date.today(), date.today())
    max_issue_date = min(opened_date + relativedelta(days=30), end_date)

    if max_issue_date < opened_date:
        max_issue_date = opened_date

    return fake_ru.date_between_dates(
        date_start=opened_date,
        date_end=max_issue_date
    )


def generate_expiry_date(issue_date: date) -> date:
    years = random.choices([3, 4, 5], weights=[0.15, 0.15, 0.70], k=1)[0]
    return issue_date + relativedelta(years=years)


def generate_card_status(closed_date: date | None, expiry_date: date) -> str:
    today = date.today()

    if expiry_date < today:
        return "expired"

    if closed_date is not None:
        return random.choices(
            CARD_STATUSES,
            weights=[0.8, 0.2, 0],
            k=1
        )[0]

    return "active"


def generate_embossed_name() -> str:
    return fake_en.name().upper()[:100]


def generate_pan_hash(payment_system: str) -> str:
    if payment_system == "visa":
        prefix = "4"
        total_length = 16
    elif payment_system == "mastercard":
        prefix = random.choice(["51", "52", "53", "54", "55"])
        total_length = 16
    else:
        raise ValueError(f"Unknown payment system: {payment_system}")

    raw_pan = prefix + "".join(
        random.choices("0123456789", k=total_length - len(prefix))
    )

    return hashlib.sha256(raw_pan.encode("utf-8")).hexdigest()


def generate_daily_limit(card_product: str, card_type: str) -> Decimal:
    if card_type == "credit":
        if card_product == "classic":
            amount = random.uniform(100_000, 300_000)
        elif card_product == "gold":
            amount = random.uniform(300_000, 700_000)
        else:
            amount = random.uniform(700_000, 1_500_000)
    else:
        if card_product == "classic":
            amount = random.uniform(100_000, 500_000)
        elif card_product == "gold":
            amount = random.uniform(500_000, 1_500_000)
        else:
            amount = random.uniform(1_500_000, 3_000_000)

    return Decimal(str(round(amount, 2)))


with get_session("card_processing") as session:
    try:
        with get_session("abs") as session2:
            accounts = load_accounts(session2)

        max_possible_cards = sum(account["remain"] for account in accounts)
        total_cards = min(TOTAL_CARDS, max_possible_cards)

        for _ in range(total_cards):
            account = get_account(accounts)

            card_product = generate_card_product(account["is_salary_account"])
            card_type = generate_card_type(account["is_salary_account"])
            payment_system = generate_payment_system()

            issue_date = generate_issue_date(
                opened_date=account["opened_date"],
                closed_date=account["closed_date"]
            )

            expiry_date = generate_expiry_date(issue_date)
            card_status = generate_card_status(
                closed_date=account["closed_date"],
                expiry_date=expiry_date
            )

            row_to_insert = {
                "client_id": account["client_id"],
                "account_id": account["account_id"],
                "card_pan_hash": generate_pan_hash(payment_system),
                "card_product": card_product,
                "expiry_date": expiry_date,
                "embossed_name": generate_embossed_name(),
                "card_status": card_status,
                "issue_date": issue_date,
                "card_type": card_type,
                "payment_system": payment_system,
                "daily_limit": generate_daily_limit(card_product, card_type),
            }

            session.execute(
                text("""
                    INSERT INTO cards (
                        client_id,
                        account_id,
                        card_pan_hash,
                        card_product,
                        expiry_date,
                        embossed_name,
                        card_status,
                        issue_date,
                        card_type,
                        payment_system,
                        daily_limit
                    )
                    VALUES (
                        :client_id,
                        :account_id,
                        :card_pan_hash,
                        :card_product,
                        :expiry_date,
                        :embossed_name,
                        :card_status,
                        :issue_date,
                        :card_type,
                        :payment_system,
                        :daily_limit
                    )
                """),
                row_to_insert
            )

        session.commit()

    except Exception:
        session.rollback()
        raise