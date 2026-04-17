import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import TypedDict

from sqlalchemy import text

from db import get_session
from enums import CARD_SETTLEMENT_STATUSES

TOTAL_CLEARINGS = 30000


class AuthorizationRow(TypedDict):
    auth_id: int
    auth_datetime: datetime
    amount: Decimal
    currency: str
    payment_system: str
    card_type: str
    is_international: bool
    pos_entry_mode: str
    remain: int


def load_authorizations(session) -> list[AuthorizationRow]:
    rows = session.execute(
        text("""
             SELECT a.auth_id,
                    a.auth_datetime,
                    a.amount,
                    a.currency::TEXT       AS currency,
                    c.payment_system::TEXT AS payment_system,
                    c.card_type::TEXT      AS card_type,
                    a.is_international,
                    a.pos_entry_mode::TEXT AS pos_entry_mode
             FROM authorizations a
                      JOIN cards c
                           ON c.card_id = a.card_id
                      LEFT JOIN clearing_transactions ct
                                ON ct.auth_id = a.auth_id
             WHERE a.auth_result::TEXT = 'approved'
               AND ct.auth_id IS NULL
             ORDER BY a.auth_id
             """)
    ).mappings().all()

    return [
        {
            "auth_id": row["auth_id"],
            "auth_datetime": row["auth_datetime"],
            "amount": Decimal(str(row["amount"])),
            "currency": row["currency"],
            "payment_system": row["payment_system"],
            "card_type": row["card_type"],
            "is_international": row["is_international"],
            "pos_entry_mode": row["pos_entry_mode"],
            "remain": 1,
        }
        for row in rows
    ]


def get_authorization(authorizations: list[AuthorizationRow]) -> AuthorizationRow:
    available = [auth for auth in authorizations if auth["remain"] > 0]

    if not available:
        raise ValueError("Закончились доступные authorizations")

    auth = random.choice(available)
    auth["remain"] -= 1
    return auth


def generate_settlement_status(auth_datetime: datetime) -> str:
    days_since_auth = (date.today() - auth_datetime.date()).days

    if days_since_auth <= 1:
        return random.choices(
            CARD_SETTLEMENT_STATUSES,
            weights=[0.45, 0.02, 0.53],
            k=1
        )[0]

    if days_since_auth <= 3:
        return random.choices(
            CARD_SETTLEMENT_STATUSES,
            weights=[0.80, 0.04, 0.16],
            k=1
        )[0]

    return random.choices(
        CARD_SETTLEMENT_STATUSES,
        weights=[0.93, 0.04, 0.03],
        k=1
    )[0]


def generate_settlement_date(
        auth_datetime: datetime,
        settlement_status: str,
        is_international: bool,
        pos_entry_mode: str,
) -> date | None:
    auth_date = auth_datetime.date()

    if settlement_status == "pending":
        auth_datetime.date()

    if settlement_status == "settled":
        if is_international or pos_entry_mode == "ecom":
            delay_days = random.choices(
                [1, 2, 3, 4, 5],
                weights=[0.20, 0.35, 0.25, 0.15, 0.05],
                k=1
            )[0]
        else:
            delay_days = random.choices(
                [0, 1, 2, 3],
                weights=[0.20, 0.45, 0.25, 0.10],
                k=1
            )[0]

        return min(auth_date + timedelta(days=delay_days), date.today())

    if settlement_status == "reversed":
        delay_days = random.choices(
            [1, 2, 3, 5, 7, 10, 14],
            weights=[0.20, 0.20, 0.18, 0.15, 0.12, 0.10, 0.05],
            k=1
        )[0]
        return min(auth_date + timedelta(days=delay_days), date.today())

    return auth_datetime.date()


