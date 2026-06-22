"""Application defaults and shared constants."""

DEFAULT_DATE_TOLERANCE_DAYS = 3
AMOUNT_TOLERANCE = 0.01

DESCRIPTION_TIE_BREAK_MARGIN = 10

DEFAULT_CARDHOLDER_MAP = {
    "3894": "Catherine Bainbridge",
    "3811": "Archita Ghosh",
    "3818": "Brittany Leborgne",
    "3810": "Shantae Gibson",
    "5589": "Ernest Webb",
    "2261": "Ernest Webb",
}

CARDHOLDER_NAMES = [
    "Catherine Bainbridge",
    "Archita Ghosh",
    "Brittany Leborgne",
    "Ernest Webb",
    "Shantae Gibson",
]

OUTPUT_COLUMNS = [
    "QBO Date",
    "QBO Bank description",
    "QBO Spent",
    "QBO Received",
    "QBO From/To",
    "QBO Amount",
    "Card number",
    "Cardholder name",
    "Bank transaction date",
    "Bank description",
    "Bank amount",
    "Match confidence",
    "Match note",
    "Date difference days",
    "Description similarity",
    "Bank reference",
]
