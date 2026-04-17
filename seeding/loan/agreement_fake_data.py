import random
from datetime import date
from decimal import Decimal
from typing import TypedDict

from dateutil.relativedelta import relativedelta
from sqlalchemy import text

from db import get_session
from enums import LOAN_STATUSES

TOTAL_LOANS = 2000

class ApplicationRow(TypedDict):
    application_id: int
    application_dt: date
    decision_dt: date
    requested_amount: Decimal
    requested_term_months: int
    purpose_code: str
    income_amount: Decimal
    credit_score: int
    assigned_risk_grade: str
    remain: int


def load_approved_applications(session) -> list[ApplicationRow]:
    rows = session.execute(
        text("""
            SELECT
                la.application_id,
                la.application_dt::date AS application_dt,
                la.decision_dt::date AS decision_dt,
                la.requested_amount,
                la.requested_term_months,
                la.purpose_code::text AS purpose_code,
                la.income_amount,
                la.credit_score,
                la.assigned_risk_grade::text AS assigned_risk_grade
            FROM loan_applications la
            LEFT JOIN loan_agreements lg
              ON lg.application_id = la.application_id
            WHERE la.status::text = 'approved'
              AND lg.application_id IS NULL
            ORDER BY la.application_id
        """)
    ).mappings().all()

    if not rows:
        raise ValueError("Нет approved заявок без соглашения")

    return [
        {
            "application_id": row["application_id"],
            "application_dt": row["application_dt"],
            "decision_dt": row["decision_dt"],
            "requested_amount": Decimal(str(row["requested_amount"])),
            "requested_term_months": row["requested_term_months"],
            "purpose_code": row["purpose_code"],
            "income_amount": Decimal(str(row["income_amount"])),
            "credit_score": row["credit_score"],
            "assigned_risk_grade": row["assigned_risk_grade"],
            "remain": 1,
        }
        for row in rows
    ]


def get_application(applications: list[ApplicationRow]) -> ApplicationRow:
    available = [app for app in applications if app["remain"] > 0]

    if not available:
        raise ValueError("Закончились approved заявки для генерации договоров")

    app = random.choice(available)
    app["remain"] -= 1
    return app


def generate_approved_amount(
    requested_amount: Decimal,
    risk_grade: str
) -> Decimal:
    if risk_grade == "A":
        ratio = random.uniform(0.95, 1.00)
    elif risk_grade == "B":
        ratio = random.uniform(0.85, 0.95)
    elif risk_grade == "C":
        ratio = random.uniform(0.70, 0.85)
    else:
        ratio = random.uniform(0.55, 0.75)

    amount = requested_amount * Decimal(str(ratio))
    amount = Decimal(str(round(float(amount) / 1000) * 1000))
    return amount.quantize(Decimal("0.01"))


def generate_interest_rate(
    purpose_code: str,
    risk_grade: str
) -> Decimal:
    if purpose_code == "mortgage":
        base = {
            "A": 15.5,
            "B": 17.0,
            "C": 18.5,
            "D": 20.0,
        }[risk_grade]
    elif purpose_code == "car":
        base = {
            "A": 17.0,
            "B": 18.5,
            "C": 20.0,
            "D": 22.0,
        }[risk_grade]
    else:
        base = {
            "A": 19.0,
            "B": 21.0,
            "C": 23.0,
            "D": 25.0,
        }[risk_grade]

    rate = base + random.uniform(-0.5, 0.8)
    return Decimal(str(round(rate, 2)))


def generate_effective_rate(interest_rate: Decimal) -> Decimal:
    addon = Decimal(str(round(random.uniform(0.8, 3.0), 2)))
    return (interest_rate + addon).quantize(Decimal("0.01"))


def generate_disbursement_date(decision_dt: date) -> date:
    return min(
        decision_dt + relativedelta(days=random.choice([0, 1, 2, 3, 5])),
        date.today()
    )


def generate_maturity_date(disbursement_date: date, term_months: int) -> date:
    return disbursement_date + relativedelta(months=term_months)


def generate_collateral_type(purpose_code: str) -> str:
    if purpose_code == "mortgage":
        return "real_estate"
    if purpose_code == "car":
        return "car"
    return "none"


def generate_loan_status(disbursement_date: date, maturity_date: date, risk_grade: str) -> str:
    today = date.today()

    if maturity_date < today:
        return random.choices(
            LOAN_STATUSES,
            weights=[0.10, 0.65, 0.15, 0.10],
            k=1
        )[0]

    if risk_grade == "D":
        return random.choices(
            LOAN_STATUSES,
            weights=[0.70, 0.05, 0.20, 0.05],
            k=1
        )[0]

    if risk_grade == "C":
        return random.choices(
            LOAN_STATUSES,
            weights=[0.78, 0.06, 0.10, 0.06],
            k=1
        )[0]

    return random.choices(
        LOAN_STATUSES,
        weights=[0.88, 0.07, 0.02, 0.03],
        k=1
    )[0]


