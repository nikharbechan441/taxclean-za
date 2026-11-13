"""
TaxClean ZA — South African Legal & Tax Compliance Engine
Adheres strictly to:
1. SARS VAT Act 89 of 1991 (Section 7, 11, 12, 17(2))
2. SARS Tax Administration Act 28 of 2011 (Section 29, 30 — 5-Year Record Keeping)
3. POPIA Act 4 of 2013 (Data Minimization, Localized Processing & Masking)
"""

import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any


def _dec_round(val: float) -> float:
    return float(Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


# ==============================================================================
# 1. SARS 10-DIGIT FORMAT & MOD-10 VAT NUMBER VALIDATION
# ==============================================================================
def validate_sars_vat_number(vat_input: str) -> bool:
    """
    Validates a South African VAT registration number format and check digit:
    - Must be exactly 10 numeric digits.
    - Must start with the digit '4' (SARS VAT reference prefix).
    - Passes the standard Mod-10 (Luhn) check-digit test.
    """
    digits = [int(c) for c in str(vat_input or "") if c.isdigit()]
    if len(digits) != 10 or digits[0] != 4:
        return False

    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d2 = d * 2
            total += (d2 // 10) + (d2 % 10)
        else:
            total += d

    return total % 10 == 0


# ==============================================================================
# 2. POPIA COMPLIANCE: LOCAL PRIVACY & SENSITIVE DATA MASKING
# ==============================================================================
def mask_account_number(acc_str: str) -> str:
    """
    Complies with POPIA Section 14 (Security Safeguards):
    Masks bank account numbers in audit exports and logs (e.g., '62891048291' -> '******48291').
    """
    raw = re.sub(r"\s+", "", str(acc_str or "")).strip()
    if len(raw) <= 4:
        return "****"
    return "*" * (len(raw) - 4) + raw[-4:]


def scrub_popia_diagnostics(text: str) -> str:
    """
    Complies with POPIA Act 4 of 2013 (Data Minimization):
    Scrubs sensitive private personal information from error traces and statement samples:
    - Masks 8-18 digit account, card, or SA ID numbers.
    - Masks email addresses.
    - Preserves error tracebacks, keywords, dates, and column structures needed for debugging.
    """
    if not text:
        return ""
    # Mask email addresses
    scrubbed = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[REDACTED_EMAIL]', text)
    # Mask 8-18 digit account, card, or SA ID numbers
    scrubbed = re.sub(r'\b\d{8,18}\b', lambda m: m.group(0)[:2] + '*' * (len(m.group(0)) - 4) + m.group(0)[-2:], scrubbed)
    return scrubbed



POPIA_COMPLIANCE_NOTICE = (
    "POPIA NOTICE (Act 4 of 2013):\n"
    "TaxClean ZA operates locally on your device. Bank statements, transaction records, "
    "and client account numbers are processed offline on your PC by default. "
    "If you optionally configure Google Gemini AI Vision for faded receipts, only the selected "
    "document image is transmitted to Google via your private API key with your consent. "
    "You retain complete custody and control as the Responsible Party under South African law."
)

SARS_EULA_DISCLAIMER = (
    "LEGAL & AUDIT DISCLAIMER (SARS TAA Act 28 of 2011 & CPA Act 68 of 2008):\n"
    "TaxClean ZA is an automated bank statement parsing and audit assistance engine. "
    "While TaxClean applies standard SARS VAT Act rules (15% Standard, Zero-Rated, Exempt, "
    "and Section 17(2) blocked entertainment), the user / registered tax practitioner remains "
    "legally responsible for reviewing allocations and verifying final VAT201 / IT14 submissions."
)


# ==============================================================================
# 3. SARS VAT ACT 89 OF 1991 KEYWORD LISTS & RECONCILIATION
# ==============================================================================
# Entertainment keywords strictly blocked under Section 17(2)(a)
BLOCKED_ENTERTAINMENT_KEYWORDS = [
    "MUGG & BEAN", "MUGG AND BEAN", "SPUR", "VIDA E CAFFE", "KFC", "NANDOS", "NANDO'S",
    "STEERS", "WIMPY", "MCDONALD", "STARBUCKS", "SEATTLE COFFEE", "ROCO MAMAS",
    "RESTAURANT", "CAFE", "COFFEE SHOP", "BISTRO", "GRILL", "PIZZERIA", "DEBONAIRS",
    "ROMANS PIZZA", "ROMAN'S PIZZA", "SUSHI", "BAR & LOUNGE", "TAVERN", "LIQUORS",
    "TOPS AT SPAR", "CHECKERS LIQUOR", "LIQUOR CITY"
]

# Zero-Rated fuel keywords under Section 11(1)(h) / 11(1)(m) (Subject to fuel levy)
ZERO_RATED_FUEL_KEYWORDS = [
    "ENGEN", "SHELL", "BP ", "SASOL", "TOTALENERGIES", "CALTEX",
    "ASTRON ENERGY", "PUMA ENERGY", "PETROL", "DIESEL", "SERVICE STATION",
    "ULTRA CITY", "1-STOP", "ONE STOP"
]

# Exempt supplies under Section 12(a) (Financial services: interest, life assurance)
EXEMPT_FINANCIAL_KEYWORDS = [
    "INTEREST PAID", "INTEREST CHARGED", "FINANCE CHARGE", "LIFE ASSURANCE",
    "LIFE INSURANCE", "CREDIT INTEREST", "DEBIT RATE"
]

# Standard-rated bank service fees (SARS VAT Act Section 7(1)(a) - fee-based financial services)
STANDARD_BANK_FEE_KEYWORDS = [
    "SERVICE FEES", "MONTHLY FEE", "CASH HANDLING FEE", "TRANSACTION FEE",
    "CARD FEE", "STATEMENT FEE", "OVERDRAFT FEE", "SASWITCH", "SERVICE FEE",
    "BANK CHARGES", "ACCOUNT FEE"
]


def calculate_sars_reconciliation(open_bal: float, transactions: list, close_bal: float) -> Dict[str, Any]:
    """
    Strict SARS Tax Administration Act (TAA) reconciliation formula:
    Opening Balance + Total Receipts - Total Payments == Closing Balance
    """
    total_receipts = sum(float(t.get("amount", 0.0)) for t in transactions if float(t.get("amount", 0.0)) > 0)
    total_payments = sum(abs(float(t.get("amount", 0.0))) for t in transactions if float(t.get("amount", 0.0)) < 0)
    net_movement = total_receipts - total_payments
    calculated_closing = _dec_round(open_bal + net_movement)
    discrepancy = _dec_round(calculated_closing - close_bal)
    is_balanced = abs(discrepancy) <= 0.05

    return {
        "opening_balance": _dec_round(open_bal),
        "total_receipts": _dec_round(total_receipts),
        "total_payments": _dec_round(total_payments),
        "net_movement": _dec_round(net_movement),
        "closing_balance": _dec_round(close_bal),
        "calculated_closing": calculated_closing,
        "discrepancy": discrepancy,
        "is_balanced": is_balanced,
    }
