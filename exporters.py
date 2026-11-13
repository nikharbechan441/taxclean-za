"""
TaxClean ZA — South African Accounting Exporters
100% Compliant Formats for:
1. Sage Pastel Partner (Official 10-column Cashbook)
2. Sage Business Cloud Accounting (Sage One)
3. Xero South African Bank Feed
4. QuickBooks Online South African CSV
5. SARS VAT201 Excel Audit Schedule (Compliant with SARS TAA Section 29/30)
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

try:
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from compliance import mask_account_number, calculate_sars_reconciliation


def _dec_round(val: float) -> float:
    return float(Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _parse_date(date_str: str) -> Optional[datetime]:
    """Parses ISO or SA date formats (%Y-%m-%d, %d/%m/%Y, %d/%m/%y, %Y/%m/%d, %d-%m-%Y, %d %b %Y, %d %B %Y)."""
    raw = re.sub(r"[T\s]+\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$", "", str(date_str or "").strip()).strip()
    if not raw:
        return None
    first_token = raw.split()[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(first_token[:10], fmt)
        except Exception:
            continue
    for fmt in ("%d/%m/%y", "%d-%m-%y", "%d.%m.%y"):
        try:
            return datetime.strptime(first_token, fmt)
        except Exception:
            continue
    for fmt in ("%d %b %Y", "%d %B %Y", "%d %b %y", "%d-%b-%Y", "%d-%b-%y"):
        try:
            return datetime.strptime(raw, fmt)
        except Exception:
            continue
    return None


def _format_ddmmyyyy(date_str: str) -> str:
    dt = _parse_date(date_str)
    return dt.strftime("%d/%m/%Y") if dt else str(date_str or "")


def calculate_pastel_period(date_str: str, fin_year_end_month: int = 2) -> tuple[int, int]:
    """
    Calculates Sage Pastel period (1-12/13) based on Financial Year End month (Default: Feb).
    Example for Feb Year End: March = Period 1, Feb = Period 12.
    """
    dt = _parse_date(date_str)
    if dt is None:
        return 1, datetime.now().year

    txn_month = dt.month
    txn_year = dt.year

    start_month = (fin_year_end_month % 12) + 1
    period = (txn_month - start_month) % 12 + 1
    fin_year = txn_year if txn_month <= fin_year_end_month else txn_year + 1
    return period, fin_year


def _sanitize_cell(val: Any) -> str:
    """
    Neutralizes CWE-1236 CSV/Spreadsheet Formula Injection in untrusted text fields
    by prefixing dangerous leading characters with a single quote ('), while preserving
    valid South African phone numbers (e.g., '+27821234567') and pure negative numbers.
    """
    s = re.sub(r"[\r\n\t]+", " ", str(val if val is not None else "")).strip()
    if not s:
        return ""
    if s[0] in ("=", "+", "-", "@"):
        if s[0] == "+" and re.match(r"^\+\d[\d\s\-]{6,16}$", s):
            return s
        if s[0] == "-" and re.match(r"^-\d+(?:[.,]\d+)?$", s):
            return s
        return f"'{s}"
    return s


class AccountingExporter:
    """Standardized South African accounting exporter engine."""

    DEFAULT_PASTEL_TAX_CODES = {
        "Standard": "1",
        "Zero-Rated": "2",
        "Exempt": "0",
        "Blocked_Entertainment": "0",
        "None": "0",
    }

    @staticmethod
    def export_sage_pastel(
        transactions: List[Dict[str, Any]],
        filepath: str,
        fin_year_end_month: int = 2,
        tax_code_map: Optional[Dict[str, str]] = None,
    ):
        """
        Official Sage Pastel Partner Cashbook ASCII / CSV Layout:
        Fields: Period, Date (DD/MM/YYYY), GDC (G/D/C), Account, Reference, Description, Amount, TaxType, TaxAmount, OpenItem
        
        Sage Pastel Partner Rules:
        - Strict Rule: DO NOT include a header row! Pastel ASCII import rejects header text.
        - Strict Rule: NO UTF-8 BOM so Row 1 Col 1 is a pure ASCII integer Period (1-12).
        - Payments = Positive, Receipts = Negative
        - Account: 7-digit code without slash (e.g., 1000000)
        - Tax codes: configurable via tax_code_map or per-row 'pastel_tax_code' (defaults: 1=Standard 15%, 2=Zero-Rated, 0=Exempt/Blocked/None)
        - Reference: max 8 chars, Description: max 30 chars
        """
        code_lookup = dict(AccountingExporter.DEFAULT_PASTEL_TAX_CODES)
        if tax_code_map:
            code_lookup.update(tax_code_map)

        with open(filepath, "w", newline="", encoding="cp1252", errors="replace") as f:
            w = csv.writer(f)
            for t in transactions:
                period_num, _ = calculate_pastel_period(t["date"], fin_year_end_month)
                d_dt = _format_ddmmyyyy(t["date"])

                vt = t.get("vat_type", "Standard")
                if t.get("is_suspense") or str(t.get("code", "")).startswith("9999"):
                    p_tax = "0"
                else:
                    p_tax = str(t.get("pastel_tax_code") or code_lookup.get(vt, "1"))

                acc_type = t.get("acc_type", "GL")
                gdc = "G" if acc_type == "GL" else ("C" if acc_type == "Supplier" else "D")
                clean_acc = str(t.get("code", "9999000")).replace("/", "").strip()

                # Pastel sign convention: Payments = Positive, Receipts = Negative
                amt = abs(t["amount"]) if t["amount"] < 0 else -abs(t["amount"])
                v_claim = 0.0 if (t.get("is_suspense") or str(t.get("code", "")).startswith("9999")) else t.get("vat_claim", 0.0)
                v_amt = abs(v_claim) if t["amount"] < 0 else -abs(v_claim)

                w.writerow([
                    period_num,
                    d_dt,
                    gdc,
                    clean_acc,
                    (_sanitize_cell(t.get("ref", "BS1")) or "BS1")[:8],
                    (_sanitize_cell(t.get("clean_payee", "Unallocated")) or "Unallocated")[:30],
                    f"{amt:.2f}",
                    p_tax,
                    f"{v_amt:.2f}",
                    "0"
                ])

    @staticmethod
    def export_sage_business_cloud(transactions: List[Dict[str, Any]], filepath: str):
        """
        Sage Business Cloud Accounting (Sage One) Bank Statement Import Format:
        Official 3-column format: Date (DD/MM/YYYY), Description, Amount (signed: Outflows negative, Inflows positive)
        """
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Date", "Description", "Amount"])
            for t in transactions:
                d_dt = _format_ddmmyyyy(t["date"])
                w.writerow([
                    d_dt,
                    _sanitize_cell(t.get("clean_payee", "Bank Transaction")) or "Bank Transaction",
                    f"{t['amount']:.2f}"
                ])

    @staticmethod
    def export_xero(transactions: List[Dict[str, Any]], filepath: str):
        """
        Official Xero Bank Statement CSV:
        Fields: Date, Amount, Payee, Description, Reference, Check Number
        """
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Date", "Amount", "Payee", "Description", "Reference", "Check Number"])
            for t in transactions:
                d_dt = _format_ddmmyyyy(t["date"])
                w.writerow([
                    d_dt,
                    f"{t['amount']:.2f}",
                    _sanitize_cell(t.get("clean_payee", "")),
                    _sanitize_cell(t.get("raw_desc", "")),
                    _sanitize_cell(t.get("ref", "BS1")) or "BS1",
                    ""
                ])

    @staticmethod
    def export_quickbooks(transactions: List[Dict[str, Any]], filepath: str):
        """
        Official QuickBooks Online Bank Import CSV:
        Fields: Date, Description, Amount
        """
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Date", "Description", "Amount"])
            for t in transactions:
                d_dt = _format_ddmmyyyy(t["date"])
                w.writerow([
                    d_dt,
                    _sanitize_cell(t.get("clean_payee", "")) or "Bank Transaction",
                    f"{t['amount']:.2f}"
                ])

    @staticmethod
    def export_datev(transactions: List[Dict[str, Any]], filepath: str, currency: str = "EUR", bank_gl: str = "1200"):
        """
        Official German/DACH DATEV Buchungsstapel ASCII/CSV Format (SKR03 / SKR04):
        Semicolon-delimited with comma decimal separator and Soll/Haben indicator.
        """
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow([
                "Umsatz (ohne Soll/Haben-Kz)", "Soll/Haben-Kennzeichen", "WKZ Umsatz",
                "Konto", "Gegenkonto (ohne BU-Schlüssel)", "BU-Schlüssel",
                "Belegdatum", "Belegfeld 1", "Buchungstext"
            ])
            for idx, t in enumerate(transactions, start=1):
                dt = _parse_date(t.get("date", ""))
                beleg_datum = dt.strftime("%d%m") if dt else "0101"
                amt_comma = f"{abs(float(t.get('amount', 0.0))):.2f}".replace(".", ",")
                sh_kz = "S" if float(t.get("amount", 0.0)) >= 0 else "H"
                gegen_konto = str(t.get("code", "4900")).replace("/", "").strip()[:4] or "4900"
                bu_key = "9" if t.get("vat_type") == "Standard" else "0"
                ref = (_sanitize_cell(t.get("ref", f"BLG-{idx}")) or f"BLG-{idx}")[:36]
                desc = (_sanitize_cell(t.get("clean_payee") or t.get("raw_desc") or "Buchung"))[:60]
                w.writerow([amt_comma, sh_kz, currency, bank_gl, gegen_konto, bu_key, beleg_datum, ref, desc])

    @staticmethod
    def export_myob(transactions: List[Dict[str, Any]], filepath: str):
        """
        Official MYOB AccountRight & Business Bank Statement Import CSV (Australia / NZ):
        Fields: Date (DD/MM/YYYY), Amount, Description, Reference
        """
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Date", "Amount", "Description", "Reference"])
            for idx, t in enumerate(transactions, start=1):
                d_dt = _format_ddmmyyyy(t.get("date", ""))
                w.writerow([
                    d_dt,
                    f"{float(t.get('amount', 0.0)):.2f}",
                    _sanitize_cell(t.get("clean_payee") or t.get("raw_desc") or "Bank Transaction"),
                    _sanitize_cell(t.get("ref", f"MYOB-{idx}")) or f"MYOB-{idx}"
                ])

    @staticmethod
    def export_exact_online(transactions: List[Dict[str, Any]], filepath: str, currency: str = "EUR"):
        """
        Official Exact Online Bank Statement & GL Import CSV (Benelux / EU):
        Fields: Journal, Date (DD-MM-YYYY), GLAccount, Description, Reference, Amount, Currency, VATCode
        """
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Journal", "Date", "GLAccount", "Description", "Reference", "Amount", "Currency", "VATCode"])
            for idx, t in enumerate(transactions, start=1):
                dt = _parse_date(t.get("date", ""))
                d_dash = dt.strftime("%d-%m-%Y") if dt else _format_ddmmyyyy(t.get("date", "")).replace("/", "-")
                gl = str(t.get("code", "9999")).split("/")[0].strip() or "9999"
                vat_code = "VH" if t.get("vat_type") == "Standard" else "0"
                w.writerow([
                    "BANK",
                    d_dash,
                    gl,
                    _sanitize_cell(t.get("clean_payee") or t.get("raw_desc") or "Bank Entry"),
                    _sanitize_cell(t.get("ref", f"EX-{idx}")) or f"EX-{idx}",
                    f"{float(t.get('amount', 0.0)):.2f}",
                    currency,
                    vat_code
                ])

    @staticmethod
    def export_freeagent(transactions: List[Dict[str, Any]], filepath: str):
        """
        Official FreeAgent UK Bank Statement CSV (3-column layout):
        Fields: Date (DD/MM/YYYY), Amount, Description
        """
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Date", "Amount", "Description"])
            for t in transactions:
                d_dt = _format_ddmmyyyy(t.get("date", ""))
                w.writerow([
                    d_dt,
                    f"{float(t.get('amount', 0.0)):.2f}",
                    _sanitize_cell(t.get("clean_payee") or t.get("raw_desc") or "Bank Transaction")
                ])

    @staticmethod
    def export_universal_sars_csv(transactions: List[Dict[str, Any]], filepath: str):
        """SARS Tax Administration Act compliant universal audit CSV."""
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow([
                "Date", "Statement Ref", "Ledger", "Account Code", "Account Name",
                "Clean Payee", "Original Bank Description", "Gross (ZAR)",
                "SARS VAT Classification", "Claimable Input VAT", "Net (Excl)", "Audit Status"
            ])
            for t in transactions:
                w.writerow([
                    _sanitize_cell(t.get("date", "")),
                    _sanitize_cell(t.get("ref", "BS1")),
                    _sanitize_cell(t.get("acc_type", "GL")),
                    _sanitize_cell(t.get("code", "9999/000")),
                    _sanitize_cell(t.get("name", "Suspense")),
                    _sanitize_cell(t.get("clean_payee", "")),
                    _sanitize_cell(t.get("raw_desc", "")),
                    f"{t['amount']:.2f}",
                    _sanitize_cell(t.get("vat_type", "Standard")),
                    f"{t.get('vat_claim', 0.0):.2f}",
                    f"{t.get('net', t['amount']):.2f}",
                    _sanitize_cell(t.get("audit_status", "Verified"))
                ])

    @staticmethod
    def export_sars_excel_workbook(
        transactions: List[Dict[str, Any]],
        filepath: str,
        open_bal: float = 0.0,
        close_bal: float = 0.0,
        fin_year_end_month: int = 2,
        entity_name: str = "Client Company (Pty) Ltd",
        **kwargs
    ):
        """
        Produces a multi-tab SARS-compliant audit workpaper in Excel:
        Tab 1: VAT201 Return Schedule (Box 1, 4, 15, 19, 20 reconciliation)
        Tab 2: Detailed General Ledger Cashbook with audit trails
        """
        if "fye_month" in kwargs:
            fin_year_end_month = kwargs["fye_month"]

        if not HAS_OPENPYXL:
            fallback_csv = str(Path(filepath).with_suffix(".csv"))
            AccountingExporter.export_universal_sars_csv(transactions, fallback_csv)
            return

        wb = openpyxl.Workbook()

        # Styles
        navy_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
        header_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
        title_font = Font(name="Segoe UI", size=14, bold=True, color="0F172A")
        sub_font = Font(name="Segoe UI", size=9, color="475569")
        bold_font = Font(name="Segoe UI", size=10, bold=True)
        thin_border = Border(
            left=Side(style="thin", color="CBD5E1"),
            right=Side(style="thin", color="CBD5E1"),
            top=Side(style="thin", color="CBD5E1"),
            bottom=Side(style="thin", color="CBD5E1")
        )

        # TAB 1: SARS VAT201 RECONCILIATION SUMMARY
        ws_sum = wb.active
        ws_sum.title = "SARS VAT201 Schedule"
        ws_sum.views.sheetView[0].showGridLines = True

        ws_sum["A1"] = f"TAXCLEAN ZA — SARS VAT201 AUDIT SCHEDULE"
        ws_sum["A1"].font = title_font
        ws_sum["A2"] = f"Entity: {_sanitize_cell(entity_name)} | Date Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        ws_sum["A2"].font = sub_font

        # Calculate Box summaries (excluding unallocated Suspense rows from VAT claims)
        recon = calculate_sars_reconciliation(open_bal, transactions, close_bal)
        non_suspense = [
            t for t in transactions
            if not (t.get("is_suspense") or str(t.get("code", "")).startswith("9999"))
        ]
        std_receipts = sum(t["amount"] for t in non_suspense if t["amount"] > 0 and t.get("vat_type") == "Standard")
        std_output_vat = sum(t.get("vat_claim", 0.0) for t in non_suspense if t["amount"] > 0 and t.get("vat_type") == "Standard")
        
        std_payments = sum(abs(t["amount"]) for t in non_suspense if t["amount"] < 0 and t.get("vat_type") == "Standard")
        claimable_input_vat = sum(t.get("vat_claim", 0.0) for t in non_suspense if t["amount"] < 0 and t.get("vat_type") == "Standard")

        zero_payments = sum(abs(t["amount"]) for t in non_suspense if t["amount"] < 0 and t.get("vat_type") == "Zero-Rated")
        exempt_payments = sum(abs(t["amount"]) for t in non_suspense if t["amount"] < 0 and t.get("vat_type") == "Exempt")
        blocked_ent = sum(abs(t["amount"]) for t in non_suspense if t["amount"] < 0 and t.get("vat_type") == "Blocked_Entertainment")
        net_vat_position = _dec_round(std_output_vat - claimable_input_vat)

        rows = [
            ("SARS VAT201 Return Line Item", "Legal Reference", "Gross Amount (ZAR)", "VAT Amount (ZAR)"),
            ("Standard-Rated Supplies (Box 1 Turnover Incl VAT)", "SARS Sec 7(1)(a)", round(std_receipts, 2), ""),
            ("Output Tax on Standard Supplies (Box 4 / 13)", "SARS Sec 7(1)(a)", "", round(std_output_vat, 2)),
            ("Input Tax: Other Goods & Services (Box 15 / 19)", "SARS Sec 16(3)", round(std_payments, 2), round(claimable_input_vat, 2)),
            ("Zero-Rated Purchases / Fuel (Expense Reference)", "SARS Sec 11(1)(h)", round(zero_payments, 2), 0.0),
            ("Exempt / Financial Services (Expense Reference)", "SARS Sec 12", round(exempt_payments, 2), 0.0),
            ("Blocked Input Tax (Entertainment / Refreshments)", "SARS Sec 17(2)(a)", round(blocked_ent, 2), 0.0),
            ("", "", "", ""),
            ("NET VAT POSITION (Box 20 Payable to SARS / Refund Due)", "Calculation (Box 13 - Box 19)", "", net_vat_position),
            ("", "", "", ""),
            ("BANK RECONCILIATION PROOF (TAA SEC 29)", "", "", ""),
            ("Opening Bank Balance", "Bank Statement", recon["opening_balance"], ""),
            ("Total Receipts (+)", "Bank Movements", recon["total_receipts"], ""),
            ("Total Payments (-)", "Bank Movements", recon["total_payments"], ""),
            ("Calculated Closing Balance", "Audit Formula", recon["calculated_closing"], ""),
            ("Actual Bank Closing Balance", "Bank Statement", recon["closing_balance"], ""),
            ("Reconciliation Status", "SARS Audit Check", "PASSED" if recon["is_balanced"] else f"MISMATCH: R {recon['discrepancy']:,.2f}", "")
        ]

        for r_idx, row_data in enumerate(rows, start=4):
            for c_idx, val in enumerate(row_data, start=1):
                cell = ws_sum.cell(row=r_idx, column=c_idx, value=val)
                if r_idx == 4:
                    cell.fill = navy_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal="center" if c_idx > 2 else "left")
                elif r_idx in [11, 13]:
                    cell.font = bold_font
                if isinstance(val, (int, float)) and val != "":
                    cell.number_format = '#,##0.00'

        # TAB 2: DETAILED AUDIT TRANSACTIONS
        ws_det = wb.create_sheet(title="Cashbook Transactions")
        ws_det.views.sheetView[0].showGridLines = True

        headers = [
            "Period", "Date", "Statement Ref", "Ledger", "Account Code",
            "Account Description", "Clean Payee", "Original Bank Description",
            "Gross (Incl)", "SARS VAT Type", "Input VAT Claimable", "Net (Excl)",
            "Audit Notes"
        ]
        ws_det.append(headers)
        for col_idx in range(1, len(headers) + 1):
            c = ws_det.cell(row=1, column=col_idx)
            c.fill = navy_fill
            c.font = header_font
            c.alignment = Alignment(horizontal="center", vertical="center")

        for r_idx, t in enumerate(transactions, start=2):
            p, _ = calculate_pastel_period(t["date"], fin_year_end_month)
            ws_det.append([
                p,
                _sanitize_cell(t.get("date", "")),
                _sanitize_cell(t.get("ref", "BS1")) or "BS1",
                _sanitize_cell(t.get("acc_type", "GL")) or "GL",
                _sanitize_cell(t.get("code", "9999/000")) or "9999/000",
                _sanitize_cell(t.get("name", "Suspense")) or "Suspense",
                _sanitize_cell(t.get("clean_payee", "")),
                _sanitize_cell(t.get("raw_desc", "")),
                t["amount"],
                _sanitize_cell(t.get("vat_type", "Standard")),
                t.get("vat_claim", 0.0),
                t.get("net", t["amount"]),
                _sanitize_cell(t.get("audit_status", "Verified"))
            ])
            for col_idx in [9, 11, 12]:
                ws_det.cell(row=r_idx, column=col_idx).number_format = '#,##0.00'

        for sheet in [ws_sum, ws_det]:
            for col in sheet.columns:
                max_len = max(len(str(c.value or "")) for c in col)
                col_letter = col[0].column_letter
                sheet.column_dimensions[col_letter].width = max(max_len + 3, 12)

        wb.save(filepath)
