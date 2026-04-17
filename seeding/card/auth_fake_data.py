import random
import string
from datetime import date, datetime, time
from decimal import Decimal
from typing import TypedDict
import pandas as pd
from faker import Faker
from sqlalchemy import text

from db import get_session
from enums import CARD_POS_ENTRY_MODES, CITIES, DOMESTIC_COUNTRY_CODE, FOREIGN_COUNTRIES, INTERNATIONAL_MERCHANTS, \
    ECOM_MERCHANTS, DOMESTIC_MERCHANTS, DECLINE_REASONS

fake = Faker("ru_RU")

TOTAL_AUTHORIZATIONS = 30000

class CardRow(TypedDict):
    card_id: int
    client_id: int
    currency: str
    issue_date: date
    expiry_date: date
    card_status: str
    card_type: str
    payment_system: str
    daily_limit: Decimal
    remain: int


def load_cards() -> list[dict]:
    with get_session("card_processing") as session:
        card_rows = session.execute(
            text("""
                 SELECT c.card_id,
                        c.client_id,
                        c.account_id,
                        c.issue_date::DATE     AS issue_date,
                        c.expiry_date::DATE    AS expiry_date,
                        c.card_status::TEXT    AS card_status,
                        c.card_type::TEXT      AS card_type,
                        c.payment_system::TEXT AS payment_system,
                        c.daily_limit
                 FROM cards c
                 ORDER BY c.card_id
                 """)
        ).mappings().all()

    with get_session("abs") as session:
        account_rows = session.execute(
            text("""
                 SELECT account_id,
                        currency
                 FROM accounts
                 """)
        ).mappings().all()

    df_cards = pd.DataFrame(card_rows)
    df_accounts = pd.DataFrame(account_rows)

    df = df_cards.merge(
        df_accounts,
        on="account_id",
        how="left"
    )

    df["remain"] = df["card_status"].apply(
        lambda status: random.randint(5, 20) if status == "active" else random.randint(1, 3)
    )

    return df.to_dict(orient="records")


def get_card(cards: list[CardRow]) -> CardRow:
    available_cards = [card for card in cards if card["remain"] > 0]

    weights = []
    for card in available_cards:
        if card["card_status"] == "active":
            weights.append(0.94)
        elif card["card_status"] == "blocked":
            weights.append(0.04)
        else:
            weights.append(0.02)

    card = random.choices(available_cards, weights=weights, k=1)[0]
    card["remain"] -= 1
    return card


def generate_auth_datetime(issue_date: date, expiry_date: date) -> datetime:
    end_date = min(expiry_date, date.today())

    if issue_date > end_date:
        start_dt = datetime.combine(issue_date, time.min)
        return start_dt

    return fake.date_time_between_dates(
        datetime_start=datetime.combine(issue_date, time.min),
        datetime_end=datetime.combine(end_date, time.max),
    )


def generate_pos_entry_mode(card_type: str) -> str:
    if card_type == "credit":
        return random.choices(
            CARD_POS_ENTRY_MODES,
            weights=[0.30, 0.25, 0.45],
            k=1
        )[0]

    return random.choices(
        CARD_POS_ENTRY_MODES,
        weights=[0.35, 0.45, 0.20],
        k=1
    )[0]


def generate_country_code(pos_entry_mode: str) -> tuple[str, bool]:
    if pos_entry_mode == "ecom":
        is_international = random.choices([False, True], weights=[0.78, 0.22], k=1)[0]
    else:
        is_international = random.choices([False, True], weights=[0.93, 0.07], k=1)[0]

    if is_international:
        return random.choice(FOREIGN_COUNTRIES), True

    return DOMESTIC_COUNTRY_CODE, False


def generate_merchant(pos_entry_mode: str, is_international: bool) -> dict:
    if is_international:
        merchant = random.choice(INTERNATIONAL_MERCHANTS)
    elif pos_entry_mode == "ecom":
        merchant = random.choice(ECOM_MERCHANTS)
    else:
        merchant = random.choice(DOMESTIC_MERCHANTS)

    merchant_id = "MID" + "".join(random.choices(string.digits, k=9))

    return {
        "merchant_id": merchant_id,
        "merchant_name": merchant["name"],
        "merchant_category_code": merchant["mcc"],
        "min_amount": merchant["min_amount"],
        "max_amount": merchant["max_amount"],
    }