def generate_final_amount(
        auth_amount: Decimal,
        settlement_status: str,
        is_international: bool,
) -> int | Decimal:
    if settlement_status == "pending":
        return auth_amount

    if settlement_status == "reversed":
        return auth_amount.quantize(Decimal("0.01"))

    if settlement_status == "settled":
        if is_international:
            multiplier = Decimal(str(round(random.uniform(0.99, 1.03), 4)))
            final_amount = auth_amount * multiplier
        else:
            same_amount = random.choices([True, False], weights=[0.94, 0.06], k=1)[0]

            if same_amount:
                final_amount = auth_amount
            else:
                multiplier = Decimal(str(round(random.uniform(0.995, 1.005), 4)))
                final_amount = auth_amount * multiplier

        return final_amount.quantize(Decimal("0.01"))

    raise ValueError(f"Unknown settlement_status: {settlement_status}")


def generate_fees(
        final_amount: Decimal | None,
        settlement_status: str,
        payment_system: str,
        card_type: str,
        is_international: bool,
        pos_entry_mode: str,
) -> tuple[Decimal | None, Decimal | None]:
    if settlement_status == "pending":
        return None, None

    if settlement_status == "reversed":
        return Decimal("0.00"), Decimal("0.00")

    if card_type == "debit":
        interchange_rate = Decimal("0.011")
    else:
        interchange_rate = Decimal("0.018")

    if is_international:
        interchange_rate += Decimal("0.003")

    if pos_entry_mode == "ecom":
        interchange_rate += Decimal("0.0015")

    interchange_rate += Decimal(str(round(random.uniform(-0.001, 0.001), 4)))

    if payment_system == "visa":
        scheme_rate = Decimal("0.0012")
    elif payment_system == "mastercard":
        scheme_rate = Decimal("0.0011")
    else:
        scheme_rate = Decimal("0.0010")

    if is_international:
        scheme_rate += Decimal("0.0007")

    if pos_entry_mode == "ecom":
        scheme_rate += Decimal("0.0002")

    interchange_fee = (final_amount * interchange_rate).quantize(Decimal("0.01"))
    scheme_fee = (final_amount * scheme_rate).quantize(Decimal("0.01"))

    if interchange_fee < Decimal("0.00"):
        interchange_fee = Decimal("0.00")

    if scheme_fee < Decimal("0.00"):
        scheme_fee = Decimal("0.00")

    return interchange_fee, scheme_fee


with get_session("card_processing") as session:
    try:
        authorizations = load_authorizations(session)

        max_possible_clearings = sum(auth["remain"] for auth in authorizations)
        total_clearings = min(TOTAL_CLEARINGS, max_possible_clearings)

        for _ in range(total_clearings):
            auth = get_authorization(authorizations)

            settlement_status = generate_settlement_status(auth["auth_datetime"])
            settlement_date = generate_settlement_date(
                auth_datetime=auth["auth_datetime"],
                settlement_status=settlement_status,
                is_international=auth["is_international"],
                pos_entry_mode=auth["pos_entry_mode"],
            )

            final_amount = generate_final_amount(
                auth_amount=auth["amount"],
                settlement_status=settlement_status,
                is_international=auth["is_international"],
            )

            interchange_fee, scheme_fee = generate_fees(
                final_amount=final_amount,
                settlement_status=settlement_status,
                payment_system=auth["payment_system"],
                card_type=auth["card_type"],
                is_international=auth["is_international"],
                pos_entry_mode=auth["pos_entry_mode"],
            )

            row_to_insert = {
                "auth_id": auth["auth_id"],
                "settlement_date": settlement_date,
                "final_amount": final_amount,
                "interchange_fee": interchange_fee,
                "scheme_fee": scheme_fee,
                "settlement_currency": auth["currency"],
                "settlement_status": settlement_status,
            }

            session.execute(
                text("""
                     INSERT INTO clearing_transactions (auth_id,
                                                        settlement_date,
                                                        final_amount,
                                                        interchange_fee,
                                                        scheme_fee,
                                                        settlement_currency,
                                                        settlement_status)
                     VALUES (:auth_id,
                             :settlement_date,
                             :final_amount,
                             :interchange_fee,
                             :scheme_fee,
                             :settlement_currency,
                             :settlement_status)
                     """),
                row_to_insert
            )

        session.commit()

    except Exception:
        session.rollback()
        raise
