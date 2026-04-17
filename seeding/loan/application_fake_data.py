import random
from datetime import date
from decimal import Decimal
from typing import TypedDict

from dateutil.relativedelta import relativedelta
from faker import Faker
from sqlalchemy import text

from db import get_session
from enums import LOAN_CHANNELS, LOAN_APPLICATION_STATUSES, LOAN_PURPOSES, BRANCHES

fake = Faker("ru_RU")

TOTAL_APPLICATIONS = 2000

class ClientRow(TypedDict):
    client_id: int
    registration_date: date
    remain: int


def load_clients(session) -> list[ClientRow]:
    rows = session.execute(
        text("""
            SELECT client_id, registration_date::date AS registration_date
            FROM clients
            ORDER BY client_id
        """)
    ).mappings().all()

    clients: list[ClientRow] = []

    for row in rows:
        months = max(
            0,
            (date.today().year - row["registration_date"].year) * 12
            + (date.today().month - row["registration_date"].month)
        )

        if months >= 24:
            remain = random.choices([0, 1, 2], weights=[0.35, 0.45, 0.20], k=1)[0]
        elif months >= 12:
            remain = random.choices([0, 1], weights=[0.55, 0.45], k=1)[0]
        else:
            remain = random.choices([0, 1], weights=[0.75, 0.25], k=1)[0]

        clients.append(
            {
                "client_id": row["client_id"],
                "registration_date": row["registration_date"],
                "remain": remain,
            }
        )

    return clients


def get_client(clients: list[ClientRow]) -> ClientRow:
    available = [client for client in clients if client["remain"] > 0]

    client = random.choice(available)
    client["remain"] -= 1
    return client


def generate_application_dt(registration_date: date) -> date:
    return fake.date_between_dates(
        date_start=max(registration_date, date.today() - relativedelta(years=3)),
        date_end=date.today()
    )


def generate_income_amount() -> Decimal:
    income = random.choices(
        [
            random.uniform(120_000, 250_000),
            random.uniform(250_000, 600_000),
            random.uniform(600_000, 1_200_000),
            random.uniform(1_200_000, 2_500_000),
        ],
        weights=[0.35, 0.40, 0.20, 0.05],
        k=1
    )[0]

    return Decimal(str(round(income, 2)))


def generate_employment_length_years() -> int:
    return random.choices(
        [
            random.randint(0, 1),
            random.randint(2, 5),
            random.randint(6, 10),
            random.randint(11, 25),
        ],
        weights=[0.20, 0.40, 0.28, 0.12],
        k=1
    )[0]


def generate_credit_score(income_amount: Decimal, employment_years: int) -> int:
    score = random.randint(540, 820)

    if income_amount >= Decimal("1000000"):
        score += 20
    elif income_amount <= Decimal("180000"):
        score -= 20

    if employment_years >= 7:
        score += 15
    elif employment_years == 0:
        score -= 25

    return max(300, min(850, score))


def generate_requested_term_months(purpose: str) -> int:
    if purpose == "mortgage":
        return random.choice([120, 180, 240, 300])
    if purpose == "car":
        return random.choice([24, 36, 48, 60, 72, 84])
    return random.choice([6, 12, 18, 24, 36, 48, 60])


def generate_requested_amount(purpose: str, income_amount: Decimal, credit_score: int) -> Decimal:
    income = float(income_amount)

    if purpose == "mortgage":
        amount = income * random.uniform(25, 90)
        amount = max(8_000_000, min(amount, 60_000_000))
    elif purpose == "car":
        amount = income * random.uniform(6, 30)
        amount = max(2_000_000, min(amount, 20_000_000))
    else:
        amount = income * random.uniform(2, 12)
        amount = max(300_000, min(amount, 8_000_000))

    if credit_score >= 780:
        amount *= 1.1
    elif credit_score < 600:
        amount *= 0.85

    amount = round(amount / 1000) * 1000
    return Decimal(str(f"{amount:.2f}"))


def generate_channel(purpose: str, requested_amount: Decimal) -> str:
    if purpose == "mortgage":
        return random.choices(LOAN_CHANNELS, weights=[0.75, 0.10, 0.15], k=1)[0]

    if purpose == "car":
        return random.choices(LOAN_CHANNELS, weights=[0.35, 0.15, 0.50], k=1)[0]

    if requested_amount >= Decimal("5000000"):
        return random.choices(LOAN_CHANNELS, weights=[0.60, 0.30, 0.10], k=1)[0]

    return random.choices(LOAN_CHANNELS, weights=[0.20, 0.75, 0.05], k=1)[0]


