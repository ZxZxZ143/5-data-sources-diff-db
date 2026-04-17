import random
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import TypedDict

from dateutil.relativedelta import relativedelta
from sqlalchemy import text

from db import get_session
from enums import LOAN_PAYMENT_STATUSES


class LoanRow(TypedDict):
    loan_id: int
    approved_amount: Decimal
    interest_rate: Decimal
    disbursement_date: date
    maturity_date: date
    loan_status: str
    requested_term_months: int


def q(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def load_loans_without_schedule(session) -> list[LoanRow]:
    rows = session.execute(
        text("""
            SELECT
                lg.loan_id,
                lg.approved_amount,
                lg.interest_rate,
                lg.disbursement_date::date AS disbursement_date,
                lg.maturity_date::date AS maturity_date,
                lg.loan_status::text AS loan_status,
                la.requested_term_months
            FROM loan_agreements lg
            JOIN loan_applications la
              ON la.application_id = lg.application_id
            LEFT JOIN payment_schedule ps
              ON ps.loan_id = lg.loan_id
            WHERE ps.loan_id IS NULL
            ORDER BY lg.loan_id
        """)
    ).mappings().all()

    if not rows:
        raise ValueError("Нет loan_agreements без payment_schedule")

    return [
        {
            "loan_id": row["loan_id"],
            "approved_amount": Decimal(str(row["approved_amount"])),
            "interest_rate": Decimal(str(row["interest_rate"])),
            "disbursement_date": row["disbursement_date"],
            "maturity_date": row["maturity_date"],
            "loan_status": row["loan_status"],
            "requested_term_months": row["requested_term_months"],
        }
        for row in rows
    ]


def generate_payment_status(loan_status: str, due_date: date) -> str:
    today = date.today()

    if due_date > today:
        return "planned"

    if loan_status == "paid":
        return "paid"

    if loan_status == "default":
        return random.choices(
            LOAN_PAYMENT_STATUSES,
            weights=[0.0, 0.08, 0.72, 0.20],
            k=1
        )[0]

    if loan_status == "restructured":
        return random.choices(
            LOAN_PAYMENT_STATUSES,
            weights=[0.0, 0.60, 0.12, 0.28],
            k=1
        )[0]

    overdue_days = (today - due_date).days

    if overdue_days <= 15:
        return random.choices(
            LOAN_PAYMENT_STATUSES,
            weights=[0.0, 0.72, 0.12, 0.16],
            k=1
        )[0]

    return random.choices(
        LOAN_PAYMENT_STATUSES,
        weights=[0.0, 0.82, 0.08, 0.10],
        k=1
    )[0]


def generate_payment_facts(
    due_date: date,
    total_due: Decimal,
    payment_status: str
) -> tuple[date | None, Decimal | None, int]:
    today = date.today()

    if payment_status == "planned":
        return None, None, 0

    if payment_status == "paid":
        payment_date = min(
            due_date + relativedelta(days=random.choice([-3, -1, 0, 1, 3, 5])),
            today
        )
        overdue_days = max((payment_date - due_date).days, 0)
        return payment_date, total_due, overdue_days

    if payment_status == "partial":
        payment_date = min(
            due_date + relativedelta(days=random.choice([0, 1, 3, 5, 10, 15])),
            today
        )
        paid_ratio = Decimal(str(round(random.uniform(0.35, 0.90), 2)))
        actual_paid = q(total_due * paid_ratio)
        overdue_days = max((today - due_date).days, 0)
        return payment_date, actual_paid, overdue_days

    if payment_status == "overdue":
        overdue_days = max((today - due_date).days, 1)
        return None, None, overdue_days

    raise ValueError(f"Unknown payment_status: {payment_status}")


with get_session("loan_system") as session:
    try:
        loans = load_loans_without_schedule(session)

        TOTAL_LOANS_FOR_SCHEDULE = 100

        if len(loans) > TOTAL_LOANS_FOR_SCHEDULE:
            loans = random.sample(loans, TOTAL_LOANS_FOR_SCHEDULE)

        for loan in loans:
            term = loan["requested_term_months"]
            approved_amount = loan["approved_amount"]
            monthly_rate = loan["interest_rate"] / Decimal("1200")

            remaining_principal = approved_amount
            base_principal = q(approved_amount / Decimal(term))

            for installment_number in range(1, term + 1):
                due_date = loan["disbursement_date"] + relativedelta(months=installment_number)

                if installment_number == term:
                    principal_due = q(remaining_principal)
                else:
                    principal_due = base_principal

                interest_due = q(remaining_principal * monthly_rate)
                total_due = q(principal_due + interest_due)

                payment_status = generate_payment_status(
                    loan_status=loan["loan_status"],
                    due_date=due_date
                )

                actual_payment_date, actual_paid, overdue_days = generate_payment_facts(
                    due_date=due_date,
                    total_due=total_due,
                    payment_status=payment_status
                )

                row_to_insert = {
                    "loan_id": loan["loan_id"],
                    "due_date": due_date,
                    "principal_due": principal_due,
                    "interest_due": interest_due,
                    "total_due": total_due,
                    "actual_payment_date": actual_payment_date,
                    "actual_paid": actual_paid,
                    "overdue_days": overdue_days,
                    "installment_number": installment_number,
                    "payment_status": payment_status,
                }

                session.execute(
                    text("""
                        INSERT INTO payment_schedule (
                            loan_id,
                            due_date,
                            principal_due,
                            interest_due,
                            total_due,
                            actual_payment_date,
                            actual_paid,
                            overdue_days,
                            installment_number,
                            payment_status
                        )
                        VALUES (
                            :loan_id,
                            :due_date,
                            :principal_due,
                            :interest_due,
                            :total_due,
                            :actual_payment_date,
                            :actual_paid,
                            :overdue_days,
                            :installment_number,
                            :payment_status
                        )
                    """),
                    row_to_insert
                )

                remaining_principal = q(remaining_principal - principal_due)

        session.commit()

    except Exception:
        session.rollback()
        raise