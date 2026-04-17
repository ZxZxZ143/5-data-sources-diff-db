CREATE TYPE loan_purpose_enum AS ENUM (
    'mortgage',
    'car',
    'consumer'
    );

CREATE TYPE loan_application_status_enum AS ENUM (
    'new',
    'in_review',
    'approved',
    'rejected'
    );

CREATE TYPE risk_grade_enum AS ENUM (
    'A',
    'B',
    'C',
    'D'
    );

CREATE TYPE loan_channel_enum AS ENUM (
    'branch',
    'online',
    'partner'
    );

CREATE TYPE loan_status_enum AS ENUM (
    'active',
    'paid',
    'default',
    'restructured'
    );

CREATE TYPE collateral_type_enum AS ENUM (
    'none',
    'car',
    'real_estate'
    );

CREATE TYPE payment_status_enum AS ENUM (
    'planned',
    'paid',
    'overdue',
    'partial'
    );

CREATE TABLE loan_applications
(
    application_id          BIGSERIAL PRIMARY KEY,
    client_id               BIGINT                       NOT NULL,
    application_dt          DATE                         NOT NULL,
    requested_amount        NUMERIC(15, 2)               NOT NULL CHECK (requested_amount > 0),
    requested_term_months   INT                          NOT NULL CHECK (requested_term_months > 0),
    purpose_code            loan_purpose_enum,
    income_amount           NUMERIC(12, 2) CHECK (income_amount >= 0),
    employment_length_years INT CHECK (employment_length_years >= 0),
    credit_score            INT CHECK (credit_score BETWEEN 0 AND 1000),
    status                  loan_application_status_enum NOT NULL,
    decision_dt             DATE,
    assigned_risk_grade     risk_grade_enum,
    branch_code             VARCHAR(20),
    channel                 loan_channel_enum,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_loan_applications_client_id
    ON loan_applications (client_id);

CREATE TABLE loan_agreements
(
    loan_id               BIGSERIAL PRIMARY KEY,
    application_id        BIGINT           NOT NULL,
    approved_amount       NUMERIC(15, 2)   NOT NULL CHECK (approved_amount > 0),
    interest_rate         NUMERIC(5, 2)    NOT NULL CHECK (interest_rate >= 0),
    effective_rate        NUMERIC(5, 2) CHECK (effective_rate >= 0),
    disbursement_date     DATE             NOT NULL,
    maturity_date         DATE             NOT NULL,
    loan_status           loan_status_enum NOT NULL,
    collateral_type       collateral_type_enum,
    overdue_amount        NUMERIC(15, 2) DEFAULT 0 CHECK (overdue_amount >= 0),
    outstanding_principal NUMERIC(15, 2) DEFAULT 0 CHECK (outstanding_principal >= 0),
    outstanding_interest  NUMERIC(15, 2) DEFAULT 0 CHECK (outstanding_interest >= 0),
    created_at            TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_loan_agreements_application
        FOREIGN KEY (application_id)
            REFERENCES loan_applications (application_id)
            ON DELETE NO ACTION
            ON UPDATE CASCADE,

    CONSTRAINT uq_loan_agreements_application_id
        UNIQUE (application_id),

    CONSTRAINT chk_loan_dates
        CHECK (maturity_date >= disbursement_date)
);

CREATE TABLE payment_schedule
(
    schedule_id         BIGSERIAL PRIMARY KEY,
    loan_id             BIGINT         NOT NULL,
    due_date            DATE           NOT NULL,
    principal_due       NUMERIC(15, 2) NOT NULL CHECK (principal_due >= 0),
    interest_due        NUMERIC(15, 2) NOT NULL CHECK (interest_due >= 0),
    total_due           NUMERIC(15, 2) NOT NULL CHECK (total_due >= 0),
    actual_payment_date DATE,
    actual_paid         NUMERIC(15, 2) CHECK (actual_paid >= 0),
    overdue_days        INT                 DEFAULT 0 CHECK (overdue_days >= 0),
    installment_number  INT            NOT NULL CHECK (installment_number > 0),
    payment_status      payment_status_enum DEFAULT 'planned',
    created_at          TIMESTAMP           DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP           DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_payment_schedule_loan
        FOREIGN KEY (loan_id)
            REFERENCES loan_agreements (loan_id)
            ON DELETE CASCADE
            ON UPDATE CASCADE,

    CONSTRAINT uq_payment_schedule_loan_installment
        UNIQUE (loan_id, installment_number),

    CONSTRAINT chk_payment_total
        CHECK (total_due = principal_due + interest_due),

    CONSTRAINT chk_actual_payment
        CHECK (
            (actual_payment_date IS NULL AND actual_paid IS NULL)
                OR
            (actual_payment_date IS NOT NULL AND actual_paid IS NOT NULL)
            )
);