def generate_balances(
    approved_amount: Decimal,
    disbursement_date: date,
    maturity_date: date,
    loan_status: str
) -> tuple[Decimal, Decimal, Decimal]:
    today = date.today()

    if loan_status == "paid":
        return Decimal("0.00"), Decimal("0.00"), Decimal("0.00")

    if loan_status == "default":
        principal = approved_amount * Decimal(str(random.uniform(0.45, 0.95)))
        interest = approved_amount * Decimal(str(random.uniform(0.02, 0.10)))
        overdue = approved_amount * Decimal(str(random.uniform(0.05, 0.20)))
        return (
            principal.quantize(Decimal("0.01")),
            interest.quantize(Decimal("0.01")),
            overdue.quantize(Decimal("0.01")),
        )

    if loan_status == "restructured":
        principal = approved_amount * Decimal(str(random.uniform(0.25, 0.70)))
        interest = approved_amount * Decimal(str(random.uniform(0.01, 0.05)))
        overdue = approved_amount * Decimal(str(random.uniform(0.00, 0.04)))
        return (
            principal.quantize(Decimal("0.01")),
            interest.quantize(Decimal("0.01")),
            overdue.quantize(Decimal("0.01")),
        )

    total_days = max((maturity_date - disbursement_date).days, 1)
    passed_days = min(max((today - disbursement_date).days, 0), total_days)
    paid_ratio = Decimal(str(passed_days / total_days))

    principal = approved_amount * (Decimal("1.00") - paid_ratio)
    principal = max(principal, approved_amount * Decimal("0.03"))

    interest = approved_amount * Decimal(str(random.uniform(0.003, 0.02)))
    overdue = Decimal("0.00")

    if random.random() < 0.10:
        overdue = approved_amount * Decimal(str(random.uniform(0.002, 0.02)))

    return (
        principal.quantize(Decimal("0.01")),
        interest.quantize(Decimal("0.01")),
        overdue.quantize(Decimal("0.01")),
    )


with get_session("loan_system") as session:
    try:
        applications = load_approved_applications(session)

        max_possible = sum(app["remain"] for app in applications)
        total_loans = min(TOTAL_LOANS, max_possible)

        for _ in range(total_loans):
            app = get_application(applications)

            approved_amount = generate_approved_amount(
                requested_amount=app["requested_amount"],
                risk_grade=app["assigned_risk_grade"]
            )

            interest_rate = generate_interest_rate(
                purpose_code=app["purpose_code"],
                risk_grade=app["assigned_risk_grade"]
            )

            effective_rate = generate_effective_rate(interest_rate)
            disbursement_date = generate_disbursement_date(app["decision_dt"])
            maturity_date = generate_maturity_date(disbursement_date, app["requested_term_months"])
            collateral_type = generate_collateral_type(app["purpose_code"])

            loan_status = generate_loan_status(
                disbursement_date=disbursement_date,
                maturity_date=maturity_date,
                risk_grade=app["assigned_risk_grade"]
            )

            outstanding_principal, outstanding_interest, overdue_amount = generate_balances(
                approved_amount=approved_amount,
                disbursement_date=disbursement_date,
                maturity_date=maturity_date,
                loan_status=loan_status
            )

            row_to_insert = {
                "application_id": app["application_id"],
                "approved_amount": approved_amount,
                "interest_rate": interest_rate,
                "effective_rate": effective_rate,
                "disbursement_date": disbursement_date,
                "maturity_date": maturity_date,
                "loan_status": loan_status,
                "collateral_type": collateral_type,
                "overdue_amount": overdue_amount,
                "outstanding_principal": outstanding_principal,
                "outstanding_interest": outstanding_interest,
            }

            session.execute(
                text("""
                     INSERT INTO loan_agreements (application_id,
                                                  approved_amount,
                                                  interest_rate,
                                                  effective_rate,
                                                  disbursement_date,
                                                  maturity_date,
                                                  loan_status,
                                                  collateral_type,
                                                  overdue_amount,
                                                  outstanding_principal,
                                                  outstanding_interest)
                     VALUES (:application_id,
                             :approved_amount,
                             :interest_rate,
                             :effective_rate,
                             :disbursement_date,
                             :maturity_date,
                             :loan_status,
                             :collateral_type,
                             :overdue_amount,
                             :outstanding_principal,
                             :outstanding_interest)
                     """),
                row_to_insert
            )

        session.commit()

    except Exception:
        session.rollback()
        raise