def generate_risk_grade(credit_score: int, income_amount: Decimal, requested_amount: Decimal, term_months: int) -> str:
    monthly_load = requested_amount / Decimal(term_months)
    ratio = monthly_load / income_amount

    if credit_score >= 760 and ratio <= Decimal("0.30"):
        return "A"
    if credit_score >= 680 and ratio <= Decimal("0.45"):
        return "B"
    if credit_score >= 600 and ratio <= Decimal("0.60"):
        return "C"
    return "D"


def generate_status(application_dt: date, risk_grade: str) -> str:
    days_ago = (date.today() - application_dt).days

    if days_ago <= 2:
        return random.choices(
            LOAN_APPLICATION_STATUSES,
            weights=[0.45, 0.40, 0.08, 0.07],
            k=1
        )[0]

    if risk_grade == "A":
        return random.choices(
            LOAN_APPLICATION_STATUSES,
            weights=[0.03, 0.07, 0.80, 0.10],
            k=1
        )[0]

    if risk_grade == "B":
        return random.choices(
            LOAN_APPLICATION_STATUSES,
            weights=[0.05, 0.12, 0.60, 0.23],
            k=1
        )[0]

    if risk_grade == "C":
        return random.choices(
            LOAN_APPLICATION_STATUSES,
            weights=[0.07, 0.15, 0.35, 0.43],
            k=1
        )[0]

    return random.choices(
        LOAN_APPLICATION_STATUSES,
        weights=[0.08, 0.18, 0.12, 0.62],
        k=1
    )[0]


def generate_decision_dt(application_dt: date, status: str) -> date | None:
    if status in ("new", "in_review"):
        return None

    return min(
        application_dt + relativedelta(days=random.choice([1, 2, 3, 5, 7, 10])),
        date.today()
    )


with get_session("loan_system") as session:
    try:
        with get_session("abs") as session_2:
            clients = load_clients(session_2)

        max_possible = sum(client["remain"] for client in clients)
        total_applications = min(TOTAL_APPLICATIONS, max_possible)

        for _ in range(total_applications):
            client = get_client(clients)

            application_dt = generate_application_dt(client["registration_date"])
            purpose_code = random.choices(LOAN_PURPOSES, weights=[0.12, 0.23, 0.65], k=1)[0]

            income_amount = generate_income_amount()
            employment_length_years = generate_employment_length_years()
            credit_score = generate_credit_score(income_amount, employment_length_years)

            requested_term_months = generate_requested_term_months(purpose_code)
            requested_amount = generate_requested_amount(
                purpose_code,
                income_amount,
                credit_score
            )

            assigned_risk_grade = generate_risk_grade(
                credit_score,
                income_amount,
                requested_amount,
                requested_term_months
            )

            status = generate_status(application_dt, assigned_risk_grade)
            decision_dt = generate_decision_dt(application_dt, status)
            channel = generate_channel(purpose_code, requested_amount)

            row_to_insert = {
                "client_id": client["client_id"],
                "application_dt": application_dt,
                "requested_amount": requested_amount,
                "requested_term_months": requested_term_months,
                "purpose_code": purpose_code,
                "income_amount": income_amount,
                "employment_length_years": employment_length_years,
                "credit_score": credit_score,
                "status": status,
                "decision_dt": decision_dt,
                "assigned_risk_grade": assigned_risk_grade,
                "branch_code": random.choice(BRANCHES),
                "channel": channel,
            }

            session.execute(
                text("""
                    INSERT INTO loan_applications (
                        client_id,
                        application_dt,
                        requested_amount,
                        requested_term_months,
                        purpose_code,
                        income_amount,
                        employment_length_years,
                        credit_score,
                        status,
                        decision_dt,
                        assigned_risk_grade,
                        branch_code,
                        channel
                    )
                    VALUES (
                        :client_id,
                        :application_dt,
                        :requested_amount,
                        :requested_term_months,
                        :purpose_code,
                        :income_amount,
                        :employment_length_years,
                        :credit_score,
                        :status,
                        :decision_dt,
                        :assigned_risk_grade,
                        :branch_code,
                        :channel
                    )
                """),
                row_to_insert
            )

        session.commit()

    except Exception:
        session.rollback()
        raise