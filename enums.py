ABS_GENDERS = [
    "male",
    "female",
]

ABS_CLIENT_STATUSES = [
    "active",
    "blocked",
    "closed",
]

ABS_CLIENT_SEGMENTS = [
    "mass",
    "premium",
    "vip",
]

ABS_PRODUCT_TYPES = [
    "current",
    "savings",
    "deposit",
]

ABS_ACCOUNT_STATUSES = [
    "active",
    "blocked",
    "closed",
]

ABS_TRX_TYPES = [
    "credit",
    "debit",
    "transfer",
    "cash_withdrawal",
]

ABS_CHANNELS = [
    "branch",
    "atm",
    "mobile_app",
    "web",
    "terminal",
]

ABS_TRANSACTION_STATUSES = [
    "posted",
    "reversed",
    "pending",
]

LOAN_PURPOSES = [
    "mortgage",
    "car",
    "consumer",
]

LOAN_APPLICATION_STATUSES = [
    "new",
    "in_review",
    "approved",
    "rejected",
]

LOAN_RISK_GRADES = [
    "A",
    "B",
    "C",
    "D",
]

LOAN_CHANNELS = [
    "branch",
    "online",
    "partner",
]

LOAN_STATUSES = [
    "active",
    "paid",
    "default",
    "restructured",
]

LOAN_COLLATERAL_TYPES = [
    "none",
    "car",
    "real_estate",
]

LOAN_PAYMENT_STATUSES = [
    "planned",
    "paid",
    "overdue",
    "partial",
]

CARD_PRODUCTS = [
    "classic",
    "gold",
    "platinum",
]

CARD_STATUSES = [
    "active",
    "blocked",
    "expired",
]

CARD_TYPES = [
    "debit",
    "credit",
]

CARD_PAYMENT_SYSTEMS = [
    "visa",
    "mastercard",
]

CARD_AUTH_RESULTS = [
    "approved",
    "declined",
]

CARD_POS_ENTRY_MODES = [
    "chip",
    "contactless",
    "ecom",
]

CARD_SETTLEMENT_STATUSES = [
    "settled",
    "reversed",
    "pending",
]

CURRENCIES = [
    "KZT",
    "USD",
    "EUR",
]

CITIES = [
    "Almaty",
    "Astana",
    "Shymkent"
    "Karaganda",
    "Aktobe",
    "Atyrau",
    "Aktau",
    "Pavlodar",
    "Kostanay",
    "Oskemen",
    "Taraz",
    "Kokshetau",
]

BRANCHES = [
    "ALM001",
    "ALM002",
    "AST001",
    "AST002",
    "SHY001",
    "KRG001",
    "AKT001",
    "ATY001",
    "AKT002",
    "PAV001",
    "KOS001",
    "OSK001",
    "TRZ001",
    "KOK001"
]

DEVICE_TYPES = [
    "android",
    "ios",
    "web",
]

APP_VERSIONS_MOBILE = [
    "1.9.0",
    "1.10.2",
    "1.11.0",
    "1.11.3",
    "1.12.1",
    "2.0.0",
]

APP_VERSIONS_WEB = [
    "web-1.0",
    "web-1.1",
    "web-1.2",
]

LOGIN_FAILURE_REASONS = [
    "Invalid password",
    "OTP verification failed",
    "Too many attempts",
    "Suspicious login attempt",
    "Temporary service unavailable",
]

EVENT_TYPES = [
    "view_balance",
    "make_transfer",
    "pay_utility",
]

TRANSFER_BANKS = [
    "Halyk Bank",
    "Kaspi Bank",
    "Freedom Bank",
    "Jusan Bank",
    "Bank CenterCredit",
]

UTILITY_PROVIDERS = [
    "Beeline",
    "Kcell",
    "Kazakhtelecom",
    "Alseco",
    "Almaty Su",
    "Astana Energosbyt",
]

TRANSFER_ERROR_TEXTS = [
    "Insufficient funds",
    "Transfer limit exceeded",
    "Recipient validation failed",
    "Temporary service unavailable",
]

UTILITY_ERROR_TEXTS = [
    "Provider unavailable",
    "Payment timeout",
    "Operation declined",
]

GENERIC_ERROR_TEXTS = [
    "Temporary error",
    "Timeout",
    "Unexpected server error",
]

RULES = [
    "large_cash_withdrawal",
    "high_value_transfer",
    "high_value_fx_transaction",
    "large_digital_payment",
    "reversed_large_transaction",
]

RISK_LEVELS = [
    "medium",
    "high",
    "critical",
]

INVESTIGATION_STATUSES = [
    "new",
    "in_review",
    "escalated",
    "closed_true_positive",
    "closed_false_positive",
]


DOMESTIC_COUNTRY_CODE = "KAZ"
FOREIGN_COUNTRIES = ["USA", "TUR", "DEU", "ARE", "GBR"]

DECLINE_REASONS = [
    "insufficient_funds",
    "do_not_honor",
    "suspected_fraud",
    "limit_exceeded",
]

DOMESTIC_MERCHANTS = [
    {"name": "Magnum", "mcc": "5411", "min_amount": 1500, "max_amount": 85000},
    {"name": "Small", "mcc": "5411", "min_amount": 800, "max_amount": 45000},
    {"name": "Technodom", "mcc": "5732", "min_amount": 12000, "max_amount": 450000},
    {"name": "Sulpak", "mcc": "5732", "min_amount": 10000, "max_amount": 400000},
    {"name": "Burger King", "mcc": "5814", "min_amount": 2000, "max_amount": 18000},
    {"name": "KFC", "mcc": "5814", "min_amount": 1800, "max_amount": 16000},
    {"name": "Coffee Boom", "mcc": "5812", "min_amount": 2000, "max_amount": 22000},
    {"name": "Invivo", "mcc": "5912", "min_amount": 2500, "max_amount": 70000},
    {"name": "Helios", "mcc": "5541", "min_amount": 5000, "max_amount": 50000},
    {"name": "Happylon", "mcc": "7996", "min_amount": 3000, "max_amount": 40000},
]

ECOM_MERCHANTS = [
    {"name": "Kaspi Shop", "mcc": "5311", "min_amount": 3000, "max_amount": 250000},
    {"name": "Wildberries", "mcc": "5311", "min_amount": 2500, "max_amount": 180000},
    {"name": "Ozon", "mcc": "5311", "min_amount": 3000, "max_amount": 200000},
    {"name": "Yandex Plus", "mcc": "4899", "min_amount": 1000, "max_amount": 15000},
    {"name": "Steam", "mcc": "5816", "min_amount": 1500, "max_amount": 80000},
    {"name": "Apple.com", "mcc": "5734", "min_amount": 2000, "max_amount": 180000},
]

INTERNATIONAL_MERCHANTS = [
    {"name": "Amazon", "mcc": "5311", "min_amount": 10, "max_amount": 1000},
    {"name": "Booking", "mcc": "7011", "min_amount": 30, "max_amount": 2000},
    {"name": "Uber", "mcc": "4121", "min_amount": 5, "max_amount": 200},
    {"name": "Starbucks Intl", "mcc": "5814", "min_amount": 5, "max_amount": 50},
    {"name": "Zara", "mcc": "5651", "min_amount": 20, "max_amount": 500},
]
