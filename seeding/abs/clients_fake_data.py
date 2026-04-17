import random
from collections import OrderedDict
from datetime import date

from dateutil.relativedelta import relativedelta
from faker import Faker
from sqlalchemy import text

from db import get_session
from enums import CITIES, ABS_GENDERS

fake = Faker("ru_RU")

TOTAL_CLIENTS = 2000

with get_session("abs") as session:
    for _ in range(TOTAL_CLIENTS):
        birth_date = fake.date_of_birth(minimum_age=18, maximum_age=70)

        adult_date = birth_date + relativedelta(years=18)

        registration_start = min(adult_date, date.today())

        row_to_insert = {
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "middle_name": fake.middle_name(),
                "birth_date": birth_date,
                "gender": random.choice(ABS_GENDERS),
                "phone": fake.phone_number()
                .replace("-", "")
                .replace(" ", "")
                .replace("(", "")
                .replace(")", ""),
                "email": fake.email(),
                "city": random.choice(CITIES),
                "address": fake.street_address(),
                "document_number": fake.numerify("############"),
                "client_segment": fake.random_element(elements=OrderedDict([
                    ("mass", 0.7),
                    ("vip", 0.2),
                    ("premium", 0.1),
                ])),
                "residency_flag": fake.random_element(elements=OrderedDict([
                    (True, 0.95),
                    (False, 0.05),
                ])),
                "registration_date": fake.date_between_dates(
                    date_start=registration_start,
                    date_end=date.today()
                ),
                "status": fake.random_element(elements=OrderedDict([
                    ("active", 0.7),
                    ("blocked", 0.1),
                    ("closed", 0.2),
                ])),
        }

        session.execute(
            text("""
                 INSERT INTO clients (first_name,
                                          last_name,
                                          middle_name,
                                          birth_date,
                                          gender,
                                          phone,
                                          email,
                                          city,
                                          address,
                                          document_number,
                                          client_segment,
                                          residency_flag,
                                          registration_date,
                                          status)
                 VALUES (:first_name,
                         :last_name,
                         :middle_name,
                         :birth_date,
                         :gender,
                         :phone,
                         :email,
                         :city,
                         :address,
                         :document_number,
                         :client_segment,
                         :residency_flag,
                         :registration_date,
                         :status)
                 """),
            row_to_insert
        )

    session.commit()
