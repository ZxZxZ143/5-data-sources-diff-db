CREATE TYPE gender_enum AS ENUM (
    'male',
    'female'
    );

CREATE TYPE client_status_enum AS ENUM (
    'active',
    'blocked',
    'closed'
    );

CREATE TYPE client_segment_enum AS ENUM (
    'mass',
    'premium',
    'vip'
    );

CREATE TYPE product_type_enum AS ENUM (
    'current',
    'savings',
    'deposit'
    );

CREATE TYPE account_status_enum AS ENUM (
    'active',
    'blocked',
    'closed'
    );

CREATE TYPE trx_type_enum AS ENUM (
    'credit',
    'debit',
    'transfer',
    'cash_withdrawal'
    );

CREATE TYPE channel_enum AS ENUM (
    'branch',
    'atm',
    'mobile_app',
    'web',
    'terminal'
    );

CREATE TYPE transaction_status_enum AS ENUM (
    'posted',
    'reversed',
    'pending'
    );

CREATE TYPE currency_enum AS ENUM (
    'KZT',
    'USD',
    'EUR'
    );

CREATE TABLE clients
(
    client_id         BIGSERIAL PRIMARY KEY,
    first_name        VARCHAR(100)       NOT NULL,
    last_name         VARCHAR(100)       NOT NULL,
    middle_name       VARCHAR(100),
    birth_date        DATE,
    gender            gender_enum,
    phone             VARCHAR(30)        NOT NULL,
    email             VARCHAR(150),
    city              VARCHAR(50)        NOT NULL,
    address           VARCHAR(255),
    document_number   VARCHAR(50)        NOT NULL,
    client_segment    client_segment_enum,
    residency_flag    BOOLEAN            NOT NULL DEFAULT TRUE,
    registration_date TIMESTAMP          NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status            client_status_enum NOT NULL DEFAULT 'active',
    created_at        TIMESTAMP          NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP          NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_clients_document_number UNIQUE (document_number),
    CONSTRAINT uq_clients_phone UNIQUE (phone),

    CONSTRAINT chk_clients_birth_date
        CHECK (birth_date IS NULL OR birth_date <= CURRENT_DATE),

    CONSTRAINT chk_clients_registration_date
        CHECK (
            birth_date IS NULL
                OR registration_date:: DATE >= birth_date
            ),

    CONSTRAINT chk_clients_phone_not_blank
        CHECK (BTRIM(phone) ~ '^(\+7|8)[0-9]{10}$'),

    CONSTRAINT chk_clients_email_not_blank
        CHECK (email IS NULL OR BTRIM(email) <> ''),

    CONSTRAINT chk_clients_document_not_blank
        CHECK (BTRIM(document_number) <> '')
);

CREATE INDEX idx_clients_city_id
    ON clients (city);

CREATE TABLE accounts
(
    account_id        VARCHAR(34) PRIMARY KEY,
    client_id         BIGINT              NOT NULL,
    product_type      product_type_enum   NOT NULL,
    currency          currency_enum       NOT NULL,
    balance           NUMERIC(18, 2)      NOT NULL DEFAULT 0,
    opened_date       DATE                NOT NULL,
    closed_date       DATE,
    branch_code       VARCHAR(20)         NOT NULL,
    account_status    account_status_enum NOT NULL DEFAULT 'active',
    is_salary_account BOOLEAN             NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMP           NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP           NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_accounts_client
        FOREIGN KEY (client_id)
            REFERENCES clients (client_id)
            ON DELETE NO ACTION
            ON UPDATE CASCADE,

    CONSTRAINT chk_accounts_balance
        CHECK (balance >= 0),

    CONSTRAINT chk_accounts_dates
        CHECK (closed_date IS NULL OR closed_date >= opened_date)
);

CREATE INDEX idx_accounts_client_id
    ON accounts (client_id);

CREATE INDEX idx_accounts_branch_code
    ON accounts (branch_code);

CREATE TABLE transactions
(
    trx_id               BIGSERIAL PRIMARY KEY,
    account_id           VARCHAR(34)             NOT NULL,
    trx_datetime         TIMESTAMP               NOT NULL,
    trx_type             trx_type_enum           NOT NULL,
    amount               NUMERIC(18, 2)          NOT NULL,
    currency             currency_enum           NOT NULL,
    counterparty_account VARCHAR(34),
    counterparty_name    VARCHAR(200),
    reference            VARCHAR(255),
    channel              channel_enum,
    posting_date         DATE                    NOT NULL,
    status               transaction_status_enum NOT NULL DEFAULT 'pending',
    mcc_code             VARCHAR(4),
    city                 VARCHAR(50)             NOT NULL,
    created_at           TIMESTAMP               NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP               NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_transactions_account
        FOREIGN KEY (account_id)
            REFERENCES accounts (account_id)
            ON DELETE CASCADE
            ON UPDATE CASCADE,

    CONSTRAINT chk_transactions_amount
        CHECK (amount > 0),

    CONSTRAINT chk_transactions_counterparty_account_not_blank
        CHECK (counterparty_account IS NULL OR BTRIM(counterparty_account) <> ''),

    CONSTRAINT chk_transactions_counterparty_name_not_blank
        CHECK (counterparty_name IS NULL OR BTRIM(counterparty_name) <> ''),

    CONSTRAINT chk_transactions_reference_not_blank
        CHECK (reference IS NULL OR BTRIM(reference) <> ''),

    CONSTRAINT chk_transactions_mcc_code
        CHECK (mcc_code IS NULL OR mcc_code ~ '^[0-9]{4}$'
            ),

    CONSTRAINT chk_transactions_posting_date
        CHECK (posting_date >= trx_datetime::DATE)
);

CREATE INDEX idx_transactions_account_id
    ON transactions (account_id);

CREATE INDEX idx_transactions_account_id_trx_datetime
    ON transactions (account_id, trx_datetime DESC);