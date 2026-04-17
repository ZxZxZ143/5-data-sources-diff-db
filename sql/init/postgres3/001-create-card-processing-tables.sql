CREATE TYPE card_product_enum AS ENUM (
    'classic',
    'gold',
    'platinum'
    );

CREATE TYPE currency_enum AS ENUM (
    'KZT',
    'USD',
    'EUR'
    );

CREATE TYPE card_status_enum AS ENUM (
    'active',
    'blocked',
    'expired'
    );

CREATE TYPE card_type_enum AS ENUM (
    'debit',
    'credit'
    );

CREATE TYPE payment_system_enum AS ENUM (
    'visa',
    'mastercard'
    );

CREATE TYPE auth_result_enum AS ENUM (
    'approved',
    'declined'
    );

CREATE TYPE pos_entry_mode_enum AS ENUM (
    'chip',
    'contactless',
    'ecom'
    );

CREATE TYPE settlement_status_enum AS ENUM (
    'settled',
    'reversed',
    'pending'
    );

CREATE TABLE cards
(
    card_id        BIGSERIAL PRIMARY KEY,
    client_id      BIGINT           NOT NULL,
    account_id     VARCHAR(34),
    card_pan_hash  VARCHAR(255)     NOT NULL,
    card_product   card_product_enum,
    expiry_date    DATE             NOT NULL,
    embossed_name  VARCHAR(100),
    card_status    card_status_enum NOT NULL DEFAULT 'active',
    issue_date     DATE             NOT NULL,
    card_type      card_type_enum,
    payment_system payment_system_enum,
    daily_limit    NUMERIC(12, 2),
    created_at     TIMESTAMP        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_cards_card_pan_hash
        UNIQUE (card_pan_hash),

    CONSTRAINT chk_cards_dates
        CHECK (expiry_date >= issue_date),

    CONSTRAINT chk_cards_daily_limit
        CHECK (daily_limit IS NULL OR daily_limit >= 0),

    CONSTRAINT chk_cards_pan_hash_not_blank
        CHECK (BTRIM(card_pan_hash) <> ''),

    CONSTRAINT chk_cards_embossed_name_not_blank
        CHECK (embossed_name IS NULL OR BTRIM(embossed_name) <> '')
);

CREATE TABLE authorizations
(
    auth_id                BIGSERIAL PRIMARY KEY,
    card_id                BIGINT           NOT NULL,
    auth_datetime          TIMESTAMP        NOT NULL,
    merchant_id            VARCHAR(50),
    merchant_name          VARCHAR(150),
    merchant_category_code VARCHAR(4),
    amount                 NUMERIC(12, 2)   NOT NULL,
    currency               currency_enum    NOT NULL,
    auth_code              VARCHAR(20),
    auth_result            auth_result_enum NOT NULL,
    decline_reason         VARCHAR(100),
    terminal_id            VARCHAR(50),
    country_code           CHAR(3),
    city                   VARCHAR(50)      NOT NULL,
    pos_entry_mode         pos_entry_mode_enum,
    is_international       BOOLEAN          NOT NULL DEFAULT FALSE,
    created_at             TIMESTAMP        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at             TIMESTAMP        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_authorizations_card
        FOREIGN KEY (card_id)
            REFERENCES cards (card_id)
            ON DELETE CASCADE
            ON UPDATE CASCADE,

    CONSTRAINT chk_authorizations_amount
        CHECK (amount > 0),

    CONSTRAINT chk_authorizations_merchant_id_not_blank
        CHECK (merchant_id IS NULL OR BTRIM(merchant_id) <> ''),

    CONSTRAINT chk_authorizations_merchant_name_not_blank
        CHECK (merchant_name IS NULL OR BTRIM(merchant_name) <> ''),

    CONSTRAINT chk_authorizations_auth_code_not_blank
        CHECK (auth_code IS NULL OR BTRIM(auth_code) <> ''),

    CONSTRAINT chk_authorizations_mcc
        CHECK (
            merchant_category_code IS NULL
                OR merchant_category_code ~ '^[0-9]{4}$'
            ),

    CONSTRAINT chk_authorizations_decline_reason_not_blank
        CHECK (decline_reason IS NULL OR BTRIM(decline_reason) <> ''),

    CONSTRAINT chk_authorizations_terminal_id_not_blank
        CHECK (terminal_id IS NULL OR BTRIM(terminal_id) <> ''),

    CONSTRAINT chk_authorizations_country_code
        CHECK (
            country_code IS NULL
                OR country_code ~ '^[A-Z]{3}$'
            ),

    CONSTRAINT chk_authorizations_decline_logic
        CHECK (
            (auth_result = 'approved' AND decline_reason IS NULL)
                OR
            (auth_result = 'declined' AND decline_reason IS NOT NULL)
            )
);

CREATE INDEX idx_authorizations_card_id
    ON authorizations (card_id);

CREATE INDEX idx_authorizations_card_id_auth_datetime
    ON authorizations (card_id, auth_datetime DESC);

CREATE TABLE clearing_transactions
(
    clearing_id         BIGSERIAL PRIMARY KEY,
    auth_id             BIGINT                 NOT NULL,
    settlement_date     DATE                   NOT NULL,
    final_amount        NUMERIC(12, 2)         NOT NULL,
    interchange_fee     NUMERIC(10, 2),
    scheme_fee          NUMERIC(10, 2),
    settlement_currency currency_enum,
    settlement_status   settlement_status_enum NOT NULL DEFAULT 'settled',
    created_at          TIMESTAMP              NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP              NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_clearing_transactions_auth
        FOREIGN KEY (auth_id)
            REFERENCES authorizations (auth_id)
            ON DELETE CASCADE
            ON UPDATE CASCADE,

    CONSTRAINT uq_clearing_transactions_auth_id
        UNIQUE (auth_id),

    CONSTRAINT chk_clearing_transactions_final_amount
        CHECK (final_amount > 0),

    CONSTRAINT chk_clearing_transactions_interchange_fee
        CHECK (interchange_fee IS NULL OR interchange_fee >= 0),

    CONSTRAINT chk_clearing_transactions_scheme_fee
        CHECK (scheme_fee IS NULL OR scheme_fee >= 0)
);