def generate_amount(
        merchant_min: int | float,
        merchant_max: int | float,
        currency: str,
        is_international: bool
) -> int:
    amount = random.uniform(merchant_min, merchant_max)

    if not is_international and currency == "KZT":
        return int(round(amount, 2))

    return int(round(amount, 2))


def generate_auth_result_and_decline_reason(
        card_status: str,
        amount: Decimal,
        daily_limit: Decimal,
        is_international: bool,
        pos_entry_mode: str
) -> tuple[str, str | None]:
    if card_status == "blocked":
        return "declined", "card_blocked"

    if card_status == "expired":
        return "declined", "card_expired"

    if amount > daily_limit:
        return "declined", "limit_exceeded"

    decline_probability = 0.05

    if is_international:
        decline_probability += 0.03

    if pos_entry_mode == "ecom":
        decline_probability += 0.02

    if amount > (daily_limit * Decimal("0.7")):
        decline_probability += 0.05

    is_approved = random.choices(
        [True, False],
        weights=[1 - decline_probability, decline_probability],
        k=1
    )[0]

    if is_approved:
        return "approved", None

    return "declined", random.choice(DECLINE_REASONS)


def generate_auth_code(auth_result: str) -> str | None:
    if auth_result == "approved":
        return "".join(random.choices(string.digits, k=6))

    return None


def generate_terminal_id(pos_entry_mode: str) -> str:
    if pos_entry_mode == "ecom":
        return "ECOM-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))

    return "TERM-" + "".join(random.choices(string.digits, k=8))


with get_session("card_processing") as session:
    try:
        cards = load_cards()

        max_possible_auths = sum(card["remain"] for card in cards)
        total_auths = min(TOTAL_AUTHORIZATIONS, max_possible_auths)

        for _ in range(total_auths):
            card = get_card(cards)

            auth_datetime = generate_auth_datetime(
                issue_date=card["issue_date"],
                expiry_date=card["expiry_date"]
            )

            pos_entry_mode = generate_pos_entry_mode(card["card_type"])
            country_code, is_international = generate_country_code(pos_entry_mode)
            merchant = generate_merchant(pos_entry_mode, is_international)

            amount = generate_amount(
                merchant_min=merchant["min_amount"],
                merchant_max=merchant["max_amount"],
                currency=card["currency"],
                is_international=is_international
            )

            auth_result, decline_reason = generate_auth_result_and_decline_reason(
                card_status=card["card_status"],
                amount=amount,
                daily_limit=Decimal(str(card["daily_limit"])),
                is_international=is_international,
                pos_entry_mode=pos_entry_mode
            )

            row_to_insert = {
                "card_id": card["card_id"],
                "auth_datetime": auth_datetime,
                "merchant_id": merchant["merchant_id"],
                "merchant_name": merchant["merchant_name"][:150],
                "merchant_category_code": merchant["merchant_category_code"],
                "amount": amount,
                "currency": card["currency"],
                "auth_code": generate_auth_code(auth_result),
                "auth_result": auth_result,
                "decline_reason": decline_reason,
                "terminal_id": generate_terminal_id(pos_entry_mode),
                "country_code": country_code,
                "city": random.choice(CITIES),
                "pos_entry_mode": pos_entry_mode,
                "is_international": is_international,
            }

            session.execute(
                text("""
                     INSERT INTO authorizations (card_id,
                                                 auth_datetime,
                                                 merchant_id,
                                                 merchant_name,
                                                 merchant_category_code,
                                                 amount,
                                                 currency,
                                                 auth_code,
                                                 auth_result,
                                                 decline_reason,
                                                 terminal_id,
                                                 country_code,
                                                 city,
                                                 pos_entry_mode,
                                                 is_international)
                     VALUES (:card_id,
                             :auth_datetime,
                             :merchant_id,
                             :merchant_name,
                             :merchant_category_code,
                             :amount,
                             :currency,
                             :auth_code,
                             :auth_result,
                             :decline_reason,
                             :terminal_id,
                             :country_code,
                             :city,
                             :pos_entry_mode,
                             :is_international)
                     """),
                row_to_insert
            )

        session.commit()

    except Exception:
        session.rollback()
        raise
