# TaxClean ZA — South African Bank Statement OCR & Accounting Automation Suite

**Live Platform:** [https://taxcleanza.com](https://taxcleanza.com) · **Desktop App:** Windows MSIX & macOS Build

TaxClean ZA is a desktop and web accounting automation suite tailored for South African bookkeepers, SMEs, and tax practitioners. It extracts structured transactions from PDF and scanned bank statements using local high-speed OCR, validates bank formats across major South African banks, and exports SARS-compliant schedules alongside ready-to-import formats for Sage Pastel, Xero, and QuickBooks.

---

## Key Engineering Highlights

- **Desktop PDF & Local OCR Pipeline (`TaxCleanDesktop.pyw`)**
  - Built in Python with CustomTkinter (`customtkinter`), `pypdf`, `pypdfium2`, `pdfplumber`, `rapidocr_onnxruntime`, and `onnxruntime`.
  - Runs OCR locally so sensitive financial PDFs can be parsed on-device without uploading raw statements by default.
- **South African Bank Format Diagnostics (`sa_bank_checker.py`)**
  - Detects and normalizes statement structures across FNB (Cheque & Aspire/Platinum Credit), Standard Bank, ABSA, Nedbank, Capitec (dual-date columns), Investec, Discovery Bank, and generic statements.
- **Accounting & SARS-Compliant Exporters (`exporters.py`, `compliance.py`)**
  - Generates formatted Excel/CSV exports for **Sage Pastel Partner (10-column Cashbook)**, **Sage Business Cloud Accounting (Sage One)**, **Xero South African Bank Feed**, **QuickBooks Online SA**, and **SARS VAT201 Audit Schedules** (TAA Section 29/30 aligned) with masked account output.
- **Offline RSA-1024 Asymmetric Licensing (`licensing.py`)**
  - Embeds only the RSA-1024 public verification modulus (`PUBLIC_MODULUS_N`) client-side for 100% offline license verification and hardware ID binding; private signing keys never leave vendor environments.
- **Edge Pricing & Entitlements Worker + Web Platform (`worker.js`, `website/`)**
  - Multi-currency server-authoritative SKU catalog (`worker.js` on Cloudflare Workers) paired with MSIX/PyInstaller desktop packaging (`build_msix.py`, `TaxCleanZA.spec`, `build_macos.sh`) and localized bank converter pages (`website/`).

---

## Tech Stack

- **Desktop App:** Python 3, CustomTkinter, RapidOCR (ONNX Runtime), `pypdf` / `pdfplumber` / `pypdfium2`, `openpyxl`, NumPy, Pillow, PyInstaller / MSIX
- **Web & Edge API:** Cloudflare Workers (`worker.js`, `wrangler.toml`), HTML/CSS/JS static web platform (`website/`)
- **Testing & QA:** Python pre-deploy verification & Playwright browser suite (`verify_all_pre_deploy.py`, `test_complete_r49_suite.py`)

---

## Local Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Launch desktop application
python TaxCleanDesktop.pyw
```

*(Private signing scripts, `.env*` secrets, sample bank statement PDFs, and internal operational utilities are excluded from version control.)*
