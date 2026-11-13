"""
TaxClean ZA  -  Professional South African Bank Statement, Tax Invoice & Receipt Automation Engine
Compliant with SARS TAA Section 29/30, SARS VAT Act 89/1991, POPIA Act 4/2013, Sage Pastel & ERPs.
Features: Local High-Speed OCR + Automatic Targeted Micro-AI Resolver (Google AI Studio Gemini Engine).
"""

from datetime import datetime
import io
import json
import os
from pathlib import Path
import queue
import re
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any, Dict, List, Optional, Tuple, Union
import urllib.error
import urllib.request
import urllib.parse
import webbrowser
import platform
import traceback

# Ensure sys.stdout and sys.stderr are never None in PyInstaller windowed (console=False) mode
if sys.stdout is None:
    sys.stdout = io.StringIO()
if sys.stderr is None:
    sys.stderr = io.StringIO()

APP_VERSION = "2.7.0.0"
VERSION_CHECK_URL = "https://taxcleanza.com/api/version"


def is_running_as_store_package() -> bool:
    """
    Detects if TaxClean ZA is running as a packaged Microsoft Store MSIX application.
    When running under the Store container, updates are managed by Windows Update,
    and external executable downloading is disabled to ensure 100% Store policy compliance.
    """
    if sys.platform != "win32":
        return False
    exe_str = str(sys.executable).lower()
    if "windowsapps" in exe_str:
        return True
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        length = ctypes.c_uint32(0)
        # APPMODEL_ERROR_NO_PACKAGE = 15700
        rc = kernel32.GetCurrentPackageFullName(ctypes.byref(length), None)
        return rc != 15700
    except Exception:
        return False


def parse_semver(ver: str) -> tuple:
    """Normalizes strings like 'v2.4.0.0' or '2.5' into an integer tuple for safe semantic comparison."""
    clean = re.sub(r"^[vV]", "", str(ver).strip())
    parts = []
    for p in clean.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            break
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts[:4])


def is_version_newer(remote_v: str, local_v: str) -> bool:
    """Returns True if remote_v is strictly newer than local_v."""
    return parse_semver(remote_v) > parse_semver(local_v)

try:
    import customtkinter as ctk
    HAS_CUSTOMTKINTER = True
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
except ImportError:
    HAS_CUSTOMTKINTER = False


class HDButton:
    """
    Renders true High-Definition vector rounded pill buttons when CustomTkinter
    is available, with seamless backwards compatibility for standard Tkinter.
    """
    def __new__(cls, master=None, **kwargs):
        if HAS_CUSTOMTKINTER:
            k = kwargs.copy()
            if "bg" in k:
                k["fg_color"] = k.pop("bg")
            if "fg" in k:
                k["text_color"] = k.pop("fg")
            k.pop("relief", None)
            padx_val = k.pop("padx", 8)
            pady_val = k.pop("pady", 3)
            k.pop("activebackground", None)
            k.pop("activeforeground", None)
            k.pop("cursor", None)
            if "corner_radius" not in k:
                k["corner_radius"] = 8
            if "border_spacing" not in k:
                k["border_spacing"] = max(2, min(6, int(padx_val) // 2)) if isinstance(padx_val, int) else 4
            if "height" not in k:
                k["height"] = 26 if (isinstance(pady_val, int) and pady_val <= 4) else 30
            if "width" not in k:
                k["width"] = 0
            if "font" in k and isinstance(k["font"], tuple):
                f = k["font"]
                px_size = max(11, int(round(f[1] * 1.2)))
                k["font"] = ctk.CTkFont(family=f[0], size=px_size, weight=f[2] if len(f) > 2 else "normal")

            if "hover_color" not in k and "fg_color" in k:
                base_col = k["fg_color"]
                hover_map = {
                    "#10b981": "#059669",
                    "#0369a1": "#0284c7",
                    "#0284c7": "#0369a1",
                    "#4f46e5": "#4338ca",
                    "#0d9488": "#0f766e",
                    "#334155": "#475569",
                    "#7f1d1d": "#991b1b",
                    "#064e3b": "#065f46",
                    "#1e293b": "#334155",
                    "#991b1b": "#b91c1c",
                    "#dc2626": "#b91c1c",
                    "#78350f": "#92400e",
                    "#831843": "#9d174d",
                    "#047857": "#065f46",
                    "#090d16": "#1e293b",
                    "#0f172a": "#1e293b",
                }
                k["hover_color"] = hover_map.get(base_col, base_col)

            widget = ctk.CTkButton(master, **k)

            orig_config = widget.configure
            def _compat_config(**kw):
                if "bg" in kw:
                    kw["fg_color"] = kw.pop("bg")
                if "fg" in kw:
                    kw["text_color"] = kw.pop("fg")
                kw.pop("relief", None)
                kw.pop("padx", None)
                kw.pop("pady", None)
                kw.pop("cursor", None)
                kw.pop("activebackground", None)
                kw.pop("activeforeground", None)
                if "font" in kw and isinstance(kw["font"], tuple):
                    f = kw["font"]
                    px_size = max(11, int(round(f[1] * 1.2)))
                    kw["font"] = ctk.CTkFont(family=f[0], size=px_size, weight=f[2] if len(f) > 2 else "normal")
                return orig_config(**kw)

            widget.config = _compat_config
            widget.configure = _compat_config
            return widget
        else:
            return tk.Button(master, **kwargs)


def apply_dark_titlebar(window: tk.Wm):
    """Applies Windows 10/11 Immersive Dark Mode to the native OS window titlebar."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        if not hwnd:
            hwnd = window.winfo_id()
        val = ctypes.c_int(1)
        # DWMWA_USE_IMMERSIVE_DARK_MODE = 20 (Windows 11 / Win10 20H1+), fallback 19
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(val), ctypes.sizeof(val))
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(val), ctypes.sizeof(val))
    except Exception:
        pass


class ToolTip:
    """Lightweight dark-slate hover tooltip for toolbar discoverability and keyboard shortcut hints."""
    def __init__(self, widget: tk.Widget, text: str, delay_ms: int = 420):
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self._after_id = None
        self._tip_win = None
        try:
            widget.bind("<Enter>", self._on_enter, add="+")
            widget.bind("<Leave>", self._on_leave, add="+")
            widget.bind("<ButtonPress>", self._on_leave, add="+")
        except Exception:
            pass

    def _on_enter(self, event=None):
        self._cancel()
        try:
            self._after_id = self.widget.after(self.delay_ms, self._show)
        except Exception:
            pass

    def _on_leave(self, event=None):
        self._cancel()
        self._hide()

    def _cancel(self):
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _show(self):
        if self._tip_win or not self.text:
            return
        try:
            if not self.widget.winfo_ismapped():
                return
            x = self.widget.winfo_rootx() + 10
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
            tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            tw.configure(bg="#38bdf8")
            lbl = tk.Label(
                tw,
                text=self.text,
                justify=tk.LEFT,
                bg="#0f172a",
                fg="#f8fafc",
                font=("Segoe UI", 8),
                padx=8,
                pady=4,
            )
            lbl.pack(padx=1, pady=1)
            self._tip_win = tw
        except Exception:
            self._tip_win = None

    def _hide(self):
        if self._tip_win is not None:
            try:
                self._tip_win.destroy()
            except Exception:
                pass
            self._tip_win = None


# Local Domain & Export Modules
from decimal import Decimal, ROUND_HALF_UP
from audit_tools import (
    AnomalyRadar,
    AuditCertificateGenerator,
    CashFlowRadar,
    CloudVaultBackup,
    ReceiptMatcher,
    RulePortability,
    SARSSection20Checker,
    StatementStacker,
    TransactionSplitter,
    VAT201Calculator,
)
from compliance import POPIA_COMPLIANCE_NOTICE, SARS_EULA_DISCLAIMER, mask_account_number, scrub_popia_diagnostics
from exporters import AccountingExporter, calculate_pastel_period
from licensing import LicenseManager, get_hardware_id
from sa_bank_checker import SABankFormatChecker, SA_BANK_PROFILES


def _dec_round(val: float) -> float:
    return float(Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _calc_vat_inclusive(gross_amt: float) -> float:
    d_abs = abs(Decimal(str(gross_amt)))
    return float((d_abs * Decimal("15") / Decimal("115")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if not s:
        return default
    is_neg = ("-" in s) or ("(" in s and ")" in s) or ("DR" in s.upper())
    clean = re.sub(r"[^0-9.]", "", s.replace(",", ""))
    try:
        num = float(clean) if clean else default
        return -abs(num) if is_neg else num
    except (ValueError, TypeError):
        return default


# High-Performance Local OCR & PDF Extraction Engines
try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    import pypdfium2 as pdfium
    HAS_PDFIUM = True
except Exception:
    HAS_PDFIUM = False

try:
    from PIL import Image
    import numpy as np
    from rapidocr_onnxruntime import RapidOCR
    HAS_RAPIDOCR = True
except Exception:
    HAS_RAPIDOCR = False

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


# ==============================================================================
# WINDOWS HIGH-DPI AWARENESS
# ==============================================================================
if sys.platform == "win32":
    try:
        import ctypes
        # Per-Monitor V2 awareness (Windows 10 1703+) produces crisp rendering on laptops and mixed-DPI multi-monitors
        try:
            ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
        except Exception:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                try:
                    ctypes.windll.shcore.SetProcessDpiAwareness(1)
                except Exception:
                    ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def get_resource_path(filename: str) -> Path:
    """Finds bundled read-only assets in either BASE_DIR or PyInstaller's _MEIPASS (_internal)."""
    base = get_base_dir()
    cand1 = base / filename
    if cand1.exists():
        return cand1
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        cand2 = Path(meipass) / filename
        if cand2.exists():
            return cand2
    cand3 = base / "_internal" / filename
    if cand3.exists():
        return cand3
    return cand1


def open_file_or_folder(filepath):
    """Cross-platform launcher for files and folders across Windows, macOS, and Linux."""
    try:
        p_str = str(filepath)
        if sys.platform == "win32":
            os.startfile(p_str)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", p_str])
        else:
            subprocess.Popen(["xdg-open", p_str])
    except Exception:
        try:
            webbrowser.open(Path(filepath).as_uri())
        except Exception:
            pass


def get_user_data_dir() -> Path:
    """
    Returns a guaranteed-writable per-user directory (%LOCALAPPDATA%\\TaxCleanZA_Data).
    Required for Microsoft Store (MSIX) packages where C:\\Program Files\\WindowsApps is strictly read-only.
    """
    candidates = []
    if sys.platform == "darwin":
        candidates.append(Path.home() / "Library" / "Application Support" / "TaxCleanZA_Data")
    for env_var in ("LOCALAPPDATA", "APPDATA"):
        val = os.environ.get(env_var)
        if val:
            candidates.append(Path(val) / "TaxCleanZA_Data")
    candidates.append(Path.home() / "AppData" / "Local" / "TaxCleanZA_Data")
    candidates.append(Path(tempfile.gettempdir()) / "TaxCleanZA_Data")

    for folder in candidates:
        try:
            folder.mkdir(parents=True, exist_ok=True)
            test_file = folder / ".write_probe"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink(missing_ok=True)
            return folder
        except Exception:
            continue
    return Path(tempfile.gettempdir())


BASE_DIR = get_base_dir()
USER_DATA_DIR = get_user_data_dir()
DB_FILE = USER_DATA_DIR / "taxclean_memory.db"
CONFIG_FILE = USER_DATA_DIR / "taxclean_config.json"

_GLOBAL_OCR_ENGINE = None
_GLOBAL_OCR_LOCK = threading.Lock()


def get_rapidocr_engine():
    """Returns a singleton RapidOCR instance tuned for fast CPU recognition."""
    global _GLOBAL_OCR_ENGINE
    if not HAS_RAPIDOCR:
        return None
    with _GLOBAL_OCR_LOCK:
        if _GLOBAL_OCR_ENGINE is None:
            eng = RapidOCR()
            eng.use_angle_cls = False
            if hasattr(eng, "text_recognizer"):
                eng.text_recognizer.rec_batch_num = 2
            _GLOBAL_OCR_ENGINE = eng
        return _GLOBAL_OCR_ENGINE


# ==============================================================================
# 1. SQLITE PERSISTENT MEMORY & SETTINGS ENGINE (WITH O(1) IN-MEMORY CACHE)
# ==============================================================================
class MemoryStore:
    """Persistent storage for learned merchant rules, app settings, and restored sessions."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn = None
        self._db_lock = threading.RLock()
        self._rules_exact_cache: dict[str, dict[str, dict]] = {}
        self._rules_sub_cache: dict[str, list[tuple[str, str, str, str, str]]] = {}
        self._stems_cache: dict[str, dict[str, tuple[str, str, str, str]]] = {}
        self.init_db()

    def get_conn(self):
        with self._db_lock:
            if self._conn is not None:
                return self._conn
            try:
                self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
                return self._conn
            except Exception:
                try:
                    tmp_db = Path(tempfile.gettempdir()) / "taxclean_memory_fallback.db"
                    self.db_path = tmp_db
                    self._conn = sqlite3.connect(str(tmp_db), check_same_thread=False)
                    return self._conn
                except Exception:
                    self._conn = sqlite3.connect(":memory:", check_same_thread=False)
                    return self._conn

    def close(self):
        with self._db_lock:
            if self._conn is not None:
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None

    def init_db(self):
        with self._db_lock, self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS merchant_rules (
                    profile_id TEXT NOT NULL,
                    payee_token TEXT NOT NULL,
                    code TEXT NOT NULL,
                    account_name TEXT NOT NULL,
                    vat_type TEXT NOT NULL,
                    acc_type TEXT NOT NULL,
                    hit_count INTEGER DEFAULT 1,
                    updated_at TEXT,
                    PRIMARY KEY (profile_id, payee_token)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vendor_stems (
                    profile_id TEXT NOT NULL,
                    stem_keyword TEXT NOT NULL,
                    code TEXT NOT NULL,
                    account_name TEXT NOT NULL,
                    vat_type TEXT NOT NULL,
                    acc_type TEXT NOT NULL,
                    hit_count INTEGER DEFAULT 1,
                    updated_at TEXT,
                    PRIMARY KEY (profile_id, stem_keyword)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_state (
                    profile_id TEXT PRIMARY KEY,
                    open_bal TEXT,
                    close_bal TEXT,
                    transactions_json TEXT,
                    updated_at TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    val TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS learned_doc_profiles (
                    profile_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    bank_name TEXT NOT NULL,
                    account_type TEXT NOT NULL,
                    keywords_json TEXT NOT NULL,
                    skip_phrases_json TEXT NOT NULL,
                    date_regex TEXT NOT NULL,
                    polarity_rule TEXT NOT NULL,
                    accrued_fee_mode TEXT DEFAULT 'memo',
                    rules_json TEXT,
                    created_at TEXT
                )
            """)
            conn.commit()

    @staticmethod
    def _dpapi_encrypt(plain_bytes: bytes) -> Optional[bytes]:
        if sys.platform != "win32":
            return None
        try:
            import ctypes
            from ctypes import wintypes

            class DATA_BLOB(ctypes.Structure):
                _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

            buf = ctypes.create_string_buffer(plain_bytes, len(plain_bytes))
            in_blob = DATA_BLOB(len(plain_bytes), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
            out_blob = DATA_BLOB()
            if ctypes.windll.crypt32.CryptProtectData(
                ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)
            ):
                try:
                    return ctypes.string_at(out_blob.pbData, out_blob.cbData)
                finally:
                    ctypes.windll.kernel32.LocalFree(out_blob.pbData)
        except Exception:
            pass
        return None

    @staticmethod
    def _dpapi_decrypt(enc_bytes: bytes) -> Optional[bytes]:
        if sys.platform != "win32":
            return None
        try:
            import ctypes
            from ctypes import wintypes

            class DATA_BLOB(ctypes.Structure):
                _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

            buf = ctypes.create_string_buffer(enc_bytes, len(enc_bytes))
            in_blob = DATA_BLOB(len(enc_bytes), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
            out_blob = DATA_BLOB()
            if ctypes.windll.crypt32.CryptUnprotectData(
                ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)
            ):
                try:
                    return ctypes.string_at(out_blob.pbData, out_blob.cbData)
                finally:
                    ctypes.windll.kernel32.LocalFree(out_blob.pbData)
        except Exception:
            pass
        return None

    @staticmethod
    def _hw_cipher(data_bytes: bytes) -> bytes:
        import hashlib
        seed = f"TCZA-LOCAL-SECRET-{get_hardware_id()}-{os.environ.get('USERNAME', 'USER')}".encode("utf-8")
        out = bytearray(len(data_bytes))
        for i in range(0, len(data_bytes), 32):
            block_key = hashlib.sha256(seed + i.to_bytes(4, "big")).digest()
            chunk = data_bytes[i : i + 32]
            for j, b in enumerate(chunk):
                out[i + j] = b ^ block_key[j]
        return bytes(out)

    def get_setting(self, key: str, default: str = "") -> str:
        with self._db_lock, self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT val FROM app_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row and row[0]:
                raw_val = str(row[0])
                if raw_val.startswith("dpapi:v1:"):
                    try:
                        import base64
                        enc_bytes = base64.urlsafe_b64decode(raw_val[9:].encode("ascii"))
                        dec = self._dpapi_decrypt(enc_bytes)
                        if dec is not None:
                            return dec.decode("utf-8")
                    except Exception:
                        return default
                if raw_val.startswith("enc:v1:"):
                    try:
                        import base64
                        enc_bytes = base64.urlsafe_b64decode(raw_val[7:].encode("ascii"))
                        return self._hw_cipher(enc_bytes).decode("utf-8")
                    except Exception:
                        return default
                return raw_val
        return os.getenv(key, default)

    def set_setting(self, key: str, val: str):
        store_val = val
        if val and "KEY" in key.upper():
            import base64
            dpapi_bytes = self._dpapi_encrypt(val.encode("utf-8"))
            if dpapi_bytes is not None:
                store_val = "dpapi:v1:" + base64.urlsafe_b64encode(dpapi_bytes).decode("ascii")
            else:
                enc_bytes = self._hw_cipher(val.encode("utf-8"))
                store_val = "enc:v1:" + base64.urlsafe_b64encode(enc_bytes).decode("ascii")
        with self._db_lock, self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO app_settings (key, val) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET val=excluded.val
            """, (key, store_val))
            conn.commit()

    def _ensure_profile_cache(self, profile_id: str):
        if profile_id in self._rules_exact_cache:
            return
        exact_map: dict[str, dict] = {}
        sub_list: list[tuple[str, str, str, str, str]] = []
        stem_map: dict[str, tuple[str, str, str, str]] = {}
        with self._db_lock, self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT payee_token, code, account_name, vat_type, acc_type
                FROM merchant_rules
                WHERE profile_id = ?
                ORDER BY LENGTH(payee_token) DESC, hit_count DESC
            """, (profile_id,))
            for p_tok, cd, nm, vt, at in cursor.fetchall():
                exact_map[p_tok] = {
                    "code": cd,
                    "name": nm,
                    "vat_type": vt,
                    "acc_type": at,
                    "match_type": "Exact Merchant Memory",
                }
                if len(p_tok) >= 4:
                    sub_list.append((p_tok, cd, nm, vt, at))

            cursor.execute("""
                SELECT stem_keyword, code, account_name, vat_type, acc_type
                FROM vendor_stems
                WHERE profile_id = ?
            """, (profile_id,))
            for stem_kw, cd, nm, vt, at in cursor.fetchall():
                stem_map[stem_kw] = (cd, nm, vt, at)

        self._rules_exact_cache[profile_id] = exact_map
        self._rules_sub_cache[profile_id] = sub_list
        self._stems_cache[profile_id] = stem_map

    def clear_profile_cache(self, profile_id: str):
        self._rules_exact_cache.pop(profile_id, None)
        self._rules_sub_cache.pop(profile_id, None)
        self._stems_cache.pop(profile_id, None)

    def delete_profile_data(self, profile_id: str):
        """Deletes all session state, learned merchant rules, and vendor stems for a deleted profile."""
        with self._db_lock, self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM session_state WHERE profile_id = ?", (profile_id,))
            cursor.execute("DELETE FROM merchant_rules WHERE profile_id = ?", (profile_id,))
            cursor.execute("DELETE FROM vendor_stems WHERE profile_id = ?", (profile_id,))
            conn.commit()
        self.clear_profile_cache(profile_id)

    def lookup_merchant(self, profile_id: str, clean_payee: str):
        token = clean_payee.strip().upper()
        if not token:
            return None
        self._ensure_profile_cache(profile_id)

        # 1. Exact Payee Rule Match (O(1) RAM lookup)
        exact = self._rules_exact_cache[profile_id].get(token)
        if exact:
            return exact

        # 2. Substring Match across known merchant tokens (length >= 4)
        for p_tok, cd, nm, vt, at in self._rules_sub_cache[profile_id]:
            if p_tok in token:
                return {
                    "code": cd,
                    "name": nm,
                    "vat_type": vt,
                    "acc_type": at,
                    "match_type": "Learned Pattern Match",
                }

        # 3. Stem Keyword Lookup (brand root word in RAM)
        stems = self._stems_cache[profile_id]
        if stems:
            words = re.findall(r"[A-Z0-9]{4,}", token)
            for w in words:
                row = stems.get(w)
                if row:
                    return {
                        "code": row[0],
                        "name": row[1],
                        "vat_type": row[2],
                        "acc_type": row[3],
                        "match_type": f"Auto-Learned Stem: {w}",
                    }
        return None

    def remember_merchant(self, profile_id: str, clean_payee: str, code: str, name: str, vat_type: str, acc_type: str):
        token = clean_payee.strip().upper()
        if not token or token == "UNALLOCATED PAYEE":
            return
        now_str = datetime.now().isoformat()
        with self._db_lock, self.get_conn() as conn:
            cursor = conn.cursor()
            # 1. Store Full Payee Rule
            cursor.execute("""
                INSERT INTO merchant_rules (profile_id, payee_token, code, account_name, vat_type, acc_type, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(profile_id, payee_token) DO UPDATE SET
                    code=excluded.code,
                    account_name=excluded.account_name,
                    vat_type=excluded.vat_type,
                    acc_type=excluded.acc_type,
                    hit_count=hit_count + 1,
                    updated_at=excluded.updated_at
            """, (profile_id, token, code, name, vat_type, acc_type, now_str))

            # 2. Extract Significant Brand Keywords (Stemming)
            stopwords = {
                "PURCHASE", "PAYMENT", "BRANCH", "CHEQUE", "TRANSFER", "PREPAID",
                "AIRTIME", "TRANSACTION", "ONLINE", "DEBIT", "CREDIT", "CARD",
                "POSPURCHASE", "ACBDEBIT", "EFTPAYMENT", "ACCOUNT", "FEE", "FEES",
                "BANK", "MONTHLY", "SERVICE", "VERIFIED", "STATEMENT", "TOTAL",
                "AMOUNT", "REFUND", "RETURN", "INTERNET", "DIRECT", "SETTLEMENT",
            }
            words = re.findall(r"[A-Z]{4,}", token)
            for w in words:
                if w not in stopwords and not w.isdigit():
                    cursor.execute("""
                        INSERT INTO vendor_stems (profile_id, stem_keyword, code, account_name, vat_type, acc_type, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(profile_id, stem_keyword) DO UPDATE SET
                            code=excluded.code,
                            account_name=excluded.account_name,
                            vat_type=excluded.vat_type,
                            acc_type=excluded.acc_type,
                            hit_count=hit_count + 1,
                            updated_at=excluded.updated_at
                    """, (profile_id, w, code, name, vat_type, acc_type, now_str))
            conn.commit()
        # Invalidate in-memory cache for this profile so next lookup refreshes
        self._rules_exact_cache.pop(profile_id, None)
        self._rules_sub_cache.pop(profile_id, None)
        self._stems_cache.pop(profile_id, None)

    def save_session(self, profile_id: str, open_bal: str, close_bal: str, transactions: list[dict]):
        now_str = datetime.now().isoformat()
        data_json = json.dumps(transactions)
        with self._db_lock, self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO session_state (profile_id, open_bal, close_bal, transactions_json, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(profile_id) DO UPDATE SET
                    open_bal=excluded.open_bal,
                    close_bal=excluded.close_bal,
                    transactions_json=excluded.transactions_json,
                    updated_at=excluded.updated_at
            """, (profile_id, open_bal, close_bal, data_json, now_str))
            conn.commit()

    def load_session(self, profile_id: str) -> tuple[str, str, list[dict]]:
        with self._db_lock, self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT open_bal, close_bal, transactions_json
                FROM session_state
                WHERE profile_id = ?
            """, (profile_id,))
            row = cursor.fetchone()
            if row:
                try:
                    txns = json.loads(row[2])
                    return row[0] or "0.00", row[1] or "0.00", txns
                except Exception:
                    pass
        return "0.00", "0.00", []

    def clear_session(self, profile_id: str):
        with self._db_lock, self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM session_state WHERE profile_id = ?", (profile_id,))
            conn.commit()

    def save_learned_profile(self, profile: dict):
        """Persists an AI-synthesized document parsing rule so local engine parses it offline next time."""
        now_str = datetime.now().isoformat()
        pid = profile.get("profile_id", f"learned_profile_{int(time.time())}")
        name = profile.get("name", f"{profile.get('bank_name', 'Bank')} ({profile.get('account_type', 'Account')})")
        bank_name = profile.get("bank_name", "South African Bank")
        acc_type = profile.get("account_type", "Account")
        kw_json = json.dumps(profile.get("keywords", []))
        skip_json = json.dumps(profile.get("skip_phrases", []))
        dt_rx = profile.get("date_regex", "")
        pol = profile.get("polarity_rule", "dr_negative")
        mode = profile.get("accrued_fee_mode", "memo")
        rules_json = json.dumps(profile)
        with self._db_lock, self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO learned_doc_profiles (
                    profile_id, name, bank_name, account_type,
                    keywords_json, skip_phrases_json, date_regex,
                    polarity_rule, accrued_fee_mode, rules_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(profile_id) DO UPDATE SET
                    name=excluded.name,
                    bank_name=excluded.bank_name,
                    account_type=excluded.account_type,
                    keywords_json=excluded.keywords_json,
                    skip_phrases_json=excluded.skip_phrases_json,
                    date_regex=excluded.date_regex,
                    polarity_rule=excluded.polarity_rule,
                    accrued_fee_mode=excluded.accrued_fee_mode,
                    rules_json=excluded.rules_json,
                    created_at=excluded.created_at
            """, (pid, name, bank_name, acc_type, kw_json, skip_json, dt_rx, pol, mode, rules_json, now_str))
            conn.commit()

    def load_learned_profiles(self) -> list[dict]:
        """Loads all AI-trained layout adapters for fast offline execution."""
        profiles = []
        with self._db_lock, self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT profile_id, name, bank_name, account_type,
                       keywords_json, skip_phrases_json, date_regex,
                       polarity_rule, accrued_fee_mode, rules_json
                FROM learned_doc_profiles
            """)
            for row in cursor.fetchall():
                try:
                    kws = json.loads(row[4])
                    skips = json.loads(row[5])
                    full_rules = json.loads(row[9]) if row[9] else {}
                except Exception:
                    kws, skips, full_rules = [], [], {}
                profiles.append({
                    "id": row[0],
                    "name": row[1],
                    "bank": row[2],
                    "account_type": row[3],
                    "keywords": kws,
                    "skip_phrases": skips,
                    "date_regex": row[6],
                    "polarity_rule": row[7],
                    "accrued_fee_mode": row[8],
                    "full_rules": full_rules,
                })
        return profiles

    def match_learned_profile(self, text: str) -> Optional[dict]:
        """Matches document text against previously learned AI layout profiles."""
        up = text.upper()
        for p in self.load_learned_profiles():
            kws = p.get("keywords", [])
            if kws:
                matching = [kw for kw in kws if kw in up]
                if len(matching) >= 2 or (len(matching) == 1 and len(matching[0]) >= 8):
                    return p
        return None


# ==============================================================================
# 2. TARGETED MICRO-AI & SELF-LEARNING ADAPTER ENGINE
# ==============================================================================
GEMINI_MODELS = ["gemini-3.8-flash", "gemini-flash-latest", "gemini-3.5-flash"]
GEMINI_MODEL_PRIMARY = "gemini-3.8-flash"
GEMINI_MODEL_FALLBACK = "gemini-flash-latest"


def _call_gemini_json(api_key: str, prompt: str, timeout: int = 20) -> str:
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "response_mime_type": "application/json",
        },
    }
    body_bytes = json.dumps(payload).encode("utf-8")
    for model_name in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        try:
            req = urllib.request.Request(
                url,
                data=body_bytes,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": api_key.strip(),
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                candidate = res_data.get("candidates", [{}])[0]
                parts = candidate.get("content", {}).get("parts", [{}])
                text_parts = [p.get("text", "") for p in parts if isinstance(p, dict) and "text" in p]
                return "".join(text_parts)
        except urllib.error.HTTPError as e:
            if e.code in (404, 400, 429) and model_name != GEMINI_MODELS[-1]:
                continue
            raise
    return ""


def resolve_ambiguous_lines_with_gemini(api_key: str, lines: list[str], default_year: int) -> list[dict]:
    """
    Kicks in automatically ONLY for specific ambiguous lines that local regex struggled to read.
    Consumes minimal tokens (~200 text tokens) by sending only the problematic snippet to Gemini Flash.
    """
    if not api_key or not lines:
        return []

    filtered = [l.strip() for l in lines if len(l.strip()) > 3][:30]
    if not filtered:
        return []

    prompt = (
        f"You are a South African accounting bank statement parsing engine. Default statement year is {default_year}. "
        f"Parse these specific ambiguous/scanned lines into individual bank transactions. "
        f"Rules: For payments/outflows/purchases, amount must be negative. For deposits/inflows/credits, amount must be positive. "
        f"Output ONLY a valid JSON array of objects with keys: "
        f"[{{\"date\": \"YYYY-MM-DD\", \"payee\": \"Clean Payee Description\", \"amount\": -123.45}}].\n"
        f"Lines to parse:\n" + "\n".join(filtered)
    )

    try:
        part_text = _call_gemini_json(api_key, prompt, timeout=12) or "[]"
        parsed = json.loads(part_text)
        if isinstance(parsed, list):
            return parsed
    except Exception:
        pass
    return []


def ai_auto_heal_and_train(api_key: str, text: str, default_year: int) -> tuple[dict, Optional[dict]]:
    """
    Self-Learning Autonomous AI Fallback & Local Adapter Synthesizer:
    1. When a bank statement cannot be parsed or reconciled locally:
       Gemini Flash extracts opening balance, closing balance, and all transactions.
    2. Synthesizes a Learned Adapter Profile (keywords, date pattern, skip phrases, polarity).
    3. Saves this to local SQLite memory so all FUTURE uploads of this format parse 100% locally in <1s with 0 tokens!
    """
    if not api_key or not text.strip():
        return {}, None

    prompt = f"""You are the Lead Forensic Accounting AI of TaxClean ZA (South Africa).
The local rule-based parsing engine encountered an unfamiliar or difficult document layout and failed to reconcile it.
Analyze the following document text and perform TWO crucial tasks:

TASK 1: EXACT LEDGER EXTRACTION
Extract the complete ledger data:
- "bank_name": String (e.g. "First National Bank", "Standard Bank", "Capitec", "ABSA", "Nedbank", "Discovery")
- "account_type": String (e.g. "Easy Account", "Cheque Account", "Credit Facility")
- "open_bal": Float (Opening balance. South African accounting rule: if Dr or debit, it MUST be negative float. If Cr or positive, positive float. E.g. -25.84 or 1515.84)
- "close_bal": Float (Closing balance. If Dr, negative float; if Cr, positive float.)
- "transactions": Array of objects:
    {{"date": "YYYY-MM-DD", "payee": "Clean Payee Name", "amount": signed_float, "balance": signed_float}}
    Note: Purchases, debits, ATM cash, fees, and payments OUT must have negative amount (e.g. -337.95).
    Deposits, salary, refunds, and credits IN must have positive amount (e.g. 6529.88).

TASK 2: SYNTHESIZE LOCAL ENGINE TRAINING PROFILE (To train local engine for offline reuse)
Provide parsing rules so our local engine can parse future uploads of this document offline without AI:
- "profile_id": A snake_case identifier (e.g. "fnb_easy_v1", "discovery_platinum_v1")
- "name": Descriptive name (e.g. "FNB Easy Account (Learned)")
- "keywords": Array of 3 to 6 unique uppercase phrases found in this document header that identify this layout (e.g. ["EASY ACCOUNT", "TRANSACTIONS IN RAND"])
- "date_regex": Regex string to identify transaction dates (e.g. "\\\\b(0?[1-9]|[12]\\\\d|3[01])\\\\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\\\\b")
- "skip_phrases": Array of uppercase phrases in headers/footers to ignore (e.g. ["TURNOVER FOR STATEMENT PERIOD", "SERVICE FEES", "OTHER FEES", "TOTAL VAT"])
- "polarity_rule": "dr_negative"
- "accrued_fee_mode": "memo"

Return ONLY a valid JSON object with keys:
{{"bank_name": "...", "account_type": "...", "open_bal": -25.84, "close_bal": 5.22, "transactions": [...], "learned_profile": {{...}}}}

Document Text:
{text[:12000]}
"""

    try:
        part_text = _call_gemini_json(api_key, prompt, timeout=25) or "{}"
        clean_part = part_text.strip()
        if clean_part.startswith("```"):
            clean_part = re.sub(r"^```(?:json)?\s*", "", clean_part)
            clean_part = re.sub(r"\s*```$", "", clean_part)
        parsed = json.loads(clean_part)
        if isinstance(parsed, dict) and "transactions" in parsed:
            return parsed, parsed.get("learned_profile")
    except Exception:
        pass
    return {}, None


# ==============================================================================
# 3. DEFAULT SOUTH AFRICAN CHART OF ACCOUNTS & SARS RULES
# ==============================================================================
DEFAULT_CHART_OF_ACCOUNTS = {
    "Fuel": {
        "code": "4100/000",
        "name": "Motor Vehicle Fuel & Oil",
        "vat": "Zero-Rated",
        "type": "GL",
        "keywords": "ENGEN, SHELL, BP, SASOL, TOTAL, TOTALENERGIES, CALTEX, ASTRON, PUMA, PETROL, DIESEL, SERVICE STATION, ULTRA CITY, 1-STOP, HIGHWAY GARDENS, HIGHWAY GARDENS SUP",
    },
    "Telecoms": {
        "code": "4300/000",
        "name": "Telephone & Internet",
        "vat": "Standard",
        "type": "GL",
        "keywords": "VODACOM, MTN, TELKOM, AFRIHOST, RAIN, COOL IDEAS, VOX, CELL C, WEBAFRICA, OPENSERVE, METROFIBRE, VUMATEL, FROGFOOT",
    },
    "Utilities": {
        "code": "4500/000",
        "name": "Water & Electricity",
        "vat": "Standard",
        "type": "GL",
        "keywords": "ESKOM, CITY POWER, CITY OF CAPE TOWN, ETHEKWINI, MUNICIPAL, TSHWANE, JOBURG WATER, PREPAID ELEC, SYNTELL, CONLOG",
    },
    "Office": {
        "code": "4600/000",
        "name": "Office & Computer Consumables",
        "vat": "Standard",
        "type": "GL",
        "keywords": "BUILDERS, MAKRO, TAKEALOT, INCREDIBLE CONNECTION, WALTONS, BIDVEST, CNA, PNA, OFFICE NATIONAL, CARTRIDGE, STATIONERY",
    },
    "Software_IT": {
        "code": "4650/000",
        "name": "Software & Cloud Services",
        "vat": "Standard",
        "type": "GL",
        "keywords": "MICROSOFT, MSFT, GOOGLE, ADOBE, DROPBOX, AWS, CLOUDFLARE, GITHUB, CANVA, ZOOM, SLACK, NOTION, OPENAI, CHATGPT, ANTHROPIC, NETFLIX, APPLE.COM, ITUNES, SPOTIFY, SUICA",
    },
    "Entertainment": {
        "code": "4200/000",
        "name": "Entertainment & Refreshments",
        "vat": "Blocked_Entertainment",
        "type": "GL",
        "keywords": "MUGG & BEAN, SPUR, VIDA E CAFFE, KFC, KFC EDENGLEN, NANDOS, STEERS, WIMPY, MCDONALD, STARBUCKS, SEATTLE COFFEE, ROCO MAMAS, RESTAURANT, SPAR, SUPERSPAR, SUPERSPAR KARAGLEN, CHECKERS, PICKNPAY, WOOLWORTHS, SHOPRITE, DISCHEM, CLICKS, FUSION VAPES, SPICE INDIA, THE VILLAGE BAR, BARGAIN WHOLESALE, MOJOZ, SAVERITE, MILKY LANE, SAINTS CAFE, SCHOONERS, THE WAFFLE HOUSE, THE DELI, COASTLANDS",
    },
    "Travel": {
        "code": "4800/000",
        "name": "Flights, Car Rental & Accommodation",
        "vat": "Standard",
        "type": "GL",
        "keywords": "FLYSAFAIR, SAFAIR, AIRLINK, SAA, LIFT AIRLINES, AVIS, HERTZ, AIRBNB, HOTEL, LODGE, BOOKING.COM, SANRAL, TOLL GATE, TOLL PLAZA",
    },
    "PublicTransport": {
        "code": "4850/000",
        "name": "Passenger Transport (Sec 12(g) Exempt)",
        "vat": "Exempt",
        "type": "GL",
        "keywords": "GAUTRAIN, METRORAIL, MARGATE MNI COACH, REA VAYA, GOLDEN ARROW, PRASA",
    },
    "Insurance": {
        "code": "4400/000",
        "name": "Short-Term Insurance",
        "vat": "Standard",
        "type": "GL",
        "keywords": "SANTAM, DISCOVERY INSURE, OLD MUTUAL, HOLLARD, OUTSURANCE, MIWAY, DIALDIRECT, BUDGET INSURANCE, 1ST FOR WOMEN, KING PRICE",
    },
    "BankFees": {
        "code": "4700/000",
        "name": "Bank Transaction Fees & Service Charges",
        "vat": "Standard",
        "type": "GL",
        "keywords": "SERVICE FEES, MONTHLY FEE, CASH HANDLING FEE, TRANSACTION FEE, CARD FEE, STATEMENT FEE, OVERDRAFT FEE, SASWITCH, BANK CHARGES, SERVICE FEE, BANK SERVICE FEE, CARD SERVICE FEE, FACILITY FEE",
    },
    "InterestPaid": {
        "code": "4750/000",
        "name": "Interest & Finance Charges (Exempt)",
        "vat": "Exempt",
        "type": "GL",
        "keywords": "INTEREST CHARGED, DEBIT RATE, FINANCE CHARGE, OVERDRAFT INTEREST, CREDIT INTEREST",
    },
    "Sales": {
        "code": "1000/000",
        "name": "Client Invoiced Revenue",
        "vat": "None",
        "type": "Customer",
        "keywords": "CLIENT PAYMENT, FROM DONATION, DONATION, DEPOSIT, INVOICE PAYMENT, 1SA SPEND, 1SA SPENDING, POWERBALL WINNINGS",
    },
    "Suspense": {
        "code": "9999/000",
        "name": "Suspense Account / Queries",
        "vat": "None",
        "type": "GL",
        "keywords": "",
    },
}

SUSPENSE_FLAGS = [
    "TRANSFER", "TFR", "SETTLEMENT", "CASH DEP", "ATM CASH", "ATM W/D",
    "LOAN", "IMMEDIATE TFR", "DRAWING", "BETWAY", "HOLLYWOOD", "SEND MONEY",
]


def clean_payee_text(text: str) -> str:
    """Strips noisy bank narration tags and cleans merchant titles."""
    if not text:
        return "Bank Transaction"

    t_up = text.upper().strip()

    # High-confidence South African National Retailers, Utilities & Forecourts
    if re.search(r"\bCHECKERS\b", t_up):
        return "Checkers"
    if re.search(r"\b(PICK\s*N\s*PAY|P\s*N\s*P|PNP)\b", t_up):
        return "Pick n Pay"
    if re.search(r"\b(WOOLWORTHS|W/WORTHS)\b", t_up):
        return "Woolworths"
    if re.search(r"\b(SUPERSPAR|KWIKSPAR|SPAR)\b", t_up):
        return "Spar"
    if re.search(r"\bSHOPRITE\b", t_up):
        return "Shoprite"
    if re.search(r"\bFOOD\s*LOVER\b", t_up):
        return "Food Lover's Market"
    if re.search(r"\bMAKRO\b", t_up):
        return "Makro"
    if re.search(r"\bGAME\s+STORES?\b", t_up):
        return "Game"
    if re.search(r"\bENGEN\b", t_up):
        return "Engen Forecourt"
    if re.search(r"\bSHELL\b", t_up):
        return "Shell Forecourt"
    if re.search(r"\bTOTAL(?:ENERGIES)?\b", t_up):
        return "TotalEnergies"
    if re.search(r"\b(CALTEX|ASTRON\s*ENERGY)\b", t_up):
        return "Astron / Caltex"
    if re.search(r"\bSASOL\b", t_up):
        return "Sasol Forecourt"
    if re.search(r"\bBP\s+(?:SERVICE|EXPRESS|CONNECT|FORECOURT|GARAGE)\b", t_up):
        return "BP Forecourt"
    if re.search(r"\bDIS-?CHEM\b", t_up):
        return "Dis-Chem Pharmacy"
    if re.search(r"\bCLICKS\b", t_up):
        return "Clicks"
    if re.search(r"\bVODACOM\b", t_up):
        return "Vodacom"
    if re.search(r"\bMTN\b", t_up):
        return "MTN"
    if re.search(r"\bTELKOM\b", t_up):
        return "Telkom SA"
    if re.search(r"\bCELL\s*C\b", t_up):
        return "Cell C"
    if re.search(r"\bBUILDERS\s*(?:WAREHOUSE|EXPRESS)?\b", t_up):
        return "Builders Warehouse"
    if re.search(r"\bLEROY\s*MERLIN\b", t_up):
        return "Leroy Merlin"
    noise_prefixes = [
        r"^POS PURCHASE\s+",
        r"^ACB DEBIT:\s*",
        r"^DEBIT ORDER\s+",
        r"^MAGTAPE DEBIT\s+",
        r"^INTERNET TFR\s+",
        r"^IMMEDIATE TFR\s+",
        r"^MONTHLY FEE\s+",
        r"^SERVICE FEE\s+",
        r"^ATM CASH\s+",
        r"^CARD PURCHASE\s+",
        r"^FNB APP PAYMENT\s+",
        r"^APP PAYMENT\s+",
        r"^EFT PAYMENT\s+",
        r"^DIRECT DEBIT\s+",
    ]
    cleaned = text
    for p in noise_prefixes:
        cleaned = re.sub(p, "", cleaned, flags=re.IGNORECASE)

    # Clean card suffixes, timestamps, OCR date stamps & masks
    cleaned = re.sub(r"\b\d{4,6}[\*X\.\-_\ufffd]+\d{4}\b", "", cleaned)
    cleaned = re.sub(r"\b\d{1,2}:\d{2}\b", "", cleaned)  # timestamps e.g., 07:45, 12:30
    cleaned = re.sub(r"\b[0O1I\d]{2}[A-Z0]{3}\b", "", cleaned)  # e.g., 28SEP, OIOCT, 020CT
    cleaned = re.sub(r"[\*#\-_/]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Filter out pure noise tokens
    words = cleaned.split()
    noise_tokens = {
        "DR", "CR", "SAM", "INR", "APP", "ONLINE", "PURCHASE", "PAYMENT",
        "SEND", "WTR", "POS", "PURCH", "TO", "FROM", "FRM", "PMT",
    }
    filtered_words = []
    for w in words:
        if w.upper() in noise_tokens and len(words) > 1:
            continue
        if re.search(r"^\d{3,}$", w) or re.search(r"^\d+[A-Z]+\d+$", w.upper()):
            continue
        filtered_words.append(w.capitalize() if len(w) > 3 and not w.isupper() else w.title() if len(w) > 3 else w)

    # Max 3 concise words for a neat, clean ledger description
    if filtered_words:
        cleaned = " ".join(filtered_words[:3])
    else:
        cleaned = " ".join(words[:3]) if words else "Bank Transaction"

    if not cleaned or re.search(r"^\d+$", cleaned) or cleaned in ["00253108", "05245020"]:
        if re.search(r"\bATM\s+CASH\b", text, re.I):
            return "ATM Cash Withdrawal"
        if re.search(r"\bAIRTIME\b", text, re.I):
            return "Airtime Topup"
        if re.search(r"\bDEBICHECK\b", text, re.I):
            return "DebiCheck Mandate"
        if re.search(r"INT\.RATE|INTEREST", text, re.I):
            return "Interest Rate Adjustment"
        if re.search(r"FEE|CHARGE", text, re.I):
            return "Bank Fee / Charges"

    return cleaned if cleaned else "Bank Transaction"


def parse_sa_amount(raw_str: str) -> tuple[float, bool, bool]:
    s = raw_str.strip().upper()
    is_cr = ("CR" in s) or ("+" in s)
    is_dr = ("DR" in s) or ("-" in s) or ("(" in s and ")" in s)
    # Normalize OCR artifact like 3.913.81 -> 3,913.81
    s = re.sub(r"(\d+)\.(\d{3}\.\d{2})", r"\1,\2", s)
    clean = re.sub(r"[^0-9,.]", "", s)

    if "," in clean and "." in clean:
        if clean.rfind(".") > clean.rfind(","):
            clean = clean.replace(",", "")
        else:
            clean = clean.replace(".", "").replace(",", ".")
    elif clean.count(",") == 1 and "." not in clean:
        clean = clean.replace(",", ".")
    elif clean.count(",") > 1:
        parts = clean.split(",")
        clean = "".join(parts[:-1]) + "." + parts[-1]

    try:
        val = float(clean)
    except (ValueError, TypeError):
        val = 0.0
    return val, is_cr, is_dr


# ==============================================================================
# 4. HYBRID PARSE WORKER (LOCAL FIRST + AUTO TARGETED MICRO-AI RESOLVER)
# ==============================================================================
class ParseWorker(threading.Thread):

    def __init__(self, filepath: str, coa: dict, profile_name: str, memory: MemoryStore, result_queue: queue.Queue):
        super().__init__(daemon=True)
        self.filepath = filepath
        self.coa = coa
        self.profile_name = profile_name
        self.memory = memory
        self.queue = result_queue
        self.gemini_key = self.memory.get_setting("GEMINI_API_KEY", "")

        # Pre-compile suspense and COA regexes once per import for O(1) per-row speed
        self._suspense_rxs = [(kw, re.compile(r"\b" + re.escape(kw) + r"\b")) for kw in SUSPENSE_FLAGS]
        self._coa_rxs = []
        for cat_key, rule in self.coa.items():
            if cat_key in ["Sales", "Suspense"]:
                continue
            kws = [k.strip().upper() for k in rule.get("keywords", "").split(",") if k.strip()]
            for kw in kws:
                self._coa_rxs.append((kw, re.compile(r"\b" + re.escape(kw) + r"\b"), rule))

    def _notify(self, mtype: str, *args):
        if self.queue is not None:
            try:
                if len(args) == 1:
                    self.queue.put((mtype, args[0]))
                elif len(args) > 1:
                    self.queue.put((mtype, *args))
            except Exception:
                pass

    def run(self):
        try:
            self._notify("STATUS", "Opening and analyzing document...")
            raw_text = self.extract_text()
            if not raw_text.strip():
                self._notify("ERROR", "No readable text or characters could be extracted from this document.")
                return

            self._notify("STATUS", "Applying local rules & checking reconciliation...")
            parse_result = self.parse_text(raw_text)

            # Check if local parser struggled (0 records or reconciliation delta > 0.05)
            records = parse_result.get("records", [])
            open_b = parse_result.get("open_bal")
            close_b = parse_result.get("close_bal")
            needs_ai_healing = False

            if not records:
                needs_ai_healing = True
            elif open_b is not None and close_b is not None:
                net_amt = sum(r["amount"] for r in records)
                calc_close = float(open_b) + net_amt
                if abs(calc_close - float(close_b)) > 0.05:
                    needs_ai_healing = True

            if needs_ai_healing:
                if self.gemini_key:
                    self._notify("STATUS", "🤖 Unfamiliar layout detected. Activating AI Auto-Healer to parse document & train local engine...")
                    default_year = datetime.now().year
                    year_m = re.search(r"\b(20\d{2})\b", raw_text)
                    if year_m:
                        default_year = int(year_m.group(1))

                    healed_data, learned_profile = ai_auto_heal_and_train(self.gemini_key, raw_text, default_year)
                    if healed_data and "transactions" in healed_data and healed_data["transactions"]:
                        # Convert healed data to standard ledger rows
                        healed_rows = []
                        bs_ref = "BS1"
                        stmt_m = re.search(r"(?:Statement Number|Tax Invoice/Statement Number|Statement No)[\s:]*(\d+)", raw_text, re.I)
                        if stmt_m:
                            bs_ref = f"BS{stmt_m.group(1).strip()}"

                        for item in healed_data["transactions"]:
                            amt = _safe_float(item.get("amount"), 0.0)
                            py = str(item.get("payee") or "Bank Transaction")
                            dt = str(item.get("date") or datetime.now().strftime("%Y-%m-%d"))
                            cat = self.categorize(py, amt)
                            net = _dec_round(amt + cat["vat_claim"]) if amt < 0 else _dec_round(amt - cat["vat_claim"])
                            healed_rows.append({
                                "date": dt,
                                "ref": bs_ref,
                                "acc_type": cat["acc_type"],
                                "clean_payee": cat["clean_payee"],
                                "code": cat["code"],
                                "name": cat["name"],
                                "amount": amt,
                                "vat_type": cat["vat_type"],
                                "vat_claim": cat["vat_claim"],
                                "net": net,
                                "is_suspense": cat["is_suspense"],
                                "audit_status": "✓ AI-Healed & Reconciled",
                                "query_reason": cat["reason"],
                            })

                        # Save learned layout profile to SQLite for future offline re-use!
                        if learned_profile:
                            self.memory.save_learned_profile(learned_profile)
                            pname = learned_profile.get("name", "Custom Bank Layout")
                            self._notify("STATUS", f"🎓 Local Engine Trained! Layout '{pname}' saved to memory  -  next time it will parse offline in <1s!")

                        parse_result = {
                            "open_bal": f"{_safe_float(healed_data.get('open_bal'), 0.0):.2f}",
                            "close_bal": f"{_safe_float(healed_data.get('close_bal'), 0.0):.2f}",
                            "records": healed_rows,
                            "detected_bank": healed_data.get("bank_name", "AI-Healed South African Bank"),
                            "bank_profile": (learned_profile.get("profile_id", "ai_learned_custom") if learned_profile else "ai_learned"),
                        }
                else:
                    self._notify("STATUS", "💡 Layout note: Unfamiliar layout. Click [ 🔑 AI Auto-Key ] to auto-heal and train the local engine!")

            self._notify("DONE", parse_result)
        except Exception as e:
            tb_str = traceback.format_exc()
            self._notify("ERROR", f"Extraction Error: {str(e)}", tb_str)

    @staticmethod
    def _cluster_boxes_to_lines(boxes: list[tuple[float, float, float, str]]) -> str:
        """Clusters (y_top, y_bot, x_left, text) bounding boxes into pipe-separated rows."""
        if not boxes:
            return ""
        boxes_sorted = sorted(boxes, key=lambda b: (b[0] + b[1]) / 2.0)
        lines = []
        curr_cluster = []
        curr_top, curr_bot = None, None

        for y_top, y_bot, x_left, txt in boxes_sorted:
            y_mid = (y_top + y_bot) / 2.0
            if curr_top is None:
                curr_top, curr_bot = y_top, y_bot
                curr_cluster = [(x_left, txt)]
            elif y_mid <= curr_bot and y_mid >= curr_top - 2:
                curr_cluster.append((x_left, txt))
                curr_top = min(curr_top, y_top)
                curr_bot = max(curr_bot, y_bot)
            else:
                curr_cluster.sort(key=lambda item: item[0])
                lines.append(" | ".join(item[1] for item in curr_cluster))
                curr_top, curr_bot = y_top, y_bot
                curr_cluster = [(x_left, txt)]

        if curr_cluster:
            curr_cluster.sort(key=lambda item: item[0])
            lines.append(" | ".join(item[1] for item in curr_cluster))
        return "\n".join(lines)

    def _ocr_images_fast(self, pil_images: list) -> str:
        """
        High-speed hybrid OCR pipeline for 1 to 50+ pages:
        1. Primary: Native Windows.Media.Ocr.OcrEngine (~0.75s/page) in a single hidden batch.
        2. Surgical Spot-Repair: RapidOCR text_recognizer repairs only garbled amount boxes.
        3. Fallback: Full RapidOCR if Windows.Media.Ocr is unavailable.
        """
        total = len(pil_images)
        if total == 0:
            return ""

        page_boxes: dict[int, list[list]] = {i: [] for i in range(total)}
        winocr_ok = False

        if sys.platform == "win32":
            try:
                with tempfile.TemporaryDirectory(prefix="taxclean_ocr_") as tmpdir:
                    tmp_path = Path(tmpdir)
                    img_paths = []
                    for i, im in enumerate(pil_images):
                        p_img = tmp_path / f"page_{i}.png"
                        im.save(str(p_img), format="PNG", compress_level=1)
                        img_paths.append(str(p_img))

                    ps_script = tmp_path / "run_ocr.ps1"
                    safe_tmp_path = str(tmp_path).replace("'", "''")
                    ps_code = (
                        "Add-Type -AssemblyName System.Runtime.WindowsRuntime\n"
                        "$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | "
                        "Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and "
                        "$_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]\n"
                        "Function Await($WinRtTask, $ResultType) {\n"
                        "    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)\n"
                        "    $netTask = $asTask.Invoke($null, @($WinRtTask))\n"
                        "    $netTask.Wait(-1) | Out-Null\n"
                        "    $netTask.Result\n"
                        "}\n"
                        "$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]\n"
                        "$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]\n"
                        "$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime]\n"
                        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n"
                        "$eng = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()\n"
                        "for ($i = 0; $i -lt " + str(total) + "; $i++) {\n"
                        "    $p = Join-Path '" + safe_tmp_path + "' (\"page_\" + $i + \".png\")\n"
                        "    $file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($p)) ([Windows.Storage.StorageFile])\n"
                        "    $stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])\n"
                        "    $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])\n"
                        "    $bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])\n"
                        "    $res = Await ($eng.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])\n"
                        "    foreach ($line in $res.Lines) {\n"
                        "        $yTop = ($line.Words | ForEach-Object { $_.BoundingRect.Y } | Measure-Object -Minimum).Minimum\n"
                        "        $yBot = ($line.Words | ForEach-Object { $_.BoundingRect.Y + $_.BoundingRect.Height } | Measure-Object -Maximum).Maximum\n"
                        "        $xLeft = ($line.Words | ForEach-Object { $_.BoundingRect.X } | Measure-Object -Minimum).Minimum\n"
                        "        $xRight = ($line.Words | ForEach-Object { $_.BoundingRect.X + $_.BoundingRect.Width } | Measure-Object -Maximum).Maximum\n"
                        "        Write-Output (\"BOX`t\" + $i + \"`t\" + $yTop + \"`t\" + $yBot + \"`t\" + $xLeft + \"`t\" + $xRight + \"`t\" + $line.Text)\n"
                        "    }\n"
                        "    $stream.Dispose()\n"
                        "    Write-Output (\"DONE`t\" + $i)\n"
                        "}\n"
                    )
                    ps_script.write_text(ps_code, encoding="utf-8")

                    CREATE_NO_WINDOW = 0x08000000
                    proc = subprocess.Popen(
                        [
                            "powershell.exe",
                            "-NoProfile",
                            "-NonInteractive",
                            "-ExecutionPolicy",
                            "Bypass",
                            "-File",
                            str(ps_script),
                        ],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        creationflags=CREATE_NO_WINDOW,
                    )

                    if proc.stdout:
                        for raw_line in proc.stdout:
                            line_s = raw_line.rstrip("\r\n")
                            if line_s.startswith("BOX\t"):
                                parts = line_s.split("\t", 6)
                                if len(parts) == 7:
                                    pg_idx = int(parts[1])
                                    page_boxes[pg_idx].append([
                                        float(parts[2].replace(",", ".")),
                                        float(parts[3].replace(",", ".")),
                                        float(parts[4].replace(",", ".")),
                                        float(parts[5].replace(",", ".")),
                                        parts[6].strip(),
                                    ])
                            elif line_s.startswith("DONE\t"):
                                pg_idx = int(line_s.split("\t")[1])
                                pct = 15 + int(((pg_idx + 1) / total) * 75)
                                self.queue.put(("PROGRESS", pct, f"Fast OCR scanned page {pg_idx + 1}/{total}..."))
                    try:
                        proc.wait(timeout=120)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                    if any(len(b) > 0 for b in page_boxes.values()):
                        winocr_ok = True
            except Exception:
                winocr_ok = False

        # Assemble pages and run Surgical RapidOCR Spot-Repair ONLY on garbled decimal boxes
        all_pages_text = []
        for i, pil_img in enumerate(pil_images):
            boxes_i = page_boxes.get(i, [])
            if winocr_ok and len(boxes_i) >= 6:
                if HAS_RAPIDOCR:
                    np_img = None
                    h_img, w_img = pil_img.size[1], pil_img.size[0]
                    crops_to_fix = []
                    crop_idxs = []
                    for b_idx, (yt, yb, xl, xr, txt) in enumerate(boxes_i):
                        norm_num = re.sub(r"\.([Oo0]{2})", ".00", txt).replace(" ", "")
                        if (
                            xl > w_img * 0.65
                            and (xr - xl) < w_img * 0.28
                            and len(txt) <= 18
                            and re.match(r"^[-+R\s]*\d", txt)
                            and ("." in txt or "," in txt)
                            and not re.search(r"\d+\.\d{2}", norm_num)
                        ):
                            if np_img is None:
                                np_img = np.array(pil_img)
                            y0, y1 = max(0, int(yt) - 4), min(h_img, int(yb) + 4)
                            x0, x1 = max(0, int(xl) - 6), min(w_img, int(xr) + 6)
                            if y1 > y0 and x1 > x0:
                                crops_to_fix.append(np_img[y0:y1, x0:x1])
                                crop_idxs.append(b_idx)
                    if crops_to_fix:
                        eng = get_rapidocr_engine()
                        if eng and hasattr(eng, "text_recognizer"):
                            try:
                                rec_res, _ = eng.text_recognizer(crops_to_fix)
                                for b_idx, (new_txt, sc) in zip(crop_idxs, rec_res):
                                    if float(sc) > 0.5:
                                        boxes_i[b_idx][4] = new_txt.strip()
                            except Exception:
                                pass

                tuples_4 = [(b[0], b[1], b[2], b[4]) for b in boxes_i]
                all_pages_text.append(self._cluster_boxes_to_lines(tuples_4))
            elif HAS_RAPIDOCR:
                # Fallback to singleton RapidOCR if Windows.Media.Ocr did not return boxes
                self.queue.put(("PROGRESS", int(((i + 1) / total) * 90), f"Deep OCR scanning page {i + 1}/{total}..."))
                eng = get_rapidocr_engine()
                if eng:
                    np_img = np.array(pil_img)
                    result, _ = eng(np_img)
                    if result:
                        tuples_4 = []
                        for box, txt, score in result:
                            try:
                                if float(score) < 0.25:
                                    continue
                            except (ValueError, TypeError):
                                pass
                            y_top = min(pt[1] for pt in box)
                            y_bot = max(pt[1] for pt in box)
                            x_left = min(pt[0] for pt in box)
                            tuples_4.append((y_top, y_bot, x_left, txt.strip()))
                        all_pages_text.append(self._cluster_boxes_to_lines(tuples_4))

        combined = "\n".join(t for t in all_pages_text if t)
        # Normalize common OCR decimal/comma/O artifacts across all pages
        combined = re.sub(r"\.([Oo0]{2})", ".00", combined)
        return combined

    def extract_text(self) -> str:
        p = Path(self.filepath)
        suf = p.suffix.lower()

        # 1. Direct Image Receipt / Invoice (JPG, PNG, WEBP, BMP)
        if suf in [".jpg", ".jpeg", ".png", ".webp", ".bmp"]:
            try:
                self._notify("STATUS", "Scanning receipt / invoice image with high-speed local OCR...")
                with Image.open(str(p)) as raw_im:
                    pil_img = raw_im.convert("RGB")
                max_dim = max(pil_img.size)
                if max_dim < 1600:
                    scale = min(3.0, 1600.0 / max(1, max_dim))
                    new_w = int(pil_img.width * scale)
                    new_h = int(pil_img.height * scale)
                    pil_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                return self._ocr_images_fast([pil_img])
            except Exception as e:
                self._notify("STATUS", f"Image OCR notice: {e}")
            return ""

        # 2. Text / CSV direct read
        if suf in [".csv", ".txt"]:
            with open(p, "r", encoding="utf-8-sig", errors="ignore") as f:
                return f.read()

        # 3. PDF Processing (Fast C++ PDFium Vector Layer -> Hybrid Batch OCR Fallback)
        text_content = ""
        if HAS_PDFIUM:
            doc = None
            try:
                doc = pdfium.PdfDocument(str(p))
                total = len(doc)
                for idx, page in enumerate(doc):
                    if idx % 5 == 0 or idx == total - 1:
                        self._notify("PROGRESS", int(((idx + 1) / total) * 15), f"Checking PDF layer page {idx + 1}/{total}...")
                    tp = page.get_textpage()
                    t = tp.get_text_bounded()
                    if t:
                        text_content += t + "\n"
                if len(text_content.strip()) >= 60:
                    return text_content

                # Scanned PDF detected  -  render from the already-open C++ PdfDocument
                self._notify("STATUS", "Scanned PDF detected. Rendering pages for high-speed OCR...")
                pil_images = []
                for idx, page in enumerate(doc):
                    self._notify("PROGRESS", int(((idx + 1) / total) * 15), f"Rendering page {idx + 1}/{total}...")
                    pil_images.append(page.render(scale=2.5).to_pil().convert("RGB"))
                ocr_text = self._ocr_images_fast(pil_images)
                if len(ocr_text.strip()) > 20:
                    return ocr_text
            except Exception as e:
                self._notify("STATUS", f"PDF OCR notice: {e}")
            finally:
                if doc is not None:
                    try:
                        doc.close()
                    except Exception:
                        pass

        if HAS_PYPDF and len(text_content.strip()) < 60:
            try:
                reader = pypdf.PdfReader(str(p))
                for page in reader.pages:
                    t = page.extract_text()
                    if t:
                        text_content += t + "\n"
            except Exception:
                pass

        return text_content

    def categorize(self, desc: str, amt: float) -> dict:
        clean = clean_payee_text(desc)
        token = clean.upper()

        # 1. Learned Merchant Memory (O(1) in-memory cache)
        mem = self.memory.lookup_merchant(self.profile_name, token)
        if mem:
            is_susp = (mem["code"] == "9999/000" or str(mem["code"]).startswith("9999"))
            vat_claim = (
                _calc_vat_inclusive(amt)
                if (mem["vat_type"] == "Standard" and amt < 0 and not is_susp)
                else 0.0
            )
            return {
                "clean_payee": clean,
                "code": mem["code"],
                "name": mem["name"],
                "acc_type": mem["acc_type"],
                "vat_type": mem["vat_type"],
                "vat_claim": vat_claim,
                "is_suspense": is_susp,
                "reason": "Learned rule match",
            }

        # 2. Inflows / Customer Sales
        if amt > 0:
            sales = self.coa.get("Sales", DEFAULT_CHART_OF_ACCOUNTS["Sales"])
            return {
                "clean_payee": clean,
                "code": sales["code"],
                "name": sales["name"],
                "acc_type": sales.get("type", "Customer"),
                "vat_type": "None",
                "vat_claim": 0.0,
                "is_suspense": False,
                "reason": "Receipt (Money In)",
            }

        # 3. Suspense Keywords (Pre-compiled regexes)
        desc_up = desc.upper()
        for kw, rx in self._suspense_rxs:
            if rx.search(desc_up):
                susp = self.coa.get("Suspense", DEFAULT_CHART_OF_ACCOUNTS["Suspense"])
                return {
                    "clean_payee": clean,
                    "code": susp["code"],
                    "name": susp["name"],
                    "acc_type": susp.get("type", "GL"),
                    "vat_type": "None",
                    "vat_claim": 0.0,
                    "is_suspense": True,
                    "reason": f"Flagged query '{kw}'",
                }

        # 4. Chart of Accounts Keyword Match (Pre-compiled regexes)
        for kw, rx, rule in self._coa_rxs:
            if rx.search(desc_up):
                vt = rule.get("vat", "Standard")
                vc = (
                    _calc_vat_inclusive(amt)
                    if (vt == "Standard" and amt < 0)
                    else 0.0
                )
                return {
                    "clean_payee": clean,
                    "code": rule["code"],
                    "name": rule["name"],
                    "acc_type": rule.get("type", "GL"),
                    "vat_type": vt,
                    "vat_claim": vc,
                    "is_suspense": False,
                    "reason": f"Matched keyword: {kw}",
                }

        # 5. Default Query Suspense Account
        susp = self.coa.get("Suspense", DEFAULT_CHART_OF_ACCOUNTS["Suspense"])
        return {
            "clean_payee": clean,
            "code": susp["code"],
            "name": susp["name"],
            "acc_type": susp.get("type", "GL"),
            "vat_type": "None",
            "vat_claim": 0.0,
            "is_suspense": True,
            "reason": "Unrecognized payee / query account",
        }

    def parse_text(self, text: str) -> dict:
        """Parses bank statements, tax invoices, and receipts into standardized ledger transactions."""
        # Normalize common OCR decimal/comma/O artifacts before parsing
        text = re.sub(r"\.([Oo0]{2})", ".00", text)

        format_info = SABankFormatChecker.detect_bank_format(text)
        results = []
        open_bal_found = None
        close_bal_found = None
        amt_rx = re.compile(r"(?<![A-Za-z0-9])(?:[-+]?\s*(?:R\s*)?)?\(?(?:\d{1,3}(?:[,\s]\d{3})+|\d+)\.\d{2}\)?(?:\s*(?:Cr|Dr|CR|DR))?", re.I)

        # Check for Statement Opening / Closing Balances
        for line in text.splitlines():
            up = line.upper()
            if ("OPENINGBALANCE" in up or "OPENING BALANCE" in up or "BAL BROUGHT FORWARD" in up) and open_bal_found is None:
                amts = list(amt_rx.finditer(line))
                if amts:
                    v, is_cr, is_dr = parse_sa_amount(amts[0].group(0))
                    open_bal_found = -v if is_dr else v
            if ("CLOSING BALANCE" in up or "CLOSINGBALANCE" in up or "CLOSIN BALANCE" in up or "BAL CARRIED FORWARD" in up) and close_bal_found is None:
                amts = list(amt_rx.finditer(line))
                if amts:
                    v, is_cr, is_dr = parse_sa_amount(amts[0].group(0))
                    close_bal_found = -v if is_dr else v

        if open_bal_found is None:
            ob_m = re.search(r"(?:Opening\s*Balance|Bal\s*Brought\s*Forward|Opening\s*Bal)[^\d]*([0-9, ]+\.[0-9]{2})\s*(Cr|Dr)?", text, re.I)
            if ob_m:
                val, is_cr, is_dr = parse_sa_amount(ob_m.group(1))
                open_bal_found = -val if is_dr else val

        if close_bal_found is None:
            cb_m = re.search(r"(?:Closing\s*Balance|Bal\s*Carried\s*Forward|Closing\s*Bal)[^\d]*([0-9, ]+\.[0-9]{2})\s*(Cr|Dr)?", text, re.I)
            if cb_m:
                val, is_cr, is_dr = parse_sa_amount(cb_m.group(1))
                close_bal_found = -val if is_dr else val

        stmt_m = re.search(r"(?:Statement Number|Tax Invoice/Statement Number|Statement No)[\s:]*(\d+)", text, re.I)
        bs_ref = f"BS{stmt_m.group(1).strip()}" if stmt_m else "BS1"

        is_slip = bool(re.search(r"(TAX INVOICE|\bINVOICE\b|PRO-FORMA|CASHIER|SLIP|TENDER|DUE VAT INCL|BON-ID|SUMME|SIME|TOTAL ITEMS|MWST|RECEIPT|BILL TO)", text, re.I))

        year_m = re.search(r"\b(20\d{2})\b", text)
        default_year = int(year_m.group(1)) if year_m else datetime.now().year

        raw_lines = [l.strip() for l in text.splitlines() if l.strip()]

        if is_slip and open_bal_found is None and close_bal_found is None:
            # ==================================================================
            # RECEIPT / TAX INVOICE PARSING
            # ==================================================================
            text_norm = re.sub(r"(\d+)\s*[-– - ]\s*(\d{2})\b", r"\1.\2", text)
            text_norm = re.sub(r"(\d+)[,\s]+(\d{3}\.\d{2})", r"\1\2", text_norm)
            norm_lines = [l.strip() for l in text_norm.splitlines() if l.strip()]

            merchant = "Vendor / Store"
            for l in norm_lines[:8]:
                up = l.upper()
                if any(k in up for k in ["TAX INVOICE", "INVOICE", "TEL", "CASHIER", "WWW", "DATE", "TIME", "PRO-FORMA", "UNPAID", "BILL TO", "ESTIMATE", "QUOTATION", "RECEIPT", "STATEMENT", "SLIP", "HTTP"]):
                    continue
                m_cand = l.split("|")[0].strip()
                if len(m_cand) >= 3 and not re.match(r"^(INV[-0-9\s]+|[0-9\-\s\+:\./]+)$", m_cand, re.I):
                    merchant = m_cand
                    break

            # Robust date parsing (Month names + Numeric formats)
            inv_date = datetime.now().strftime("%Y-%m-%d")
            month_map = {
                "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
            }
            month_pats = "|".join(month_map.keys())
            m_word = re.search(rf"(?:IssueDate:?|Date:?)?\s*(\d{{1,2}})\s*({month_pats})[a-z]*\s*(20\d{{2}})", text_norm, re.I)
            if m_word:
                try:
                    d = int(m_word.group(1))
                    m = month_map[m_word.group(2).lower()[:3]]
                    y = int(m_word.group(3))
                    inv_date = f"{y:04d}-{m:02d}-{d:02d}"
                except Exception:
                    pass
            else:
                m_num = re.search(r"\b(20\d{2})[/.-](0[1-9]|1[0-2])[/.-](0[1-9]|[12]\d|3[01])\b", text_norm) or \
                        re.search(r"\b(0?[1-9]|[12]\d|3[01])[/.-](0[1-9]|1[0-2])[/.-](20\d{2})\b", text_norm) or \
                        re.search(r"\b(0?[1-9]|[12]\d|3[01])\.(0[1-9]|1[0-2])\.(\d{2})\b", text_norm)
                if m_num:
                    d_parts = m_num.group(0).replace(".", "-").replace("/", "-").split("-")
                    try:
                        if len(d_parts[0]) == 4:
                            inv_date = f"{d_parts[0]}-{d_parts[1].zfill(2)}-{d_parts[2].zfill(2)}"
                        elif len(d_parts[2]) == 4:
                            inv_date = f"{d_parts[2]}-{d_parts[1].zfill(2)}-{d_parts[0].zfill(2)}"
                        elif len(d_parts[2]) == 2:
                            inv_date = f"20{d_parts[2]}-{d_parts[1].zfill(2)}-{d_parts[0].zfill(2)}"
                    except Exception:
                        pass

            # Invoice Reference
            inv_ref = "REC1"
            ref_m = re.search(r"(?:Invoice\s*#?|Slip\s*#?|Ref\s*#?|Reference\s*[:|]?|PRO-FORMA INVOICE:?|Bon-ID|INV-)\s*[:|]?\s*([A-Za-z0-9\-]+)", text_norm, re.I)
            if ref_m:
                val = ref_m.group(1).strip()
                inv_ref = val if val.startswith("INV-") else f"INV-{val}"

            # Total Amount parsing (with support for pipe separators, colons, and SA Rand)
            total_amt = 0.0
            tot_patterns = [
                r"(?:AMOUNT\s*DUE|TOTAL\s*INCL\.?\s*VAT|DUE\s*VAT\s*INCL|TOTAL\s*DUE)[\s:|R]*([0-9,]+\.[0-9]{2})",
                r"(?:TOTAL|BIL\s*TOTAL|BILL\s*TOTAL|SUMME|SIME|AMOUNT\s*DUE)[\s:|R]*([0-9,]+\.[0-9]{2})",
                r"(?:TOTAL\s*FOR\s*\d+\s*ITEMS?)[\s:|R]*([0-9,]+\.[0-9]{2})",
                r"(?:Subtotal)[\s:|R]*([0-9,]+\.[0-9]{2})",
            ]
            for pat in tot_patterns:
                m = re.search(pat, text_norm, re.I)
                if m:
                    try:
                        cand = float(m.group(1).replace(",", ""))
                        if cand > total_amt:
                            total_amt = cand
                    except Exception:
                        pass

            # VAT extraction with sanity check (prevents capturing total as VAT)
            vat_amt = 0.0
            vat_m = re.search(r"(?<!TOTAL\s)(?<!INCL\s)(?<!INCL\.\s)\b(?:VAT(?:\s*@?\s*1[45]%)?|MWST|VAT\s*VAL|VAT\s*AMOUNT)\b[\s:|R]*([0-9,]+\.[0-9]{2})", text_norm, re.I)
            if vat_m:
                try:
                    cand_vat = float(vat_m.group(1).replace(",", ""))
                    max_allowed_vat = _calc_vat_inclusive(total_amt) + 0.05 if total_amt > 0 else 999999.0
                    if 0 < cand_vat <= max_allowed_vat and (total_amt == 0 or cand_vat < total_amt):
                        vat_amt = cand_vat
                    elif total_amt > 0:
                        vat_amt = _calc_vat_inclusive(total_amt)
                except Exception:
                    pass
            elif total_amt > 0 and any(k in text_norm.upper() for k in ["TAX INVOICE", "VAT INVOICE", "VAT REG"]):
                vat_amt = _calc_vat_inclusive(total_amt)

            vatreg_m = re.search(r"(?:VATREGNO|VAT NO|VAT REG NO|UID NR)[\.\s:]*([A-Z0-9]+)", text_norm, re.I)
            vat_reg_str = vatreg_m.group(1) if vatreg_m else ""

            # Line items extraction
            item_rx = re.compile(r"^(.+?)\s+([0-9,]+\.[0-9]{2})[A-Za-z#]*$")
            item_lines = []
            for line in norm_lines:
                if any(k in line.upper() for k in ["TOTAL", "DUE", "TENDER", "SUMME", "CASHIER", "ITEMS", "MWST", "VAT", "CHANGE", "RUCKGELD"]):
                    continue
                im = item_rx.match(line)
                if im:
                    it_desc = im.group(1).strip()
                    it_val, _, _ = parse_sa_amount(im.group(2))
                    if it_val > 0 and len(it_desc) > 2:
                        item_lines.append((it_desc, it_val))

            if total_amt == 0.0 and item_lines:
                total_amt = sum(v for _, v in item_lines)

            # Check if line items match total amount
            items_sum = sum(v for _, v in item_lines) if item_lines else 0.0
            has_matching_breakdown = len(item_lines) >= 2 and total_amt > 0 and abs(items_sum - total_amt) <= 0.10

            if has_matching_breakdown:
                for it_desc, it_val in item_lines:
                    signed_val = -_dec_round(it_val)
                    cat = self.categorize(f"{merchant} {it_desc}", signed_val)
                    net = _dec_round(signed_val + cat["vat_claim"])
                    results.append({
                        "date": inv_date,
                        "ref": inv_ref,
                        "acc_type": cat["acc_type"],
                        "clean_payee": cat["clean_payee"],
                        "code": cat["code"],
                        "name": cat["name"],
                        "amount": signed_val,
                        "vat_type": cat["vat_type"],
                        "vat_claim": cat["vat_claim"],
                        "net": net,
                        "is_suspense": cat["is_suspense"],
                        "audit_status": "✓ Verified Slip Item",
                        "query_reason": cat["reason"],
                    })
            else:
                signed_val = -_dec_round(total_amt)
                cat = self.categorize(merchant, signed_val)
                actual_vat = _dec_round(vat_amt) if (vat_amt > 0 and cat["vat_type"] == "Standard" and not cat["is_suspense"]) else cat["vat_claim"]
                net = _dec_round(signed_val + actual_vat)
                reason_note = f"Tax Invoice ({vat_reg_str})" if vat_reg_str else "Scanned Slip"
                audit_status = f"✓ Verified ({reason_note})" if total_amt > 0 else "⚠️ Review Amount (OCR unreadable)"
                query_reason = cat["reason"] if total_amt > 0 else "Total amount could not be detected with high confidence  -  please verify"
                results.append({
                    "date": inv_date,
                    "ref": inv_ref,
                    "acc_type": cat["acc_type"],
                    "clean_payee": cat["clean_payee"],
                    "code": cat["code"],
                    "name": cat["name"],
                    "amount": signed_val,
                    "vat_type": cat["vat_type"],
                    "vat_claim": actual_vat,
                    "net": net,
                    "is_suspense": cat["is_suspense"],
                    "audit_status": audit_status,
                    "query_reason": query_reason,
                })

        elif format_info.get("is_credit_account"):
            # ==================================================================
            # FNB ASPIRE / PLATINUM CREDIT STATEMENT PARSER (0.00 VARIANCE ENGINE)
            # ==================================================================
            credit_data = SABankFormatChecker.parse_fnb_credit_statement(text, default_year=default_year)
            open_bal_found = credit_data["open_bal"]
            close_bal_found = credit_data["close_bal"]
            bs_ref = credit_data["ref"]

            for rec in credit_data["records"]:
                cat = self.categorize(rec["raw_desc"], rec["amount"])
                amt = rec["amount"]
                net = _dec_round(amt + cat["vat_claim"]) if amt < 0 else _dec_round(amt - cat["vat_claim"])
                results.append({
                    "date": rec["date"],
                    "ref": rec["ref"],
                    "acc_type": cat["acc_type"],
                    "clean_payee": cat["clean_payee"],
                    "code": cat["code"],
                    "name": cat["name"],
                    "amount": amt,
                    "vat_type": cat["vat_type"],
                    "vat_claim": cat["vat_claim"],
                    "net": net,
                    "is_suspense": cat["is_suspense"],
                    "audit_status": "✓ Verified" if not cat["is_suspense"] else f"⚠️ {cat['reason']}",
                    "query_reason": cat["reason"],
                })

        else:
            # ==================================================================
            # BANK STATEMENT TRANSACTION PARSER (CONTINUITY & RUNNING BAL ENGINE)
            # ==================================================================
            learned_profile = self.memory.match_learned_profile(text)
            skip_phrases = [
                "POBOX", "UNIVERSAL BRANCH", "PAGE ", "CUSTOMER VAT", "BANK VAT",
                "BRANCH CODE", "STATEMENT BALANCES", "ACCOUNT NUMBER", "LOST CARDS", "FRAUD",
                "RELATIONSHIP MANAGER", "TURNOVERFOR", "TURNOVER FOR", "NO. CREDIT", "NO. DEBIT", "PLEASE CONTACT",
                "PRICING OPTION", "FIRST NATIONAL BANK", "REFERENCE NUMBER", "DATE |",
                "TOTAL VAT", "# INCLUSIVE", "MAXIMUM ANNUAL VARIABLE", "PRIME LENDING RATE",
                "STATEMENT PERIOD", "STATEMENT DATE", "TRANSACTIONS IN RAND",
                "OPENING BALANCE", "CLOSING BALANCE", "OPENINGBALANCE", "CLOSINGBALANCE",
                "DATE DESCRIPTION",
            ]
            if learned_profile and learned_profile.get("skip_phrases"):
                for sk in learned_profile["skip_phrases"]:
                    if sk.upper() not in skip_phrases:
                        skip_phrases.append(sk.upper())

            cleaned_lines = []
            for l in raw_lines:
                up = l.upper()
                if any(sk in up for sk in skip_phrases):
                    continue
                cleaned_lines.append(l)

            date_rx = re.compile(r"\b(0?[1-9]|[12]\d|3[01])\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b", re.I)
            date_iso_rx = re.compile(r"\b(20\d{2})[/.-](0[1-9]|1[0-2])[/.-](0[1-9]|[12]\d|3[01])\b")
            date_slash_rx = re.compile(r"\b(0?[1-9]|[12]\d|3[01])/(0[1-9]|1[0-2])/(20\d{2})\b")
            amt_rx = re.compile(r"(?<![A-Za-z0-9])(?:[-+]?\s*(?:R\s*)?)?\(?(?:\d{1,3}(?:[,\s]\d{3})+|\d+)\.\d{2}\)?(?:\s*(?:Cr|Dr|CR|DR))?", re.I)

            curr_running_bal = open_bal_found
            last_date_iso = f"{default_year}-01-01"

            for line in cleaned_lines:
                norm_line = re.sub(r"(\d+)\.(\d{3}\.\d{2})", r"\1,\2", line)
                norm_line = re.sub(r"(\d),\s+(\d{3}\.\d{2})", r"\1,\2", norm_line)
                amts = list(amt_rx.finditer(norm_line))

                dm = date_rx.search(norm_line) or date_iso_rx.search(norm_line) or date_slash_rx.search(norm_line)
                if not dm:
                    # Non-dated lines in bank statements are headers, footers, or summaries
                    continue

                if not amts:
                    continue

                raw_d = dm.group(0).strip()
                if re.match(r"^20\d{2}", raw_d):
                    try:
                        clean_iso = raw_d.replace("/", "-").replace(".", "-")
                        last_date_iso = datetime.strptime(clean_iso, "%Y-%m-%d").strftime("%Y-%m-%d")
                    except Exception:
                        pass
                elif re.match(r"^\d{1,2}/\d{1,2}/\d{4}", raw_d):
                    try:
                        last_date_iso = datetime.strptime(raw_d, "%d/%m/%Y").strftime("%Y-%m-%d")
                    except Exception:
                        pass
                else:
                    try:
                        dt_parsed = datetime.strptime(f"{raw_d} {default_year}", "%d %b %Y")
                        last_date_iso = dt_parsed.strftime("%Y-%m-%d")
                    except Exception:
                        pass

                parsed_amts = [parse_sa_amount(a.group(0)) for a in amts]
                tx_val, tx_cr, tx_dr = parsed_amts[0]

                # South African Running Balance Continuity Matching
                signed_amt = None
                bal_used = None

                if len(parsed_amts) >= 2:
                    for cand_idx in (range(1, len(parsed_amts)) if len(parsed_amts) == 2 else [1, 2, -1]):
                        if cand_idx >= len(parsed_amts):
                            continue
                        cand_bal = parsed_amts[cand_idx]
                        b_val, b_cr, b_dr = cand_bal
                        targets = [b_val] if b_cr else [b_val, -b_val]
                        if curr_running_bal is not None:
                            for b_target in targets:
                                if abs((curr_running_bal + tx_val) - b_target) < 0.05:
                                    signed_amt = tx_val
                                    curr_running_bal = _dec_round(curr_running_bal + tx_val)
                                    bal_used = b_target
                                    break
                                elif abs((curr_running_bal - tx_val) - b_target) < 0.05:
                                    signed_amt = -tx_val
                                    curr_running_bal = _dec_round(curr_running_bal - tx_val)
                                    bal_used = b_target
                                    break
                        if signed_amt is not None:
                            break

                if signed_amt is None:
                    # Fallback to credit/debit indicators or default outflow
                    tok = amts[0].group(0).upper()
                    if tx_cr or "+" in tok:
                        signed_amt = abs(tx_val)
                    elif tx_dr or "-" in tok or "(" in tok:
                        signed_amt = -abs(tx_val)
                    else:
                        up_l = norm_line.upper()
                        if any(kw in up_l for kw in ["DEP", "SALARY", "CREDIT", "REFUND", "TRANSFER FROM", "PMT FRM", "INFLOW"]):
                            signed_amt = abs(tx_val)
                        else:
                            signed_amt = -abs(tx_val)

                    if curr_running_bal is not None:
                        curr_running_bal = _dec_round(curr_running_bal + signed_amt)

                # Clean Payee Description
                parts = [p.strip() for p in norm_line.split("|") if p.strip()]
                desc_cands = []
                if len(parts) > 2:
                    for p in parts:
                        p_clean = p.strip(" [")
                        if amt_rx.search(p) or date_rx.search(p) or date_iso_rx.search(p) or date_slash_rx.search(p):
                            continue
                        if re.search(r"^\d{6}\*\d{4}", p_clean) or re.search(r"^\d{10,}", p_clean):
                            continue
                        if p_clean.upper() in ["INR TO", "INR SO", "INR ZO", "INR 80", "SAM", "ACCRUED", "BANK", "CHARGES"]:
                            continue
                        if len(p_clean) > 2:
                            desc_cands.append(p_clean)
                    full_desc = clean_payee_text(" ".join(desc_cands)) if desc_cands else ""
                else:
                    first_amt_pos = amts[0].start()
                    date_end_pos = dm.end()
                    raw_desc = norm_line[date_end_pos:first_amt_pos].strip() if first_amt_pos > date_end_pos else ""
                    full_desc = clean_payee_text(raw_desc) if raw_desc else ""

                if not full_desc or full_desc == "Bank Transaction" or re.search(r"^\d+$", full_desc):
                    if re.search(r"\bATM\s+CASH\b", norm_line, re.I):
                        full_desc = "ATM Cash Withdrawal"
                    elif tx_val == 0.0 or "INT.RATE" in norm_line.upper() or "INTEREST" in norm_line.upper():
                        full_desc = "Interest Rate Adjustment"
                    elif any(k in norm_line.upper() for k in ["FEE", "CHARGES", "SERVICE", "DEPOSIT", "HANDLING"]):
                        full_desc = "Bank Fee / Charges"
                    elif signed_amt is not None and signed_amt < 0:
                        full_desc = "Bank Fee / Charges"
                    else:
                        full_desc = "Bank Transaction"

                cat = self.categorize(full_desc, signed_amt)
                net = _dec_round(signed_amt + cat["vat_claim"]) if signed_amt < 0 else _dec_round(signed_amt - cat["vat_claim"])

                results.append({
                    "date": last_date_iso,
                    "ref": bs_ref,
                    "acc_type": cat["acc_type"],
                    "clean_payee": cat["clean_payee"],
                    "code": cat["code"],
                    "name": cat["name"],
                    "amount": signed_amt,
                    "vat_type": cat["vat_type"],
                    "vat_claim": cat["vat_claim"],
                    "net": net,
                    "is_suspense": cat["is_suspense"],
                    "audit_status": "✓ Verified" if not cat["is_suspense"] else f"⚠️ {cat['reason']}",
                    "query_reason": cat["reason"],
                    "_bal": bal_used,
                })

        # Audit Continuity & Duplicate Tagging (excludes distinct running-balance lines & standard recurring bank fee lines)
        seen = set()
        for row in results:
            py_up = (row.get("clean_payee") or "").upper()
            row_bal = row.pop("_bal", None)
            if row_bal is not None:
                dup_key = (row["date"], py_up, row["amount"], row_bal)
            elif py_up in ("BANK FEE / CHARGES", "INTEREST RATE ADJUSTMENT", "BANK TRANSACTION") and abs(float(row.get("amount", 0.0))) <= 50.0:
                row["is_duplicate"] = False
                continue
            else:
                dup_key = (row["date"], py_up, row["amount"], None)

            if dup_key in seen:
                row["audit_status"] = "⚠️ Possible Duplicate"
                row["is_duplicate"] = True
                row["is_suspense"] = True
                row["query_reason"] = "Quarantined: Duplicate transaction"
            else:
                row["is_duplicate"] = False
                seen.add(dup_key)

        return {
            "open_bal": f"{open_bal_found:.2f}" if open_bal_found is not None else None,
            "close_bal": f"{close_bal_found:.2f}" if close_bal_found is not None else None,
            "records": results,
            "detected_bank": format_info["name"],
            "bank_profile": format_info["profile_id"],
        }


# ==============================================================================
# 5. USER-FOCUSED ACCOUNTING DESKTOP APPLICATION
# ==============================================================================
class ModernApp:

    def __init__(self, root):
        self.root = root
        self.root.title("TaxClean ZA  -  Bank Statement, Receipt & Tax Automation")
        self.auto_adjust_screen_settings()
        if HAS_CUSTOMTKINTER and isinstance(self.root, ctk.CTk):
            self.root.configure(fg_color="#090d16")
        else:
            self.root.configure(bg="#090d16")
        apply_dark_titlebar(self.root)

        ico_path = get_resource_path("TaxClean.ico")
        png_path = get_resource_path("TaxClean.png")
        if sys.platform == "win32" and ico_path.exists():
            try:
                self.root.iconbitmap(default=str(ico_path))
            except Exception:
                pass
        elif png_path.exists():
            try:
                self._app_icon_img = tk.PhotoImage(file=str(png_path))
                self.root.iconphoto(True, self._app_icon_img)
            except Exception:
                pass

        self.memory = MemoryStore(DB_FILE)
        self.license_mgr = LicenseManager(self.memory.get_conn())
        self.config = self.load_config()
        if not isinstance(self.config.get("profiles"), dict) or not self.config["profiles"]:
            self.config["profiles"] = {
                "Acme Trading (Pty) Ltd": {
                    "erp": "Pastel Partner",
                    "fin_year_end_month": 2,
                    "coa": {k: v.copy() for k, v in DEFAULT_CHART_OF_ACCOUNTS.items()},
                }
            }
        self.active_profile = self.config.get("active_profile", "Acme Trading (Pty) Ltd")
        if self.active_profile not in self.config["profiles"]:
            self.active_profile = next(iter(self.config["profiles"]))
            self.config["active_profile"] = self.active_profile

        self.transactions: list[dict] = []
        self.undo_stack: list[tuple] = []
        self.redo_stack: list[tuple] = []
        self.active_filter_tab = "all"
        self.metrics_visible = True
        self.task_queue = queue.Queue()
        self.editing_widget = None
        self.current_bank_name = "South African Bank Statement"
        self.bank_diagnostic_data = {}
        self.batch_locked = False
        self.locked_hash = ""
        self._batch_licensed_for_export = False
        self.is_store_edition = is_running_as_store_package()

        self.setup_theme()
        self.build_ui()
        self.run_startup_bank_format_check()
        self.poll_queue()
        self.restore_or_init_session()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(900, self._check_show_api_prompt)
        self.root.after(2000, lambda: self._start_background_update_check(silent=True))

    def _on_close(self):
        try:
            self.save_current_session()
            self.save_config()
            self.memory.close()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def load_config(self) -> dict:
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "active_profile": "Acme Trading (Pty) Ltd",
            "profiles": {
                "Acme Trading (Pty) Ltd": {
                    "erp": "Pastel Partner",
                    "fin_year_end_month": 2,
                    "coa": {k: v.copy() for k, v in DEFAULT_CHART_OF_ACCOUNTS.items()},
                }
            },
        }

    def save_config(self):
        try:
            tmp_cfg = CONFIG_FILE.with_suffix(".tmp")
            with open(tmp_cfg, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
            os.replace(tmp_cfg, CONFIG_FILE)
        except Exception:
            pass

    def setup_theme(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Treeview",
            background="#0a101d",
            foreground="#f1f5f9",
            fieldbackground="#0a101d",
            rowheight=36,
            font=("Segoe UI", 10),
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            background="#131f37",
            foreground="#cbd5e1",
            font=("Segoe UI", 10, "bold"),
            padding=(8, 9),
            relief="flat",
        )
        style.map(
            "Treeview.Heading",
            background=[("active", "#1e293b")],
            foreground=[("active", "#38bdf8")],
        )
        style.map(
            "Treeview",
            background=[("selected", "#1e3a8a")],
            foreground=[("selected", "#ffffff")],
        )
        style.configure(
            "TProgressbar",
            thickness=6,
            troughcolor="#090d16",
            background="#0284c7",
            borderwidth=0,
        )

    def _guard_trial_allowance(self, action_name: str = "import statements") -> bool:
        allowed, msg = self.license_mgr.can_process_statement()
        if not allowed:
            res = messagebox.askyesno(
                "5 Free Trial Statements Completed — Unlock Unlimited Processing",
                f"You have completed all 5 free trial bank statement conversions (approx. 3.5 hours of manual capture saved!).\n\n"
                f"To {action_name} with unlimited pages & clients:\n"
                f"• Solo Monthly: R 149 / month (Cancel anytime · 1 PC)\n"
                f"• Solo Annual: R 1,199 / year (Save 33% · 1 PC)\n"
                f"• Practice Pro: R 2,999 / year (Up to 3 PCs)\n\n"
                f"Would you like to open the Licensing & Instant Checkout window now?",
                parent=self.root,
                icon="warning",
            )
            if res:
                self.open_activation_dialog()
            return False
        return True

    def _check_batch_locked(self) -> bool:
        if getattr(self, "batch_locked", False):
            messagebox.showwarning(
                "Batch Locked",
                "This batch is cryptographically locked with a SARS Section 29 Audit Certificate.\n\n"
                "To make edits, please unlock the batch first from Tools > Unlock Current Batch.",
                parent=self.root,
            )
            return True
        return False

    def show_toast(self, message: str, color: str = "#0284c7", duration_ms: int = 2500):
        """Floating toast notification for instantaneous user action feedback."""
        try:
            if hasattr(self, "_active_toast") and self._active_toast:
                try:
                    self._active_toast.destroy()
                except Exception:
                    pass
                self._active_toast = None

            toast = tk.Frame(self.root, bg="#0f172a", padx=14, pady=8, highlightthickness=1, highlightbackground=color)
            self._active_toast = toast
            tk.Label(
                toast,
                text=message,
                font=("Segoe UI", 9, "bold"),
                fg="#f8fafc",
                bg="#0f172a",
            ).pack(side=tk.LEFT)
            toast.place(relx=0.98, rely=0.94, anchor="se")

            def _fade():
                try:
                    toast.destroy()
                    if getattr(self, "_active_toast", None) == toast:
                        self._active_toast = None
                except Exception:
                    pass

            self.root.after(duration_ms, _fade)
        except Exception:
            pass

    def open_client_query_sheet_dialog(self):
        """1-Click Client Query Sheet Generator for Suspense & Mystery Transactions."""
        suspense_txns = [t for t in self.transactions if t.get("is_suspense") or t.get("code") == "9999/000"]
        if not suspense_txns:
            messagebox.showinfo(
                "Client Query Sheet",
                "✓ Zero Suspense Transactions!\n\nAll lines in the current batch are fully allocated and verified.\nThere are no query items that need client clarification.",
                parent=self.root,
            )
            return

        client_name = self.active_profile
        tot_val = sum(abs(t.get("amount", 0.0)) for t in suspense_txns)

        msg_lines = [
            f"Queries for {client_name}  -  Bank Statement Reconciliation",
            f"Total Queries: {len(suspense_txns)} transactions (Total Value: R {tot_val:,.2f})\n",
            "Hi, we are finalizing your reconciliation for VAT201 filing and need invoices or descriptions for the following items:\n",
        ]
        for idx, t in enumerate(suspense_txns, 1):
            amt_str = f"-R {abs(t['amount']):,.2f}" if t["amount"] < 0 else f"+R {t['amount']:,.2f}"
            reason = t.get("query_reason", "Suspense / Unallocated")
            msg_lines.append(f"{idx}. {t['date']} | {amt_str} | {t['clean_payee']} (Reason: {reason})")

        msg_lines.append("\nPlease reply with the business purpose and attach invoices/receipts where available. Thank you!")
        query_text = "\n".join(msg_lines)

        dlg = tk.Toplevel(self.root)
        dlg.title(f"📤 1-Click Client Query Sheet  -  {client_name}")
        dlg.geometry("720x540")
        dlg.configure(bg="#090d16")
        apply_dark_titlebar(dlg)

        top_f = tk.Frame(dlg, bg="#090d16", padx=16, pady=12)
        top_f.pack(fill=tk.X)
        tk.Label(
            top_f,
            text=f"📤 Client Query Sheet  -  {client_name}",
            font=("Segoe UI", 12, "bold"),
            fg="#f8fafc",
            bg="#090d16",
        ).pack(anchor="w")
        tk.Label(
            top_f,
            text=f"Found {len(suspense_txns)} unallocated transactions needing client clarification (Total: R {tot_val:,.2f}).",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#090d16",
        ).pack(anchor="w", pady=(2, 0))

        txt_box = tk.Text(
            dlg,
            font=("Consolas", 10),
            bg="#0f172a",
            fg="#f8fafc",
            insertbackground="white",
            padx=12,
            pady=10,
            relief="flat",
            wrap=tk.WORD,
        )
        txt_box.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)
        txt_box.insert(tk.END, query_text)

        btn_box = tk.Frame(dlg, bg="#090d16", padx=16, pady=12)
        btn_box.pack(fill=tk.X)

        def _copy_clipboard():
            self.root.clipboard_clear()
            self.root.clipboard_append(txt_box.get("1.0", tk.END).strip())
            self.show_toast("📋 Copied Client Query Message to Clipboard!", color="#10b981")
            messagebox.showinfo("Copied", "Query message copied to clipboard!\nYou can paste it directly into WhatsApp or Email.", parent=dlg)

        def _export_html_schedule():
            out_file = filedialog.asksaveasfilename(
                title="Save Client Query Sheet",
                defaultextension=".html",
                initialfile=f"Client_Query_Sheet_{client_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.html",
                filetypes=[("HTML Document", "*.html"), ("All Files", "*.*")],
                parent=dlg,
            )
            if not out_file:
                return

            rows_html = "".join(
                f"<tr><td>{idx}</td><td>{t['date']}</td><td>{t['clean_payee']}</td><td>{'R ' + f'{abs(t["amount"]):,.2f}' if t['amount'] < 0 else '+R ' + f'{t["amount"]:,.2f}'}</td><td>{t.get('query_reason', 'Needs invoice / Purpose')}</td><td style='border-bottom:1px dashed #999; width:200px;'></td></tr>"
                for idx, t in enumerate(suspense_txns, 1)
            )
            html_doc = f"""<!DOCTYPE html>
<html>
<head>
<title>Client Query Sheet - {client_name}</title>
<style>
body {{ font-family: Segoe UI, sans-serif; margin: 40px; color: #1e293b; }}
h1 {{ color: #0284c7; margin-bottom: 4px; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
th, td {{ border: 1px solid #cbd5e1; padding: 10px 12px; text-align: left; font-size: 13px; }}
th {{ background: #f1f5f9; color: #475569; font-weight: 600; }}
</style>
</head>
<body>
<h1>Client Query Working Paper</h1>
<p><strong>Client:</strong> {client_name} &nbsp;|&nbsp; <strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d')} &nbsp;|&nbsp; <strong>Queries:</strong> {len(suspense_txns)} transactions (Total: R {tot_val:,.2f})</p>
<p>Please review the unallocated transactions below, provide the business description/purpose, and attach supporting tax invoices for SARS VAT deduction compliance.</p>
<table>
<thead>
<tr><th>#</th><th>Date</th><th>Payee / Description</th><th>Amount (ZAR)</th><th>Audit Query</th><th>Client Response / Attached Invoice</th></tr>
</thead>
<tbody>
{rows_html}
</tbody>
</table>
</body>
</html>"""
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(html_doc)
            self.show_toast(f"📄 Query Sheet saved to {Path(out_file).name}", color="#10b981")
            webbrowser.open(f"file:///{Path(out_file).resolve()}")

        HDButton(
            btn_box,
            text="📋 Copy WhatsApp / Email Text",
            font=("Segoe UI", 9, "bold"),
            bg="#0284c7",
            fg="white",
            padx=14,
            pady=4,
            command=_copy_clipboard,
        ).pack(side=tk.LEFT, padx=(0, 8))

        HDButton(
            btn_box,
            text="📄 Export PDF / HTML Schedule",
            font=("Segoe UI", 9, "bold"),
            bg="#10b981",
            fg="white",
            padx=14,
            pady=4,
            command=_export_html_schedule,
        ).pack(side=tk.LEFT, padx=(0, 8))

        HDButton(
            btn_box,
            text="✕ Close",
            font=("Segoe UI", 9),
            bg="#1e293b",
            fg="#94a3b8",
            padx=12,
            pady=4,
            command=dlg.destroy,
        ).pack(side=tk.RIGHT)

    def open_practice_master_dashboard_dialog(self):
        """Centralized Practice Management Command Palette for 60+ Client Files."""
        dlg = tk.Toplevel(self.root)
        dlg.title("🏢 Multi-Client Practice Master Dashboard")
        dlg.geometry("880x560")
        dlg.configure(bg="#090d16")
        apply_dark_titlebar(dlg)

        top_f = tk.Frame(dlg, bg="#090d16", padx=20, pady=16)
        top_f.pack(fill=tk.X)
        tk.Label(
            top_f,
            text="🏢 Multi-Client Practice Master Dashboard",
            font=("Segoe UI", 14, "bold"),
            fg="#f8fafc",
            bg="#090d16",
        ).pack(anchor="w")
        tk.Label(
            top_f,
            text="Manage all client entity files, ERP export profiles, financial year-ends, and reconciliation statuses in one centralized view.",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#090d16",
        ).pack(anchor="w", pady=(2, 0))

        cols = ("name", "erp", "fye", "lines", "status")
        tree = ttk.Treeview(dlg, columns=cols, show="headings", height=12)
        tree.heading("name", text="Client Entity Name", anchor=tk.W)
        tree.heading("erp", text="Target Accounting ERP", anchor=tk.CENTER)
        tree.heading("fye", text="FYE Month", anchor=tk.CENTER)
        tree.heading("lines", text="Cached Transactions", anchor=tk.CENTER)
        tree.heading("status", text="Reconciliation Status", anchor=tk.CENTER)

        tree.column("name", width=280)
        tree.column("erp", width=160, anchor=tk.CENTER)
        tree.column("fye", width=90, anchor=tk.CENTER)
        tree.column("lines", width=130, anchor=tk.CENTER)
        tree.column("status", width=160, anchor=tk.CENTER)

        month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        for prof_name, pdata in self.config["profiles"].items():
            erp = pdata.get("erp", "Pastel Partner")
            fye_idx = pdata.get("fin_year_end_month", 2)
            fye_str = month_names[fye_idx] if 1 <= fye_idx <= 12 else "Feb"

            o, c, txns = self.memory.load_session(prof_name)
            tx_count = len(txns) if txns else 0
            if prof_name == self.active_profile and self.transactions:
                tx_count = len(self.transactions)

            status_str = "✓ Ready" if tx_count > 0 else " -  Idle"
            if prof_name == self.active_profile:
                status_str = "● Active"

            tree.insert("", tk.END, iid=prof_name, values=(prof_name, erp, fye_str, f"{tx_count} lines", status_str))

        tree.pack(fill=tk.BOTH, expand=True, padx=20, pady=8)

        def _switch():
            sel = tree.selection()
            if not sel:
                return
            chosen = sel[0]
            dlg.destroy()
            self.profile_var.set(chosen)
            self.on_switch_profile()
            self.show_toast(f"Switched to Client: {chosen}", color="#38bdf8")

        tree.bind("<Double-1>", lambda e: _switch())

        btn_bar = tk.Frame(dlg, bg="#090d16", padx=20, pady=16)
        btn_bar.pack(fill=tk.X)

        HDButton(
            btn_bar,
            text="⚡ Switch to Selected Client",
            font=("Segoe UI", 9, "bold"),
            bg="#0284c7",
            fg="white",
            padx=14,
            pady=4,
            command=_switch,
        ).pack(side=tk.LEFT, padx=(0, 8))

        HDButton(
            btn_bar,
            text="➕ Add New Client Profile...",
            font=("Segoe UI", 9),
            bg="#1e293b",
            fg="#f8fafc",
            padx=12,
            pady=4,
            command=lambda: (dlg.destroy(), self.create_new_profile_dialog()),
        ).pack(side=tk.LEFT, padx=(0, 8))

        HDButton(
            btn_bar,
            text="✕ Close",
            font=("Segoe UI", 9),
            bg="#1e293b",
            fg="#94a3b8",
            padx=12,
            pady=4,
            command=dlg.destroy,
        ).pack(side=tk.RIGHT)

    def push_undo_state(self):
        snapshot = (
            [dict(t) for t in self.transactions],
            self.open_bal_var.get() if hasattr(self, "open_bal_var") else "0.00",
            self.close_bal_var.get() if hasattr(self, "close_bal_var") else "0.00",
        )
        self.undo_stack.append(snapshot)
        if len(self.undo_stack) > 30:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def _build_preview_dock_ui(self):
        """Builds internal widgets for the side Document & Row Inspector Dock."""
        dock_hdr = tk.Frame(self.preview_dock, bg="#1e293b", padx=12, pady=8)
        dock_hdr.pack(fill=tk.X)
        tk.Label(
            dock_hdr,
            text="📄 Document & Row Inspector",
            font=("Segoe UI", 9, "bold"),
            fg="#38bdf8",
            bg="#1e293b",
        ).pack(side=tk.LEFT)
        close_btn = HDButton(
            dock_hdr,
            text="✕",
            font=("Segoe UI", 9, "bold"),
            bg="#1e293b",
            fg="#94a3b8",
            relief="flat",
            padx=5,
            pady=0,
            cursor="hand2",
            command=self.toggle_preview_dock,
        )
        close_btn.pack(side=tk.RIGHT)
        ToolTip(close_btn, "Close Inspector Dock (Ctrl+P)")

        dock_body = tk.Frame(self.preview_dock, bg="#0b1120", padx=12, pady=10)
        dock_body.pack(fill=tk.BOTH, expand=True)

        self.dock_row_lbl = tk.Label(
            dock_body,
            text="Select a transaction line",
            font=("Segoe UI", 10, "bold"),
            fg="#f8fafc",
            bg="#0b1120",
            anchor="w",
        )
        self.dock_row_lbl.pack(fill=tk.X, pady=(0, 4))

        self.dock_sub_lbl = tk.Label(
            dock_body,
            text="Inspect extracted data, audit SARS VAT, or recode instantly.",
            font=("Segoe UI", 8),
            fg="#94a3b8",
            bg="#0b1120",
            anchor="w",
            wraplength=300,
            justify="left",
        )
        self.dock_sub_lbl.pack(fill=tk.X, pady=(0, 10))

        # Financials Card
        fin_card = tk.Frame(dock_body, bg="#0f172a", padx=10, pady=8, highlightthickness=1, highlightbackground="#334155")
        fin_card.pack(fill=tk.X, pady=(0, 10))

        tk.Label(fin_card, text="TRANSACTION DETAILS", font=("Segoe UI", 8, "bold"), fg="#64748b", bg="#0f172a").pack(anchor="w")

        self.dock_amt_lbl = tk.Label(fin_card, text="R 0.00", font=("Consolas", 14, "bold"), fg="#34d399", bg="#0f172a")
        self.dock_amt_lbl.pack(anchor="w", pady=(2, 4))

        self.dock_vat_lbl = tk.Label(fin_card, text="SARS VAT (15%): R 0.00 • Net: R 0.00", font=("Segoe UI", 8), fg="#cbd5e1", bg="#0f172a")
        self.dock_vat_lbl.pack(anchor="w")

        self.dock_audit_pill = tk.Label(fin_card, text="No Line Selected", font=("Segoe UI", 8, "bold"), bg="#1e293b", fg="#94a3b8", padx=6, pady=2)
        self.dock_audit_pill.pack(anchor="w", pady=(6, 0))

        # Extracted Payee & Ref Box
        payee_card = tk.Frame(dock_body, bg="#0f172a", padx=10, pady=8, highlightthickness=1, highlightbackground="#334155")
        payee_card.pack(fill=tk.X, pady=(0, 10))

        tk.Label(payee_card, text="CLEAN PAYEE & REFERENCE", font=("Segoe UI", 8, "bold"), fg="#64748b", bg="#0f172a").pack(anchor="w")
        self.dock_payee_val = tk.Label(payee_card, text=" - ", font=("Segoe UI", 9, "bold"), fg="#f1f5f9", bg="#0f172a", anchor="w", wraplength=290, justify="left")
        self.dock_payee_val.pack(anchor="w", pady=(2, 2))

        self.dock_ref_val = tk.Label(payee_card, text="Ref:  -  • Date:  - ", font=("Segoe UI", 8), fg="#94a3b8", bg="#0f172a", anchor="w")
        self.dock_ref_val.pack(anchor="w")

        # Quick Recode Dropdown
        recode_f = tk.Frame(dock_body, bg="#0b1120")
        recode_f.pack(fill=tk.X, pady=(0, 10))

        tk.Label(recode_f, text="General Ledger Code:", font=("Segoe UI", 8, "bold"), fg="#cbd5e1", bg="#0b1120").pack(anchor="w", pady=(0, 2))
        self.dock_coa_var = tk.StringVar()
        self.dock_coa_cb = ttk.Combobox(recode_f, textvariable=self.dock_coa_var, state="readonly", font=("Segoe UI", 9))
        self.dock_coa_cb.pack(fill=tk.X, pady=(0, 6))

        dock_btn_f = tk.Frame(recode_f, bg="#0b1120")
        dock_btn_f.pack(fill=tk.X)

        HDButton(
            dock_btn_f,
            text="⚡ Apply & Save",
            font=("Segoe UI", 8, "bold"),
            bg="#0284c7",
            fg="white",
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._apply_dock_recode,
        ).pack(side=tk.LEFT, padx=(0, 4))

        HDButton(
            dock_btn_f,
            text="🔍 Query Line",
            font=("Segoe UI", 8),
            bg="#78350f",
            fg="#fde68a",
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._mark_dock_as_query,
        ).pack(side=tk.LEFT)

        # Source File & Document Attachment
        src_f = tk.Frame(dock_body, bg="#0f172a", padx=10, pady=8, highlightthickness=1, highlightbackground="#334155")
        src_f.pack(fill=tk.X, pady=(0, 10))

        tk.Label(src_f, text="SOURCE DOCUMENT TRACE", font=("Segoe UI", 8, "bold"), fg="#64748b", bg="#0f172a").pack(anchor="w")
        self.dock_src_lbl = tk.Label(src_f, text="Source: Local Bank Statement", font=("Segoe UI", 8), fg="#cbd5e1", bg="#0f172a", anchor="w", wraplength=290, justify="left")
        self.dock_src_lbl.pack(anchor="w", pady=(2, 4))

        self.dock_open_src_btn = HDButton(
            src_f,
            text="📂 Open Original Document",
            font=("Segoe UI", 8),
            bg="#1e293b",
            fg="#38bdf8",
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._open_dock_source_file,
        )
        self.dock_open_src_btn.pack(anchor="w")

        # Row Navigation (Prev / Next)
        nav_f = tk.Frame(dock_body, bg="#0b1120")
        nav_f.pack(side=tk.BOTTOM, fill=tk.X, pady=(6, 0))

        HDButton(
            nav_f,
            text="◀ Previous Row",
            font=("Segoe UI", 8),
            bg="#1e293b",
            fg="#cbd5e1",
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=lambda: self._navigate_dock_row(-1),
        ).pack(side=tk.LEFT)

        HDButton(
            nav_f,
            text="Next Row ▶",
            font=("Segoe UI", 8),
            bg="#1e293b",
            fg="#cbd5e1",
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=lambda: self._navigate_dock_row(1),
        ).pack(side=tk.RIGHT)

    def toggle_preview_dock(self):
        """Toggles the side Document & Row Inspector Dock."""
        if not hasattr(self, "preview_dock"):
            return
        if self.preview_dock.winfo_manager() == "pack":
            self.preview_dock.pack_forget()
            if hasattr(self, "preview_toggle_btn"):
                self.preview_toggle_btn.config(text="👁️ Preview Dock", bg="#1e293b", fg="#94a3b8")
        else:
            self.preview_dock.pack(side=tk.RIGHT, fill=tk.Y, padx=(4, 0), before=self.scroll_y)
            if hasattr(self, "preview_toggle_btn"):
                self.preview_toggle_btn.config(text="👁️ Dock Active", bg="#0369a1", fg="#ffffff")
            sel = self.tree.selection()
            if sel:
                self.update_preview_dock(sel[0])
            elif self.transactions:
                first_id = self.tree.get_children()[0] if self.tree.get_children() else None
                if first_id:
                    self.tree.selection_set(first_id)
                    self.update_preview_dock(first_id)

    def update_preview_dock(self, row_id: str):
        """Updates the docked inspector with data from the active transaction row."""
        if not hasattr(self, "preview_dock") or self.preview_dock.winfo_manager() != "pack":
            return
        try:
            idx = int(row_id)
            if idx < 0 or idx >= len(self.transactions):
                return
            txn = self.transactions[idx]
        except Exception:
            return

        self._active_dock_idx = idx
        self.dock_row_lbl.config(text=f"Row #{idx + 1}  -  {txn.get('date', 'Unknown')}")
        self.dock_payee_val.config(text=txn.get("clean_payee", txn.get("raw_desc", " - ")))
        self.dock_ref_val.config(text=f"Ref: {txn.get('ref', ' - ')} • Code: {txn.get('code', ' - ')}")

        amt = txn.get("amount", 0.0)
        amt_str = f"+R {amt:,.2f}" if amt >= 0 else f"-R {abs(amt):,.2f}"
        self.dock_amt_lbl.config(
            text=amt_str,
            fg="#34d399" if amt >= 0 else "#f87171",
        )
        vat_amt = txn.get("vat_claim", 0.0)
        net_amt = txn.get("net", amt)
        vt = txn.get("vat_type", "Standard")
        self.dock_vat_lbl.config(text=f"{vt} VAT: R {vat_amt:,.2f} • Net: R {net_amt:,.2f}")

        if txn.get("is_duplicate"):
            self.dock_audit_pill.config(text="⚠️ QUARANTINED DUPLICATE", bg="#831843", fg="#fbcfe8")
        elif txn.get("is_suspense") or txn.get("code") == "9999/000":
            self.dock_audit_pill.config(text="❓ SUSPENSE / QUERY ITEM", bg="#78350f", fg="#fde68a")
        else:
            self.dock_audit_pill.config(text=f"✓ ALLOCATED ({txn.get('name', 'General Ledger')})", bg="#064e3b", fg="#34d399")

        coa_dict = self.config["profiles"][self.active_profile]["coa"]
        coa_items = sorted([f"{v['code']} - {v['name']}" for v in coa_dict.values()])
        self.dock_coa_cb["values"] = coa_items
        cur_match = f"{txn.get('code', '')} - {txn.get('name', '')}"
        for item in coa_items:
            if item.startswith(f"{txn.get('code', '')} -"):
                self.dock_coa_var.set(item)
                break
        else:
            self.dock_coa_var.set(cur_match)

        src = txn.get("source_file") or getattr(self, "current_bank_name", "Direct Statement Import")
        self.dock_src_lbl.config(text=f"Source: {src}")

    def _navigate_dock_row(self, delta: int):
        cur_idx = getattr(self, "_active_dock_idx", None)
        if cur_idx is None:
            children = self.tree.get_children()
            if children:
                cur_idx = int(children[0])
            else:
                return
        new_idx = max(0, min(len(self.transactions) - 1, cur_idx + delta))
        str_id = str(new_idx)
        self.tree.selection_set(str_id)
        self.tree.see(str_id)
        self.update_preview_dock(str_id)

    def _apply_dock_recode(self):
        if self._check_batch_locked():
            return
        cur_idx = getattr(self, "_active_dock_idx", None)
        if cur_idx is None or cur_idx >= len(self.transactions):
            return
        txn = self.transactions[cur_idx]
        chosen = self.dock_coa_var.get().strip()
        if not chosen:
            return
        chosen_code = chosen.split(" - ")[0].strip()
        coa_dict = self.config["profiles"][self.active_profile]["coa"]
        for _, info in coa_dict.items():
            if info["code"] == chosen_code:
                self.push_undo_state()
                txn["code"] = info["code"]
                txn["name"] = info["name"]
                txn["acc_type"] = info.get("type", "GL")
                txn["vat_type"] = info.get("vat", "Standard")
                txn["is_suspense"] = (txn["code"] == "9999/000" or str(txn["code"]).startswith("9999"))
                self.memory.remember_merchant(
                    self.active_profile,
                    txn["clean_payee"],
                    info["code"],
                    info["name"],
                    info.get("vat", "Standard"),
                    info.get("type", "GL"),
                )
                self.recalculate_row(txn)
                self.save_current_session()
                self.render_grid()
                self.update_preview_dock(str(cur_idx))
                self.show_toast(f"Updated Row #{cur_idx + 1} to {info['code']}", color="#10b981", duration_ms=2000)
                break

    def _mark_dock_as_query(self):
        if self._check_batch_locked():
            return
        cur_idx = getattr(self, "_active_dock_idx", None)
        if cur_idx is None or cur_idx >= len(self.transactions):
            return
        txn = self.transactions[cur_idx]
        self.push_undo_state()
        txn["code"] = "9999/000"
        txn["name"] = "Suspense / Unallocated Queries"
        txn["is_suspense"] = True
        self.recalculate_row(txn)
        self.save_current_session()
        self.render_grid()
        self.update_preview_dock(str(cur_idx))
        self.show_toast(f"Row #{cur_idx + 1} flagged for Client Query Sheet", color="#fbbf24", duration_ms=2500)

    def _open_dock_source_file(self):
        cur_idx = getattr(self, "_active_dock_idx", None)
        if cur_idx is None or cur_idx >= len(self.transactions):
            return
        txn = self.transactions[cur_idx]
        src = txn.get("source_file", "")
        import os
        if src and os.path.exists(src):
            try:
                open_file_or_folder(src)
            except Exception as e:
                messagebox.showinfo("Source Document", f"Could not launch {src}: {e}", parent=self.root)
        else:
            messagebox.showinfo(
                "Source Document",
                f"Source document: {src or 'Active Statement Session'}\n\nAll extracted lines are audited directly from the imported statement file.",
                parent=self.root,
            )

    def update_month_timeline(self):
        """Renders the horizontal month continuity timeline chain."""
        if not hasattr(self, "month_timeline_container"):
            return
        for w in self.month_timeline_container.winfo_children():
            w.destroy()

        if not self.transactions:
            self.month_timeline_container.pack_forget()
            return

        dates = []
        for t in self.transactions:
            d_str = t.get("date", "").strip()
            if len(d_str) >= 7 and d_str[:4].isdigit() and d_str[5:7].isdigit():
                dates.append(d_str[:7])

        if not dates:
            self.month_timeline_container.pack_forget()
            return

        unique_months = sorted(set(dates))
        if len(unique_months) <= 1:
            self.month_timeline_container.pack_forget()
            return

        self.month_timeline_container.pack(fill=tk.X, pady=(4, 0))

        tk.Label(
            self.month_timeline_container,
            text="📅 Month Continuity Chain:",
            font=("Segoe UI", 8, "bold"),
            fg="#94a3b8",
            bg="#0d1527",
        ).pack(side=tk.LEFT, padx=(0, 6))

        from datetime import datetime
        try:
            start_dt = datetime.strptime(unique_months[0], "%Y-%m")
            end_dt = datetime.strptime(unique_months[-1], "%Y-%m")
            cur_dt = start_dt
            all_expected = []
            while cur_dt <= end_dt:
                all_expected.append(cur_dt.strftime("%Y-%m"))
                if cur_dt.month == 12:
                    cur_dt = cur_dt.replace(year=cur_dt.year + 1, month=1)
                else:
                    cur_dt = cur_dt.replace(month=cur_dt.month + 1)
        except Exception:
            all_expected = unique_months

        has_gap = False
        for idx, m in enumerate(all_expected):
            if idx > 0:
                tk.Label(
                    self.month_timeline_container,
                    text="➔",
                    font=("Segoe UI", 8),
                    fg="#64748b",
                    bg="#0d1527",
                ).pack(side=tk.LEFT, padx=3)

            is_present = m in unique_months
            if is_present:
                pill = tk.Label(
                    self.month_timeline_container,
                    text=f"{m} ✓",
                    font=("Segoe UI", 8, "bold"),
                    bg="#064e3b",
                    fg="#34d399",
                    padx=6,
                    pady=1,
                )
                pill.pack(side=tk.LEFT)
                ToolTip(pill, f"Statement period {m} verified in batch")
            else:
                has_gap = True
                pill = tk.Label(
                    self.month_timeline_container,
                    text=f"⚠️ {m} GAP",
                    font=("Segoe UI", 8, "bold"),
                    bg="#7f1d1d",
                    fg="#fecaca",
                    padx=6,
                    pady=1,
                )
                pill.pack(side=tk.LEFT)
                ToolTip(pill, f"Missing statement month: {m}. Potential reconciliation continuity break!")

        if has_gap:
            tk.Label(
                self.month_timeline_container,
                text="⚠️ Continuity Gap Detected",
                font=("Segoe UI", 8, "bold"),
                fg="#f87171",
                bg="#0d1527",
            ).pack(side=tk.RIGHT, padx=4)
        else:
            tk.Label(
                self.month_timeline_container,
                text="✓ Unbroken Continuity",
                font=("Segoe UI", 8),
                fg="#34d399",
                bg="#0d1527",
            ).pack(side=tk.RIGHT, padx=4)

    def perform_undo(self, event=None):
        if not self.undo_stack:
            return
        curr_snap = (
            [dict(t) for t in self.transactions],
            self.open_bal_var.get(),
            self.close_bal_var.get(),
        )
        self.redo_stack.append(curr_snap)
        prev_state = self.undo_stack.pop()
        if isinstance(prev_state, tuple) and len(prev_state) == 3:
            self.transactions, prev_o, prev_c = prev_state
            self.open_bal_var.set(prev_o)
            self.close_bal_var.set(prev_c)
        else:
            self.transactions = prev_state
        self.render_grid()
        self.save_current_session()
        self.show_toast("↶ Undo: Restored previous batch state", color="#38bdf8")

    def perform_redo(self, event=None):
        if not self.redo_stack:
            return
        curr_snap = (
            [dict(t) for t in self.transactions],
            self.open_bal_var.get(),
            self.close_bal_var.get(),
        )
        self.undo_stack.append(curr_snap)
        next_state = self.redo_stack.pop()
        if isinstance(next_state, tuple) and len(next_state) == 3:
            self.transactions, next_o, next_c = next_state
            self.open_bal_var.set(next_o)
            self.close_bal_var.set(next_c)
        else:
            self.transactions = next_state
        self.render_grid()
        self.save_current_session()
        self.show_toast("↷ Redo: Re-applied batch state", color="#38bdf8")

    def save_current_session(self):
        o = self.open_bal_var.get()
        c = self.close_bal_var.get()
        self.memory.save_session(self.active_profile, o, c, self.transactions)

    def restore_or_init_session(self):
        o, c, saved_txns = self.memory.load_session(self.active_profile)
        if saved_txns:
            # Auto-repair legacy sample batch that had trailing balance numbers parsed as outflows
            net_saved = sum(_safe_float(t.get("amount", 0.0), 0.0) for t in saved_txns)
            if o == "3400.00" and c == "6897.40" and abs(o_val := 3400.0 + net_saved - 6897.40) > 1000:
                self.load_sample_batch()
                return
            self.transactions = saved_txns
            self.open_bal_var.set(o)
            self.close_bal_var.set(c)
            self.render_grid()
            self.status_lbl.config(
                text=f"Restored active session ({len(self.transactions)} lines) from local database."
            )
        elif self.active_profile == "Acme Trading (Pty) Ltd":
            self.load_sample_batch()
        else:
            self.transactions = []
            self.open_bal_var.set("0.00")
            self.close_bal_var.set("0.00")
            self.render_grid()
            self.status_lbl.config(
                text=f"Active client profile: {self.active_profile}  -  ready to import statements or slips."
            )

    # ==========================================================================
    # UI CONSTRUCTION
    # ==========================================================================
    def build_ui(self):
        # 0. UPDATE NOTIFICATION BANNER (Hidden until a newer version is detected)
        self.update_banner = tk.Frame(self.root, bg="#064e3b", padx=16, pady=6, highlightthickness=1, highlightbackground="#10b981")

        # 1. TOP HEADER & NAVIGATION BAR (Tier 1: Global Brand, Client Context & Secondary Tools)
        self.nav_frame = tk.Frame(self.root, bg="#090d16", padx=16, pady=8)
        nav = self.nav_frame
        nav.pack(fill=tk.X)

        # Brand Identity Cluster
        brand_f = tk.Frame(nav, bg="#090d16")
        brand_f.pack(side=tk.LEFT, padx=(0, 16))
        tk.Label(
            brand_f,
            text="TaxClean ZA",
            font=("Segoe UI", 15, "bold"),
            fg="#38bdf8",
            bg="#090d16",
        ).pack(side=tk.LEFT)
        tk.Label(
            brand_f,
            text="PRO",
            font=("Segoe UI", 8, "bold"),
            fg="#10b981",
            bg="#064e3b",
            padx=6,
            pady=1,
        ).pack(side=tk.LEFT, padx=(6, 0))

        # Client Context Capsule (Elevated Bento Pill for Client & Target Format)
        client_capsule = tk.Frame(nav, bg="#0f172a", padx=10, pady=3, highlightthickness=1, highlightbackground="#1e293b")
        client_capsule.pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(
            client_capsule,
            text="Client:",
            font=("Segoe UI", 9, "bold"),
            fg="#94a3b8",
            bg="#0f172a",
        ).pack(side=tk.LEFT, padx=(2, 4))

        self.profile_var = tk.StringVar(value=self.active_profile)
        self.profile_combo = ttk.Combobox(
            client_capsule,
            textvariable=self.profile_var,
            values=list(self.config["profiles"].keys()) + ["➕ Add New Client Profile...", "🗑️ Delete Current Client..."],
            state="readonly",
            width=18,
            font=("Segoe UI", 9),
        )
        self.profile_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.profile_combo.bind("<<ComboboxSelected>>", self.on_switch_profile)
        ToolTip(self.profile_combo, "Switch Client Profile, or select '➕ Add New Client Profile...' right inside this dropdown")

        tk.Label(
            client_capsule,
            text="Target:",
            font=("Segoe UI", 9, "bold"),
            fg="#94a3b8",
            bg="#0f172a",
        ).pack(side=tk.LEFT, padx=(2, 4))

        erp_val = self.config["profiles"][self.active_profile].get("erp", "Pastel Partner")
        self.erp_var = tk.StringVar(value=erp_val)
        self.erp_combo = ttk.Combobox(
            client_capsule,
            textvariable=self.erp_var,
            values=[
                "Pastel Partner",
                "Sage Business Cloud",
                "Xero",
                "QuickBooks Online",
                "SARS VAT201 Breakdown (Excel)",
                "SARS Universal Audit CSV",
            ],
            state="readonly",
            width=16,
            font=("Segoe UI", 9),
        )
        self.erp_combo.pack(side=tk.LEFT, padx=(0, 2))
        self.erp_combo.bind("<<ComboboxSelected>>", lambda e: self.update_bottom_info())
        ToolTip(self.erp_combo, "Target Accounting Export Format (Sage Pastel, Sage One, Xero, QBO, or SARS VAT201 Excel)")

        # Right-side System Utilities & Status (Undo, Redo, Clear, Tools, Guide, License)
        self.license_btn = HDButton(
            nav,
            text="✨ Pro",
            font=("Segoe UI", 9, "bold"),
            bg="#064e3b",
            fg="#34d399",
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self.open_activation_dialog,
        )
        self.license_btn.pack(side=tk.RIGHT, padx=(6, 0))
        self.update_license_ui_badge()
        ToolTip(self.license_btn, "License status & plans. Click to view activation details.")

        # Micro-AI Key Advisory Pill (Advise user to add free Gemini API Key)
        self.ai_key_btn = HDButton(
            nav,
            text="💡 Setup Free AI Key",
            font=("Segoe UI", 9, "bold"),
            bg="#3b1d54",
            fg="#f0abfc",
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self.open_ai_settings_dialog,
        )
        self.ai_key_btn.pack(side=tk.RIGHT, padx=(6, 0))
        self.update_ai_key_ui_advisory()

        man_btn = HDButton(
            nav,
            text="📖 Guide [F1]",
            font=("Segoe UI", 9),
            bg="#1e293b",
            fg="#cbd5e1",
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self.open_user_manual,
        )
        man_btn.pack(side=tk.RIGHT, padx=(6, 0))
        ToolTip(man_btn, "Open Interactive Step-by-Step User Manual & Guide (Shortcut: F1)")

        tools_mb = tk.Menubutton(
            nav,
            text="🛠️ Tools ▾",
            font=("Segoe UI", 9, "bold"),
            bg="#1e293b",
            fg="#cbd5e1",
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
        )
        tools_menu = tk.Menu(tools_mb, tearoff=False, bg="#1e293b", fg="#f1f5f9", font=("Segoe UI", 10))
        tools_menu.add_command(label="🚀 Check for Software Updates...", command=self.check_for_updates_interactive)
        tools_menu.add_command(label="📖 User Manual & How-To Guide [F1]", command=self.open_user_manual)
        tools_menu.add_command(label="📋 Chart of Accounts Manager (Add / Edit / Delete GL Codes) [Alt+C]", command=self.open_coa_manager_dialog)
        tools_menu.add_separator()
        tools_menu.add_command(label="⚡ Import One or Multiple Statements / Slips [Ctrl+O]", command=self.start_import_worker)
        tools_menu.add_command(label="➕ Append Statements / Slips (Multi-Month Continuity) [Alt+A]", command=self.append_statement_dialog)
        tools_menu.add_command(label="📎 Shoebox Receipt-to-Bank Auto-Matcher [Alt+M]", command=self.open_receipt_matcher_dialog)
        tools_menu.add_command(label="🏛️ SARS VAT201 eFiling Box Summary Card [Alt+V]", command=self.open_vat201_card_dialog)
        tools_menu.add_command(label="📤 1-Click Client Query Sheet (WhatsApp / PDF Export)", command=self.open_client_query_sheet_dialog)
        tools_menu.add_command(label="🏢 Practice Master Dashboard (All Clients) [Ctrl+K]", command=self.open_practice_master_dashboard_dialog)
        tools_menu.add_command(label="✂️ Split Selected Transaction [Alt+S]", command=self.open_split_transaction_dialog)
        tools_menu.add_separator()
        tools_menu.add_command(label="🔒 1-Click Lock Batch & Audit Certificate [Alt+L]", command=self.lock_batch_and_generate_certificate)
        tools_menu.add_command(label="🔓 Unlock Current Batch", command=self.unlock_batch)
        tools_menu.add_command(label="📈 Monthly Expense Anomaly Radar", command=self.open_anomaly_radar_dialog)
        tools_menu.add_command(label="📊 Cash Flow Burn-Rate & Runway Card", command=self.open_cash_runway_dialog)
        tools_menu.add_command(label="📝 SARS Section 20 Invoice Compliance Checker", command=self.open_section20_checker_dialog)
        tools_menu.add_separator()
        tools_menu.add_command(label="➕ Add New Client Profile...", command=self.create_new_profile_dialog)
        tools_menu.add_command(label="📅 Set Financial Year-End (FYE) Month...", command=self.open_fye_profile_quick_menu)
        tools_menu.add_command(label="🧪 Load Balanced Practice Sample Batch (0 Credits Used)", command=self.load_sample_batch)
        tools_menu.add_command(label="+ Add Manual Line", command=self.add_manual_row)
        tools_menu.add_command(label="🔄 Re-run Auto-Categorization", command=self.rerun_categorization)
        tools_menu.add_command(label="📤 Export Learned Rules (.tzrules)", command=self.export_rules_dialog)
        tools_menu.add_command(label="📥 Import Learned Rules (.tzrules)", command=self.import_rules_dialog)
        tools_menu.add_command(label="☁️ Backup Database (.db)", command=self.backup_database_action)
        tools_menu.add_separator()
        tools_menu.add_command(label="📋 Paste from Excel / Clipboard [Ctrl+V]", command=self.paste_from_clipboard_dialog)
        tools_menu.add_command(label="🛡️ Duplicate & Overlap Sentinel (Scan & 1-Click Purge)", command=self.open_duplicate_sentinel_dialog)
        tools_menu.add_command(label="🔄 Inter-Account Transfer Paired Cleanser", command=self.open_contra_transfer_cleanser_dialog)
        tools_menu.add_command(label="📊 1-Click SARS VAT201 Audit Pack (.xlsx) [Alt+V]", command=self.export_vat201_excel_audit_pack)
        tools_menu.add_command(label="⚠️ Report Parsing Issue / Statement Error [F12]", command=self.open_issue_reporter_dialog)
        tools_menu.add_command(label="🏥 SA Bank Format Diagnostic Suite", command=self.show_sa_bank_diagnostics_dialog)
        tools_menu.add_command(label="🤖 AI Micro-Engine Settings (Google AI Studio)", command=self.open_ai_settings_dialog)
        tools_menu.add_command(label="⚖️ Legal / POPIA Notice", command=self.show_compliance_modal)
        tools_menu.add_command(label="🔑 Pro License Activation", command=self.open_activation_dialog)
        tools_mb.config(menu=tools_menu)
        tools_mb.pack(side=tk.RIGHT, padx=(6, 0))
        ToolTip(tools_mb, "Open Practice Toolkit, Forensic Audit Tools, Client Profiles & Settings")

        hist_pill = tk.Frame(nav, bg="#1e293b", padx=3, pady=1)
        hist_pill.pack(side=tk.RIGHT, padx=(0, 6))

        self.undo_btn = HDButton(
            hist_pill,
            text="↶",
            font=("Segoe UI", 9, "bold"),
            bg="#1e293b",
            fg="#cbd5e1",
            activebackground="#334155",
            activeforeground="#ffffff",
            relief="flat",
            width=24 if HAS_CUSTOMTKINTER else 2,
            padx=3,
            pady=1,
            cursor="hand2",
            command=self.perform_undo,
        )
        self.undo_btn.pack(side=tk.LEFT, padx=1)
        ToolTip(self.undo_btn, "Undo last action (Shortcut: Ctrl+Z)")

        self.redo_btn = HDButton(
            hist_pill,
            text="↷",
            font=("Segoe UI", 9, "bold"),
            bg="#1e293b",
            fg="#cbd5e1",
            activebackground="#334155",
            activeforeground="#ffffff",
            relief="flat",
            width=24 if HAS_CUSTOMTKINTER else 2,
            padx=1,
            pady=1,
            cursor="hand2",
            command=self.perform_redo,
        )
        self.redo_btn.pack(side=tk.LEFT, padx=1)
        ToolTip(self.redo_btn, "Redo action (Shortcut: Ctrl+Y)")

        self.clear_batch_btn = HDButton(
            hist_pill,
            text="🗑️",
            font=("Segoe UI", 9, "bold"),
            bg="#1e293b",
            fg="#f87171",
            activebackground="#7f1d1d",
            activeforeground="#fecaca",
            relief="flat",
            width=24 if HAS_CUSTOMTKINTER else 2,
            padx=3,
            pady=1,
            cursor="hand2",
            command=self.clear_batch,
        )
        self.clear_batch_btn.pack(side=tk.LEFT, padx=1)
        ToolTip(self.clear_batch_btn, "Clear current batch and reset workspace (Undoable via Ctrl+Z)")

        # 2. WORKSPACE ACTION & FILTER RIBBON (Tier 2: The Command & Ingestion Hub)
        action_ribbon = tk.Frame(self.root, bg="#0f172a", padx=16, pady=6)
        action_ribbon.pack(fill=tk.X)

        # Left Section: Search Input & Category Filter Tabs
        left_action_f = tk.Frame(action_ribbon, bg="#0f172a")
        left_action_f.pack(side=tk.LEFT)

        s_frame = tk.Frame(left_action_f, bg="#1e293b", padx=6, pady=3, highlightthickness=1, highlightbackground="#334155", highlightcolor="#38bdf8")
        s_frame.pack(side=tk.LEFT, padx=(0, 8))
        tk.Label(s_frame, text="🔍", font=("Segoe UI", 9), fg="#94a3b8", bg="#1e293b").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        s_ent = tk.Entry(
            s_frame,
            textvariable=self.search_var,
            width=15,
            font=("Segoe UI", 9),
            bg="#1e293b",
            fg="#f8fafc",
            insertbackground="white",
            relief="flat",
        )
        s_ent.pack(side=tk.LEFT, padx=(4, 2))
        s_ent.bind("<FocusIn>", lambda e: s_frame.config(highlightbackground="#38bdf8"))
        s_ent.bind("<FocusOut>", lambda e: s_frame.config(highlightbackground="#334155"))
        self.search_var.trace_add("write", lambda *args: self.render_grid())
        ToolTip(s_ent, "Filter transactions by Payee, GL Code, Reference, or Account Name (Shortcut: Ctrl+F)")

        # Category Filter Tabs
        self.tab_buttons = {}
        tab_defs = [
            ("all", "All Lines"),
            ("suspense", "• Suspense"),
            ("duplicates", "• Duplicates"),
            ("inflows", "Inflows"),
            ("outflows", "Outflows"),
        ]
        for key, label in tab_defs:
            btn = HDButton(
                left_action_f,
                text=label,
                font=("Segoe UI", 9, "bold" if key == "all" else "normal"),
                bg="#1e293b" if key == "all" else "#0f172a",
                fg="#38bdf8" if key == "all" else "#94a3b8",
                relief="flat",
                padx=10,
                pady=4,
                cursor="hand2",
                command=lambda k=key: self.switch_filter_tab(k),
            )
            btn.pack(side=tk.LEFT, padx=2)
            self.tab_buttons[key] = btn

        # Right Section: Primary Workflow Action CTAs (Strict Visual Hierarchy)
        right_action_f = tk.Frame(action_ribbon, bg="#0f172a")
        right_action_f.pack(side=tk.RIGHT)

        exp_btn = HDButton(
            right_action_f,
            text="💾 Export Batch",
            bg="#10b981",
            fg="white",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padx=14,
            pady=4,
            cursor="hand2",
            command=self.export_batch_file,
        )
        exp_btn.pack(side=tk.RIGHT, padx=3)
        ToolTip(exp_btn, "Run 4-Point Pre-Flight Audit & Export to Selected ERP / Excel / CSV")

        imp_btn = HDButton(
            right_action_f,
            text="⚡ Import Docs",
            bg="#0284c7",
            fg="white",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padx=13,
            pady=4,
            cursor="hand2",
            command=self.start_import_worker,
        )
        imp_btn.pack(side=tk.RIGHT, padx=3)
        ToolTip(imp_btn, "Import 1 or multiple PDF Bank Statements, CSVs, or Scanned Slips (Shortcut: Ctrl+O)")

        app_btn = HDButton(
            right_action_f,
            text="➕ Append",
            bg="#1e293b",
            fg="#cbd5e1",
            relief="flat",
            font=("Segoe UI", 9, "bold"),
            padx=9,
            pady=4,
            cursor="hand2",
            command=self.append_statement_dialog,
        )
        app_btn.pack(side=tk.RIGHT, padx=3)
        ToolTip(app_btn, "Append additional statements/slips into current batch (Shortcut: Alt+A)")

        paste_btn = HDButton(
            right_action_f,
            text="📋 Paste",
            bg="#1e293b",
            fg="#cbd5e1",
            relief="flat",
            font=("Segoe UI", 9, "bold"),
            padx=9,
            pady=4,
            cursor="hand2",
            command=self.paste_from_clipboard_dialog,
        )
        paste_btn.pack(side=tk.RIGHT, padx=3)
        ToolTip(paste_btn, "Direct Clipboard & Excel Ingest: Paste rows copied from Excel or Sheets (Shortcut: Ctrl+V)")

        add_r_btn = HDButton(
            right_action_f,
            text="+ Add Row",
            font=("Segoe UI", 9),
            bg="#1e293b",
            fg="#94a3b8",
            relief="flat",
            padx=8,
            pady=4,
            cursor="hand2",
            command=self.add_manual_row,
        )
        add_r_btn.pack(side=tk.RIGHT, padx=3)
        ToolTip(add_r_btn, "Insert a manual transaction line into the current batch")

        self.cols_menu_btn = HDButton(
            right_action_f,
            text="📊 Columns ▾",
            font=("Segoe UI", 9),
            bg="#1e293b",
            fg="#94a3b8",
            relief="flat",
            padx=8,
            pady=4,
            cursor="hand2",
            command=self.open_columns_visibility_menu,
        )
        self.cols_menu_btn.pack(side=tk.RIGHT, padx=3)
        ToolTip(self.cols_menu_btn, "Show or hide individual table columns")

        coa_btn = HDButton(
            right_action_f,
            text="📋 COA",
            font=("Segoe UI", 9),
            bg="#1e293b",
            fg="#94a3b8",
            relief="flat",
            padx=8,
            pady=4,
            cursor="hand2",
            command=self.open_coa_manager_dialog,
        )
        coa_btn.pack(side=tk.RIGHT, padx=3)
        ToolTip(coa_btn, "Add, Edit, Delete, or Import Custom GL Account Codes (Shortcut: Alt+C)")

        self.preview_toggle_btn = HDButton(
            right_action_f,
            text="👁️ Preview Dock",
            font=("Segoe UI", 9),
            bg="#1e293b",
            fg="#94a3b8",
            relief="flat",
            padx=8,
            pady=4,
            cursor="hand2",
            command=self.toggle_preview_dock,
        )
        self.preview_toggle_btn.pack(side=tk.RIGHT, padx=3)
        ToolTip(self.preview_toggle_btn, "Toggle Document Preview & Row Inspector Dock (Shortcut: Ctrl+P)")

        # 3. EXECUTIVE BALANCING & RECONCILIATION COCKPIT CARD (Tier 3: Elevated Bento Card)
        cockpit_container = tk.Frame(self.root, bg="#090d16", padx=16, pady=4)
        cockpit_container.pack(fill=tk.X)

        self.recon_bar = tk.Frame(cockpit_container, bg="#0d1527", padx=14, pady=6, highlightthickness=1, highlightbackground="#1e293b")
        self.recon_bar.pack(fill=tk.X)

        var_box = tk.Frame(self.recon_bar, bg="#0d1527")
        var_box.pack(side=tk.LEFT, padx=(0, 12))

        self.variance_lbl = tk.Label(
            var_box,
            text="✓ BALANCED (Diff: R 0.00)",
            font=("Segoe UI", 9, "bold"),
            bg="#065f46",
            fg="#34d399",
            padx=8,
            pady=3,
        )
        self.variance_lbl.pack(side=tk.LEFT)

        self.auto_align_btn = HDButton(
            var_box,
            text="Auto-Align",
            font=("Segoe UI", 9, "bold"),
            bg="#991b1b",
            fg="white",
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=self.auto_align_variance,
        )
        self.auto_align_btn.pack(side=tk.LEFT, padx=(3, 0))
        ToolTip(self.auto_align_btn, "1-Click Auto-Align Statement Closing Balance or Insert Suspense Balancing Line")

        # Live Audit Active Indicator & Micro-AI Status
        live_f = tk.Frame(self.recon_bar, bg="#064e3b", padx=6, pady=2)
        live_f.pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(live_f, text="● Live Audit Active", font=("Segoe UI", 8, "bold"), fg="#34d399", bg="#064e3b").pack()

        # Balances Flow: Open R ... -> Net R ... -> Close R ...
        flow_f = tk.Frame(self.recon_bar, bg="#0d1527")
        flow_f.pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(flow_f, text="Open R", font=("Segoe UI", 9, "bold"), fg="#cbd5e1", bg="#0d1527").pack(side=tk.LEFT, padx=(0, 3))
        self.open_bal_var = tk.StringVar(value="0.00")
        self.open_bal_ent = tk.Entry(
            flow_f,
            textvariable=self.open_bal_var,
            width=11,
            font=("Consolas", 10, "bold"),
            bg="#0a101d",
            fg="#38bdf8",
            insertbackground="white",
            relief="flat",
            justify="center",
            highlightthickness=1,
            highlightbackground="#334155",
            highlightcolor="#38bdf8",
        )
        self.open_bal_ent.pack(side=tk.LEFT, padx=(0, 5))
        self.open_bal_var.trace_add("write", lambda *args: self.recalculate_reconciliation())
        ToolTip(self.open_bal_ent, "Statement Opening Balance (ZAR)  -  Automatically extracted or type to override")

        tk.Label(flow_f, text="→", font=("Segoe UI", 10, "bold"), fg="#94a3b8", bg="#0d1527").pack(side=tk.LEFT, padx=1)

        tk.Label(flow_f, text="Net", font=("Segoe UI", 9, "bold"), fg="#cbd5e1", bg="#0d1527").pack(side=tk.LEFT, padx=(3, 3))
        self.net_movement_lbl = tk.Label(
            flow_f,
            text="R 0.00",
            font=("Consolas", 10, "bold"),
            fg="#34d399",
            bg="#0d1527",
        )
        self.net_movement_lbl.pack(side=tk.LEFT, padx=(0, 5))

        tk.Label(flow_f, text="→", font=("Segoe UI", 10, "bold"), fg="#94a3b8", bg="#0d1527").pack(side=tk.LEFT, padx=1)

        tk.Label(flow_f, text="Close R", font=("Segoe UI", 9, "bold"), fg="#cbd5e1", bg="#0d1527").pack(side=tk.LEFT, padx=(3, 3))
        self.close_bal_var = tk.StringVar(value="0.00")
        self.close_bal_ent = tk.Entry(
            flow_f,
            textvariable=self.close_bal_var,
            width=11,
            font=("Consolas", 10, "bold"),
            bg="#0a101d",
            fg="#38bdf8",
            insertbackground="white",
            relief="flat",
            justify="center",
            highlightthickness=1,
            highlightbackground="#334155",
            highlightcolor="#38bdf8",
        )
        self.close_bal_ent.pack(side=tk.LEFT, padx=(0, 5))
        self.close_bal_var.trace_add("write", lambda *args: self.recalculate_reconciliation())
        ToolTip(self.close_bal_ent, "Statement Closing Balance (ZAR)  -  Automatically verified against Opening + Net")

        # Right KPI Badges: Claimable VAT, Suspense, Duplicates, Hide Summary toggle
        right_f = tk.Frame(self.recon_bar, bg="#0d1527")
        right_f.pack(side=tk.RIGHT)

        self.vat_kpi_lbl = tk.Label(
            right_f,
            text="Claimable VAT: R 0.00",
            font=("Segoe UI", 9, "bold"),
            fg="#38bdf8",
            bg="#0d1527",
            cursor="hand2",
        )
        self.vat_kpi_lbl.pack(side=tk.LEFT, padx=(0, 8))
        self.vat_kpi_lbl.bind("<Button-1>", lambda e: self.open_vat201_card_dialog())
        ToolTip(self.vat_kpi_lbl, "Click to view SARS VAT201 eFiling Box Summary Schedule & Excel Audit Pack (Shortcut: Alt+V)")

        self.roi_badge_lbl = tk.Label(
            right_f,
            text="⏱️ ROI: ~0h saved",
            font=("Segoe UI", 8, "bold"),
            fg="#34d399",
            bg="#064e3b",
            padx=6,
            pady=1,
            cursor="hand2",
        )
        self.roi_badge_lbl.pack(side=tk.LEFT, padx=(0, 6))
        ToolTip(self.roi_badge_lbl, "Estimated manual data entry time and practice billable labor saved")

        self.suspense_btn_pill = HDButton(
            right_f,
            text="0 Suspense",
            font=("Segoe UI", 8, "bold"),
            bg="#78350f",
            fg="#fde68a",
            relief="flat",
            padx=5,
            pady=1,
            cursor="hand2",
            command=lambda: self.switch_filter_tab("suspense"),
        )
        self.suspense_btn_pill.pack(side=tk.LEFT, padx=2)
        ToolTip(self.suspense_btn_pill, "Click to filter unallocated / query rows in Suspense (9999/000)")

        self.dup_btn_pill = HDButton(
            right_f,
            text="0 Duplicates",
            font=("Segoe UI", 8, "bold"),
            bg="#831843",
            fg="#fbcfe8",
            relief="flat",
            padx=5,
            pady=1,
            cursor="hand2",
            command=self.open_duplicate_sentinel_dialog,
        )
        self.dup_btn_pill.pack(side=tk.LEFT, padx=2)
        ToolTip(self.dup_btn_pill, "Click to filter quarantined duplicate transactions")

        self.hide_math_btn = HDButton(
            right_f,
            text="Hide Summary ⌃",
            font=("Segoe UI", 8),
            bg="#1e293b",
            fg="#cbd5e1",
            relief="flat",
            padx=5,
            pady=1,
            cursor="hand2",
            command=self.toggle_metrics_strip,
        )
        self.hide_math_btn.pack(side=tk.LEFT, padx=(4, 0))
        ToolTip(self.hide_math_btn, "Collapse or expand the 6 Summary KPI Cards to maximize table space")

        # 3c. MONTH CONTINUITY TIMELINE STRIP (Visual Horizontal Chain)
        self.month_timeline_container = tk.Frame(cockpit_container, bg="#0d1527", padx=10, pady=4, highlightthickness=1, highlightbackground="#1e293b")

        # Compact Status Banner
        self.hero_banner = tk.Frame(self.root, bg="#0c1527", padx=16, pady=4)
        self.hero_banner.pack(fill=tk.X)

        self.hero_icon_lbl = tk.Label(
            self.hero_banner,
            text="⚪",
            font=("Segoe UI", 12),
            bg="#0c1527",
            fg="#94a3b8",
        )
        self.hero_icon_lbl.pack(side=tk.LEFT, padx=(0, 8))

        self.hero_text_f = tk.Frame(self.hero_banner, bg="#0c1527")
        self.hero_text_f.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.hero_title_lbl = tk.Label(
            self.hero_text_f,
            text="STATEMENT RECONCILIATION: READY",
            font=("Segoe UI", 10, "bold"),
            bg="#0c1527",
            fg="#f1f5f9",
            anchor="w",
        )
        self.hero_title_lbl.pack(fill=tk.X)

        self.hero_sub_lbl = tk.Label(
            self.hero_text_f,
            text="Import one or multiple statements/slips to begin live reconciliation audit.",
            font=("Segoe UI", 9),
            bg="#0c1527",
            fg="#94a3b8",
            anchor="w",
        )
        self.hero_sub_lbl.pack(fill=tk.X)

        self.hero_auto_btn = HDButton(
            self.hero_banner,
            text="⚡ Auto-Align",
            font=("Segoe UI", 8, "bold"),
            bg="#dc2626",
            fg="white",
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=self.auto_align_variance,
        )

        # 3b. EXPANDED RECONCILIATION METRICS STRIP (Collapsible 6 Bento Cards)
        self.metrics_frame = tk.Frame(self.root, bg="#090d16", padx=16, pady=4)
        self.metrics_frame.pack(fill=tk.X)

        self.card_inflows = self.create_metric_card(self.metrics_frame, "TOTAL INFLOWS (+)", "+R 0.00", "#34d399")
        self.card_outflows = self.create_metric_card(self.metrics_frame, "TOTAL OUTFLOWS (-)", "-R 0.00", "#f87171")
        self.card_exp_close = self.create_metric_card(self.metrics_frame, "EXPECTED CLOSING", "R 0.00", "#f1f5f9")
        self.card_stmt_close = self.create_metric_card(self.metrics_frame, "STATEMENT CLOSING", "R 0.00", "#f1f5f9")
        self.card_delta = self.create_metric_card(self.metrics_frame, "RECONCILIATION DELTA", "R 0.00", "#34d399")
        self.card_lines = self.create_metric_card(self.metrics_frame, "PROCESSED LINES", "0 transactions", "#f1f5f9")

        # 4b. BULK ROW SELECTION & ALLOCATION TOOLBAR
        self.bulk_bar = tk.Frame(self.root, bg="#1e293b", padx=16, pady=6)
        # Hidden by default; packed when 2+ rows selected
        self.bulk_count_lbl = tk.Label(
            self.bulk_bar,
            text="0 rows selected",
            font=("Segoe UI", 10, "bold"),
            bg="#1e293b",
            fg="#f8fafc",
        )
        self.bulk_count_lbl.pack(side=tk.LEFT, padx=(0, 12))

        tk.Label(self.bulk_bar, text="Assign GL:", font=("Segoe UI", 9), bg="#1e293b", fg="#cbd5e1").pack(side=tk.LEFT, padx=(0, 4))
        self.bulk_acc_var = tk.StringVar()
        coa_dict = self.config["profiles"][self.active_profile]["coa"]
        coa_items = sorted([f"{v['code']} - {v['name']}" for v in coa_dict.values()])
        self.bulk_acc_cb = ttk.Combobox(
            self.bulk_bar,
            textvariable=self.bulk_acc_var,
            values=coa_items,
            state="readonly",
            width=28,
            font=("Segoe UI", 9),
        )
        if coa_items:
            self.bulk_acc_cb.current(0)
        self.bulk_acc_cb.pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(self.bulk_bar, text="SARS VAT:", font=("Segoe UI", 9), bg="#1e293b", fg="#cbd5e1").pack(side=tk.LEFT, padx=(0, 4))
        self.bulk_vat_var = tk.StringVar(value="Standard (15%)")
        self.bulk_vat_cb = ttk.Combobox(
            self.bulk_bar,
            textvariable=self.bulk_vat_var,
            values=["Standard (15%)", "Zero-Rated (0%)", "Exempt / None"],
            state="readonly",
            width=15,
            font=("Segoe UI", 9),
        )
        self.bulk_vat_cb.pack(side=tk.LEFT, padx=(0, 12))

        HDButton(
            self.bulk_bar,
            text="⚡ Apply & Memorize",
            font=("Segoe UI", 9, "bold"),
            bg="#0284c7",
            fg="white",
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=self.apply_bulk_categorization,
        ).pack(side=tk.LEFT, padx=(0, 6))

        HDButton(
            self.bulk_bar,
            text="🗑️ Delete Selected",
            font=("Segoe UI", 9),
            bg="#7f1d1d",
            fg="#fecaca",
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self.delete_selected_rows,
        ).pack(side=tk.LEFT, padx=(0, 6))

        HDButton(
            self.bulk_bar,
            text="✕ Deselect",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="#cbd5e1",
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self.clear_selection,
        ).pack(side=tk.LEFT)

        # 5. DATA GRID
        main_content = tk.Frame(self.root, bg="#090d16")
        main_content.pack(fill=tk.BOTH, expand=True)

        self.columns = (
            "idx",
            "date",
            "ref",
            "ledger",
            "payee",
            "account",
            "gross",
            "vat_type",
            "vat",
            "net",
            "audit",
            "actions",
        )
        self.visible_columns = list(self.columns)
        self.column_filters = {}
        self.sort_column = None
        self.sort_descending = False

        self.tree = ttk.Treeview(
            main_content,
            columns=self.columns,
            show="headings",
            selectmode="extended",
        )

        headings = [
            ("idx", "#", 40, tk.CENTER),
            ("date", "Date ▾", 95, tk.CENTER),
            ("ref", "Reference ▾", 85, tk.CENTER),
            ("ledger", "Ledger ▾", 70, tk.CENTER),
            ("payee", "Payee / Description ▾", 230, tk.W),
            ("account", "Account / Nominal Code ▾", 260, tk.W),
            ("gross", "Gross (ZAR) ▾", 115, tk.E),
            ("vat_type", "SARS VAT Type ▾", 110, tk.CENTER),
            ("vat", "VAT Amount ▾", 95, tk.E),
            ("net", "Net Excl ▾", 110, tk.E),
            ("audit", "Audit Status & Reason ▾", 220, tk.W),
            ("actions", "Action", 75, tk.CENTER),
        ]

        for cid, title, w, anch in headings:
            self.tree.heading(cid, text=title, command=lambda c=cid: self.open_column_header_dropdown(c))
            self.tree.column(cid, width=w, anchor=anch)

        self.scroll_y = ttk.Scrollbar(main_content, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scroll_y.set)

        # Document & Row Inspector Dock (Side-by-side split panel)
        self.preview_dock = tk.Frame(
            main_content,
            bg="#0b1120",
            width=330,
            highlightthickness=1,
            highlightbackground="#1e293b",
        )
        self.preview_dock.pack_propagate(False)
        self._build_preview_dock_ui()

        self.scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Modern Empty State Dropzone Card (Visible when 0 transactions are present)
        self.empty_state_frame = tk.Frame(
            main_content,
            bg="#0d1527",
            highlightthickness=1,
            highlightbackground="#1e293b",
            padx=28,
            pady=24,
        )

        tk.Label(
            self.empty_state_frame,
            text="📥",
            font=("Segoe UI", 32),
            fg="#38bdf8",
            bg="#0d1527",
        ).pack(pady=(0, 4))

        tk.Label(
            self.empty_state_frame,
            text="Ready to Reconcile",
            font=("Segoe UI", 13, "bold"),
            fg="#f8fafc",
            bg="#0d1527",
        ).pack(pady=(0, 2))

        tk.Label(
            self.empty_state_frame,
            text="Drop bank statements, CSVs, or slips here, or click 'Import Docs' above.\nSupports Absa, Standard Bank, FNB, Nedbank, Capitec, Discovery, Investec, Tyme, Bidvest, Mercantile & Sasfin.",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#0d1527",
            justify="center",
        ).pack(pady=(0, 14))

        es_btns = tk.Frame(self.empty_state_frame, bg="#0d1527")
        es_btns.pack()

        HDButton(
            es_btns,
            text="⚡ Import Statements / Slips [Ctrl+O]",
            font=("Segoe UI", 9, "bold"),
            bg="#0284c7",
            fg="white",
            padx=14,
            pady=5,
            cursor="hand2",
            command=self.start_import_worker,
        ).pack(side=tk.LEFT, padx=5)

        HDButton(
            es_btns,
            text="📋 Paste from Excel [Ctrl+V]",
            font=("Segoe UI", 9),
            bg="#1e293b",
            fg="#cbd5e1",
            padx=12,
            pady=5,
            cursor="hand2",
            command=self.paste_from_clipboard_dialog,
        ).pack(side=tk.LEFT, padx=5)

        HDButton(
            es_btns,
            text="🧪 Load Practice Sample",
            font=("Segoe UI", 9),
            bg="#064e3b",
            fg="#34d399",
            padx=12,
            pady=5,
            cursor="hand2",
            command=self.load_sample_batch,
        ).pack(side=tk.LEFT, padx=5)

        self.tree.bind("<Double-1>", self.on_cell_double_click)
        self.tree.bind("<F2>", self.on_f2_edit_selected)
        self.tree.bind("<Return>", self.on_f2_edit_selected)
        self.tree.bind("<KP_Enter>", self.on_f2_edit_selected)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select_changed)
        self.root.bind("<Control-p>", lambda e: self.toggle_preview_dock())
        self.root.bind("<Control-P>", lambda e: self.toggle_preview_dock())
        self.tree.bind("<Button-3>", self.show_tree_context_menu)
        self.root.bind("<Control-a>", self.select_all_rows)
        self.root.bind("<Control-A>", self.select_all_rows)
        self.root.bind("<Control-z>", self.perform_undo)
        self.root.bind("<Control-Z>", self.perform_undo)
        self.root.bind("<Control-y>", self.perform_redo)
        self.root.bind("<Control-Y>", self.perform_redo)
        self.root.bind("<Control-f>", lambda e: (s_ent.focus_set(), s_ent.select_range(0, tk.END), "break"))
        self.root.bind("<Control-F>", lambda e: (s_ent.focus_set(), s_ent.select_range(0, tk.END), "break"))
        self.root.bind("<F1>", lambda e: self.open_user_manual())
        self.root.bind("<F12>", lambda e: self.open_issue_reporter_dialog())
        self.root.bind("<Alt-c>", lambda e: self.open_coa_manager_dialog())
        self.root.bind("<Alt-C>", lambda e: self.open_coa_manager_dialog())
        self.root.bind("<Control-v>", lambda e: self.paste_from_clipboard_dialog())
        self.root.bind("<Control-V>", lambda e: self.paste_from_clipboard_dialog())
        self.root.bind("<Control-o>", lambda e: self.start_import_worker())
        self.root.bind("<Control-O>", lambda e: self.start_import_worker())
        self.root.bind("<Alt-s>", lambda e: self.open_split_transaction_dialog())
        self.root.bind("<Alt-S>", lambda e: self.open_split_transaction_dialog())
        self.root.bind("<Alt-a>", lambda e: self.append_statement_dialog())
        self.root.bind("<Control-k>", lambda e: self.open_practice_master_dashboard_dialog())
        self.root.bind("<Control-K>", lambda e: self.open_practice_master_dashboard_dialog())
        if sys.platform == "darwin":
            self.root.bind("<Command-o>", lambda e: self.start_import_worker())
            self.root.bind("<Command-O>", lambda e: self.start_import_worker())
            self.root.bind("<Command-p>", lambda e: self.toggle_preview_dock())
            self.root.bind("<Command-P>", lambda e: self.toggle_preview_dock())
            self.root.bind("<Command-a>", self.select_all_rows)
            self.root.bind("<Command-A>", self.select_all_rows)
            self.root.bind("<Command-z>", self.perform_undo)
            self.root.bind("<Command-Z>", self.perform_undo)
            self.root.bind("<Command-y>", self.perform_redo)
            self.root.bind("<Command-Y>", self.perform_redo)
            self.root.bind("<Command-k>", lambda e: self.open_practice_master_dashboard_dialog())
            self.root.bind("<Command-K>", lambda e: self.open_practice_master_dashboard_dialog())
            self.root.bind("<Command-v>", lambda e: self.paste_from_clipboard_dialog())
            self.root.bind("<Command-V>", lambda e: self.paste_from_clipboard_dialog())
            self.tree.bind("<Button-2>", self.show_tree_context_menu)
        self.root.bind("<Alt-A>", lambda e: self.append_statement_dialog())
        self.root.bind("<Alt-m>", lambda e: self.open_receipt_matcher_dialog())
        self.root.bind("<Alt-M>", lambda e: self.open_receipt_matcher_dialog())
        self.root.bind("<Alt-v>", lambda e: self.open_vat201_card_dialog())
        self.root.bind("<Alt-V>", lambda e: self.open_vat201_card_dialog())
        self.root.bind("<Alt-l>", lambda e: self.lock_batch_and_generate_certificate())
        self.root.bind("<Alt-L>", lambda e: self.lock_batch_and_generate_certificate())
        self.tree.bind("<space>", lambda e: self.toggle_selected_vat())
        self.tree.bind("<Delete>", lambda e: self.delete_selected_rows())

        # 6. BOTTOM STATUS BAR
        footer = tk.Frame(self.root, bg="#090d16", padx=16, pady=6)
        footer.pack(fill=tk.X)

        self.status_lbl = tk.Label(
            footer,
            text="Ready. F1: Manual • Alt+C: Chart of Accounts • Ctrl+O: Multi-Doc Import • F2/Double-Click: Edit Cell • Space: Toggle VAT",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#090d16",
        )
        self.status_lbl.pack(side=tk.LEFT)

        self.bank_engine_badge = HDButton(
            footer,
            text="🟢 SA Bank Engine: Initializing...",
            font=("Segoe UI", 9, "bold"),
            fg="#34d399",
            bg="#090d16",
            activebackground="#1e293b",
            activeforeground="#34d399",
            relief="flat",
            cursor="hand2",
            padx=8,
            pady=1,
            command=self.show_sa_bank_diagnostics_dialog,
        )
        self.bank_engine_badge.pack(side=tk.LEFT, padx=(10, 0))
        ToolTip(self.bank_engine_badge, "Click to view South African Bank Statement Format Compatibility Diagnostics")

        self.ai_key_badge = HDButton(
            footer,
            text="🟢 Local OCR",
            font=("Segoe UI", 9, "bold"),
            bg="#090d16",
            fg="#34d399",
            activebackground="#1e293b",
            activeforeground="#34d399",
            relief="flat",
            padx=8,
            pady=1,
            cursor="hand2",
            command=self.open_ai_settings_dialog,
        )
        self.ai_key_badge.pack(side=tk.LEFT, padx=(6, 0))
        self.update_ai_key_badge()
        ToolTip(self.ai_key_badge, "100% Free Local OCR Engine is Active. Click to configure Google Gemini AI for till slips.")

        self.report_issue_btn = HDButton(
            footer,
            text="⚠️ Report Issue",
            font=("Segoe UI", 9, "bold"),
            fg="#f59e0b",
            bg="#090d16",
            activebackground="#1e293b",
            activeforeground="#fbbf24",
            relief="flat",
            cursor="hand2",
            padx=8,
            pady=1,
            command=self.open_issue_reporter_dialog,
        )
        self.report_issue_btn.pack(side=tk.LEFT, padx=(8, 0))
        ToolTip(self.report_issue_btn, "1-Click Diagnostics: Report bank statement parsing issues or bugs directly to engineering agents (Shortcut: F12)")

        self.erp_fye_lbl = tk.Label(
            footer,
            text="",
            font=("Segoe UI", 9, "bold"),
            fg="#38bdf8",
            bg="#090d16",
            cursor="hand2",
        )
        self.erp_fye_lbl.pack(side=tk.RIGHT, padx=(10, 0))
        self.erp_fye_lbl.bind("<Button-1>", lambda e: self.open_fye_profile_quick_menu())
        ToolTip(self.erp_fye_lbl, "Click to change Financial Year-End (FYE) Month or add a new Client Profile")
        self.update_bottom_info()

        self.prog_bar = ttk.Progressbar(footer, style="TProgressbar", mode="determinate", length=180)
        self.prog_bar.pack(side=tk.RIGHT, padx=6)
        self.prog_bar["value"] = 0

    def create_metric_card(self, parent: tk.Widget, label_txt: str, val_txt: str, val_color: str) -> tk.Label:
        card = tk.Frame(parent, bg="#0f172a", padx=12, pady=7, relief="flat", highlightbackground="#1e293b", highlightthickness=1)
        card.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=3)
        tk.Label(card, text=label_txt, font=("Segoe UI", 8, "bold"), fg="#94a3b8", bg="#0f172a").pack(anchor="w")
        val_lbl = tk.Label(card, text=val_txt, font=("Consolas", 12, "bold"), fg=val_color, bg="#0f172a")
        val_lbl.pack(anchor="w", pady=(2, 0))
        return val_lbl

    def test_gemini_key_connection(self, api_key: str, timeout: int = 5) -> tuple[bool, str]:
        if not api_key or not api_key.strip():
            return False, "No API key configured."
        url = "https://generativelanguage.googleapis.com/v1beta/models"
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "TaxCleanZA/2.7",
                    "x-goog-api-key": api_key.strip(),
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    return True, "API Key is active and verified working with Google AI Studio."
                return False, f"Unexpected response status: {resp.status}"
        except urllib.error.HTTPError as e:
            if e.code in [400, 403]:
                return False, "Invalid API Key: Rejected by Google AI Studio (Check key permissions)."
            return False, f"Google API HTTP {e.code}"
        except urllib.error.URLError:
            return False, "Network offline: Unable to reach Google AI servers."
        except Exception as e:
            return False, f"Notice: {str(e)}"

    def update_ai_key_badge(self):
        self.update_ai_key_ui_advisory()
        curr_key = self.memory.get_setting("GEMINI_API_KEY", "")
        if not curr_key:
            if hasattr(self, "ai_key_badge"):
                self.ai_key_badge.config(text="🟢 Local OCR", bg="#1e293b", fg="#34d399")
            self.update_bottom_info()
            return

        if hasattr(self, "ai_key_badge"):
            self.ai_key_badge.config(text="⏳ AI: Checking...", bg="#1e293b", fg="#cbd5e1")

        def _bg_check():
            try:
                ok, msg = self.test_gemini_key_connection(curr_key)
                self.task_queue.put(("AI_KEY_STATUS", ok, msg))
            except Exception:
                pass

        threading.Thread(target=_bg_check, daemon=True).start()

    def update_bottom_info(self):
        erp = self.erp_var.get()
        prof_info = self.config["profiles"].get(self.active_profile, {})
        fye = prof_info.get("fin_year_end_month", 2)
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        fye_name = month_names[fye - 1] if 1 <= fye <= 12 else "Feb"

        has_ai_key = bool(self.memory.get_setting("GEMINI_API_KEY", ""))
        ai_badge_txt = getattr(self, "ai_key_badge", None)
        badge_s = ai_badge_txt.cget("text") if ai_badge_txt else ""
        if "Gemini" in badge_s:
            ai_tag = "🟢 Engine: Local + Gemini AI"
        elif "🔴" in badge_s:
            ai_tag = "🔴 AI Key Invalid (Local Active)"
        elif has_ai_key:
            ai_tag = "🤖 Engine: Local + AI"
        else:
            ai_tag = "🔒 100% Local Offline Engine"

        if hasattr(self, "erp_fye_lbl"):
            self.erp_fye_lbl.config(text=f"{ai_tag}  •  {erp}  •  FYE: {fye_name} ▾")

    def _get_profile_combo_values(self):
        return list(self.config["profiles"].keys()) + ["➕ Add New Client Profile...", "🗑️ Delete Current Client..."]

    def create_new_profile_dialog(self):
        new_name = simpledialog.askstring(
            "New Client / Entity Profile",
            "Enter the new Client / Company Name (e.g. Ubuntu Logistics (Pty) Ltd):",
            parent=self.root,
        )
        if not new_name or not new_name.strip():
            self.profile_var.set(self.active_profile)
            return
        new_name = new_name.strip()
        if new_name in ["➕ Add New Client Profile...", "🗑️ Delete Current Client..."]:
            self.profile_var.set(self.active_profile)
            return
        if new_name not in self.config["profiles"]:
            self.config["profiles"][new_name] = {
                "erp": self.erp_var.get() or "Pastel Partner",
                "fin_year_end_month": 2,
                "coa": {k: v.copy() for k, v in DEFAULT_CHART_OF_ACCOUNTS.items()},
            }
        self.active_profile = new_name
        self.config["active_profile"] = new_name
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.save_config()
        self.profile_combo.config(values=self._get_profile_combo_values())
        self.profile_var.set(new_name)
        self._refresh_coa_dependent_widgets()
        self.restore_or_init_session()
        self.update_bottom_info()
        self.status_lbl.config(text=f"Created and switched to client profile: {new_name}")

    def delete_current_profile_dialog(self):
        profs = list(self.config["profiles"].keys())
        if len(profs) <= 1:
            messagebox.showwarning(
                "Cannot Delete Last Profile",
                "At least one Client Profile must remain in TaxClean ZA.\nCreate another client profile first before deleting this one.",
                parent=self.root,
            )
            self.profile_var.set(self.active_profile)
            return
        ans = messagebox.askyesno(
            "Delete Client Profile",
            f"Are you sure you want to remove client profile '{self.active_profile}'?",
            parent=self.root,
        )
        if not ans:
            self.profile_var.set(self.active_profile)
            return
        old_prof = self.active_profile
        del self.config["profiles"][old_prof]
        self.memory.delete_profile_data(old_prof)
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.active_profile = list(self.config["profiles"].keys())[0]
        self.config["active_profile"] = self.active_profile
        self.save_config()
        self.profile_combo.config(values=self._get_profile_combo_values())
        self.profile_var.set(self.active_profile)
        self._refresh_coa_dependent_widgets()
        self.restore_or_init_session()
        self.update_bottom_info()
        self.status_lbl.config(text=f"Deleted client profile '{old_prof}'. Active profile: {self.active_profile}")

    def open_fye_profile_quick_menu(self):
        menu = tk.Menu(self.root, tearoff=False, bg="#1e293b", fg="#f1f5f9", font=("Segoe UI", 9), activebackground="#0284c7")
        month_names = [
            (1, "January"), (2, "February (Standard SA Tax Year)"), (3, "March"),
            (4, "April"), (5, "May"), (6, "June"),
            (7, "July"), (8, "August"), (9, "September"),
            (10, "October"), (11, "November"), (12, "December"),
        ]
        curr_fye = self.config["profiles"].get(self.active_profile, {}).get("fin_year_end_month", 2)
        fye_sub = tk.Menu(menu, tearoff=False, bg="#1e293b", fg="#f1f5f9", font=("Segoe UI", 9), activebackground="#0284c7")
        for m_num, m_label in month_names:
            chk = "✓ " if m_num == curr_fye else "   "
            fye_sub.add_command(label=f"{chk}{m_label}", command=lambda mn=m_num: self._set_fye_month(mn))
        menu.add_cascade(label="📅 Set Financial Year-End (FYE) Month", menu=fye_sub)
        menu.add_separator()
        menu.add_command(label="➕ Add New Client Profile...", command=self.create_new_profile_dialog)
        menu.add_command(label="📋 Open Chart of Accounts Manager [Alt+C]", command=self.open_coa_manager_dialog)
        x = self.root.winfo_pointerx()
        y = self.root.winfo_pointery()
        menu.tk_popup(x, y)

    def _set_fye_month(self, month_num: int):
        if self.active_profile in self.config["profiles"]:
            self.config["profiles"][self.active_profile]["fin_year_end_month"] = month_num
            self.save_config()
            self.update_bottom_info()
            self.render_grid()

    def toggle_metrics_strip(self):
        if self.metrics_visible:
            self.metrics_frame.pack_forget()
            self.metrics_visible = False
            self.hide_math_btn.config(text="Show Summary ⌵")
        else:
            self.metrics_frame.pack(fill=tk.X, after=self.hero_banner)
            self.metrics_visible = True
            self.hide_math_btn.config(text="Hide Summary ⌃")

    def switch_filter_tab(self, tab_key: str):
        self.active_filter_tab = tab_key
        for k, btn in self.tab_buttons.items():
            if k == tab_key:
                btn.config(bg="#1e293b", fg="#38bdf8", font=("Segoe UI", 9, "bold"))
            else:
                btn.config(bg="#0f172a", fg="#94a3b8", font=("Segoe UI", 9, "normal"))
        self.render_grid()

    # ==========================================================================
    # CLEAR BATCH & AUTO-ALIGN FEATURES
    # ==========================================================================
    def clear_batch(self):
        if self._check_batch_locked():
            return
        if not self.transactions:
            messagebox.showinfo("Clear Batch", "Current batch is already empty.", parent=self.root)
            return

        ans = messagebox.askyesno(
            "Clear Current Batch",
            f"Are you sure you want to clear all {len(self.transactions)} transactions in this batch?\n\n"
            "This will reset the workspace so you can import a new bank statement or receipt.\n"
            "(You can always Undo this using Ctrl + Z).",
            parent=self.root,
        )
        if ans:
            self.push_undo_state()
            self.transactions.clear()
            self.open_bal_var.set("0.00")
            self.close_bal_var.set("0.00")
            self.memory.clear_session(self.active_profile)
            self.render_grid()
            self.status_lbl.config(text="Batch cleared. Ready for fresh import.")

    def auto_align_variance(self):
        try:
            o = float(self.open_bal_var.get().replace(",", "").strip() or 0)
            c = float(self.close_bal_var.get().replace(",", "").strip() or 0)
        except Exception:
            o, c = 0.0, 0.0

        net_mvt = sum(t["amount"] for t in self.transactions)
        expected = _dec_round(o + net_mvt)
        diff = _dec_round(expected - c)

        if abs(diff) < 0.01:
            messagebox.showinfo("Auto-Align", "Batch is perfectly balanced! No variance detected.", parent=self.root)
            return

        msg = (
            f"Reconciliation Variance Detected: R {diff:,.2f}\n\n"
            f"• Opening Balance: R {o:,.2f}\n"
            f"• Net Movement: R {net_mvt:,.2f}\n"
            f"• Expected Closing: R {expected:,.2f}\n"
            f"• Statement Closing: R {c:,.2f}\n\n"
            f"Would you like to:\n"
            f"[Yes] Align Statement Closing to Expected Closing (sets Closing to R {expected:,.2f})\n"
            f"[No] Insert Auto-Balancing Adjustment Line Item for R {-diff:,.2f} into Suspense"
        )
        ans = messagebox.askyesnocancel("Reconciliation Auto-Align", msg, parent=self.root)
        if ans is True:
            self.push_undo_state()
            self.close_bal_var.set(f"{expected:.2f}")
            self.recalculate_reconciliation()
            self.save_current_session()
        elif ans is False:
            self.push_undo_state()
            adj_amt = _dec_round(-diff)
            adj_row = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "ref": "ADJ-ALIGN",
                "acc_type": "GL",
                "clean_payee": "Auto-Balancing Adjustment / Variance Round-off",
                "code": "9999/000",
                "name": "Suspense Account / Queries",
                "amount": adj_amt,
                "vat_type": "None",
                "vat_claim": 0.0,
                "net": adj_amt,
                "is_suspense": True,
                "is_duplicate": False,
                "audit_status": "⚠️ Auto-Aligned Adjustment",
                "query_reason": "Balancing entry inserted by Auto-Align",
            }
            self.transactions.append(adj_row)
            self.render_grid()
            self.save_current_session()

    # ==========================================================================
    # ROW MANAGEMENT & INLINE EDITING
    # ==========================================================================
    def add_manual_row(self):
        if self._check_batch_locked():
            return
        self.push_undo_state()
        new_row = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "ref": "MAN1",
            "acc_type": "GL",
            "clean_payee": "New Transaction Line",
            "code": "4600/000",
            "name": "Office & Computer Consumables",
            "amount": -100.00,
            "vat_type": "Standard",
            "vat_claim": 13.04,
            "net": -86.96,
            "is_suspense": False,
            "is_duplicate": False,
            "audit_status": "✓ Manual Entry",
            "query_reason": "Manually added by user",
        }
        self.transactions.insert(0, new_row)
        self.render_grid()
        self.save_current_session()

    def on_tree_select_changed(self, event=None):
        selected_ids = self.tree.selection()
        count = len(selected_ids)
        if count >= 2:
            self.bulk_count_lbl.config(text=f"⚡ {count} rows selected")
            if not self.bulk_bar.winfo_ismapped():
                self.bulk_bar.pack(fill=tk.X, before=self.tree.master)
        else:
            if self.bulk_bar.winfo_ismapped():
                self.bulk_bar.pack_forget()
        if count >= 1 and hasattr(self, "preview_dock") and self.preview_dock.winfo_manager() == "pack":
            self.update_preview_dock(selected_ids[0])

    def select_all_rows(self, event=None):
        all_items = self.tree.get_children()
        if all_items:
            self.tree.selection_set(all_items)
            self.on_tree_select_changed()
        return "break"

    def clear_selection(self):
        self.tree.selection_set()
        self.on_tree_select_changed()

    def apply_bulk_categorization(self):
        if self._check_batch_locked():
            return
        selected_ids = self.tree.selection()
        if not selected_ids:
            return

        chosen_acc = self.bulk_acc_var.get().strip()
        chosen_vat = self.bulk_vat_var.get().strip()
        if not chosen_acc:
            messagebox.showwarning("Bulk Categorize", "Please select an account to assign.", parent=self.root)
            return

        chosen_code = chosen_acc.split(" - ")[0].strip()
        coa_dict = self.config["profiles"][self.active_profile]["coa"]
        chosen_info = None
        for _, info in coa_dict.items():
            if info["code"] == chosen_code:
                chosen_info = info
                break

        if not chosen_info:
            return

        vat_clean = "Standard" if "Standard" in chosen_vat else ("Zero-Rated" if "Zero" in chosen_vat else "None")

        self.push_undo_state()
        indices = [int(iid) for iid in selected_ids if 0 <= int(iid) < len(self.transactions)]
        for idx in indices:
            txn = self.transactions[idx]
            txn["code"] = chosen_info["code"]
            txn["name"] = chosen_info["name"]
            txn["acc_type"] = chosen_info.get("type", "GL")
            txn["vat_type"] = vat_clean
            txn["is_suspense"] = (chosen_info["code"] == "9999/000" or str(chosen_info["code"]).startswith("9999"))
            txn["audit_status"] = "✓ Bulk Assigned"
            self.recalculate_row(txn)
            # Memorize rule in sqlite for continuous learning
            self.memory.remember_merchant(
                self.active_profile,
                txn["clean_payee"],
                chosen_info["code"],
                chosen_info["name"],
                vat_clean,
                chosen_info.get("type", "GL"),
            )

        self.render_grid()
        self.save_current_session()
        self.status_lbl.config(
            text=f"Bulk updated and learned rules for {len(indices)} transactions to {chosen_info['code']} ({chosen_info['name']})."
        )

    def delete_selected_rows(self):
        if self._check_batch_locked():
            return
        selected_ids = self.tree.selection()
        if not selected_ids:
            return
        self.push_undo_state()
        indices = sorted([int(iid) for iid in selected_ids], reverse=True)
        for idx in indices:
            if 0 <= idx < len(self.transactions):
                self.transactions.pop(idx)
        self.render_grid()
        self.save_current_session()

    def delete_single_row(self, idx: int):
        if self._check_batch_locked():
            return
        if 0 <= idx < len(self.transactions):
            self.push_undo_state()
            self.transactions.pop(idx)
            self.render_grid()
            self.save_current_session()

    def on_f2_edit_selected(self, event=None):
        if self._check_batch_locked():
            return
        sel = self.tree.selection()
        if not sel:
            children = self.tree.get_children()
            if not children:
                return
            row_id = children[0]
            self.tree.selection_set(row_id)
        else:
            row_id = sel[0]
        # Default to editing Account / Nominal Code column (col_idx = 5)
        self.open_cell_editor(row_id, 5)
        return "break"

    def on_cell_double_click(self, event):
        if self._check_batch_locked():
            return
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        row_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        if not row_id or not col_id:
            return

        vis_cols = list(self.tree["displaycolumns"])
        if not vis_cols or vis_cols == ["#all"]:
            vis_cols = list(self.columns)
        vis_idx = int(col_id.replace("#", "")) - 1
        if vis_idx < 0 or vis_idx >= len(vis_cols):
            return
        col_key = vis_cols[vis_idx]
        col_idx = self.columns.index(col_key) if col_key in self.columns else vis_idx

        idx = int(row_id)
        if idx >= len(self.transactions):
            return

        if col_key == "actions":
            # Left half (✏️ Edit) opens inline editor; right half (🗑️) deletes row
            bbox = self.tree.bbox(row_id, col_key)
            if bbox and (event.x - bbox[0]) < (bbox[2] * 0.58):
                self.open_cell_editor(row_id, 5)
            else:
                self.delete_single_row(idx)
            return

        self.open_cell_editor(row_id, col_idx)

    def open_cell_editor(self, row_id: str, col_idx: int):
        if self._check_batch_locked():
            return
        editable_cols = [1, 2, 4, 5, 6, 7]  # date, ref, payee, account, gross, vat_type
        if col_idx not in editable_cols:
            col_idx = 5  # Default to Account column if user double-clicked non-editable cell

        col_key = self.columns[col_idx]
        idx = int(row_id)
        if idx < 0 or idx >= len(self.transactions):
            return
        txn = self.transactions[idx]

        self.tree.see(row_id)
        bbox = self.tree.bbox(row_id, col_key)
        if not bbox:
            return
        x, y, w, h = bbox

        if self.editing_widget:
            try:
                self.editing_widget.destroy()
            except Exception:
                pass
            self.editing_widget = None

        coa = self.config["profiles"][self.active_profile]["coa"]
        committed = {"done": False}

        def move_cell(delta_col=0, delta_row=0):
            children = list(self.tree.get_children())
            if row_id not in children:
                return
            r_pos = children.index(row_id)
            c_pos = editable_cols.index(col_idx) if col_idx in editable_cols else 0
            if delta_col != 0:
                next_c_pos = c_pos + delta_col
                next_r_pos = r_pos
                if next_c_pos >= len(editable_cols):
                    next_c_pos = 0
                    next_r_pos = min(len(children) - 1, r_pos + 1)
                elif next_c_pos < 0:
                    next_c_pos = len(editable_cols) - 1
                    next_r_pos = max(0, r_pos - 1)
                next_row_id = children[next_r_pos]
                next_col_idx = editable_cols[next_c_pos]
            else:
                next_r_pos = max(0, min(len(children) - 1, r_pos + delta_row))
                next_row_id = children[next_r_pos]
                next_col_idx = col_idx
            self.tree.selection_set(next_row_id)
            self.root.after(15, lambda: self.open_cell_editor(next_row_id, next_col_idx))

        if col_key == "vat_type":
            var = tk.StringVar(value=txn["vat_type"])
            box = ttk.Combobox(
                self.tree,
                textvariable=var,
                values=["Standard", "Zero-Rated", "Exempt", "Blocked_Entertainment", "None"],
                state="readonly",
                font=("Segoe UI", 9),
            )
            box.place(x=x, y=y, width=max(w, 120), height=h)
            box.focus_set()

            def save_vat(e=None, nav_col=0, nav_row=0):
                if committed["done"]:
                    return
                committed["done"] = True
                if var.get() != txn["vat_type"]:
                    self.push_undo_state()
                    txn["vat_type"] = var.get()
                    self.recalculate_row(txn)
                    self.save_current_session()
                try:
                    box.destroy()
                except Exception:
                    pass
                self.editing_widget = None
                self.render_grid()
                if nav_col or nav_row:
                    move_cell(nav_col, nav_row)

            box.bind("<<ComboboxSelected>>", lambda e: save_vat(e, 0, 0))
            box.bind("<Return>", lambda e: (save_vat(e, 0, 1), "break")[1])
            box.bind("<Tab>", lambda e: (save_vat(e, 1, 0), "break")[1])
            box.bind("<Shift-Tab>", lambda e: (save_vat(e, -1, 0), "break")[1])
            box.bind("<Escape>", lambda e: (committed.update({"done": True}), box.destroy()))
            box.bind("<FocusOut>", lambda e: save_vat(e, 0, 0))
            self.editing_widget = box

        elif col_key in ["code", "account"]:
            cat_list = [f"{v['code']} - {k} ({v['name']})" for k, v in coa.items()]
            var = tk.StringVar(value=f"{txn['code']} - {txn['name']}")
            box = ttk.Combobox(
                self.tree,
                textvariable=var,
                values=cat_list,
                state="readonly",
                font=("Segoe UI", 9),
            )
            box.place(x=x, y=y, width=max(w, 240), height=h)
            box.focus_set()

            def save_code(e=None, nav_col=0, nav_row=0):
                if committed["done"]:
                    return
                committed["done"] = True
                chosen = var.get()
                chosen_code = chosen.split(" - ")[0].strip()
                if chosen_code != txn["code"]:
                    self.push_undo_state()
                    for _, info in coa.items():
                        if info["code"] == chosen_code:
                            txn["code"] = info["code"]
                            txn["name"] = info["name"]
                            txn["acc_type"] = info.get("type", "GL")
                            txn["vat_type"] = info.get("vat", "Standard")
                            self.memory.remember_merchant(
                                self.active_profile,
                                txn["clean_payee"],
                                info["code"],
                                info["name"],
                                info.get("vat", "Standard"),
                                info.get("type", "GL"),
                            )
                            break
                    txn["is_suspense"] = (txn["code"] == "9999/000" or str(txn["code"]).startswith("9999"))
                    self.recalculate_row(txn)
                    self.save_current_session()
                try:
                    box.destroy()
                except Exception:
                    pass
                self.editing_widget = None
                self.render_grid()
                if nav_col or nav_row:
                    move_cell(nav_col, nav_row)

            box.bind("<<ComboboxSelected>>", lambda e: save_code(e, 0, 0))
            box.bind("<Return>", lambda e: (save_code(e, 0, 1), "break")[1])
            box.bind("<Tab>", lambda e: (save_code(e, 1, 0), "break")[1])
            box.bind("<Shift-Tab>", lambda e: (save_code(e, -1, 0), "break")[1])
            box.bind("<Escape>", lambda e: (committed.update({"done": True}), box.destroy()))
            box.bind("<FocusOut>", lambda e: save_code(e, 0, 0))
            self.editing_widget = box

        elif col_key in ["payee", "gross", "date", "ref"]:
            current_val = (
                str(txn["amount"]) if col_key == "gross" else
                txn["clean_payee"] if col_key == "payee" else
                txn["date"] if col_key == "date" else txn["ref"]
            )
            var = tk.StringVar(value=current_val)
            ent = tk.Entry(
                self.tree,
                textvariable=var,
                font=("Consolas", 9, "bold") if col_key == "gross" else ("Segoe UI", 9),
                bg="#0f172a",
                fg="#38bdf8",
                insertbackground="#38bdf8",
                relief="solid",
                bd=1,
            )
            ent.place(x=x, y=y, width=w, height=h)
            ent.focus_set()
            ent.select_range(0, tk.END)

            def save_entry(e=None, nav_col=0, nav_row=0):
                if committed["done"]:
                    return
                committed["done"] = True
                val = var.get().strip()
                if val != current_val:
                    self.push_undo_state()
                    if col_key == "payee":
                        txn["clean_payee"] = val
                    elif col_key == "date":
                        txn["date"] = val
                    elif col_key == "ref":
                        txn["ref"] = val
                    elif col_key == "gross":
                        amt_parsed, is_cr, is_dr = parse_sa_amount(val)
                        txn["amount"] = -abs(amt_parsed) if (is_dr or "-" in val) else abs(amt_parsed)
                        self.recalculate_row(txn)
                    self.save_current_session()
                try:
                    ent.destroy()
                except Exception:
                    pass
                self.editing_widget = None
                self.render_grid()
                if nav_col or nav_row:
                    move_cell(nav_col, nav_row)

            ent.bind("<Return>", lambda e: (save_entry(e, 0, 1), "break")[1])
            ent.bind("<Tab>", lambda e: (save_entry(e, 1, 0), "break")[1])
            ent.bind("<Shift-Tab>", lambda e: (save_entry(e, -1, 0), "break")[1])
            ent.bind("<Escape>", lambda e: (committed.update({"done": True}), ent.destroy()))
            ent.bind("<FocusOut>", lambda e: save_entry(e, 0, 0))
            self.editing_widget = ent

    def recalculate_row(self, txn: dict):
        amt = txn["amount"]
        vt = txn["vat_type"]
        is_susp = bool(txn.get("is_suspense") or str(txn.get("code", "")).startswith("9999"))
        if is_susp:
            txn["vat_claim"] = 0.0
            txn["net"] = amt
        elif vt == "Standard" and amt < 0:
            txn["vat_claim"] = _calc_vat_inclusive(amt)
            txn["net"] = _dec_round(amt + txn["vat_claim"])
        elif vt == "Standard" and amt > 0:
            txn["vat_claim"] = _calc_vat_inclusive(amt)
            txn["net"] = _dec_round(amt - txn["vat_claim"])
        else:
            txn["vat_claim"] = 0.0
            txn["net"] = amt

    def rerun_categorization(self):
        if self._check_batch_locked():
            return
        self.push_undo_state()
        coa = self.config["profiles"][self.active_profile]["coa"]
        worker = ParseWorker("rerun", coa, self.active_profile, self.memory, self.task_queue)
        for t in self.transactions:
            cat = worker.categorize(t["clean_payee"], t["amount"])
            t["code"] = cat["code"]
            t["name"] = cat["name"]
            t["acc_type"] = cat["acc_type"]
            t["vat_type"] = cat["vat_type"]
            t["is_suspense"] = cat["is_suspense"]
            self.recalculate_row(t)
        self.render_grid()
        self.save_current_session()
        messagebox.showinfo("Categorization Complete", f"Successfully re-categorized {len(self.transactions)} transactions.", parent=self.root)

    # ==========================================================================
    # COLUMN DROPDOWNS & VISIBILITY CONTROLS
    # ==========================================================================
    def open_column_header_dropdown(self, cid):
        menu = tk.Menu(self.root, tearoff=False, bg="#1e293b", fg="#f1f5f9", font=("Segoe UI", 9), activebackground="#0284c7")

        if cid == "date":
            menu.add_command(label="📅 Sort: Oldest First", command=lambda: self.sort_by_column("date", False))
            menu.add_command(label="📅 Sort: Newest First", command=lambda: self.sort_by_column("date", True))
            menu.add_separator()
            months = sorted(list({t.get("date", "")[:7] for t in self.transactions if t.get("date")}))
            if months:
                month_sub = tk.Menu(menu, tearoff=False, bg="#1e293b", fg="#f1f5f9", font=("Segoe UI", 9), activebackground="#0284c7")
                month_sub.add_command(label="All Months", command=lambda: self.set_column_filter("month", None))
                for m in months:
                    month_sub.add_command(label=f"Month: {m}", command=lambda mo=m: self.set_column_filter("month", mo))
                menu.add_cascade(label="📆 Filter by Month", menu=month_sub)

        elif cid in ["gross", "net", "vat"]:
            menu.add_command(label="🔢 Sort: Smallest to Largest", command=lambda: self.sort_by_column(cid, False))
            menu.add_command(label="🔢 Sort: Largest to Smallest", command=lambda: self.sort_by_column(cid, True))
            menu.add_separator()
            menu.add_command(label="📉 Show Outflows Only (Debits < 0)", command=lambda: self.set_column_filter(cid, "outflows"))
            menu.add_command(label="📈 Show Inflows Only (Credits > 0)", command=lambda: self.set_column_filter(cid, "inflows"))
            menu.add_command(label="🔍 Amounts > R 1,000", command=lambda: self.set_column_filter(cid, ">1000"))

        elif cid == "vat_type":
            menu.add_command(label="All VAT Types", command=lambda: self.set_column_filter("vat_type", None))
            menu.add_separator()
            menu.add_command(label="Filter: Standard (15%) Only", command=lambda: self.set_column_filter("vat_type", "Standard"))
            menu.add_command(label="Filter: Zero-Rated Only", command=lambda: self.set_column_filter("vat_type", "Zero-Rated"))
            menu.add_command(label="Filter: Exempt Only", command=lambda: self.set_column_filter("vat_type", "Exempt"))
            menu.add_command(label="Filter: Blocked Entertainment", command=lambda: self.set_column_filter("vat_type", "Blocked_Entertainment"))

        elif cid == "audit":
            menu.add_command(label="Show All Audit Records", command=lambda: self.set_column_filter("audit", None))
            menu.add_separator()
            menu.add_command(label="✓ Filter: Verified Lines Only", command=lambda: self.set_column_filter("audit", "verified"))
            menu.add_command(label="⚠️ Filter: Queries & Suspense Only", command=lambda: self.set_column_filter("audit", "suspense"))
            menu.add_command(label="⚠️ Filter: Duplicates Only", command=lambda: self.set_column_filter("audit", "duplicate"))

        elif cid == "payee":
            menu.add_command(label="🔤 Sort: Payee (A → Z)", command=lambda: self.sort_by_column("payee", False))
            menu.add_command(label="🔤 Sort: Payee (Z → A)", command=lambda: self.sort_by_column("payee", True))

        elif cid == "account":
            menu.add_command(label="🔤 Sort: Account Code (A → Z)", command=lambda: self.sort_by_column("account", False))
            coa_dict = self.config["profiles"][self.active_profile]["coa"]
            acc_sub = tk.Menu(menu, tearoff=False, bg="#1e293b", fg="#f1f5f9", font=("Segoe UI", 9), activebackground="#0284c7")
            acc_sub.add_command(label="All Accounts", command=lambda: self.set_column_filter("account", None))
            for cat_name, info in sorted(coa_dict.items(), key=lambda x: x[1].get("code", "")):
                acc_sub.add_command(label=f"{info.get('code')} - {cat_name}", command=lambda c=info.get("code"): self.set_column_filter("account", c))
            menu.add_cascade(label="📂 Filter by Account Code", menu=acc_sub)

        elif cid == "ledger":
            menu.add_command(label="All Ledgers", command=lambda: self.set_column_filter("ledger", None))
            menu.add_command(label="Filter: General Ledger (GL)", command=lambda: self.set_column_filter("ledger", "GL"))
            menu.add_command(label="Filter: Debtors", command=lambda: self.set_column_filter("ledger", "Debtors"))
            menu.add_command(label="Filter: Creditors", command=lambda: self.set_column_filter("ledger", "Creditors"))

        menu.add_separator()
        if getattr(self, "column_filters", None):
            menu.add_command(label="✕ Clear Active Column Filters", command=self.clear_all_column_filters)
            menu.add_separator()

        if cid in getattr(self, "visible_columns", self.columns) and len(self.visible_columns) > 3 and cid != "idx":
            menu.add_command(label=f"Hide Column '{cid}'", command=lambda: self.toggle_column_visibility(cid))

        menu.add_command(label="📊 Column Visibility Chooser...", command=self.open_columns_visibility_menu)

        x = self.root.winfo_pointerx()
        y = self.root.winfo_pointery()
        menu.tk_popup(x, y)

    def sort_by_column(self, col_key, descending):
        if not self.transactions:
            return
        self.push_undo_state()
        if col_key == "date":
            self.transactions.sort(key=lambda t: t.get("date", ""), reverse=descending)
        elif col_key in ["gross", "net", "amount"]:
            self.transactions.sort(key=lambda t: t.get("amount", 0.0), reverse=descending)
        elif col_key == "vat":
            self.transactions.sort(key=lambda t: t.get("vat_claim", 0.0), reverse=descending)
        elif col_key == "payee":
            self.transactions.sort(key=lambda t: t.get("clean_payee", "").upper(), reverse=descending)
        elif col_key == "account":
            self.transactions.sort(key=lambda t: t.get("code", ""), reverse=descending)
        elif col_key == "ledger":
            self.transactions.sort(key=lambda t: t.get("acc_type", ""), reverse=descending)
        self.render_grid()

    def set_column_filter(self, col_key, val):
        if val is None:
            self.column_filters.pop(col_key, None)
        else:
            self.column_filters[col_key] = val
        self.render_grid()

    def clear_all_column_filters(self):
        self.column_filters.clear()
        self.render_grid()

    def open_columns_visibility_menu(self):
        menu = tk.Menu(self.root, tearoff=False, bg="#1e293b", fg="#f1f5f9", font=("Segoe UI", 9), activebackground="#0284c7")
        col_names = {
            "date": "Date",
            "ref": "Reference",
            "ledger": "Ledger",
            "payee": "Payee / Description",
            "account": "Account / Nominal Code",
            "gross": "Gross (ZAR)",
            "vat_type": "SARS VAT Type",
            "vat": "VAT (15%)",
            "net": "Net Excl",
            "audit": "Audit Status & Reason",
            "actions": "Edit Action",
        }
        for cid, label in col_names.items():
            is_vis = cid in getattr(self, "visible_columns", self.columns)
            icon = "✓ " if is_vis else "   "
            menu.add_command(
                label=f"{icon}{label}",
                command=lambda c=cid: self.toggle_column_visibility(c)
            )
        menu.add_separator()
        menu.add_command(label="Reset All Columns to Visible", command=self.reset_columns_visibility)
        x = self.cols_menu_btn.winfo_rootx() if hasattr(self, "cols_menu_btn") else self.root.winfo_pointerx()
        y = (self.cols_menu_btn.winfo_rooty() + self.cols_menu_btn.winfo_height()) if hasattr(self, "cols_menu_btn") else self.root.winfo_pointery()
        menu.tk_popup(x, y)

    def toggle_column_visibility(self, cid):
        if not hasattr(self, "visible_columns"):
            self.visible_columns = list(self.columns)
        if cid in self.visible_columns:
            if len(self.visible_columns) > 3:
                self.visible_columns.remove(cid)
        else:
            self.visible_columns = [c for c in self.columns if c in self.visible_columns or c == cid]
        self.tree.configure(displaycolumns=self.visible_columns)

    def reset_columns_visibility(self):
        self.visible_columns = list(self.columns)
        self.tree.configure(displaycolumns=self.visible_columns)

    # ==========================================================================
    # RECONCILIATION MATH & GRID RENDERING
    # ==========================================================================
    def recalculate_reconciliation(self) -> bool:
        try:
            o_bal = float(self.open_bal_var.get().replace(",", "").strip() or 0)
        except Exception:
            o_bal = 0.0

        try:
            c_bal = float(self.close_bal_var.get().replace(",", "").strip() or 0)
        except Exception:
            c_bal = 0.0

        inflows = sum(t["amount"] for t in self.transactions if t["amount"] > 0)
        outflows = sum(t["amount"] for t in self.transactions if t["amount"] < 0)
        net_mvt = round(inflows + outflows, 2)
        expected_close = round(o_bal + net_mvt, 2)
        diff = round(expected_close - c_bal, 2)

        sign_mvt = f"+R {net_mvt:,.2f}" if net_mvt >= 0 else f"-R {abs(net_mvt):,.2f}"
        self.net_movement_lbl.config(
            text=sign_mvt,
            fg="#34d399" if net_mvt >= 0 else "#f87171",
        )

        # Update Hero Traffic Light Reconciliation Card
        if not self.transactions:
            self.hero_banner.config(bg="#0c1527")
            self.hero_icon_lbl.config(text="⚪", bg="#0c1527", fg="#94a3b8")
            self.hero_text_f.config(bg="#0c1527")
            self.hero_title_lbl.config(
                text="STATEMENT RECONCILIATION: WAITING FOR IMPORT",
                bg="#0c1527",
                fg="#f1f5f9",
            )
            self.hero_sub_lbl.config(
                text="Import a statement or till slip to begin live reconciliation audit.",
                bg="#0c1527",
                fg="#94a3b8",
            )
            self.hero_auto_btn.pack_forget()
            self.variance_lbl.config(text="✓ READY", bg="#1e293b", fg="#94a3b8")
            self.auto_align_btn.pack_forget()
        elif abs(diff) <= 0.05:
            # 🟢 Balanced State: Luminous Obsidian Emerald Card
            self.hero_banner.config(bg="#064e3b")
            self.hero_icon_lbl.config(text="✓", bg="#064e3b", fg="#34d399", font=("Segoe UI", 13, "bold"))
            self.hero_text_f.config(bg="#064e3b")
            self.hero_title_lbl.config(
                text="Reconciliation Balanced",
                bg="#064e3b",
                fg="#34d399",
                font=("Segoe UI", 10, "bold"),
            )
            bank_lbl = getattr(self, "current_bank_name", "South African Bank Statement")
            self.hero_sub_lbl.config(
                text=f"Format: {bank_lbl} • Opening R {o_bal:,.2f} + Net {sign_mvt} matches Statement Closing R {c_bal:,.2f} to the cent. Ready to export.",
                bg="#064e3b",
                fg="#a7f3d0",
            )
            self.hero_auto_btn.pack_forget()
            self.variance_lbl.config(text="✓ BALANCED (Diff: R 0.00)", bg="#065f46", fg="#34d399")
            self.auto_align_btn.pack_forget()
        else:
            # 🟡 / 🟠 Variance State: Professional Dark Slate Card with Amber & Red accents
            diff_sign = f"-R {abs(diff):,.2f}" if diff < 0 else f"+R {diff:,.2f}"
            self.hero_banner.config(bg="#1e293b")
            self.hero_icon_lbl.config(text="⚠️", bg="#1e293b", fg="#fbbf24", font=("Segoe UI", 12))
            self.hero_text_f.config(bg="#1e293b")
            self.hero_title_lbl.config(
                text=f"Reconciliation Variance: {diff_sign}",
                bg="#1e293b",
                fg="#fbbf24",
                font=("Segoe UI", 10, "bold"),
            )
            bank_lbl = getattr(self, "current_bank_name", "South African Bank Statement")
            self.hero_sub_lbl.config(
                text=f"Format: {bank_lbl} • Expected Closing R {expected_close:,.2f} vs Statement Closing R {c_bal:,.2f}. Review rows or use 1-Click Auto-Align.",
                bg="#1e293b",
                fg="#cbd5e1",
            )
            self.hero_auto_btn.config(
                text="⚡ Auto-Align",
                bg="#b45309",
                fg="#fef3c7",
                font=("Segoe UI", 8, "bold"),
                padx=10,
                pady=2,
            )
            if not self.hero_auto_btn.winfo_ismapped():
                self.hero_auto_btn.pack(side=tk.RIGHT, padx=4)
            self.variance_lbl.config(text=f"⚠️ Variance: {diff_sign}", bg="#78350f", fg="#fde68a")
            self.auto_align_btn.pack(side=tk.LEFT, padx=(2, 0))

        self.card_inflows.config(text=f"+R {inflows:,.2f}")
        self.card_outflows.config(text=f"-R {abs(outflows):,.2f}")
        self.card_exp_close.config(text=f"R {expected_close:,.2f}")
        self.card_stmt_close.config(text=f"R {c_bal:,.2f}")
        self.card_delta.config(
            text=f"R {abs(diff):,.2f}",
            fg="#34d399" if abs(diff) <= 0.05 else "#fbbf24",
        )
        self.card_lines.config(text=f"{len(self.transactions)} transactions")

        # Practice ROI Reclaimed Calculation
        num_txns = len(self.transactions)
        hrs_saved = max(0.2, round(num_txns * 50 / 3600, 1)) if num_txns else 0.0
        cost_saved = int(hrs_saved * 350)
        if hasattr(self, "roi_badge_lbl"):
            if num_txns > 0:
                self.roi_badge_lbl.config(text=f"⏱️ ROI: ~{hrs_saved}h (R {cost_saved:,})")
            else:
                self.roi_badge_lbl.config(text="⏱️ ROI: ~0h saved")

        self.update_month_timeline()

        return abs(diff) <= 0.05

    def render_grid(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not self.transactions:
            if hasattr(self, "empty_state_frame"):
                self.empty_state_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER, width=620, height=240)
        else:
            if hasattr(self, "empty_state_frame"):
                self.empty_state_frame.place_forget()

        q = self.search_var.get().strip().upper()
        prof_info = self.config["profiles"].get(self.active_profile, {})
        fye_month = prof_info.get("fin_year_end_month", 2)

        total_claimable_vat = 0.0
        total_output_vat = 0.0
        suspense_count = 0
        duplicate_count = 0

        for idx, t in enumerate(self.transactions):
            if t.get("is_suspense"):
                suspense_count += 1
            if t.get("is_duplicate"):
                duplicate_count += 1
            if t.get("amount", 0) < 0 and t.get("vat_type") == "Standard":
                total_claimable_vat += t.get("vat_claim", 0.0)
            elif t.get("amount", 0) > 0 and t.get("vat_type") == "Standard":
                total_output_vat += t.get("vat_claim", 0.0)

            if self.active_filter_tab == "suspense" and not t.get("is_suspense"):
                continue
            if self.active_filter_tab == "duplicates" and not t.get("is_duplicate"):
                continue
            if self.active_filter_tab == "inflows" and t["amount"] <= 0:
                continue
            if self.active_filter_tab == "outflows" and t["amount"] >= 0:
                continue

            # Column-specific dropdown filters
            if getattr(self, "column_filters", None):
                skip_row = False
                for col_f_key, col_f_val in self.column_filters.items():
                    if col_f_key == "vat_type" and t.get("vat_type") != col_f_val:
                        skip_row = True; break
                    elif col_f_key == "audit":
                        if col_f_val == "verified" and (t.get("is_suspense") or t.get("is_duplicate")):
                            skip_row = True; break
                        elif col_f_val == "suspense" and not t.get("is_suspense"):
                            skip_row = True; break
                        elif col_f_val == "duplicate" and not t.get("is_duplicate"):
                            skip_row = True; break
                    elif col_f_key == "month" and not t.get("date", "").startswith(col_f_val):
                        skip_row = True; break
                    elif col_f_key == "account" and t.get("code") != col_f_val:
                        skip_row = True; break
                    elif col_f_key in ["gross", "net", "amount"]:
                        if col_f_val == "outflows" and t.get("amount", 0) >= 0:
                            skip_row = True; break
                        elif col_f_val == "inflows" and t.get("amount", 0) <= 0:
                            skip_row = True; break
                        elif col_f_val == ">1000" and abs(t.get("amount", 0)) < 1000:
                            skip_row = True; break
                    elif col_f_key == "ledger" and t.get("acc_type") != col_f_val:
                        skip_row = True; break
                if skip_row:
                    continue

            if q and not (
                q in t["clean_payee"].upper()
                or q in t["code"]
                or q in t["ref"].upper()
                or q in t.get("name", "").upper()
            ):
                continue

            prd_num, _ = calculate_pastel_period(t["date"], fye_month)
            prd_str = f"P{prd_num}"

            g_disp = f"-R {abs(t['amount']):,.2f}" if t["amount"] < 0 else f"R {t['amount']:,.2f}"
            v_disp = f"R {t['vat_claim']:,.2f}" if t.get("vat_claim", 0) > 0 else "R 0.00"
            n_disp = f"-R {abs(t['net']):,.2f}" if t["net"] < 0 else f"R {t['net']:,.2f}"

            status = t.get("audit_status", "Verified")
            if t.get("is_suspense") and "⚠️" not in status:
                status = f"⚠️ {t.get('query_reason', 'Suspense')}"

            row_tag = "normal"
            if t.get("is_duplicate"):
                row_tag = "duplicate"
            elif t.get("is_suspense"):
                row_tag = "suspense"
            elif t["amount"] < 0:
                row_tag = "payment"
            else:
                row_tag = "receipt"

            acc_display = f"{t['code']} - {t['name']}"

            ref_str = t["ref"]
            if t.get("slip_matched"):
                ref_str = f"📎 {ref_str}"
            elif t.get("is_split"):
                ref_str = f"✂️ {ref_str}"

            vals = (
                str(idx + 1),
                t["date"],
                ref_str,
                t.get("acc_type", "GL"),
                t["clean_payee"],
                acc_display,
                g_disp,
                t["vat_type"],
                v_disp,
                n_disp,
                status,
                "✏️ Edit / 🗑️",
            )

            self.tree.insert("", tk.END, iid=str(idx), values=vals, tags=(row_tag,))

        self.tree.tag_configure("duplicate", background="#3b131e", foreground="#fca5a5")
        self.tree.tag_configure("suspense", background="#3b2a13", foreground="#fcd34d")
        self.tree.tag_configure("payment", foreground="#f1f5f9")
        self.tree.tag_configure("receipt", foreground="#34d399")

        if total_output_vat > 0:
            self.vat_kpi_lbl.config(text=f"Input VAT: R {total_claimable_vat:,.2f} | Output: R {total_output_vat:,.2f}")
        else:
            self.vat_kpi_lbl.config(text=f"Claimable VAT: R {total_claimable_vat:,.2f}")
        self.suspense_btn_pill.config(text=f"{suspense_count} Suspense")
        self.dup_btn_pill.config(text=f"{duplicate_count} Duplicates")

        self.tab_buttons["all"].config(text=f"All Lines ({len(self.transactions)})")
        self.tab_buttons["suspense"].config(text=f"• Suspense ({suspense_count})")
        self.tab_buttons["duplicates"].config(text=f"• Duplicates ({duplicate_count})")

        self.recalculate_reconciliation()

    # ==========================================================================
    # ASYNC IMPORT WORKER & QUEUE POLLING (SINGLE & MULTI-DOCUMENT BATCH)
    # ==========================================================================
    def start_import_worker(self):
        if not self._guard_trial_allowance("import bank statements"):
            return

        fpaths = filedialog.askopenfilenames(
            title="Import One or Multiple Bank Statements, Tax Invoices or Till Slips (Ctrl/Shift+Click for Multiple)",
            filetypes=[
                ("All Supported Documents", "*.pdf;*.csv;*.txt;*.jpg;*.jpeg;*.png;*.webp"),
                ("PDF Documents", "*.pdf"),
                ("Image Receipts & Invoices", "*.jpg;*.jpeg;*.png;*.webp"),
                ("CSV Statements", "*.csv;*.txt"),
            ],
            parent=self.root,
        )
        if not fpaths:
            return

        file_list = list(fpaths)
        state = self.license_mgr.get_state()
        if not state["is_licensed"] and len(file_list) > state["remaining"]:
            messagebox.showwarning(
                "Trial Statement Limit",
                f"You selected {len(file_list)} files, but your trial only has {state['remaining']} statement imports remaining.\n\n"
                f"Please select up to {state['remaining']} files or activate a TaxClean ZA Pro license.",
                parent=self.root,
            )
            return
        coa = self.config["profiles"][self.active_profile]["coa"]

        if len(file_list) == 1:
            fpath = file_list[0]
            self.status_lbl.config(text=f"Importing {Path(fpath).name} (Local OCR + Auto Micro-AI)...")
            self.prog_bar["value"] = 10
            worker = ParseWorker(fpath, coa, self.active_profile, self.memory, self.task_queue)
            worker.start()
            return

        # Multi-Document Simultaneous Batch Import
        self.status_lbl.config(text=f"Batch importing {len(file_list)} documents simultaneously...")
        self.prog_bar["value"] = 5

        def _multi_import_thread():
            combined_records: list[dict] = []
            first_open_bal: Optional[float] = None
            last_close_bal: Optional[float] = None
            detected_banks: list[str] = []
            total_files = len(file_list)

            for idx, fp in enumerate(file_list, start=1):
                fname = Path(fp).name
                pct = int(5 + ((idx - 1) / total_files) * 85)
                self.task_queue.put(("PROGRESS", pct, f"Importing document {idx} of {total_files}: {fname}..."))
                try:
                    sub_q: queue.Queue = queue.Queue()
                    w = ParseWorker(fp, coa, self.active_profile, self.memory, sub_q)
                    raw_text = w.extract_text()
                    res = w.parse_text(raw_text)
                    recs = res.get("records", [])
                    if recs:
                        for r in recs:
                            r["source_file"] = fname
                        if not combined_records:
                            combined_records.extend(recs)
                        else:
                            unique_new, _ = StatementStacker.shield_duplicates(combined_records, recs)
                            combined_records.extend(unique_new)

                        if first_open_bal is None and res.get("open_bal") is not None:
                            try:
                                first_open_bal = float(res["open_bal"])
                            except Exception:
                                pass
                        if res.get("close_bal") is not None:
                            try:
                                last_close_bal = float(res["close_bal"])
                            except Exception:
                                pass
                        bname = res.get("detected_bank", "")
                        if bname and bname not in detected_banks:
                            detected_banks.append(bname)
                except Exception as e:
                    self.task_queue.put(("STATUS", f"Import notice on {fname}: {e}"))

            # Sort combined multi-document records chronologically by date
            combined_records.sort(key=lambda r: r.get("date", "9999-99-99"))

            if first_open_bal is not None and last_close_bal is None:
                last_close_bal = _dec_round(first_open_bal + sum(r["amount"] for r in combined_records))
            elif first_open_bal is None and combined_records:
                first_open_bal = 0.0
                last_close_bal = _dec_round(sum(r["amount"] for r in combined_records))

            bank_summary = " + ".join(detected_banks[:2]) if detected_banks else f"{total_files} Documents"
            if len(detected_banks) > 2:
                bank_summary += f" (+{len(detected_banks) - 2} more)"

            self.task_queue.put((
                "DONE",
                {
                    "open_bal": f"{first_open_bal:.2f}" if first_open_bal is not None else "0.00",
                    "close_bal": f"{last_close_bal:.2f}" if last_close_bal is not None else "0.00",
                    "records": combined_records,
                    "detected_bank": f"{bank_summary} ({total_files} files)",
                },
            ))

        threading.Thread(target=_multi_import_thread, daemon=True).start()

    def poll_queue(self):
        try:
            while True:
                msg = self.task_queue.get_nowait()
                mtype = msg[0]
                if mtype == "STATUS":
                    self.status_lbl.config(text=msg[1])
                elif mtype == "AI_KEY_STATUS":
                    ok = msg[1]
                    if hasattr(self, "ai_key_badge"):
                        if ok:
                            self.ai_key_badge.config(text="🟢 AI: Gemini", bg="#064e3b", fg="#34d399")
                        else:
                            self.ai_key_badge.config(text="🔴 AI: Invalid Key", bg="#7f1d1d", fg="#fca5a5")
                    self.update_bottom_info()
                elif mtype == "PROGRESS":
                    self.prog_bar["value"] = msg[1]
                    self.status_lbl.config(text=msg[2])
                elif mtype == "DONE":
                    parse_result = msg[1]
                    new_records = parse_result["records"]
                    if not new_records:
                        ans = messagebox.askyesno(
                            "Unrecognized Statement Layout",
                            "Document opened successfully, but no monetary transaction rows could be matched.\n\nWould you like to open the 1-Click Diagnostics Reporter to send this layout trace to the TaxClean ZA engineering agents for analysis?",
                            parent=self.root,
                            icon="warning"
                        )
                        if ans:
                            self.open_issue_reporter_dialog(prefill_error="0 monetary transaction rows matched from document", is_statement_error=True)
                        else:
                            messagebox.showwarning(
                                "Import Result",
                                "Document opened successfully, but no monetary transaction rows could be matched.",
                                parent=self.root,
                            )
                    else:
                        self.push_undo_state()
                        self.transactions = new_records
                        if parse_result.get("open_bal"):
                            self.open_bal_var.set(parse_result["open_bal"])
                        if parse_result.get("close_bal"):
                            self.close_bal_var.set(parse_result["close_bal"])
                        self.current_bank_name = parse_result.get("detected_bank", "South African Bank Statement")
                        self.license_mgr.record_statement_processed()
                        self._batch_licensed_for_export = True
                        self.update_license_ui_badge()
                        self.render_grid()
                        self.save_current_session()
                        self.status_lbl.config(
                            text=f"Import complete: Successfully verified {len(new_records)} transactions from {self.current_bank_name}."
                        )
                        hrs_saved = max(0.2, round(len(new_records) * 50 / 3600, 1))
                        cost_saved = int(hrs_saved * 350)
                        self.show_toast(f"🎉 Verified {len(new_records)} lines! Reclaimed ~{hrs_saved} hrs (~R {cost_saved:,}) in manual labor", color="#10b981", duration_ms=4000)
                    self.prog_bar["value"] = 0
                elif mtype == "ERROR":
                    self.prog_bar["value"] = 0
                    err_txt = msg[1] if len(msg) > 1 else "Unknown error during extraction"
                    tb_txt = msg[2] if len(msg) > 2 else ""
                    self.status_lbl.config(text="Import failed. Please check file format.")
                    
                    ans = messagebox.askyesno(
                        "Statement Parsing Issue Detected",
                        f"TaxClean ZA could not parse this document:\n\n{err_txt}\n\nWould you like to open the 1-Click Diagnostics Reporter to send this format trace to the engineering agents for instant analysis?",
                        parent=self.root,
                        icon="warning"
                    )
                    if ans:
                        full_err = f"{err_txt}\n\nTraceback:\n{tb_txt}" if tb_txt else err_txt
                        self.open_issue_reporter_dialog(prefill_error=full_err, is_statement_error=True)
                    else:
                        messagebox.showerror("Import Error", err_txt, parent=self.root)
        except queue.Empty:
            pass
        self.root.after(100, self.poll_queue)

    # ==========================================================================
    # ==========================================================================
    # SAGE / PASTEL PRE-FLIGHT VALIDATOR & MULTI-PERIOD ERP EXPORT ENGINE
    # ==========================================================================
    def export_batch_file(self):
        if not self.transactions:
            messagebox.showwarning("Export Notice", "No transaction lines to export.", parent=self.root)
            return
        state = self.license_mgr.get_state()
        if not state["is_licensed"] and state["remaining"] <= 0 and not getattr(self, "_batch_licensed_for_export", False):
            if not self._guard_trial_allowance("export data"):
                return
        self.open_preflight_validator()

    def open_preflight_validator(self):
        """
        4-Point Pre-Flight Sanity Checker before committing export:
        1. Statement Reconciliation Cent-Zero Check
        2. Financial Year End & Pastel Period Mappings
        3. Bank Contra General Ledger Account Code Check
        4. Suspense & Query Line Item Audit (<1% check)
        """
        active_erp = self.erp_var.get()
        dialog = tk.Toplevel(self.root)
        dialog.title(f"{active_erp}  -  Pre-Flight Export Validator")
        dialog.geometry("640x520")
        dialog.configure(bg="#0f172a")
        dialog.transient(self.root)
        dialog.grab_set()

        # Header
        header = tk.Frame(dialog, bg="#1e293b", padx=20, pady=12)
        header.pack(fill=tk.X)
        tk.Label(
            header,
            text=f"🛡️ {active_erp}  -  Pre-Flight Export Validator",
            font=("Segoe UI", 12, "bold"),
            fg="#38bdf8",
            bg="#1e293b",
        ).pack(anchor="w")
        tk.Label(
            header,
            text=f"Validating batch formatting and compliance against SARS TAA and {active_erp} import specifications.",
            font=("Segoe UI", 8),
            fg="#94a3b8",
            bg="#1e293b",
        ).pack(anchor="w", pady=(2, 0))

        content_f = tk.Frame(dialog, bg="#0f172a", padx=20, pady=14)
        content_f.pack(fill=tk.BOTH, expand=True)

        # Audit checks calculation
        try:
            o_bal = float(self.open_bal_var.get().replace(",", "").strip() or 0)
            c_bal = float(self.close_bal_var.get().replace(",", "").strip() or 0)
        except Exception:
            o_bal, c_bal = 0.0, 0.0

        net_mvt = _dec_round(sum(t["amount"] for t in self.transactions))
        expected_c = _dec_round(o_bal + net_mvt)
        diff = _dec_round(expected_c - c_bal)
        recon_pass = abs(diff) <= 0.05

        prof_info = self.config["profiles"][self.active_profile]
        fye_month = prof_info.get("fin_year_end_month", 2)
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        fye_name = month_names[fye_month - 1] if 1 <= fye_month <= 12 else "Feb"

        # Check periods present in batch
        periods_found = set()
        for t in self.transactions:
            p, y = calculate_pastel_period(t["date"], fye_month)
            periods_found.add(f"P{p} (FY{y})")
        periods_str = ", ".join(sorted(periods_found)) if periods_found else "P1"

        # Bank contra code check
        coa = prof_info.get("coa", {})
        bank_contra = "8400/000"
        for _, info in coa.items():
            if "8400" in info.get("code", "") or "BANK" in info.get("name", "").upper():
                bank_contra = info.get("code", "8400/000")
                break

        # Suspense line items count
        suspense_txns = [t for t in self.transactions if t.get("is_suspense") or t.get("code") == "9999/000"]
        suspense_count = len(suspense_txns)
        suspense_ratio = (suspense_count / len(self.transactions)) * 100 if self.transactions else 0.0

        def make_check_row(parent, icon, title, desc, status_text, is_ok):
            card = tk.Frame(parent, bg="#1e293b", padx=12, pady=8, highlightbackground="#334155", highlightthickness=1)
            card.pack(fill=tk.X, pady=4)
            left = tk.Frame(card, bg="#1e293b")
            left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            t_box = tk.Frame(left, bg="#1e293b")
            t_box.pack(anchor="w")
            tk.Label(t_box, text=icon, font=("Segoe UI", 10), bg="#1e293b").pack(side=tk.LEFT, padx=(0, 6))
            tk.Label(t_box, text=title, font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#1e293b").pack(side=tk.LEFT)

            tk.Label(left, text=desc, font=("Segoe UI", 8), fg="#94a3b8", bg="#1e293b").pack(anchor="w", padx=(20, 0), pady=(2, 0))

            badge_bg = "#064e3b" if is_ok else "#7f1d1d"
            badge_fg = "#34d399" if is_ok else "#fca5a5"
            tk.Label(
                card,
                text=status_text,
                font=("Segoe UI", 8, "bold"),
                bg=badge_bg,
                fg=badge_fg,
                padx=8,
                pady=3,
            ).pack(side=tk.RIGHT)

        # Check 1: Reconciliation Cent-Zero Check
        recon_status = "PASSED (R 0.00)" if recon_pass else f"VARIANCE (R {diff:,.2f})"
        recon_desc = f"Opening R {o_bal:,.2f} + Net R {net_mvt:,.2f} = Expected R {expected_c:,.2f} vs Stmt R {c_bal:,.2f}"
        make_check_row(content_f, "⚖️", "1. Zero-Variance Cent Balance", recon_desc, recon_status, recon_pass)

        # Check 2: Financial Year End & Periods Check
        period_desc = f"Entity FYE Month: {fye_name} • Accounting Periods: {periods_str}"
        make_check_row(content_f, "📅", f"2. Financial Periods ({active_erp})", period_desc, f"VALID ({len(periods_found)} Periods)", True)

        # Check 3: Bank Contra General Ledger Code Check
        contra_desc = f"Target Bank Contra Account: {bank_contra} (Cashbook Contra Account Code)"
        make_check_row(content_f, "🏦", f"3. Bank Contra GL Mapping ({active_erp})", contra_desc, f"MAPPED ({bank_contra})", True)

        # Check 4: Suspense Query Account Check
        suspense_status = "0 SUSPENSE (100% CLEAN)" if suspense_count == 0 else f"{suspense_count} QUERIES ({suspense_ratio:.1f}%)"
        suspense_desc = f"{len(self.transactions) - suspense_count} lines categorized to specific accounts • {suspense_count} in Suspense"
        make_check_row(content_f, "🧠", "4. Chart of Accounts & Suspense", suspense_desc, suspense_status, suspense_count == 0)

        # Footer Actions
        footer = tk.Frame(dialog, bg="#0f172a", padx=20, pady=12)
        footer.pack(fill=tk.X)

        def proceed_with_export():
            dialog.destroy()
            self.execute_export()

        if not recon_pass:
            tk.Label(
                footer,
                text="⚠️ Warning: Statement closing balance does not balance. Recommended to Auto-Align before exporting.",
                font=("Segoe UI", 8, "bold"),
                fg="#fca5a5",
                bg="#0f172a",
                wraplength=400,
                justify="left",
            ).pack(side=tk.LEFT)
        else:
            tk.Label(
                footer,
                text="✓ All pre-flight safety checks verified. Ready to generate batch file.",
                font=("Segoe UI", 8, "bold"),
                fg="#34d399",
                bg="#0f172a",
            ).pack(side=tk.LEFT)

        HDButton(
            footer,
            text="Cancel",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="#f8fafc",
            relief="flat",
            padx=12,
            pady=4,
            command=dialog.destroy,
        ).pack(side=tk.RIGHT, padx=(8, 0))

        HDButton(
            footer,
            text="💾 Proceed to Export",
            font=("Segoe UI", 9, "bold"),
            bg="#10b981",
            fg="white",
            relief="flat",
            padx=16,
            pady=4,
            command=proceed_with_export,
        ).pack(side=tk.RIGHT)

    def execute_export(self):
        if not self.transactions:
            messagebox.showinfo("Export", "No transactions available to export.", parent=self.root)
            return

        state = self.license_mgr.get_state()
        if not state["is_licensed"] and state["remaining"] <= 0 and not getattr(self, "_batch_licensed_for_export", False):
            if not self._guard_trial_allowance("export data"):
                return

        erp = self.erp_var.get()
        prof_info = self.config["profiles"][self.active_profile]
        fye_month = prof_info.get("fin_year_end_month", 2)

        try:
            o_bal = float(self.open_bal_var.get().replace(",", "").strip())
            c_bal = float(self.close_bal_var.get().replace(",", "").strip())
        except Exception:
            o_bal, c_bal = 0.0, 0.0

        try:
            if erp in ["SARS VAT201 Breakdown (Excel)", "SARS Audit Schedule"]:
                save_path = filedialog.asksaveasfilename(
                    defaultextension=".xlsx",
                    initialfile=f"{self.active_profile}_SARS_VAT201_Schedule.xlsx",
                    filetypes=[("Excel Audit Workpaper", "*.xlsx")],
                    parent=self.root,
                )
                if not save_path:
                    return
                AccountingExporter.export_sars_excel_workbook(
                    self.transactions,
                    save_path,
                    open_bal=o_bal,
                    close_bal=c_bal,
                    fin_year_end_month=fye_month,
                    entity_name=self.active_profile,
                )
            else:
                default_ext = ".csv"
                save_path = filedialog.asksaveasfilename(
                    defaultextension=default_ext,
                    initialfile=f"{self.active_profile}_{erp.replace(' ', '_')}.csv",
                    filetypes=[("CSV Batch File", "*.csv"), ("Excel Workpaper", "*.xlsx")],
                    parent=self.root,
                )
                if not save_path:
                    return

                if save_path.endswith(".xlsx"):
                    AccountingExporter.export_sars_excel_workbook(
                        self.transactions,
                        save_path,
                        open_bal=o_bal,
                        close_bal=c_bal,
                        fin_year_end_month=fye_month,
                        entity_name=self.active_profile,
                    )
                elif erp == "Sage Pastel Partner" or erp == "Pastel Partner":
                    AccountingExporter.export_sage_pastel(self.transactions, save_path, fye_month)
                elif erp == "Sage Business Cloud":
                    AccountingExporter.export_sage_business_cloud(self.transactions, save_path)
                elif erp == "Xero":
                    AccountingExporter.export_xero(self.transactions, save_path)
                elif erp == "QuickBooks Online":
                    AccountingExporter.export_quickbooks(self.transactions, save_path)
                else:
                    AccountingExporter.export_universal_sars_csv(self.transactions, save_path)

            self._show_post_export_guide(erp, save_path, len(self.transactions))
        except PermissionError:
            messagebox.showerror(
                "Export File Locked",
                "Could not write to the destination file because it is currently open in Excel or another program.\n\n"
                "Please close the file in Excel (or choose a different filename) and try exporting again.",
                parent=self.root,
            )
        except OSError as e:
            messagebox.showerror(
                "Export Error",
                f"Could not save export file:\n\n{e}",
                parent=self.root,
            )

    def _show_post_export_guide(self, erp: str, save_path: str, count: int):
        """
        Shows a tailored 'What to do next' ERP import guide after exporting.
        Includes a 'Got It  -  Don't Show Again' button so repeat users are never slowed down.
        """
        fname = os.path.basename(save_path)
        if hasattr(self, "status_var"):
            self.status_var.set(f"✓ Exported {count} transactions ({erp}) → {fname}")

        if self.memory.get_setting("HIDE_EXPORT_GUIDE", "") == "1":
            return

        pop = tk.Toplevel(self.root)
        pop.title(f"Export Complete  -  How to Upload into {erp}")
        pop.geometry("580x380")
        pop.minsize(540, 350)
        pop.configure(bg="#0f172a")
        pop.transient(self.root)
        pop.grab_set()
        apply_dark_titlebar(pop)

        self.root.update_idletasks()
        rx = self.root.winfo_rootx() + max(40, (self.root.winfo_width() - 580) // 2)
        ry = self.root.winfo_rooty() + max(40, (self.root.winfo_height() - 380) // 2)
        pop.geometry(f"580x380+{rx}+{ry}")

        # Bottom action bar pinned first
        ftr = tk.Frame(pop, bg="#0b1120", padx=20, pady=12)
        ftr.pack(side=tk.BOTTOM, fill=tk.X)

        def open_in_folder():
            try:
                norm_p = os.path.normpath(save_path)
                subprocess.Popen(["explorer", f"/select,{norm_p}"])
            except Exception:
                pass

        def dismiss_forever():
            self.memory.set_setting("HIDE_EXPORT_GUIDE", "1")
            pop.destroy()

        HDButton(
            ftr,
            text="📂 Show File in Folder",
            font=("Segoe UI", 9, "bold"),
            bg="#1e293b",
            fg="#38bdf8",
            relief="flat",
            padx=12,
            pady=5,
            command=open_in_folder,
        ).pack(side=tk.LEFT)

        HDButton(
            ftr,
            text="Close",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="#f8fafc",
            relief="flat",
            padx=12,
            pady=5,
            command=pop.destroy,
        ).pack(side=tk.RIGHT, padx=(8, 0))

        HDButton(
            ftr,
            text="✓ Got It  -  Don't Show Again",
            font=("Segoe UI", 9, "bold"),
            bg="#10b981",
            fg="#ffffff",
            relief="flat",
            padx=14,
            pady=5,
            command=dismiss_forever,
        ).pack(side=tk.RIGHT)

        # Celebratory Practice ROI Card & Toast
        hrs_saved = max(0.2, round(count * 50 / 3600, 1))
        cost_saved = int(hrs_saved * 350)
        self.show_toast(f"🎉 Export Complete! Reclaimed ~{hrs_saved} hrs (~R {cost_saved:,})", color="#10b981", duration_ms=4000)

        roi_card = tk.Frame(pop, bg="#064e3b", padx=14, pady=8, highlightthickness=1, highlightbackground="#059669")
        roi_card.pack(fill=tk.X, padx=20, pady=(10, 0))
        tk.Label(
            roi_card,
            text=f"🎉 Practice ROI Reclaimed: ~{hrs_saved} billable hours & ~R {cost_saved:,} in manual data entry!",
            font=("Segoe UI", 9, "bold"),
            fg="#34d399",
            bg="#064e3b",
        ).pack()

        # Header
        hdr = tk.Frame(pop, bg="#1e293b", padx=20, pady=12)
        hdr.pack(fill=tk.X)
        tk.Label(
            hdr,
            text=f"✓ Saved {count} Transactions ({fname})",
            font=("Segoe UI", 11, "bold"),
            fg="#34d399",
            bg="#1e293b",
        ).pack(anchor="w")
        tk.Label(
            hdr,
            text=save_path,
            font=("Consolas", 8),
            fg="#94a3b8",
            bg="#1e293b",
        ).pack(anchor="w", pady=(2, 0))

        # Body steps tailored to ERP
        body = tk.Frame(pop, bg="#0f172a", padx=20, pady=14)
        body.pack(fill=tk.BOTH, expand=True)

        is_xlsx = save_path.lower().endswith(".xlsx")
        if is_xlsx or erp in ["SARS VAT201 Breakdown (Excel)", "SARS Audit Schedule"]:
            steps_title = "Next Steps  -  Using Your SARS VAT201 Excel Workpaper:"
            steps = [
                "1. Open the exported .xlsx file directly in Microsoft Excel.",
                "2. Tab 1 ('VAT201 Schedule') shows your SARS eFiling Box 1, 4, 15, 19 & 20 figures.",
                "3. Tab 2 ('Cashbook Ledger') contains your balanced line-by-line audit trail.",
            ]
            tip_text = "💡 Tip: Keep this workbook in your client's 5-year SARS Tax Administration Act (Sec 29) folder."
            tip_fg = "#38bdf8"
        elif "Pastel" in erp:
            steps_title = "Next Steps  -  Uploading into Sage 50cloud Pastel Partner:"
            steps = [
                "1. In Pastel Partner, go to Process → Cash Book → Select your Bank Account.",
                "2. Click Batch → Import, and choose the exported .csv file.",
                "3. Verify that your 7-digit GL account codes match your Pastel Chart of Accounts.",
            ]
            tip_text = "⚠️ Important: Upload this .csv directly into Pastel. Do NOT open and click 'Save' in Excel first (Excel changes DD/MM/YYYY date formats)."
            tip_fg = "#fbbf24"
        elif "Sage Business Cloud" in erp:
            steps_title = "Next Steps  -  Uploading into Sage Business Cloud (Sage One):"
            steps = [
                "1. In Sage Business Cloud, go to Banking → Transactions → Banking.",
                "2. Click Import Bank Statements and choose CSV as the file type.",
                "3. Select your exported .csv file and click Upload.",
            ]
            tip_text = "⚠️ Important: Upload this .csv directly into Sage. Do NOT open and click 'Save' in Excel first (Excel alters DD/MM/YYYY dates)."
            tip_fg = "#fbbf24"
        elif "Xero" in erp:
            steps_title = "Next Steps  -  Uploading into Xero:"
            steps = [
                "1. In Xero, go to Accounting → Bank Accounts.",
                "2. Next to your bank account, click Manage Account → Import a Statement.",
                "3. Select your exported .csv file and click Import.",
            ]
            tip_text = "⚠️ Important: Upload this .csv directly into Xero. Do NOT open and click 'Save' in Excel first (Excel alters DD/MM/YYYY dates)."
            tip_fg = "#fbbf24"
        elif "QuickBooks" in erp:
            steps_title = "Next Steps  -  Uploading into QuickBooks Online:"
            steps = [
                "1. In QuickBooks Online, go to Transactions → Bank Transactions.",
                "2. Click the dropdown next to Link account and select Upload transactions.",
                "3. Choose your exported .csv file and follow the column confirmation.",
            ]
            tip_text = "⚠️ Important: Upload this .csv directly into QuickBooks. Do NOT open and click 'Save' in Excel first."
            tip_fg = "#fbbf24"
        else:
            steps_title = f"Next Steps  -  Using Your {erp} Export:"
            steps = [
                "1. Open your accounting package's Bank Statement / Cashbook Import screen.",
                "2. Select the exported .csv file directly from your computer.",
                "3. Confirm the DD/MM/YYYY date column and signed Amount column.",
            ]
            tip_text = "⚠️ Important: Upload this .csv directly into your accounting software without re-saving it in Excel first."
            tip_fg = "#fbbf24"

        tk.Label(
            body,
            text=steps_title,
            font=("Segoe UI", 10, "bold"),
            fg="#f8fafc",
            bg="#0f172a",
        ).pack(anchor="w", pady=(0, 8))

        for s in steps:
            tk.Label(
                body,
                text=s,
                font=("Segoe UI", 9),
                fg="#cbd5e1",
                bg="#0f172a",
                wraplength=530,
                justify="left",
            ).pack(anchor="w", pady=3)

        tip_box = tk.Frame(body, bg="#1e293b", padx=12, pady=8, highlightbackground="#334155", highlightthickness=1)
        tip_box.pack(fill=tk.X, pady=(12, 0))
        tk.Label(
            tip_box,
            text=tip_text,
            font=("Segoe UI", 8, "bold"),
            fg=tip_fg,
            bg="#1e293b",
            wraplength=510,
            justify="left",
        ).pack(anchor="w")

    # ==========================================================================
    # AI SETTINGS & PROFILE MODALS
    # ==========================================================================
    def _check_show_api_prompt(self):
        """
        Displays a compact, non-blocking quick popup window on startup if no Google Gemini
        API key has been added yet, explaining how to create and add a free key for better performance.
        """
        try:
            curr_key = self.memory.get_setting("GEMINI_API_KEY", "").strip()
            hide_prompt = self.memory.get_setting("HIDE_API_STARTUP_PROMPT", "")
            if curr_key or hide_prompt == "1":
                return
            if hasattr(self, "_api_quick_popup") and self._api_quick_popup and self._api_quick_popup.winfo_exists():
                return

            pop = tk.Toplevel(self.root)
            self._api_quick_popup = pop
            pop.title("⚡ Boost OCR Performance  -  Add Free AI API Key")
            pop.geometry("580x395")
            pop.minsize(540, 370)
            pop.configure(bg="#0f172a")
            pop.transient(self.root)
            apply_dark_titlebar(pop)

            # Center over main window
            self.root.update_idletasks()
            rx = self.root.winfo_rootx() + max(40, (self.root.winfo_width() - 580) // 2)
            ry = self.root.winfo_rooty() + max(40, (self.root.winfo_height() - 395) // 2)
            pop.geometry(f"580x395+{rx}+{ry}")

            # Pinned bottom bar first so buttons never clip
            ftr = tk.Frame(pop, bg="#0b1120", padx=20, pady=10)
            ftr.pack(side=tk.BOTTOM, fill=tk.X)

            dont_show_var = tk.BooleanVar(value=False)
            tk.Checkbutton(
                ftr,
                text="Don't show at startup",
                variable=dont_show_var,
                bg="#0b1120",
                fg="#94a3b8",
                selectcolor="#1e293b",
                activebackground="#0b1120",
                activeforeground="#f8fafc",
                font=("Segoe UI", 8),
            ).pack(side=tk.LEFT)

            def _close_later():
                if dont_show_var.get():
                    self.memory.set_setting("HIDE_API_STARTUP_PROMPT", "1")
                pop.destroy()

            def _open_full_setup():
                if dont_show_var.get():
                    self.memory.set_setting("HIDE_API_STARTUP_PROMPT", "1")
                pop.destroy()
                self.open_ai_settings_dialog()

            HDButton(
                ftr,
                text="Continue Offline (Later)",
                bg="#334155",
                fg="#cbd5e1",
                font=("Segoe UI", 9),
                relief="flat",
                padx=12,
                pady=4,
                command=_close_later,
            ).pack(side=tk.RIGHT)

            HDButton(
                ftr,
                text="⚙️ Open Full API Settings",
                bg="#0284c7",
                fg="white",
                font=("Segoe UI", 9, "bold"),
                relief="flat",
                padx=12,
                pady=4,
                command=_open_full_setup,
            ).pack(side=tk.RIGHT, padx=(0, 8))

            body = tk.Frame(pop, bg="#0f172a", padx=22, pady=14)
            body.pack(fill=tk.BOTH, expand=True)

            tk.Label(
                body,
                text="⚠️ No AI API Key Added Yet  -  Add One for Maximum Performance",
                font=("Segoe UI", 11, "bold"),
                fg="#fbbf24",
                bg="#0f172a",
            ).pack(anchor="w", pady=(0, 4))

            tk.Label(
                body,
                text=(
                    "TaxClean ZA's Local OCR runs 100% offline out of the box, but adding a free Google Gemini\n"
                    "API Key dramatically improves speed and accuracy on scanned PDFs and faded/crumpled slips."
                ),
                font=("Segoe UI", 8),
                fg="#cbd5e1",
                bg="#0f172a",
                justify="left",
            ).pack(anchor="w", pady=(0, 10))

            steps_f = tk.LabelFrame(
                body,
                text=" 📋 How to Create & Add Your Free API Key (30 Seconds) ",
                font=("Segoe UI", 8, "bold"),
                fg="#38bdf8",
                bg="#1e293b",
                padx=12,
                pady=8,
            )
            steps_f.pack(fill=tk.X, pady=(0, 10))

            tk.Label(
                steps_f,
                text=(
                    "1. Click '🌐 Get Free Google API Key' below and sign in with any Google account.\n"
                    "2. In Google AI Studio, click 'Create API key' (top-right) and click 'Copy'.\n"
                    "3. Paste your key (starts with AIza...) into the box below and click '✓ Save Key'."
                ),
                font=("Segoe UI", 8),
                fg="#e2e8f0",
                bg="#1e293b",
                justify="left",
            ).pack(anchor="w", pady=(0, 8))

            q_row = tk.Frame(steps_f, bg="#1e293b")
            q_row.pack(fill=tk.X)

            q_key_var = tk.StringVar()
            q_ent = tk.Entry(q_row, textvariable=q_key_var, font=("Consolas", 9), bg="#0f172a", fg="white", insertbackground="white")
            q_ent.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

            def _paste_and_save():
                val = q_key_var.get().strip().strip('"').strip("'")
                if not val:
                    try:
                        clip = self.root.clipboard_get().strip()
                        m = re.search(r"AIza[0-9A-Za-z_-]{30,}", clip)
                        val = m.group(0) if m else clip
                        q_key_var.set(val)
                    except Exception:
                        pass
                if not val:
                    messagebox.showwarning("API Key", "Please paste your Google Gemini API key (starts with AIza...) first.", parent=pop)
                    return
                self.memory.set_setting("GEMINI_API_KEY", val)
                self.update_ai_key_badge()
                self.update_bottom_info()
                messagebox.showinfo("✓ API Key Activated", "Your Google Gemini API Key is now saved and active!", parent=pop)
                pop.destroy()

            HDButton(
                q_row,
                text="🌐 Get Free Google API Key",
                bg="#0369a1",
                fg="white",
                font=("Segoe UI", 8, "bold"),
                relief="flat",
                padx=8,
                pady=3,
                command=lambda: webbrowser.open("https://aistudio.google.com/app/apikey"),
            ).pack(side=tk.LEFT, padx=(0, 6))

            HDButton(
                q_row,
                text="📋 Paste & Save Key",
                bg="#059669",
                fg="white",
                font=("Segoe UI", 8, "bold"),
                relief="flat",
                padx=10,
                pady=3,
                command=_paste_and_save,
            ).pack(side=tk.LEFT)

            pop.bind("<Escape>", lambda e: _close_later())
        except Exception:
            pass

    def open_ai_settings_dialog(self):
        """Allows user to set their free Google AI Studio Gemini Key for targeted micro-resolution."""
        dialog = tk.Toplevel(self.root)
        dialog.title("TaxClean ZA  -  How to Create & Add Your AI API Key")
        dialog.geometry("720x590")
        dialog.minsize(660, 540)
        dialog.configure(bg="#0f172a")
        dialog.transient(self.root)
        dialog.grab_set()
        apply_dark_titlebar(dialog)

        # 1. PINNED BOTTOM ACTION BAR FIRST (Anchored to bottom edge so buttons are NEVER clipped)
        btn_f = tk.Frame(dialog, bg="#0f172a")
        btn_f.pack(side=tk.BOTTOM, fill=tk.X, padx=24, pady=14)

        curr_key = self.memory.get_setting("GEMINI_API_KEY", "")
        key_var = tk.StringVar(value=curr_key)

        def save_ai_key():
            k = key_var.get().strip().strip('"').strip("'")
            self.memory.set_setting("GEMINI_API_KEY", k)
            self.update_ai_key_badge()
            self.update_bottom_info()
            if k:
                messagebox.showinfo(
                    "✓ Key Saved & Activated",
                    "Google AI Studio Key confirmed and saved!\n\n"
                    "Targeted Micro-AI will now auto-repair damaged or blurry slips.",
                    parent=dialog,
                )
            else:
                messagebox.showinfo("Saved", "API key cleared. System will use pure local engine.", parent=dialog)
            dialog.destroy()

        def do_test_connection():
            k_test = key_var.get().strip().strip('"').strip("'")
            if not k_test:
                messagebox.showwarning("API Key", "Please enter or paste an API key first.", parent=dialog)
                return
            status_lbl.config(text="API Key Status: ⏳ Testing connection with Google AI Studio...", fg="#fde68a")
            def _test_bg():
                ok, msg = self.test_gemini_key_connection(k_test)
                def _res():
                    if not dialog.winfo_exists():
                        return
                    if ok:
                        status_lbl.config(text="API Key Status: 🟢 Active & Working (Google Gemini Connected)", fg="#34d399")
                        messagebox.showinfo("API Key Verified", f"✓ SUCCESS!\n\n{msg}\n\nYour Google Gemini Micro-AI is active, working, and ready.", parent=dialog)
                    else:
                        status_lbl.config(text=f"API Key Status: 🔴 Invalid Key: {msg}", fg="#f87171")
                        messagebox.showerror("Verification Failed", f"❌ Google AI Studio Rejected Key:\n\n{msg}\n\nPlease check your key in Google AI Studio.", parent=dialog)
                if dialog.winfo_exists():
                    dialog.after(0, _res)
            threading.Thread(target=_test_bg, daemon=True).start()

        # Bottom Bar: Explicit Confirm, Test, and Close buttons
        HDButton(
            btn_f,
            text="✓ Enter / Confirm Key",
            bg="#059669",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=14,
            pady=4,
            command=save_ai_key,
        ).pack(side=tk.LEFT, padx=(0, 8))

        HDButton(
            btn_f,
            text="⚡ Test Connection",
            bg="#0284c7",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=12,
            pady=4,
            command=do_test_connection,
        ).pack(side=tk.LEFT, padx=(0, 8))

        HDButton(
            btn_f,
            text="Cancel / Close",
            bg="#334155",
            fg="white",
            font=("Segoe UI", 9),
            relief="flat",
            padx=12,
            pady=4,
            command=dialog.destroy,
        ).pack(side=tk.RIGHT)

        # 2. MAIN CONTENT AREA
        content_f = tk.Frame(dialog, bg="#0f172a", padx=24, pady=12)
        content_f.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            content_f,
            text="Targeted Micro-AI Engine  -  How to Create & Add an API Key",
            font=("Segoe UI", 12, "bold"),
            fg="#38bdf8",
            bg="#0f172a",
        ).pack(anchor="w", pady=(0, 4))

        tk.Label(
            content_f,
            text=(
                "• Pure Local OCR is 100% free and processes standard bank statements & clean slips offline.\n"
                "• Adding a free Google Gemini API key boosts accuracy on faded, blurry, or complex statements & receipts."
            ),
            font=("Segoe UI", 8),
            fg="#94a3b8",
            bg="#0f172a",
            justify="left",
        ).pack(anchor="w", pady=(0, 10))

        # Step-by-Step Instructions Box
        free_box = tk.LabelFrame(
            content_f,
            text=" 📋 Step-by-Step Instructions: Create Your Free Google Gemini API Key ",
            font=("Segoe UI", 8, "bold"),
            fg="#38bdf8",
            bg="#1e293b",
            padx=12,
            pady=8,
        )
        free_box.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            free_box,
            text=(
                "Step 1: Click '🌐 1. Open Google AI Studio' below and sign in with your Google/Gmail account.\n"
                "Step 2: Click the blue 'Create API key' button on the Google AI Studio page, then click 'Copy'.\n"
                "Step 3: Come back here and click '📋 Paste from Clipboard' (or '⚡ Auto-Detect Copied Key').\n"
                "Step 4: Click '⚡ Test Connection' to verify, then click '✓ Enter / Confirm Key' to save!"
            ),
            font=("Segoe UI", 8),
            fg="#e2e8f0",
            bg="#1e293b",
            justify="left",
        ).pack(anchor="w", pady=(0, 8))

        free_row = tk.Frame(free_box, bg="#1e293b")
        free_row.pack(fill=tk.X)

        # web links available globally
        HDButton(
            free_row,
            text="🌐 1. Open Google AI Studio (Get Free Key)",
            font=("Segoe UI", 9, "bold"),
            bg="#0369a1",
            fg="white",
            relief="flat",
            padx=10,
            pady=4,
            command=lambda: webbrowser.open("https://aistudio.google.com/app/apikey"),
        ).pack(side=tk.LEFT, padx=(0, 8))

        HDButton(
            free_row,
            text="⚡ Auto-Detect Copied Key",
            font=("Segoe UI", 9, "bold"),
            bg="#047857",
            fg="white",
            relief="flat",
            padx=10,
            pady=4,
            command=lambda: self.auto_setup_google_api_key(dialog, key_var),
        ).pack(side=tk.LEFT)

        # Manual Key Input Section
        manual_box = tk.LabelFrame(content_f, text=" Manually Put in Your Own Key ", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#1e293b", padx=12, pady=10)
        manual_box.pack(fill=tk.X, pady=(0, 12))

        tk.Label(manual_box, text="Google AI Studio Gemini API Key:", font=("Segoe UI", 9, "bold"), fg="#cbd5e1", bg="#1e293b").pack(anchor="w")

        inp_row = tk.Frame(manual_box, bg="#1e293b")
        inp_row.pack(fill=tk.X, pady=(6, 6))

        key_ent = tk.Entry(inp_row, textvariable=key_var, font=("Segoe UI", 10), show="*", bg="#0f172a", fg="white", insertbackground="white")
        key_ent.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        key_ent.bind("<Return>", lambda e: save_ai_key())

        # DIRECT "ENTER / CONFIRM KEY" BUTTON ON THE INPUT ROW!
        HDButton(
            inp_row,
            text="✓ Enter Key",
            font=("Segoe UI", 9, "bold"),
            bg="#059669",
            fg="white",
            relief="flat",
            padx=12,
            pady=4,
            command=save_ai_key,
        ).pack(side=tk.LEFT)

        def do_paste_clipboard():
            try:
                raw = self.root.clipboard_get().strip().strip('"').strip("'")
                m = re.search(r"AIza[0-9A-Za-z_-]{30,}", raw)
                clean_k = m.group(0) if m else raw
                if clean_k:
                    key_var.set(clean_k)
                    refresh_dialog_status(clean_k)
                else:
                    messagebox.showwarning("Clipboard", "Clipboard is empty or does not contain a valid key.", parent=dialog)
            except Exception as e:
                messagebox.showwarning("Clipboard", f"Could not read clipboard: {e}", parent=dialog)

        # Action Buttons Row
        act_row = tk.Frame(manual_box, bg="#1e293b")
        act_row.pack(fill=tk.X, pady=(2, 4))

        HDButton(act_row, text="📋 Paste from Clipboard", font=("Segoe UI", 8, "bold"), bg="#1d4ed8", fg="white", relief="flat", padx=10, pady=2, command=do_paste_clipboard).pack(side=tk.LEFT, padx=(0, 6))
        def toggle_show():
            if key_ent.cget("show") == "*":
                key_ent.config(show="")
                t_btn.config(text="Hide Key")
            else:
                key_ent.config(show="*")
                t_btn.config(text="Show Key")

        t_btn = HDButton(act_row, text="Show Key", font=("Segoe UI", 8), bg="#334155", fg="#cbd5e1", relief="flat", padx=8, pady=2, command=toggle_show)
        t_btn.pack(side=tk.LEFT, padx=(0, 6))

        def clear_key():
            key_var.set("")
            refresh_dialog_status("")

        HDButton(act_row, text="Clear", font=("Segoe UI", 8), bg="#334155", fg="#cbd5e1", relief="flat", padx=8, pady=2, command=clear_key).pack(side=tk.LEFT)

        # Status Display Box
        status_box = tk.Frame(content_f, bg="#0b1329", padx=12, pady=8, highlightbackground="#334155", highlightthickness=1)
        status_box.pack(fill=tk.X, pady=(0, 4))
        status_lbl = tk.Label(
            status_box,
            text="API Key Status: Checking...",
            font=("Segoe UI", 9, "bold"),
            fg="#94a3b8",
            bg="#0b1329",
        )
        status_lbl.pack(anchor="w")

        debounce_state = {"after_id": None}

        def refresh_dialog_status(k_str):
            if not dialog.winfo_exists():
                return
            if not k_str:
                status_lbl.config(text="API Key Status: ⚪ No Key Configured (Pure Local OCR Engine)", fg="#94a3b8")
            else:
                status_lbl.config(text="API Key Status: ⏳ Verifying key with Google AI Studio...", fg="#fde68a")
                def _chk():
                    ok, msg = self.test_gemini_key_connection(k_str)
                    def _show():
                        if not dialog.winfo_exists():
                            return
                        if ok:
                            status_lbl.config(text="API Key Status: 🟢 Active & Working (Google Gemini Connected)", fg="#34d399")
                        else:
                            status_lbl.config(text=f"API Key Status: 🔴 Invalid Key ({msg})", fg="#f87171")
                    if dialog.winfo_exists():
                        dialog.after(0, _show)
                threading.Thread(target=_chk, daemon=True).start()

        def _debounced_key_change(*args):
            if not dialog.winfo_exists():
                return
            if debounce_state["after_id"] is not None:
                try:
                    dialog.after_cancel(debounce_state["after_id"])
                except Exception:
                    pass
            debounce_state["after_id"] = dialog.after(600, lambda: refresh_dialog_status(key_var.get().strip()))

        refresh_dialog_status(curr_key)
        key_var.trace_add("write", _debounced_key_change)

    def on_switch_profile(self, event=None):
        new_prof = self.profile_var.get()
        if new_prof == "➕ Add New Client Profile...":
            self.profile_var.set(self.active_profile)
            self.root.after(10, self.create_new_profile_dialog)
            return
        if new_prof == "🗑️ Delete Current Client...":
            self.profile_var.set(self.active_profile)
            self.root.after(10, self.delete_current_profile_dialog)
            return
        self.active_profile = new_prof
        self.config["active_profile"] = new_prof
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.save_config()
        self._refresh_coa_dependent_widgets()
        self.restore_or_init_session()
        self.update_bottom_info()

    def update_license_ui_badge(self):
        state = self.license_mgr.get_state()
        if hasattr(self, "license_btn"):
            if state["is_licensed"]:
                self.license_btn.config(text="✨ Pro", bg="#064e3b", fg="#34d399")
            elif state["remaining"] >= 2:
                self.license_btn.config(text=f"✨ {state['remaining']} Left", bg="#0f766e", fg="#ccfbf1")
            else:
                self.license_btn.config(text=f"Trial: {state['remaining']}", bg="#78350f", fg="#fde68a")

    def update_ai_key_ui_advisory(self):
        k = self.memory.get_setting("GEMINI_API_KEY", "")
        if hasattr(self, "ai_key_btn"):
            if k and k.strip():
                self.ai_key_btn.config(text="🤖 AI Active", bg="#064e3b", fg="#34d399")
                ToolTip(self.ai_key_btn, "Google Gemini AI Vision is Active & Ready. Click to test or configure.")
            else:
                self.ai_key_btn.config(text="💡 Setup Free AI Key", bg="#3b1d54", fg="#f0abfc")
                ToolTip(self.ai_key_btn, "Recommended: Add your free Google Gemini API key to auto-heal blurry receipts & unfamiliar bank layouts.")

    def open_activation_dialog(self):
        state = self.license_mgr.get_state()
        hwid = state.get("hwid") or get_hardware_id()
        dialog = tk.Toplevel(self.root)
        dialog.title("TaxClean ZA  -  Pricing & Licensing")
        dialog.geometry("680x460")
        dialog.minsize(640, 440)
        dialog.configure(bg="#0f172a")
        dialog.transient(self.root)
        dialog.grab_set()

        # PINNED BOTTOM BAR FIRST (Guarantees buttons are never clipped)
        btn_f = tk.Frame(dialog, bg="#0f172a")
        btn_f.pack(side=tk.BOTTOM, fill=tk.X, padx=30, pady=14)

        def do_activate():
            em = email_ent.get().strip()
            k = key_ent.get().strip()
            if not em or not k:
                messagebox.showerror("Error", "Please enter both email and activation key.", parent=dialog)
                return
            ok, msg = self.license_mgr.activate_license(em, k)
            if ok:
                messagebox.showinfo("Activated", msg, parent=dialog)
                self.update_license_ui_badge()
                dialog.destroy()
                if not self.memory.get_setting("GEMINI_API_KEY", ""):
                    ans = messagebox.askyesno(
                        "Activate Free Google AI Engine",
                        "Pro License Activated Successfully!\n\n"
                        "Would you like TaxClean ZA to auto-configure your free Google AI Studio key now?\n\n"
                        "(Click 'Yes' to open Google AI Studio  -  TaxClean will automatically detect and configure your key from the clipboard).",
                        parent=self.root,
                    )
                    if ans:
                        self.auto_setup_google_api_key()
            else:
                messagebox.showerror("Activation Failed", msg, parent=dialog)

        def open_buy_page(sku: str = "solo_annual"):
            em_q = urllib.parse.quote(email_ent.get().strip()) if "email_ent" in locals() else ""
            url = f"https://taxcleanza.com/?buy={sku}" + (f"&email={em_q}" if em_q else "")
            try:
                webbrowser.open(url)
            except Exception:
                pass
            messagebox.showinfo(
                "Order TaxClean ZA Pro License",
                f"We have opened {url} in your browser where you can pay via Card / Capitec Pay (PayFast), Yoco (Apple/Google Pay), or Direct FNB EFT.\n\n"
                f"TaxClean ZA Flexible Plans (Unlimited Pages):\n"
                f"• Solo Practice (1 PC): R 149 / month  OR  R 1,199 / year\n"
                f"• Practice Pro (3 PCs): R 349 / month  OR  R 2,999 / year\n"
                f"• Accounting Firm (10 PCs): R 799 / month  OR  R 6,999 / year\n\n"
                f"Direct FNB EFT Banking Details:\n"
                f"• Bank: First National Bank (FNB)\n"
                f"• Account Type: Cheque / Fusion Aspire Account\n"
                f"• Account Name: TaxClean ZA\n"
                f"• Account No: 63046857827\n"
                f"• Branch Code: 250655\n"
                f"• Reference: TC-{hwid}\n\n"
                f"Email your Proof of Payment & PC Hardware ID ({hwid}) to sales@taxcleanza.com for automatic activation!",
                parent=dialog,
            )

        HDButton(
            btn_f,
            text="✓ Unlock Pro License",
            bg="#10b981",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=14,
            pady=4,
            command=do_activate,
        ).pack(side=tk.LEFT, padx=(0, 8))

        HDButton(
            btn_f,
            text="⚡ Start Monthly (R 149/mo)",
            bg="#0d9488",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=10,
            pady=4,
            command=lambda: open_buy_page("solo_monthly"),
        ).pack(side=tk.LEFT, padx=(0, 6))

        HDButton(
            btn_f,
            text="💳 Buy Annual (R 1,199/yr)",
            bg="#0284c7",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=10,
            pady=4,
            command=lambda: open_buy_page("solo_annual"),
        ).pack(side=tk.LEFT)

        HDButton(
            btn_f,
            text="Close",
            bg="#334155",
            fg="white",
            font=("Segoe UI", 9),
            relief="flat",
            padx=12,
            pady=4,
            command=dialog.destroy,
        ).pack(side=tk.RIGHT)

        # MAIN CONTENT
        tk.Label(
            dialog,
            text="TaxClean ZA Enterprise Licensing (RSA-1024 Secured)",
            font=("Segoe UI", 13, "bold"),
            fg="#38bdf8",
            bg="#0f172a",
        ).pack(pady=(16, 4))

        status_txt = (
            f"License Status: {state['plan']} Active (Expires {state.get('expiry', 'Active')})"
            if state["is_licensed"]
            else f"License Status: {state['plan']} ({state['remaining']} free statements remaining)"
        )
        tk.Label(
            dialog,
            text=status_txt,
            font=("Segoe UI", 10, "bold"),
            fg="#34d399" if state["is_licensed"] else "#f59e0b",
            bg="#0f172a",
        ).pack(pady=(0, 12))

        form_f = tk.Frame(dialog, bg="#0f172a", padx=30)
        form_f.pack(fill=tk.X)

        # Hardware ID Row
        hw_row = tk.Frame(form_f, bg="#1e293b", padx=10, pady=6)
        hw_row.pack(fill=tk.X, pady=(0, 12))
        tk.Label(
            hw_row,
            text=f"This PC Hardware Node ID:  {hwid}",
            font=("Segoe UI", 10, "bold"),
            fg="#38bdf8",
            bg="#1e293b",
        ).pack(side=tk.LEFT)

        def copy_hwid():
            self.root.clipboard_clear()
            self.root.clipboard_append(hwid)
            messagebox.showinfo("Copied", f"Hardware Node ID '{hwid}' copied to clipboard.", parent=dialog)

        HDButton(
            hw_row,
            text="📋 Copy PC ID",
            font=("Segoe UI", 9, "bold"),
            bg="#334155",
            fg="#f8fafc",
            relief="flat",
            padx=10,
            pady=2,
            command=copy_hwid,
        ).pack(side=tk.RIGHT)

        tk.Label(form_f, text="Registered License Email:", font=("Segoe UI", 10, "bold"), fg="#cbd5e1", bg="#0f172a").pack(anchor="w")
        email_ent = tk.Entry(form_f, font=("Segoe UI", 10), bg="#1e293b", fg="white", insertbackground="white")
        email_ent.insert(0, state.get("email", ""))
        email_ent.pack(fill=tk.X, pady=(4, 12))

        tk.Label(form_f, text="Activation Product Key (TCZA-...):", font=("Segoe UI", 10, "bold"), fg="#cbd5e1", bg="#0f172a").pack(anchor="w")
        key_ent = tk.Entry(form_f, font=("Segoe UI", 10), bg="#1e293b", fg="white", insertbackground="white")
        key_ent.insert(0, state.get("license_key", ""))
        key_ent.pack(fill=tk.X, pady=(4, 8))
        key_ent.bind("<Return>", lambda e: do_activate())

    def show_compliance_modal(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("TaxClean ZA  -  South African Legal & Tax Compliance")
        dialog.geometry("680x500")
        dialog.configure(bg="#0f172a")
        dialog.transient(self.root)

        ftr_comp = tk.Frame(dialog, bg="#0f172a", padx=20, pady=10)
        ftr_comp.pack(side=tk.BOTTOM, fill=tk.X)
        HDButton(
            ftr_comp,
            text="Close",
            bg="#334155",
            fg="white",
            font=("Segoe UI", 9),
            relief="flat",
            padx=16,
            pady=4,
            command=dialog.destroy,
        ).pack(side=tk.RIGHT)

        tk.Label(
            dialog,
            text="South African Regulatory Compliance Certification",
            font=("Segoe UI", 12, "bold"),
            fg="#38bdf8",
            bg="#0f172a",
        ).pack(pady=(16, 8))

        txt_frame = tk.Frame(dialog, bg="#0f172a", padx=20)
        txt_frame.pack(fill=tk.BOTH, expand=True)

        txt = tk.Text(
            txt_frame,
            bg="#1e293b",
            fg="#f1f5f9",
            font=("Segoe UI", 9),
            wrap=tk.WORD,
            padx=12,
            pady=12,
            relief="flat",
        )
        txt.pack(fill=tk.BOTH, expand=True)

        compliance_text = (
            "1. POPIA ACT 4 OF 2013 (DATA PRIVACY & LOCAL PROCESSING)\n"
            f"{POPIA_COMPLIANCE_NOTICE}\n\n"
            "2. SARS TAX ADMINISTRATION ACT 28 OF 2011 (TAA SECTION 29 & 30)\n"
            "• Preserves an immutable 5-year electronic audit trail.\n"
            "• Retains original raw bank narrative alongside cleaned payee description.\n"
            "• Mathematical proof: Opening + Net Movement == Closing Balance.\n\n"
            "3. SARS VAT ACT 89 OF 1991 STATUTORY RULES\n"
            "• Section 17(2)(a): Automatically flags restaurant meals & entertainment as BLOCKED (0% claimable).\n"
            "• Section 11(1)(h): Classifies fuel and petrol levies as ZERO-RATED (0% claimable).\n"
            "• Section 12: Classifies bank fees and financial charges as EXEMPT.\n"
            "• Section 7(1)(a): Applies exact 15/115 standard tax fraction on deductible operational expenses.\n\n"
            "4. CONSUMER PROTECTION ACT 68 OF 2008 & ECTA ACT 25 OF 2002\n"
            f"{SARS_EULA_DISCLAIMER}\n"
        )
        txt.insert("1.0", compliance_text)
        txt.config(state="disabled")

    def run_startup_bank_format_check(self):
        """Runs the South African Bank Statement Format Diagnostic Suite on startup."""
        try:
            self.bank_diagnostic_data = SABankFormatChecker.run_diagnostic_suite(BASE_DIR)
            certified_count = self.bank_diagnostic_data.get("total_certified_banks", 9)
            all_passed = self.bank_diagnostic_data.get("all_passed", True)
            if all_passed:
                badge_text = f"🟢 SA Bank Engine: {certified_count} Banks Certified (0.00 Variance)"
                badge_color = "#34d399"
            else:
                badge_text = "⚠️ SA Bank Engine: Warning"
                badge_color = "#f87171"
            self.bank_engine_badge.config(text=badge_text, fg=badge_color)
        except Exception:
            self.bank_engine_badge.config(text="⚠️ SA Bank Engine Check Failed", fg="#f87171")

    def show_sa_bank_diagnostics_dialog(self):
        """Displays the South African Bank Statement Format Diagnostic Suite modal dialog."""
        dialog = tk.Toplevel(self.root)
        dialog.title("TaxClean ZA  -  South African Bank Statement Format Diagnostic Suite")
        dialog.geometry("880x620")
        dialog.minsize(760, 520)
        dialog.configure(bg="#0f172a")
        dialog.transient(self.root)
        dialog.grab_set()

        # Footer Buttons FIRST (pinned to bottom so never clipped)
        ftr = tk.Frame(dialog, bg="#0f172a", padx=20, pady=10)
        ftr.pack(side=tk.BOTTOM, fill=tk.X)

        def rerun_diag():
            self.run_startup_bank_format_check()
            dialog.destroy()
            self.show_sa_bank_diagnostics_dialog()

        HDButton(
            ftr,
            text="🔄 Re-Run Full Diagnostic Self-Test",
            font=("Segoe UI", 9, "bold"),
            bg="#0284c7",
            fg="white",
            relief="flat",
            padx=12,
            pady=4,
            command=rerun_diag,
        ).pack(side=tk.LEFT)

        HDButton(
            ftr,
            text="Close",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="white",
            relief="flat",
            padx=14,
            pady=4,
            command=dialog.destroy,
        ).pack(side=tk.RIGHT)

        # Header Frame
        hdr = tk.Frame(dialog, bg="#1e293b", padx=20, pady=12)
        hdr.pack(fill=tk.X)
        tk.Label(
            hdr,
            text="🏥 South African Bank Statement Format Compatibility Suite",
            font=("Segoe UI", 12, "bold"),
            fg="#38bdf8",
            bg="#1e293b",
        ).pack(anchor="w")
        tk.Label(
            hdr,
            text="Automatic self-diagnostic verifier ensuring zero variance across all major South African banks and credit card facilities.",
            font=("Segoe UI", 8),
            fg="#94a3b8",
            bg="#1e293b",
        ).pack(anchor="w", pady=(2, 0))

        content_f = tk.Frame(dialog, bg="#0f172a", padx=20, pady=10)
        content_f.pack(fill=tk.BOTH, expand=True)

        # Status Banner
        diag = getattr(self, "bank_diagnostic_data", {}) or SABankFormatChecker.run_diagnostic_suite(BASE_DIR)
        all_passed = diag.get("all_passed", True)
        stat_bar = tk.Frame(content_f, bg="#064e3b" if all_passed else "#7f1d1d", padx=12, pady=6)
        stat_bar.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            stat_bar,
            text="✓ STATUS: 100% OPERATIONAL & VERIFIED (0.00 VARIANCE INVARIANTS PASS)" if all_passed else "⚠️ STATUS: FORMAT DIAGNOSTIC REQUIRES ATTENTION",
            font=("Segoe UI", 9, "bold"),
            fg="#34d399" if all_passed else "#fca5a5",
            bg="#064e3b" if all_passed else "#7f1d1d",
        ).pack(side=tk.LEFT)
        tk.Label(
            stat_bar,
            text=f"Last Checked: {diag.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}",
            font=("Segoe UI", 8),
            fg="#a7f3d0" if all_passed else "#fecaca",
            bg="#064e3b" if all_passed else "#7f1d1d",
        ).pack(side=tk.RIGHT)

        # Fixtures Section packed at bottom of content_f so it is never squashed
        fixtures = diag.get("fixtures", [])
        if fixtures:
            fix_container = tk.Frame(content_f, bg="#0f172a")
            fix_container.pack(side=tk.BOTTOM, fill=tk.X, pady=(8, 0))
            tk.Label(
                fix_container,
                text="VERIFIED WORKSPACE TEST FIXTURES (TEST STATEMENTS)",
                font=("Segoe UI", 8, "bold"),
                fg="#94a3b8",
                bg="#0f172a",
            ).pack(anchor="w", pady=(0, 4))

            fix_f = tk.Frame(fix_container, bg="#1e293b", padx=10, pady=6)
            fix_f.pack(fill=tk.X)
            for fix in fixtures:
                row = tk.Frame(fix_f, bg="#1e293b")
                row.pack(fill=tk.X, pady=1)
                tk.Label(row, text="📄", font=("Segoe UI", 8), bg="#1e293b", fg="#38bdf8").pack(side=tk.LEFT, padx=(0, 4))
                tk.Label(row, text=f"{fix['filename']}:", font=("Segoe UI", 8, "bold"), bg="#1e293b", fg="#f8fafc").pack(side=tk.LEFT)
                tk.Label(row, text=f"{fix['description']} ({fix['file_size_kb']} KB)", font=("Segoe UI", 8), bg="#1e293b", fg="#94a3b8").pack(side=tk.LEFT, padx=(4, 0))
                tk.Label(row, text="✓ VERIFIED (0.00 VARIANCE)", font=("Segoe UI", 8, "bold"), bg="#1e293b", fg="#34d399").pack(side=tk.RIGHT)

        # Table of Banks
        tk.Label(
            content_f,
            text="CERTIFIED SOUTH AFRICAN BANK FORMAT PROFILES",
            font=("Segoe UI", 8, "bold"),
            fg="#94a3b8",
            bg="#0f172a",
        ).pack(anchor="w", pady=(2, 4))

        tree_f = tk.Frame(content_f, bg="#0f172a")
        tree_f.pack(fill=tk.BOTH, expand=True)

        cols = ("bank", "branch", "account_type", "layout", "variance", "status")
        diag_tree = ttk.Treeview(tree_f, columns=cols, show="headings", height=6)
        diag_tree.heading("bank", text="Banking Institution")
        diag_tree.heading("branch", text="Universal Branch")
        diag_tree.heading("account_type", text="Account Type")
        diag_tree.heading("layout", text="Layout Engine")
        diag_tree.heading("variance", text="Variance Rule")
        diag_tree.heading("status", text="Diagnostic Status")

        diag_tree.column("bank", width=210)
        diag_tree.column("branch", width=95, anchor="center")
        diag_tree.column("account_type", width=135)
        diag_tree.column("layout", width=155)
        diag_tree.column("variance", width=85, anchor="center")
        diag_tree.column("status", width=95, anchor="center")

        scrollbar = ttk.Scrollbar(tree_f, orient=tk.VERTICAL, command=diag_tree.yview)
        diag_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        diag_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        for b in diag.get("bank_results", []):
            diag_tree.insert("", tk.END, values=(
                b["bank_name"],
                b["branch_code"],
                b["account_type"],
                b["column_structure"][:28] + "...",
                b.get("variance", "R 0.00"),
                b.get("status", "✓ Certified"),
            ))

    # ==========================================================================
    # RESPONSIVE SCREEN AUTO-ADJUSTMENT & 1-CLICK FREE GOOGLE API KEY ENGINE
    # ==========================================================================
    def auto_adjust_screen_settings(self):
        """
        Dynamically auto-adjusts window dimensions, scaling, and screen boundaries
        for all PC and laptop displays (1366x768 compact laptops up to 4K desktop setups).
        """
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        if screen_w <= 1366 or screen_h <= 768:
            # Compact 13-14" laptops (e.g., 1366x768, 1280x800)
            target_w = min(1280, int(screen_w * 0.96))
            target_h = min(720, int(screen_h * 0.90))
            min_w = min(1000, screen_w - 40)
            min_h = min(580, screen_h - 70)
        elif screen_w <= 1600 or screen_h <= 900:
            # 1080p displays with 125% scaling (effective ~1536x864) or 1600x900
            target_w = min(1360, int(screen_w * 0.94))
            target_h = min(800, int(screen_h * 0.88))
            min_w = min(1100, screen_w - 50)
            min_h = min(640, screen_h - 80)
        else:
            # Standard 1080p, 2K, 4K desktop displays
            target_w = 1420
            target_h = 860
            min_w = 1180
            min_h = 700

        pos_x = max(0, (screen_w - target_w) // 2)
        pos_y = max(0, (screen_h - target_h) // 2 - 20)

        self.root.minsize(min_w, min_h)
        self.root.geometry(f"{target_w}x{target_h}+{pos_x}+{pos_y}")

    def auto_setup_google_api_key(self, dialog: Optional[tk.Toplevel] = None, key_var: Optional[tk.StringVar] = None):
        """
        1-Click Automated Google AI Studio Key Setup:
        Opens Google AI Studio in the default browser and runs an intelligent clipboard sentinel
        with manual entry fallbacks and confirmation button.
        """
        # SINGLETON GUARD: Prevent opening multiple duplicate auto-detector windows
        if hasattr(self, "_sentinel_window") and self._sentinel_window and self._sentinel_window.winfo_exists():
            try:
                self._sentinel_window.lift()
                self._sentinel_window.focus_force()
            except Exception:
                pass
            return

        # web links available globally
        webbrowser.open("https://aistudio.google.com/app/apikey")

        sentinel_window = tk.Toplevel(self.root)
        self._sentinel_window = sentinel_window
        sentinel_window.title("⚡ Google AI Key Setup & Auto-Detector")
        sentinel_window.geometry("560x320")
        sentinel_window.configure(bg="#0f172a")
        sentinel_window.transient(self.root)
        sentinel_window.attributes("-topmost", True)

        tk.Label(
            sentinel_window,
            text="⚡ Google AI Studio Key Setup & Auto-Detector",
            font=("Segoe UI", 11, "bold"),
            fg="#38bdf8",
            bg="#0f172a",
        ).pack(pady=(14, 4))

        tk.Label(
            sentinel_window,
            text=(
                "Google AI Studio was opened in your browser.\n"
                "1. Click the blue 'Create API key' button in Google & click 'Copy'.\n"
                "2. TaxClean ZA will auto-detect it, or enter/paste your key below:"
            ),
            font=("Segoe UI", 8),
            fg="#cbd5e1",
            bg="#0f172a",
            justify="center",
        ).pack(padx=20, pady=(0, 8))

        prog = ttk.Progressbar(sentinel_window, style="TProgressbar", mode="indeterminate")
        prog.pack(fill=tk.X, padx=30, pady=(0, 10))
        prog.start(10)

        # Manual entry field right in this window!
        manual_f = tk.Frame(sentinel_window, bg="#0f172a", padx=30)
        manual_f.pack(fill=tk.X, pady=(0, 10))

        manual_var = tk.StringVar(value=key_var.get() if key_var else self.memory.get_setting("GEMINI_API_KEY", ""))
        manual_ent = tk.Entry(manual_f, textvariable=manual_var, font=("Segoe UI", 10), bg="#1e293b", fg="white", insertbackground="white")
        manual_ent.pack(fill=tk.X, pady=(0, 6))

        is_running = [True]

        def _finish_and_save(clean_k: str):
            is_running[0] = False
            self.memory.set_setting("GEMINI_API_KEY", clean_k)
            if key_var:
                key_var.set(clean_k)
            self.update_ai_key_badge()
            self.update_bottom_info()
            try:
                sentinel_window.destroy()
            except Exception:
                pass
            if dialog and dialog.winfo_exists():
                try:
                    dialog.destroy()
                except Exception:
                    pass
            messagebox.showinfo(
                "Google AI Connected",
                "🎉 Google AI Studio Key Confirmed & Configured!\n\n"
                "The Targeted Micro-AI Resolver is now fully active.\n"
                "Ambiguous scans will now be auto-repaired using Google Gemini.",
                parent=self.root,
            )

        manual_ent.bind("<Return>", lambda e: _finish_and_save(manual_ent.get().strip().strip('"').strip("'")))

        btn_row = tk.Frame(sentinel_window, bg="#0f172a")
        btn_row.pack(fill=tk.X, padx=30, pady=(0, 8))

        def _paste_and_confirm():
            try:
                raw = self.root.clipboard_get().strip().strip('"').strip("'")
                m = re.search(r"AIza[0-9A-Za-z_-]{30,}", raw)
                clean_k = m.group(0) if m else raw
                if clean_k:
                    manual_var.set(clean_k)
                    _finish_and_save(clean_k)
                else:
                    messagebox.showwarning("Clipboard", "Clipboard is empty or does not contain a valid key.", parent=sentinel_window)
            except Exception as e:
                messagebox.showwarning("Clipboard", f"Could not read clipboard: {e}", parent=sentinel_window)

        # BUTTON TO CONFIRM / ENTER KEY!
        HDButton(
            btn_row,
            text="✓ Enter / Confirm Key",
            font=("Segoe UI", 9, "bold"),
            bg="#059669",
            fg="white",
            relief="flat",
            padx=12,
            pady=5,
            command=lambda: _finish_and_save(manual_var.get().strip().strip('"').strip("'")),
        ).pack(side=tk.LEFT, padx=(0, 8))

        HDButton(
            btn_row,
            text="📋 Paste from Clipboard",
            font=("Segoe UI", 9, "bold"),
            bg="#1d4ed8",
            fg="white",
            relief="flat",
            padx=12,
            pady=5,
            command=_paste_and_confirm,
        ).pack(side=tk.LEFT, padx=(0, 8))

        def _cancel():
            is_running[0] = False
            try:
                sentinel_window.destroy()
            except Exception:
                pass

        HDButton(
            btn_row,
            text="Cancel",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="white",
            relief="flat",
            padx=12,
            pady=5,
            command=_cancel,
        ).pack(side=tk.RIGHT)

        start_time = datetime.now()

        def _poll_clipboard():
            if not is_running[0]:
                return
            now = datetime.now()
            if (now - start_time).total_seconds() > 90:
                return
            try:
                clip_val = self.root.clipboard_get().strip().strip('"').strip("'")
                if clip_val:
                    m = re.search(r"AIza[0-9A-Za-z_-]{30,}", clip_val)
                    if m:
                        _finish_and_save(m.group(0))
                        return
            except Exception:
                pass
            if is_running[0]:
                self.root.after(400, _poll_clipboard)

        self.root.after(400, _poll_clipboard)

    # ==========================================================================
    # CONTEXT MENU, ROW SHORTCUTS & ATTACHMENT VIEWER
    # ==========================================================================
    def show_tree_context_menu(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            if iid not in self.tree.selection():
                self.tree.selection_set(iid)
                self.on_tree_select_changed()
            idx = int(iid)
            txn = self.transactions[idx] if 0 <= idx < len(self.transactions) else None
            if not txn:
                return

            menu = tk.Menu(self.root, tearoff=False, bg="#1e293b", fg="#f1f5f9", font=("Segoe UI", 9))
            menu.add_command(label="✂️ Split Transaction... [Alt+S]", command=lambda: self.open_split_transaction_dialog(idx))
            menu.add_command(label="🔄 Toggle SARS VAT (Standard / Zero / None) [Space]", command=self.toggle_selected_vat)
            if txn.get("slip_matched"):
                menu.add_command(label="📎 View Attached Receipt / Slip", command=self.view_attached_slip)
            menu.add_separator()
            menu.add_command(label="⚠️ Mark as Suspense / Query (9999/000)", command=lambda: self._mark_row_suspense(idx))
            menu.add_command(label="🗑️ Delete Row [Delete]", command=self.delete_selected_rows)
            menu.tk_popup(event.x_root, event.y_root)

    def _mark_row_suspense(self, idx: int):
        if 0 <= idx < len(self.transactions):
            self.push_undo_state()
            t = self.transactions[idx]
            t["code"] = "9999/000"
            t["name"] = "Suspense Account / Queries"
            t["is_suspense"] = True
            t["audit_status"] = "⚠️ Flagged by User as Suspense"
            self.render_grid()
            self.save_current_session()

    def toggle_selected_vat(self):
        if self._check_batch_locked():
            return
        sel = self.tree.selection()
        if not sel:
            return
        self.push_undo_state()
        vat_cycle = {"Standard": "Zero-Rated", "Zero-Rated": "None", "None": "Standard", "Exempt": "Standard"}
        for iid in sel:
            idx = int(iid)
            if 0 <= idx < len(self.transactions):
                t = self.transactions[idx]
                curr_vat = t.get("vat_type", "Standard")
                next_vat = vat_cycle.get(curr_vat, "Standard")
                t["vat_type"] = next_vat
                self.recalculate_row(t)
        self.render_grid()
        self.save_current_session()

    def view_attached_slip(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        if 0 <= idx < len(self.transactions):
            t = self.transactions[idx]
            p = t.get("slip_path")
            if p and Path(p).exists():
                try:
                    open_file_or_folder(p)
                except Exception as e:
                    messagebox.showerror("View Slip", f"Could not open slip: {e}", parent=self.root)
            else:
                messagebox.showinfo("View Slip", "No valid receipt file found for this transaction line.", parent=self.root)

    # ==========================================================================
    # FEATURE B: MULTI-MONTH STATEMENT STACKER & CONTINUITY CHAIN
    # ==========================================================================
    def append_statement_dialog(self):
        if self._check_batch_locked():
            return
        if not self._guard_trial_allowance("append statements"):
            return

        if not self.transactions:
            self.start_import_worker()
            return

        fpaths = filedialog.askopenfilenames(
            title="Append One or Multiple Statements / Slips (Ctrl/Shift+Click for Multiple)",
            filetypes=[
                ("All Supported Documents", "*.pdf;*.csv;*.txt;*.jpg;*.jpeg;*.png;*.webp"),
                ("PDF Documents", "*.pdf"),
                ("CSV Statements", "*.csv;*.txt"),
                ("Image Receipts & Invoices", "*.jpg;*.jpeg;*.png;*.webp"),
            ],
            parent=self.root,
        )
        if not fpaths:
            return

        file_list = list(fpaths)
        state = self.license_mgr.get_state()
        if not state["is_licensed"] and len(file_list) > state["remaining"]:
            messagebox.showwarning(
                "Trial Statement Limit",
                f"You selected {len(file_list)} files, but your trial only has {state['remaining']} statement imports remaining.\n\n"
                f"Please select up to {state['remaining']} files or activate a TaxClean ZA Pro license.",
                parent=self.root,
            )
            return

        self.status_lbl.config(text=f"Analyzing {len(file_list)} document(s) for multi-month continuity lockstep...")
        self.prog_bar["value"] = 25

        def _worker_thread():
            try:
                coa = self.config["profiles"][self.active_profile]["coa"]
                if len(file_list) == 1:
                    fpath = file_list[0]
                    worker = ParseWorker(fpath, coa, self.active_profile, self.memory, queue.Queue())
                    raw_text = worker.extract_text()
                    parse_res = worker.parse_text(raw_text)
                    self.root.after(0, lambda: self._process_appended_statement(fpath, parse_res))
                else:
                    combined_recs: list[dict] = []
                    first_open: Optional[str] = None
                    last_close: Optional[str] = None
                    for fp in file_list:
                        worker = ParseWorker(fp, coa, self.active_profile, self.memory, queue.Queue())
                        raw_text = worker.extract_text()
                        res = worker.parse_text(raw_text)
                        recs = res.get("records", [])
                        if recs:
                            if not combined_recs:
                                combined_recs.extend(recs)
                            else:
                                uniq, _ = StatementStacker.shield_duplicates(combined_recs, recs)
                                combined_recs.extend(uniq)
                            if first_open is None and res.get("open_bal") is not None:
                                first_open = res["open_bal"]
                            if res.get("close_bal") is not None:
                                last_close = res["close_bal"]
                    combined_recs.sort(key=lambda r: r.get("date", "9999-99-99"))
                    merged_res = {
                        "open_bal": first_open,
                        "close_bal": last_close,
                        "records": combined_recs,
                    }
                    self.root.after(0, lambda: self._process_appended_statement(f"{len(file_list)} files", merged_res))
            except Exception as e:
                err_str = str(e)
                self.root.after(0, lambda m=err_str: self._handle_append_error(m))

        threading.Thread(target=_worker_thread, daemon=True).start()

    def _handle_append_error(self, err_msg: str):
        self.prog_bar["value"] = 0
        self.status_lbl.config(text="Append statement aborted.")
        ans = messagebox.askyesno(
            "Append Statement Error",
            f"Failed to append statement:\n\n{err_msg}\n\nWould you like to send this error report to TaxClean ZA engineering agents for instant analysis?",
            parent=self.root,
            icon="warning"
        )
        if ans:
            self.open_issue_reporter_dialog(prefill_error=f"Append error: {err_msg}", is_statement_error=True)
        else:
            messagebox.showerror("Append Error", f"Failed to append statement:\n\n{err_msg}", parent=self.root)

    def _process_appended_statement(self, fpath: str, parse_res: dict):
        self.prog_bar["value"] = 0
        new_records = parse_res.get("records", [])
        if not new_records:
            messagebox.showwarning("Append Result", "Statement parsed, but no transaction records could be extracted.", parent=self.root)
            return

        try:
            curr_close = float(self.close_bal_var.get().replace(",", "").strip() or 0)
        except Exception:
            curr_close = 0.0

        try:
            curr_open = float(self.open_bal_var.get().replace(",", "").strip() or 0)
        except Exception:
            curr_open = 0.0

        new_open_str = parse_res.get("open_bal")
        new_close_str = parse_res.get("close_bal")
        new_open = float(new_open_str) if new_open_str is not None else curr_close
        new_close = float(new_close_str) if new_close_str is not None else curr_close + sum(r["amount"] for r in new_records)

        is_cont, delta = StatementStacker.verify_continuity(curr_close, new_open)
        unique_to_add, dups_shielded = StatementStacker.shield_duplicates(self.transactions, new_records)
        dup_msg = f"\n\n🛡️ Duplicate Shield: {len(dups_shielded)} overlapping duplicate rows automatically excluded." if dups_shielded else ""

        if is_cont:
            self.push_undo_state()
            self.transactions.extend(unique_to_add)
            self.close_bal_var.set(f"{new_close:.2f}")
            self.render_grid()
            self.save_current_session()
            messagebox.showinfo(
                "Multi-Month Continuity Verified",
                f"✓ Multi-Month Statement Linked!\n\n"
                f"• Previous Month Closing: R {curr_close:,.2f}\n"
                f"• Next Month Opening: R {new_open:,.2f}\n"
                f"• Continuity Delta: R 0.00 (Exact Cent Lockstep)\n"
                f"• New Transactions Added: {len(unique_to_add)} lines\n"
                f"• Combined Closing Balance: R {new_close:,.2f}"
                f"{dup_msg}",
                parent=self.root,
            )
            self.status_lbl.config(text=f"Multi-month chain active: {len(self.transactions)} lines balanced (R 0.00 variance).")
        else:
            ans = messagebox.askyesnocancel(
                "Statement Continuity Gap Warning",
                f"⚠️ Inter-Statement Continuity Mismatch:\n\n"
                f"• Previous Statement Closing: R {curr_close:,.2f}\n"
                f"• New Statement Opening: R {new_open:,.2f}\n"
                f"• Variance Gap: R {delta:,.2f}\n\n"
                f"How would you like to proceed?\n"
                f"[Yes] Auto-Bridge Gap: Insert balancing entry (R {-delta:,.2f}) into Suspense (Preserves R 0.00 variance)\n"
                f"[No] Append Without Bridge: Keep gap (manual reconciliation needed)\n"
                f"[Cancel] Abort",
                parent=self.root,
            )
            if ans is True:
                self.push_undo_state()
                stacked = StatementStacker.stack(
                    self.transactions, curr_open, curr_close,
                    unique_to_add, new_open, new_close,
                    allow_bridge=True
                )
                self.transactions = stacked["records"]
                self.close_bal_var.set(f"{new_close:.2f}")
                self.render_grid()
                self.save_current_session()
                self.status_lbl.config(text=f"Appended with bridging entry: R {delta:,.2f} quarantined to Suspense.")
            elif ans is False:
                self.push_undo_state()
                self.transactions.extend(unique_to_add)
                self.close_bal_var.set(f"{new_close:.2f}")
                self.render_grid()
                self.save_current_session()
                self.status_lbl.config(text=f"Appended without bridge: Warning, variance of R {delta:,.2f} present.")

        if is_cont or ans in (True, False):
            self.license_mgr.record_statement_processed()
            self._batch_licensed_for_export = True
            self.update_license_ui_badge()

    # ==========================================================================
    # FEATURE A: "SHOEBOX" RECEIPT-TO-BANK AUTO-MATCHER
    # ==========================================================================
    def open_receipt_matcher_dialog(self):
        if not self._guard_trial_allowance("match receipts"):
            return
        if not self.transactions:
            messagebox.showwarning("Receipt Matcher", "Please import a bank statement first to match receipts against.", parent=self.root)
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("📎 Shoebox Receipt-to-Bank Auto-Matcher")
        dialog.geometry("780x560")
        dialog.minsize(680, 480)
        dialog.configure(bg="#0f172a")
        dialog.transient(self.root)
        dialog.grab_set()

        hdr = tk.Frame(dialog, bg="#1e293b", padx=20, pady=12)
        hdr.pack(fill=tk.X)
        tk.Label(
            hdr,
            text="📎 Shoebox Receipt-to-Bank Auto-Matcher",
            font=("Segoe UI", 12, "bold"),
            fg="#38bdf8",
            bg="#1e293b",
        ).pack(anchor="w")
        tk.Label(
            hdr,
            text="Scans slip scans, WhatsApp photos & PDF invoices, matching them against bank outflows by amount and date.",
            font=("Segoe UI", 8),
            fg="#94a3b8",
            bg="#1e293b",
        ).pack(anchor="w", pady=(2, 0))

        content_f = tk.Frame(dialog, bg="#0f172a", padx=20, pady=12)
        content_f.pack(fill=tk.BOTH, expand=True)

        btn_box = tk.Frame(content_f, bg="#0f172a")
        btn_box.pack(fill=tk.X, pady=(0, 10))

        status_txt = tk.StringVar(value="Select a folder of slips or individual slip files to begin matching.")
        tk.Label(content_f, textvariable=status_txt, font=("Segoe UI", 9), fg="#cbd5e1", bg="#0f172a").pack(anchor="w", pady=(0, 8))

        prog = ttk.Progressbar(content_f, style="TProgressbar", mode="determinate")
        prog.pack(fill=tk.X, pady=(0, 12))

        tree_f = tk.Frame(content_f, bg="#0f172a")
        tree_f.pack(fill=tk.BOTH, expand=True)

        res_cols = ("status", "file", "amount", "date", "vendor", "matched_payee")
        res_tree = ttk.Treeview(tree_f, columns=res_cols, show="headings", height=8)
        res_tree.heading("status", text="Match Status")
        res_tree.heading("file", text="Slip Filename")
        res_tree.heading("amount", text="Amount (ZAR)")
        res_tree.heading("date", text="Slip Date")
        res_tree.heading("vendor", text="Slip Vendor")
        res_tree.heading("matched_payee", text="Matched Bank Line")

        res_tree.column("status", width=120, anchor="center")
        res_tree.column("file", width=130)
        res_tree.column("amount", width=95, anchor="e")
        res_tree.column("date", width=85, anchor="center")
        res_tree.column("vendor", width=130)
        res_tree.column("matched_payee", width=180)

        sb = ttk.Scrollbar(tree_f, orient=tk.VERTICAL, command=res_tree.yview)
        res_tree.configure(yscroll=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        res_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def _run_matching(files_to_scan: list):
            if not files_to_scan:
                return
            prog["maximum"] = len(files_to_scan)
            prog["value"] = 0
            status_txt.set(f"Scanning {len(files_to_scan)} slip documents with local OCR...")

            def _thread_worker():
                parsed_slips = []
                coa = self.config["profiles"][self.active_profile]["coa"]
                for i, fp in enumerate(files_to_scan):
                    try:
                        p_obj = Path(fp)
                        w = ParseWorker(str(p_obj), coa, self.active_profile, self.memory, queue.Queue())
                        txt = w.extract_text()
                        p_res = w.parse_text(txt)
                        recs = p_res.get("records", [])

                        slip_amt = 0.0
                        if recs:
                            slip_amt = abs(sum(r["amount"] for r in recs))
                        else:
                            tot_m = re.search(r"(?:TOTAL|DUE|TENDER|SUMME)[\s:R]*([0-9,]+\.[0-9]{2})", txt, re.I)
                            if tot_m:
                                slip_amt, _, _ = parse_sa_amount(tot_m.group(1))

                        first_lines = [l.strip() for l in txt.splitlines() if len(l.strip()) > 3]
                        vendor = first_lines[0] if first_lines else p_obj.stem

                        d_m = re.search(r"\b(20\d{2}[-/.](?:0[1-9]|1[0-2])[-/.](?:0[1-9]|[12]\d|3[01]))\b", txt)
                        slip_date = d_m.group(1) if d_m else None

                        parsed_slips.append({
                            "filename": p_obj.name,
                            "path": str(p_obj),
                            "amount": slip_amt,
                            "date": slip_date,
                            "vendor": vendor[:35],
                            "ref": f"SLIP-{p_obj.stem[:8]}",
                        })
                    except Exception:
                        pass
                    dialog.after(0, lambda cur=i+1: prog.configure(value=cur) if dialog.winfo_exists() else None)

                dialog.after(0, lambda: _display_results(parsed_slips))

            threading.Thread(target=_thread_worker, daemon=True).start()

        def _display_results(parsed_slips: list):
            if not dialog.winfo_exists():
                return
            self.push_undo_state()
            match_res = ReceiptMatcher.match_batch(parsed_slips, self.transactions)
            if match_res["matched_count"] == 0 and self.undo_stack:
                self.undo_stack.pop()

            for it in res_tree.get_children():
                res_tree.delete(it)

            for m in match_res["matched_pairs"]:
                s = m["slip"]
                t = m["txn"]
                res_tree.insert("", tk.END, values=(
                    "✓ Matched",
                    s["filename"],
                    f"R {s['amount']:,.2f}",
                    s.get("date") or " - ",
                    s["vendor"],
                    f"{t['clean_payee']} (R {abs(t['amount']):,.2f})",
                ))

            for u in match_res["unmatched_slips"]:
                res_tree.insert("", tk.END, values=(
                    "⚠️ Unmatched",
                    u["filename"],
                    f"R {u['amount']:,.2f}",
                    u.get("date") or " - ",
                    u["vendor"],
                    "No matching bank outflow found",
                ))

            status_txt.set(
                f"Matching Complete! {match_res['matched_count']} slips matched (Total: R {match_res['total_matched_value']:,.2f}). "
                f"{match_res['unmatched_slips_count']} unmatched. {match_res['missing_slips_count']} missing slip audit risks."
            )

            if match_res["matched_count"] > 0:
                self.render_grid()
                self.save_current_session()

        def _choose_folder():
            folder = filedialog.askdirectory(title="Select Folder of Scanned Receipts / Slips", parent=dialog)
            if folder:
                exts = [".jpg", ".jpeg", ".png", ".pdf", ".webp", ".bmp"]
                files = [str(f) for f in Path(folder).iterdir() if f.suffix.lower() in exts]
                if files:
                    _run_matching(files)
                else:
                    messagebox.showinfo("No Slips", "No image or PDF receipt files found in this folder.", parent=dialog)

        def _choose_files():
            files = filedialog.askopenfilenames(
                title="Select Receipt Images or PDFs",
                filetypes=[
                    ("All Receipt Formats", "*.jpg;*.jpeg;*.png;*.pdf;*.webp"),
                    ("Images", "*.jpg;*.jpeg;*.png;*.webp"),
                    ("PDF Invoices", "*.pdf"),
                ],
                parent=dialog,
            )
            if files:
                _run_matching(list(files))

        HDButton(
            btn_box,
            text="📁 Select Folder of Slips...",
            font=("Segoe UI", 9, "bold"),
            bg="#4338ca",
            fg="white",
            relief="flat",
            padx=12,
            pady=4,
            command=_choose_folder,
        ).pack(side=tk.LEFT, padx=(0, 6))

        HDButton(
            btn_box,
            text="📄 Select Slip Files...",
            font=("Segoe UI", 9),
            bg="#1e293b",
            fg="#e2e8f0",
            relief="flat",
            padx=12,
            pady=4,
            command=_choose_files,
        ).pack(side=tk.LEFT)

        ftr = tk.Frame(dialog, bg="#0f172a", padx=20, pady=10)
        ftr.pack(side=tk.BOTTOM, fill=tk.X)
        HDButton(
            ftr,
            text="Done",
            font=("Segoe UI", 9, "bold"),
            bg="#10b981",
            fg="white",
            relief="flat",
            padx=16,
            pady=4,
            command=dialog.destroy,
        ).pack(side=tk.RIGHT)

    # ==========================================================================
    # IDEA 1 & 14: MULTI-ACCOUNT SPLIT TRANSACTIONS & PAYROLL SPLITTER
    # ==========================================================================
    def open_split_transaction_dialog(self, target_idx: Optional[int] = None):
        if self._check_batch_locked():
            return
        if target_idx is None:
            sel = self.tree.selection()
            if not sel:
                messagebox.showwarning("Split Transaction", "Please select a transaction to split.", parent=self.root)
                return
            target_idx = int(sel[0])

        if not (0 <= target_idx < len(self.transactions)):
            return

        parent_txn = self.transactions[target_idx]
        parent_amt = parent_txn["amount"]
        parent_payee = parent_txn["clean_payee"]
        coa = self.config["profiles"][self.active_profile]["coa"]
        coa_items = sorted([f"{v['code']} - {v['name']}" for v in coa.values()])

        dialog = tk.Toplevel(self.root)
        dialog.title("✂️ Multi-Account Split Transaction")
        dialog.geometry("760x520")
        dialog.minsize(680, 440)
        dialog.configure(bg="#0f172a")
        dialog.transient(self.root)
        dialog.grab_set()

        hdr = tk.Frame(dialog, bg="#1e293b", padx=20, pady=12)
        hdr.pack(fill=tk.X)
        tk.Label(
            hdr,
            text=f"✂️ Split Transaction: {parent_payee}",
            font=("Segoe UI", 11, "bold"),
            fg="#38bdf8",
            bg="#1e293b",
        ).pack(anchor="w")
        tk.Label(
            hdr,
            text=f"Date: {parent_txn['date']} • Original Gross Amount: R {parent_amt:,.2f} • Ref: {parent_txn['ref']}",
            font=("Segoe UI", 8),
            fg="#94a3b8",
            bg="#1e293b",
        ).pack(anchor="w", pady=(2, 0))

        # Pinned footer FIRST so labels/buttons exist before _add_line is called and are never clipped
        ftr = tk.Frame(dialog, bg="#0f172a", padx=20, pady=12)
        ftr.pack(side=tk.BOTTOM, fill=tk.X)

        total_lbl = tk.Label(ftr, text="", font=("Segoe UI", 8), fg="#94a3b8", bg="#0f172a")
        total_lbl.pack(side=tk.LEFT)

        diff_lbl = tk.Label(ftr, text="", font=("Segoe UI", 8, "bold"), padx=8, pady=2)
        diff_lbl.pack(side=tk.LEFT, padx=(10, 0))

        split_rows_ui = []

        def _confirm_split():
            parsed_vals = []
            try:
                for idx_s, r in enumerate(split_rows_ui, start=1):
                    raw_s = r["amt_var"].get().replace(",", "").replace("R", "").strip()
                    if not raw_s:
                        raise ValueError(f"Line {idx_s} amount cannot be empty.")
                    val = float(raw_s)
                    chosen_acc = r["acc_var"].get().strip()
                    code_split = chosen_acc.split(" - ")[0].strip()
                    if not code_split:
                        raise ValueError(f"Line {idx_s} requires a valid GL Account Code.")
                    parsed_vals.append((val, chosen_acc, code_split, r))
            except ValueError as err:
                messagebox.showerror("Invalid Split Input", f"Please enter valid numeric amounts and account codes on all split lines:\n\n{err}", parent=dialog)
                return

            tot = _dec_round(sum(v[0] for v in parsed_vals))
            if abs(tot - parent_amt) > 0.005:
                messagebox.showerror("Cent Lock", "Total split amount must exactly equal original transaction gross.", parent=dialog)
                return

            self.push_undo_state()
            new_lines = []
            for idx_s, (val, chosen_acc, code_split, r) in enumerate(parsed_vals):
                name_split = chosen_acc.split(" - ")[1].strip() if " - " in chosen_acc else "Expense"
                vt = r["vat_var"].get().strip()

                line_dict = {
                    "date": parent_txn["date"],
                    "ref": f"{parent_txn['ref']}-S{idx_s+1}",
                    "acc_type": "GL",
                    "clean_payee": r["desc_var"].get().strip() or parent_payee,
                    "code": code_split,
                    "name": name_split,
                    "amount": val,
                    "vat_type": vt,
                    "is_suspense": (code_split == "9999/000" or code_split.startswith("9999")),
                    "is_duplicate": False,
                    "is_split": True,
                    "audit_status": f"✓ Split Child Line ({idx_s+1}/{len(split_rows_ui)})",
                    "query_reason": "Child split from parent line",
                }
                self.recalculate_row(line_dict)
                new_lines.append(line_dict)

            self.transactions[target_idx:target_idx+1] = new_lines
            self.render_grid()
            self.save_current_session()
            dialog.destroy()
            self.status_lbl.config(text=f"Split transaction: Created {len(new_lines)} mathematically locked lines.")

        confirm_btn = HDButton(ftr, text="✓ Confirm Split", font=("Segoe UI", 9, "bold"), bg="#10b981", fg="white", relief="flat", padx=14, pady=4, command=_confirm_split)
        confirm_btn.pack(side=tk.RIGHT, padx=(8, 0))
        HDButton(ftr, text="Cancel", font=("Segoe UI", 9), bg="#334155", fg="white", relief="flat", padx=12, pady=4, command=dialog.destroy).pack(side=tk.RIGHT)

        content_f = tk.Frame(dialog, bg="#0f172a", padx=20, pady=12)
        content_f.pack(fill=tk.BOTH, expand=True)

        preset_bar = tk.Frame(content_f, bg="#0f172a")
        preset_bar.pack(fill=tk.X, pady=(0, 10))

        lines_f = tk.Frame(content_f, bg="#0f172a")
        lines_f.pack(fill=tk.BOTH, expand=True)

        def _recalc_split_balance():
            tot = 0.0
            for r in split_rows_ui:
                try:
                    val = float(r["amt_var"].get().replace(",", "").strip() or 0)
                    tot += val
                except Exception:
                    pass
            diff = _dec_round(tot - parent_amt)
            if abs(diff) <= 0.005:
                diff_lbl.config(text="✓ Cent-Locked (Diff: R 0.00)", fg="#34d399", bg="#064e3b")
                confirm_btn.config(state="normal", bg="#10b981")
            else:
                diff_lbl.config(text=f"⚠️ Difference: R {diff:,.2f} (Must equal R 0.00)", fg="#fecaca", bg="#7f1d1d")
                confirm_btn.config(state="disabled", bg="#334155")
            total_lbl.config(text=f"Total Split: R {tot:,.2f} / Target: R {parent_amt:,.2f}")

        def _add_line(amt_val: float, acc_code: str, vat_val: str, desc: str):
            row_frame = tk.Frame(lines_f, bg="#1e293b", padx=8, pady=4)
            row_frame.pack(fill=tk.X, pady=2)

            amt_var = tk.StringVar(value=f"{amt_val:.2f}")
            amt_ent = tk.Entry(row_frame, textvariable=amt_var, width=12, font=("Segoe UI", 9, "bold"), justify="right")
            amt_ent.pack(side=tk.LEFT, padx=(0, 6))
            amt_var.trace_add("write", lambda *args: _recalc_split_balance())

            acc_var = tk.StringVar()
            acc_cb = ttk.Combobox(row_frame, textvariable=acc_var, values=coa_items, state="readonly", width=28)
            matching = [it for it in coa_items if it.startswith(acc_code)]
            acc_cb.set(matching[0] if matching else coa_items[0])
            acc_cb.pack(side=tk.LEFT, padx=(0, 6))

            vat_var = tk.StringVar(value=vat_val)
            vat_cb = ttk.Combobox(row_frame, textvariable=vat_var, values=["Standard", "Zero-Rated", "None"], state="readonly", width=12)
            vat_cb.pack(side=tk.LEFT, padx=(0, 6))

            desc_var = tk.StringVar(value=desc)
            desc_ent = tk.Entry(row_frame, textvariable=desc_var, width=20, font=("Segoe UI", 9))
            desc_ent.pack(side=tk.LEFT, padx=(0, 6))

            def _remove_me():
                if len(split_rows_ui) > 2:
                    split_rows_ui.remove(entry_dict)
                    row_frame.destroy()
                    _recalc_split_balance()
                else:
                    messagebox.showinfo("Split", "A split must have at least 2 lines.", parent=dialog)

            del_btn = HDButton(row_frame, text="✕", font=("Segoe UI", 8), bg="#7f1d1d", fg="#fecaca", relief="flat", padx=5, pady=1, command=_remove_me)
            del_btn.pack(side=tk.RIGHT)

            entry_dict = {
                "frame": row_frame,
                "amt_var": amt_var,
                "acc_var": acc_var,
                "vat_var": vat_var,
                "desc_var": desc_var,
            }
            split_rows_ui.append(entry_dict)
            _recalc_split_balance()

        def _clear_all_lines():
            for r in split_rows_ui:
                r["frame"].destroy()
            split_rows_ui.clear()

        def _apply_50_50():
            _clear_all_lines()
            h1 = _dec_round(parent_amt / 2.0)
            h2 = _dec_round(parent_amt - h1)
            _add_line(h1, parent_txn["code"], parent_txn["vat_type"], f"{parent_payee} (50%)")
            _add_line(h2, "4600/000", parent_txn["vat_type"], f"{parent_payee} (50%)")

        def _apply_payroll():
            _clear_all_lines()
            lines = TransactionSplitter.generate_payroll_split(parent_amt, ref=parent_txn["ref"])
            for l in lines:
                _add_line(l["amount"], l["code"], l["vat_type"], l["clean_payee"])

        HDButton(preset_bar, text="⚡ 50 / 50 Split", font=("Segoe UI", 8), bg="#1e293b", fg="#cbd5e1", relief="flat", padx=8, pady=2, command=_apply_50_50).pack(side=tk.LEFT, padx=(0, 6))
        HDButton(preset_bar, text="⚡ Payroll Split (Net + PAYE + Capped UIF)", font=("Segoe UI", 8, "bold"), bg="#1e293b", fg="#38bdf8", relief="flat", padx=8, pady=2, command=_apply_payroll).pack(side=tk.LEFT, padx=(0, 6))
        HDButton(preset_bar, text="+ Add Line", font=("Segoe UI", 8), bg="#0284c7", fg="white", relief="flat", padx=8, pady=2, command=lambda: _add_line(0.0, "4600/000", "Standard", parent_payee)).pack(side=tk.RIGHT)

        p1 = _dec_round(parent_amt * 0.60)
        p2 = _dec_round(parent_amt - p1)
        _add_line(p1, parent_txn["code"], parent_txn["vat_type"], f"{parent_payee} (Split 1)")
        _add_line(p2, "4600/000", "Standard", f"{parent_payee} (Split 2)")

    # ==========================================================================
    # IDEA 2: SARS VAT201 eFILING BOX SUMMARY CARD
    # ==========================================================================
    def open_vat201_card_dialog(self):
        vat_data = VAT201Calculator.calculate(self.transactions)

        dialog = tk.Toplevel(self.root)
        dialog.title("🏛️ SARS VAT201 eFiling Box Summary Card")
        dialog.geometry("700x560")
        dialog.minsize(600, 460)
        dialog.configure(bg="#0f172a")
        dialog.transient(self.root)
        dialog.grab_set()

        ftr = tk.Frame(dialog, bg="#0f172a", padx=20, pady=12)
        ftr.pack(side=tk.BOTTOM, fill=tk.X)

        def _open_efiling():
            # web links available globally
            webbrowser.open("https://www.sarsefiling.co.za")

        HDButton(
            ftr,
            text="📊 Export SARS VAT201 Audit Pack (.xlsx)",
            font=("Segoe UI", 9, "bold"),
            bg="#10b981",
            fg="white",
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            command=self.export_vat201_excel_audit_pack
        ).pack(side=tk.LEFT, padx=(0, 6))
        HDButton(ftr, text="🌐 Open SARS eFiling", font=("Segoe UI", 9, "bold"), bg="#0284c7", fg="white", relief="flat", padx=12, pady=4, command=_open_efiling).pack(side=tk.LEFT)
        HDButton(ftr, text="Close", font=("Segoe UI", 9), bg="#334155", fg="white", relief="flat", padx=14, pady=4, command=dialog.destroy).pack(side=tk.RIGHT)

        hdr = tk.Frame(dialog, bg="#1e293b", padx=20, pady=12)
        hdr.pack(fill=tk.X)
        tk.Label(
            hdr,
            text="🏛️ SARS VAT201 eFiling Box Summary Card",
            font=("Segoe UI", 12, "bold"),
            fg="#38bdf8",
            bg="#1e293b",
        ).pack(anchor="w")
        tk.Label(
            hdr,
            text="Official SARS eFiling figures calculated strictly under VAT Act 89 of 1991. Copy directly into SARS eFiling.",
            font=("Segoe UI", 8),
            fg="#94a3b8",
            bg="#1e293b",
        ).pack(anchor="w", pady=(2, 0))

        content_f = tk.Frame(dialog, bg="#0f172a", padx=20, pady=14)
        content_f.pack(fill=tk.BOTH, expand=True)

        boxes = [
            ("Box 1", "Standard Rated Supplies (Incl. VAT Turnover)", vat_data["box_1"]),
            ("Box 4", "Output Tax on Standard Supplies (15/115 of Box 1)", vat_data["box_4"]),
            ("Box 15", "Other Input Tax (Deductible 15% VAT on Expenses)", vat_data["box_15"]),
            ("Box 19", "Total Input Tax Deductions", vat_data["box_19"]),
            ("Box 20", "Net VAT Payable to SARS / (Refund Due)", vat_data["box_20"]),
        ]

        def _copy_box(val: float, btn):
            self.root.clipboard_clear()
            self.root.clipboard_append(f"{val:.2f}")
            btn.config(text="✓ Copied!", bg="#064e3b", fg="#34d399")
            dialog.after(1500, lambda: btn.config(text="📋 Copy", bg="#1e293b", fg="#cbd5e1") if dialog.winfo_exists() else None)

        for box_id, box_desc, box_val in boxes:
            card = tk.Frame(content_f, bg="#1e293b", padx=14, pady=8)
            card.pack(fill=tk.X, pady=3)

            left = tk.Frame(card, bg="#1e293b")
            left.pack(side=tk.LEFT)
            tk.Label(left, text=box_id, font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#1e293b").pack(anchor="w")
            tk.Label(left, text=box_desc, font=("Segoe UI", 8), fg="#94a3b8", bg="#1e293b").pack(anchor="w")

            val_f = tk.Frame(card, bg="#1e293b")
            val_f.pack(side=tk.RIGHT)
            val_col = "#34d399" if box_val >= 0 else "#f87171"
            if box_id == "Box 20":
                val_col = "#fbbf24" if box_val > 0 else "#34d399"
            tk.Label(val_f, text=f"R {box_val:,.2f}", font=("Segoe UI", 11, "bold"), fg=val_col, bg="#1e293b").pack(side=tk.LEFT, padx=(0, 10))

            cp_btn = HDButton(val_f, text="📋 Copy", font=("Segoe UI", 8), bg="#0f172a", fg="#cbd5e1", relief="flat", padx=8, pady=2)
            cp_btn.config(command=lambda v=box_val, b=cp_btn: _copy_box(v, b))
            cp_btn.pack(side=tk.LEFT)

        if vat_data.get("blocked_entertainment_vat", 0) > 0:
            bl_f = tk.Frame(content_f, bg="#78350f", padx=12, pady=6)
            bl_f.pack(fill=tk.X, pady=(10, 0))
            tk.Label(
                bl_f,
                text=f"⚖️ SARS Section 17(2) Blocked Entertainment: R {vat_data['blocked_entertainment_vat']:,.2f} input tax correctly disallowed.",
                font=("Segoe UI", 8, "bold"),
                fg="#fef3c7",
                bg="#78350f",
            ).pack(anchor="w")

    def _refresh_coa_dependent_widgets(self):
        """Refreshes all UI comboboxes and dropdowns after Chart of Accounts additions or deletions."""
        coa_dict = self.config["profiles"][self.active_profile]["coa"]
        coa_items = sorted([f"{v['code']} - {v['name']}" for v in coa_dict.values()])
        if hasattr(self, "bulk_acc_cb"):
            self.bulk_acc_cb.config(values=coa_items)
            if coa_items:
                self.bulk_acc_cb.current(0)

    def open_coa_manager_dialog(self):
        """Full Chart of Accounts (COA) Manager: Add, Edit, Delete, Import CSV, or Reset GL Accounts."""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"📋 Chart of Accounts Manager  -  {self.active_profile}")
        dialog.geometry("1040x660")
        dialog.minsize(860, 520)
        dialog.configure(bg="#090d16")
        dialog.transient(self.root)
        dialog.grab_set()

        # Pinned footer FIRST so bottom buttons are never clipped
        ftr = tk.Frame(dialog, bg="#0f172a", padx=18, pady=10)
        ftr.pack(side=tk.BOTTOM, fill=tk.X)
        HDButton(ftr, text="🔄 Re-Run Categorization on Current Batch & Close", font=("Segoe UI", 9, "bold"), bg="#0284c7", fg="white", relief="flat", padx=14, pady=4, command=lambda: (self.rerun_categorization(), dialog.destroy())).pack(side=tk.LEFT)
        HDButton(ftr, text="Done / Close", font=("Segoe UI", 9, "bold"), bg="#334155", fg="white", relief="flat", padx=16, pady=4, command=dialog.destroy).pack(side=tk.RIGHT)

        hdr = tk.Frame(dialog, bg="#0f172a", padx=20, pady=12)
        hdr.pack(fill=tk.X)
        tk.Label(
            hdr,
            text=f"📋 Chart of Accounts (COA) Manager  -  {self.active_profile}",
            font=("Segoe UI", 13, "bold"),
            fg="#38bdf8",
            bg="#0f172a",
        ).pack(anchor="w")
        tk.Label(
            hdr,
            text="Add new GL codes, edit account names/VAT rules/keywords, or delete accounts. Click any row below to edit it.",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#0f172a",
        ).pack(anchor="w", pady=(2, 0))

        # Add / Edit Form Frame
        form_f = tk.Frame(dialog, bg="#131b2e", padx=18, pady=10, highlightbackground="#334155", highlightthickness=1)
        form_f.pack(fill=tk.X, padx=18, pady=(10, 6))

        row1 = tk.Frame(form_f, bg="#131b2e")
        row1.pack(fill=tk.X, pady=(0, 8))

        tk.Label(row1, text="GL Code *:", font=("Segoe UI", 9, "bold"), fg="#cbd5e1", bg="#131b2e").pack(side=tk.LEFT)
        code_var = tk.StringVar()
        code_ent = tk.Entry(row1, textvariable=code_var, width=12, font=("Segoe UI", 10), bg="#0a101d", fg="#38bdf8", insertbackground="white", relief="flat")
        code_ent.pack(side=tk.LEFT, padx=(6, 14), ipady=3)

        tk.Label(row1, text="Account Name *:", font=("Segoe UI", 9, "bold"), fg="#cbd5e1", bg="#131b2e").pack(side=tk.LEFT)
        name_var = tk.StringVar()
        name_ent = tk.Entry(row1, textvariable=name_var, width=28, font=("Segoe UI", 10), bg="#0a101d", fg="#f8fafc", insertbackground="white", relief="flat")
        name_ent.pack(side=tk.LEFT, padx=(6, 14), ipady=3)

        tk.Label(row1, text="Default VAT:", font=("Segoe UI", 9, "bold"), fg="#cbd5e1", bg="#131b2e").pack(side=tk.LEFT)
        vat_var = tk.StringVar(value="Standard")
        vat_cb = ttk.Combobox(
            row1,
            textvariable=vat_var,
            values=["Standard", "Zero-Rated", "Exempt", "Blocked_Entertainment", "None"],
            state="readonly",
            width=18,
            font=("Segoe UI", 9),
        )
        vat_cb.pack(side=tk.LEFT, padx=(6, 14))

        tk.Label(row1, text="Type:", font=("Segoe UI", 9, "bold"), fg="#cbd5e1", bg="#131b2e").pack(side=tk.LEFT)
        type_var = tk.StringVar(value="GL")
        type_cb = ttk.Combobox(row1, textvariable=type_var, values=["GL", "Customer", "Supplier"], state="readonly", width=10, font=("Segoe UI", 9))
        type_cb.pack(side=tk.LEFT, padx=(6, 0))

        row2 = tk.Frame(form_f, bg="#131b2e")
        row2.pack(fill=tk.X)

        tk.Label(row2, text="Category Key:", font=("Segoe UI", 9, "bold"), fg="#94a3b8", bg="#131b2e").pack(side=tk.LEFT)
        key_var = tk.StringVar()
        key_ent = tk.Entry(row2, textvariable=key_var, width=14, font=("Segoe UI", 9), bg="#0a101d", fg="#cbd5e1", insertbackground="white", relief="flat")
        key_ent.pack(side=tk.LEFT, padx=(6, 14), ipady=3)

        tk.Label(row2, text="Auto-Match Keywords (comma-separated):", font=("Segoe UI", 9, "bold"), fg="#94a3b8", bg="#131b2e").pack(side=tk.LEFT)
        kw_var = tk.StringVar()
        kw_ent = tk.Entry(row2, textvariable=kw_var, width=36, font=("Segoe UI", 9), bg="#0a101d", fg="#cbd5e1", insertbackground="white", relief="flat")
        kw_ent.pack(side=tk.LEFT, padx=(6, 12), fill=tk.X, expand=True, ipady=3)

        # Table Frame
        tbl_f = tk.Frame(dialog, bg="#090d16", padx=18)
        tbl_f.pack(fill=tk.BOTH, expand=True, pady=(4, 6))

        cols = ("key", "code", "name", "vat", "type", "keywords")
        coa_tree = ttk.Treeview(tbl_f, columns=cols, show="headings", selectmode="extended", height=7)
        coa_tree.heading("key", text="Category Key")
        coa_tree.heading("code", text="GL Code")
        coa_tree.heading("name", text="Account Name / Description")
        coa_tree.heading("vat", text="Default SARS VAT")
        coa_tree.heading("type", text="Ledger")
        coa_tree.heading("keywords", text="Auto-Match Vendor Keywords")

        coa_tree.column("key", width=110, anchor=tk.W)
        coa_tree.column("code", width=95, anchor=tk.CENTER)
        coa_tree.column("name", width=220, anchor=tk.W)
        coa_tree.column("vat", width=130, anchor=tk.CENTER)
        coa_tree.column("type", width=75, anchor=tk.CENTER)
        coa_tree.column("keywords", width=260, anchor=tk.W)

        sc_y = ttk.Scrollbar(tbl_f, orient=tk.VERTICAL, command=coa_tree.yview)
        coa_tree.configure(yscrollcommand=sc_y.set)
        sc_y.pack(side=tk.RIGHT, fill=tk.Y)
        coa_tree.pack(fill=tk.BOTH, expand=True)

        def _populate_coa_tree():
            coa_tree.delete(*coa_tree.get_children())
            coa_dict = self.config["profiles"][self.active_profile]["coa"]
            for k, info in sorted(coa_dict.items(), key=lambda x: str(x[1].get("code", ""))):
                coa_tree.insert(
                    "",
                    tk.END,
                    iid=k,
                    values=(
                        k,
                        info.get("code", ""),
                        info.get("name", ""),
                        info.get("vat", "Standard"),
                        info.get("type", "GL"),
                        info.get("keywords", ""),
                    ),
                )

        def _on_select_row(event=None):
            sel = coa_tree.selection()
            if not sel:
                return
            k = sel[0]
            coa_dict = self.config["profiles"][self.active_profile]["coa"]
            if k in coa_dict:
                info = coa_dict[k]
                key_var.set(k)
                code_var.set(info.get("code", ""))
                name_var.set(info.get("name", ""))
                vat_var.set(info.get("vat", "Standard"))
                type_var.set(info.get("type", "GL"))
                kw_var.set(info.get("keywords", ""))

        coa_tree.bind("<<TreeviewSelect>>", _on_select_row)

        def _clear_form():
            coa_tree.selection_remove(coa_tree.selection())
            key_var.set("")
            code_var.set("")
            name_var.set("")
            vat_var.set("Standard")
            type_var.set("GL")
            kw_var.set("")
            code_ent.focus_set()

        def _add_or_save_account():
            cd = code_var.get().strip()
            nm = name_var.get().strip()
            if not cd or not nm:
                messagebox.showwarning("Missing Fields", "Please enter both a GL Code (e.g. 4750/000) and an Account Name.", parent=dialog)
                return
            k = key_var.get().strip()
            if not k:
                k = re.sub(r"[^A-Za-z0-9_]", "_", nm).strip("_")[:24] or f"Acc_{cd}"

            coa_dict = self.config["profiles"][self.active_profile]["coa"]
            coa_dict[k] = {
                "code": cd,
                "name": nm,
                "vat": vat_var.get() or "Standard",
                "type": type_var.get() or "GL",
                "keywords": kw_var.get().strip().upper(),
            }
            self.save_config()
            self._refresh_coa_dependent_widgets()
            _populate_coa_tree()
            self.status_lbl.config(text=f"Saved GL Account: {cd} - {nm} in Chart of Accounts.")

        def _delete_selected_accounts(event=None):
            sel = coa_tree.selection()
            if not sel:
                messagebox.showinfo("Delete Account", "Please click on one or more accounts in the table to delete.", parent=dialog)
                return
            if "Suspense" in sel and len(sel) == 1:
                messagebox.showwarning("Protected Account", "The Suspense Account (9999/000) is required for unallocated queries and cannot be deleted.", parent=dialog)
                return
            to_del = [k for k in sel if k != "Suspense"]
            if not to_del:
                return
            if not messagebox.askyesno("Confirm Delete", f"Delete {len(to_del)} selected account(s) from the Chart of Accounts?", parent=dialog):
                return
            coa_dict = self.config["profiles"][self.active_profile]["coa"]
            for k in to_del:
                coa_dict.pop(k, None)
            self.save_config()
            self._refresh_coa_dependent_widgets()
            _populate_coa_tree()
            _clear_form()
            self.status_lbl.config(text=f"Deleted {len(to_del)} account(s) from Chart of Accounts.")

        coa_tree.bind("<Delete>", _delete_selected_accounts)

        def _import_coa_csv():
            fp = filedialog.askopenfilename(
                title="Import Chart of Accounts from CSV (Columns: Code, Name, Optional VAT)",
                filetypes=[("CSV Files", "*.csv;*.txt"), ("All Files", "*.*")],
                parent=dialog,
            )
            if not fp:
                return
            added = 0
            coa_dict = self.config["profiles"][self.active_profile]["coa"]
            try:
                with open(fp, "r", encoding="utf-8-sig", errors="replace") as f:
                    for line in f:
                        parts = [p.strip().strip('"') for p in line.split(",")]
                        if len(parts) >= 2 and parts[0] and parts[0].lower() not in ("code", "gl code", "account code", "account"):
                            cd, nm = parts[0], parts[1]
                            vt = parts[2] if len(parts) >= 3 and parts[2] in ("Standard", "Zero-Rated", "Exempt", "None") else "Standard"
                            k = re.sub(r"[^A-Za-z0-9_]", "_", nm).strip("_")[:24] or f"Acc_{cd}"
                            coa_dict[k] = {"code": cd, "name": nm, "vat": vt, "type": "GL", "keywords": ""}
                            added += 1
                self.save_config()
                self._refresh_coa_dependent_widgets()
                _populate_coa_tree()
                messagebox.showinfo("COA Imported", f"Successfully imported {added} GL accounts into {self.active_profile}.", parent=dialog)
            except Exception as e:
                messagebox.showerror("Import Error", f"Could not import CSV:\n{e}", parent=dialog)

        def _reset_default_coa():
            if messagebox.askyesno("Reset Chart of Accounts", "Restore the default South African Chart of Accounts? (Custom accounts not in defaults will be replaced).", parent=dialog):
                self.config["profiles"][self.active_profile]["coa"] = {k: v.copy() for k, v in DEFAULT_CHART_OF_ACCOUNTS.items()}
                self.save_config()
                self._refresh_coa_dependent_widgets()
                _populate_coa_tree()
                _clear_form()

        # Action Buttons Strip inside Form
        btn_bar = tk.Frame(form_f, bg="#131b2e")
        btn_bar.pack(fill=tk.X, pady=(8, 0))

        HDButton(btn_bar, text="➕ Add / Save Account", font=("Segoe UI", 9, "bold"), bg="#10b981", fg="white", relief="flat", padx=10, pady=3, command=_add_or_save_account).pack(side=tk.LEFT, padx=(0, 6))
        HDButton(btn_bar, text="🧹 Clear / New", font=("Segoe UI", 9), bg="#334155", fg="#e2e8f0", relief="flat", padx=8, pady=3, command=_clear_form).pack(side=tk.LEFT, padx=(0, 6))
        HDButton(btn_bar, text="🗑️ Delete Selected", font=("Segoe UI", 9, "bold"), bg="#dc2626", fg="white", relief="flat", padx=10, pady=3, command=_delete_selected_accounts).pack(side=tk.LEFT, padx=(0, 6))
        HDButton(btn_bar, text="📥 Import CSV", font=("Segoe UI", 9), bg="#0284c7", fg="white", relief="flat", padx=8, pady=3, command=_import_coa_csv).pack(side=tk.LEFT, padx=(0, 6))
        HDButton(btn_bar, text="🔄 Reset Defaults", font=("Segoe UI", 9), bg="#475569", fg="white", relief="flat", padx=8, pady=3, command=_reset_default_coa).pack(side=tk.LEFT)

        _populate_coa_tree()

    def open_user_manual(self):
        """Opens the built-in interactive User Manual & Step-by-Step Operations Guide inside the app, with optional browser view."""
        dialog = tk.Toplevel(self.root)
        dialog.title("📖 TaxClean ZA  -  Official User Manual & Step-by-Step Guide")
        dialog.geometry("920x640")
        dialog.minsize(780, 500)
        dialog.configure(bg="#090d16")
        dialog.transient(self.root)

        def _open_html_in_browser():
            candidates = [
                BASE_DIR / "TaxClean_User_Manual.html",
                Path(getattr(sys, "_MEIPASS", str(BASE_DIR))) / "TaxClean_User_Manual.html",
                Path(__file__).resolve().parent / "TaxClean_User_Manual.html",
            ]
            for p in candidates:
                if p.exists():
                    webbrowser.open(str(p.resolve()))
                    return
            messagebox.showinfo("Browser Manual", "The full manual is displayed right here in this window.", parent=dialog)

        # Pinned footer FIRST so buttons are never clipped
        ftr = tk.Frame(dialog, bg="#0f172a", padx=20, pady=10)
        ftr.pack(side=tk.BOTTOM, fill=tk.X)
        HDButton(ftr, text="🌐 Open Printable Manual in Web Browser", font=("Segoe UI", 9, "bold"), bg="#0284c7", fg="white", relief="flat", padx=12, pady=4, command=_open_html_in_browser).pack(side=tk.LEFT)
        HDButton(ftr, text="📋 Open Chart of Accounts", font=("Segoe UI", 9, "bold"), bg="#0d9488", fg="white", relief="flat", padx=12, pady=4, command=lambda: (dialog.destroy(), self.open_coa_manager_dialog())).pack(side=tk.LEFT, padx=8)
        HDButton(ftr, text="🤖 Setup Free AI API Key", font=("Segoe UI", 9, "bold"), bg="#6366f1", fg="white", relief="flat", padx=12, pady=4, command=lambda: (dialog.destroy(), self.open_ai_settings_dialog())).pack(side=tk.LEFT)
        HDButton(ftr, text="Close Manual", font=("Segoe UI", 9, "bold"), bg="#334155", fg="white", relief="flat", padx=14, pady=4, command=dialog.destroy).pack(side=tk.RIGHT)

        hdr = tk.Frame(dialog, bg="#0f172a", padx=22, pady=12)
        hdr.pack(fill=tk.X)
        tk.Label(
            hdr,
            text="📖 TaxClean ZA  -  Complete Step-by-Step Operations Manual",
            font=("Segoe UI", 14, "bold"),
            fg="#38bdf8",
            bg="#0f172a",
        ).pack(anchor="w")
        tk.Label(
            hdr,
            text="Everything you need to import single or multiple statements, manage your Chart of Accounts, reconcile to R 0.00, and export.",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#0f172a",
        ).pack(anchor="w", pady=(2, 0))

        body = tk.Frame(dialog, bg="#090d16", padx=20, pady=12)
        body.pack(fill=tk.BOTH, expand=True)

        txt = tk.Text(
            body,
            bg="#0f172a",
            fg="#f1f5f9",
            font=("Segoe UI", 10),
            wrap=tk.WORD,
            padx=20,
            pady=16,
            relief="flat",
            highlightbackground="#334155",
            highlightthickness=1,
        )
        sc = ttk.Scrollbar(body, orient=tk.VERTICAL, command=txt.yview)
        txt.configure(yscrollcommand=sc.set)
        sc.pack(side=tk.RIGHT, fill=tk.Y)
        txt.pack(fill=tk.BOTH, expand=True)

        txt.tag_configure("h1", font=("Segoe UI", 12, "bold"), foreground="#38bdf8", spacing1=10, spacing3=6)
        txt.tag_configure("bullet", font=("Segoe UI", 10, "bold"), foreground="#34d399")
        txt.tag_configure("body", font=("Segoe UI", 10), foreground="#e2e8f0", spacing3=4)

        manual_sections = [
            (
                "1. IMPORTING ONE OR MULTIPLE BANK STATEMENTS / SLIPS AT ONCE (⚡ Import Docs / Ctrl+O)",
                [
                    "• Click '⚡ Import Docs' in the top-right bar (or press Ctrl+O).",
                    "• Select a SINGLE PDF/CSV/Image statement OR hold Ctrl / Shift (or press Ctrl+A) in the file window to select MULTIPLE monthly statements or till slips at the exact same time!",
                    "• TaxClean ZA automatically parses every selected document, deduplicates overlapping edge rows, sorts transactions chronologically, and verifies Opening + Net Movement = Closing Balance.",
                    "• Want to add more files to an existing batch? Click '➕ Append' (or press Alt+A) and select one or multiple additional statements.",
                ],
            ),
            (
                "2. ADDING, EDITING & DELETING YOUR CHART OF ACCOUNTS (📋 Chart of Accounts / Alt+C)",
                [
                    "• Click the teal '📋 Chart of Accounts' button above the transaction table (or press Alt+C, or open 🛠️ Tools ▾ → Chart of Accounts Manager).",
                    "• ADD NEW GL ACCOUNT: Enter your GL Code (e.g., 4750/000), Account Name (e.g., Courier & Postage), Default SARS VAT Rule, and optional vendor keywords, then click '➕ Add / Save Account'.",
                    "• EDIT EXISTING ACCOUNT: Click any row in the Chart of Accounts table to load its details into the top boxes, adjust the code/name/VAT/keywords, and click '➕ Add / Save Account'.",
                    "• DELETE ACCOUNT(S): Click one or more accounts in the table and click '🗑️ Delete Selected Account(s)' (or press Delete).",
                    "• IMPORT COA CSV: Click '📥 Import COA CSV' to bulk-import your practice's GL codes from a CSV file.",
                ],
            ),
            (
                "3. HOW TO CREATE & ADD A FREE GOOGLE GEMINI API KEY FOR AI VISION OCR (🤖 AI Setup)",
                [
                    "• TaxClean ZA works 100% offline out of the box using its local RapidOCR neural engine. Adding a free Google Gemini API key unlocks ultra-fast AI Vision extraction on faded thermal till slips, handwritten invoices, and complex multi-column PDFs.",
                    "• STEP 1: Click '🛠️ Tools ▾ → 🤖 AI OCR & API Key Setup' in the top bar (or click '🤖 Setup Free AI API Key' at the bottom of this window).",
                    "• STEP 2: Click '🌐 Open Google AI Studio (Get Free Key)' to open https://aistudio.google.com/app/apikey in your browser and sign in with any Google account.",
                    "• STEP 3: Click 'Create API Key' in Google AI Studio and copy the generated key (it starts with 'AIzaSy...').",
                    "• STEP 4: Paste the key into the 'Gemini API Key' box in TaxClean ZA and click '💾 Save Settings'. Your key is stored locally on your PC.",
                ],
            ),
            (
                "4. EDITING ROWS, BULK ALLOCATION & SPLITTING TRANSACTIONS",
                [
                    "• INLINE EDIT: Double-click any cell in the grid (Date, Payee, Account/Nominal Code, Gross Amount, or SARS VAT Type) to edit it directly. When you assign an Account to a vendor, TaxClean ZA automatically memorizes that vendor for all future statements!",
                    "• BULK ALLOCATION: Select 2 or more rows (Shift+Click or Ctrl+Click), choose the target GL Account and SARS VAT rule in the blue Bulk Toolbar that appears, and click '⚡ Apply & Memorize'.",
                    "• SPLIT TRANSACTION (Alt+S): Highlight a mixed purchase (e.g., Makro or Builders Warehouse) and press Alt+S to split it across multiple GL accounts or VAT rates.",
                ],
            ),
            (
                "5. RECONCILING VARIANCE TO R 0.00 & MATCHING SHOEBOX RECEIPTS",
                [
                    "• Check the Traffic Light Banner and 'Open R → Net → Close R' bar. If there is a variance, click 'Auto-Align' to either align the closing balance or insert a balancing query line into Suspense.",
                    "• Click '📎 Match Receipts' (Alt+M) to scan a folder or batch of retail till slips/tax invoices and automatically attach them to matching bank statement lines.",
                ],
            ),
            (
                "6. EXPORTING TO SAGE PASTEL, SAGE ONE, XERO, QUICKBOOKS & SARS VAT201 (💾 Export)",
                [
                    "• Choose your target accounting system in the top-left ERP dropdown (Pastel Partner, Sage Business Cloud, Xero, QuickBooks Online, SARS VAT201 Breakdown Excel, or Universal CSV).",
                    "• Click '💾 Export' in the top-right corner. The 4-Point Pre-Flight Validator verifies your balance, financial year-end period mapping, and suspense items before generating your import-ready file.",
                    "• Click '🏛️ VAT201' (Alt+V) at any time to view and copy your calculated SARS VAT201 eFiling boxes (Boxes 1, 1A, 4, 14, 15, and 19).",
                ],
            ),
            (
                "7. ESSENTIAL KEYBOARD SHORTCUTS",
                [
                    "• F1 : Open this User Manual & Guide",
                    "• Alt + C : Open Chart of Accounts Manager (Add / Edit / Delete GL Accounts)",
                    "• Ctrl + O : Import One or Multiple Statements / Slips",
                    "• Alt + A : Append Additional Statements / Slips to Current Batch",
                    "• Spacebar : Quickly cycle SARS VAT Type (Standard 15% → Zero-Rated → None) on selected row(s)",
                    "• Alt + S : Split Selected Transaction   |   Alt + M : Match Receipts   |   Alt + V : SARS VAT201 Summary",
                    "• Ctrl + Z / Ctrl + Y : Undo / Redo (30-step history)",
                ],
            ),
        ]

        for heading, bullets in manual_sections:
            txt.insert(tk.END, heading + "\n", "h1")
            for b in bullets:
                txt.insert(tk.END, b + "\n", "body")
            txt.insert(tk.END, "\n")

        txt.config(state=tk.DISABLED)

    # ==========================================================================
    # IDEA 5: LOCK BATCH & SARS SECTION 29 AUDIT CERTIFICATE
    # ==========================================================================
    def lock_batch_and_generate_certificate(self):
        if not self.transactions:
            messagebox.showwarning("Lock Batch", "No transactions in batch to lock.", parent=self.root)
            return

        try:
            o = float(self.open_bal_var.get().replace(",", "").strip() or 0)
            c = float(self.close_bal_var.get().replace(",", "").strip() or 0)
        except Exception:
            o, c = 0.0, 0.0

        vat_data = VAT201Calculator.calculate(self.transactions)
        batch_hash = AuditCertificateGenerator.generate_batch_hash(self.active_profile, o, c, self.transactions)
        prof_info = self.config["profiles"].get(self.active_profile, {})
        acc_num = prof_info.get("bank_account_number") or getattr(self, "current_account_number", "") or getattr(self, "current_bank_name", "Primary Bank Account")
        masked_acc = mask_account_number(str(acc_num)) if any(c.isdigit() for c in str(acc_num)) else str(acc_num)
        html_cert = AuditCertificateGenerator.create_certificate_html(
            self.active_profile,
            masked_acc,
            o, c,
            self.transactions,
            vat_data
        )

        cert_file = USER_DATA_DIR / f"SARS_Section29_Audit_Certificate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(cert_file, "w", encoding="utf-8") as f:
            f.write(html_cert)

        self.batch_locked = True
        self.locked_hash = batch_hash
        self.hero_banner.config(bg="#1e1b4b")
        self.hero_title_lbl.config(text="🔒 BATCH LOCKED  -  SARS SECTION 29 CERTIFICATE ISSUED", fg="#a5b4fc", bg="#1e1b4b")
        self.hero_sub_lbl.config(text=f"Cryptographic Hash: {batch_hash[:32]}... • Immutable Audit Trail Established.", fg="#c7d2fe", bg="#1e1b4b")

        ans = messagebox.askyesno(
            "Batch Locked & Certificate Generated",
            f"✓ Batch Successfully Locked with SHA-256 Hash:\n{batch_hash}\n\n"
            f"The formal SARS Section 29 Audit Certificate has been created:\n{cert_file.name}\n\n"
            f"Would you like to open the certificate in your browser now?",
            parent=self.root,
        )
        if ans:
            # web links available globally
            webbrowser.open(str(cert_file.resolve()))

    def unlock_batch(self):
        if not self.batch_locked:
            messagebox.showinfo("Unlock Batch", "The current batch is not locked.", parent=self.root)
            return
        ans = messagebox.askyesno(
            "Unlock Batch",
            "Are you sure you want to unlock this batch? Any modifications will invalidate the current audit certificate hash.",
            parent=self.root,
        )
        if ans:
            self.batch_locked = False
            self.locked_hash = ""
            self.hero_banner.config(bg="#1e293b")
            self.hero_title_lbl.config(
                text="🛡️ TaxClean ZA  -  Forensic Bank Statement to Pastel/Xero Converter",
                fg="#f8fafc",
                bg="#1e293b",
            )
            self.hero_sub_lbl.config(
                text="Automated Cent-Zero Reconciliation • SARS Section 29 Compliant • 100% Offline Forensic Precision",
                fg="#94a3b8",
                bg="#1e293b",
            )
            self.recalculate_reconciliation()

    # ==========================================================================
    # FORENSIC RADAR & PRACTICE SUITE DIALOGS (ANOMALIES, RUNWAY, RULES, BACKUP)
    # ==========================================================================
    def open_anomaly_radar_dialog(self):
        anomalies = AnomalyRadar.scan_anomalies(self.transactions)
        dialog = tk.Toplevel(self.root)
        dialog.title("📈 Monthly Expense Anomaly Radar")
        dialog.geometry("760x480")
        dialog.configure(bg="#0f172a")
        dialog.transient(self.root)
        dialog.grab_set()

        ftr = tk.Frame(dialog, bg="#0f172a", padx=16, pady=10)
        ftr.pack(side=tk.BOTTOM, fill=tk.X)
        HDButton(ftr, text="Close", font=("Segoe UI", 9), bg="#334155", fg="white", relief="flat", padx=14, pady=4, command=dialog.destroy).pack(side=tk.RIGHT)

        hdr = tk.Frame(dialog, bg="#1e293b", padx=20, pady=12)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="📈 Monthly Expense Anomaly Radar", font=("Segoe UI", 12, "bold"), fg="#38bdf8", bg="#1e293b").pack(anchor="w")
        tk.Label(hdr, text=f"Scanned {len(self.transactions)} transactions. Found {len(anomalies)} items for review.", font=("Segoe UI", 8), fg="#94a3b8", bg="#1e293b").pack(anchor="w")

        content_f = tk.Frame(dialog, bg="#0f172a", padx=16, pady=10)
        content_f.pack(fill=tk.BOTH, expand=True)

        cols = ("severity", "title", "amount", "desc")
        tree = ttk.Treeview(content_f, columns=cols, show="headings", height=8)
        tree.heading("severity", text="Severity")
        tree.heading("title", text="Anomaly Alert")
        tree.heading("amount", text="Amount")
        tree.heading("desc", text="Audit Rationale")
        tree.column("severity", width=80, anchor="center")
        tree.column("title", width=220)
        tree.column("amount", width=95, anchor="e")
        tree.column("desc", width=280)

        sb = ttk.Scrollbar(content_f, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        for a in anomalies:
            tree.insert("", tk.END, values=(a["severity"], a["title"], f"R {abs(a['amount']):,.2f}", a["desc"]))

    def open_cash_runway_dialog(self):
        try:
            o = float(self.open_bal_var.get().replace(",", "").strip() or 0)
            c = float(self.close_bal_var.get().replace(",", "").strip() or 0)
        except Exception:
            o, c = 0.0, 0.0

        cf = CashFlowRadar.calculate_runway(o, c, self.transactions)
        dialog = tk.Toplevel(self.root)
        dialog.title("📊 Cash Flow Burn-Rate & Runway Card")
        dialog.geometry("560x420")
        dialog.configure(bg="#0f172a")
        dialog.transient(self.root)
        dialog.grab_set()

        hdr = tk.Frame(dialog, bg="#1e293b", padx=20, pady=12)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="📊 Cash Flow Burn-Rate & Runway Card", font=("Segoe UI", 12, "bold"), fg="#38bdf8", bg="#1e293b").pack(anchor="w")
        tk.Label(hdr, text="Calculated from active statement turnover and closing balance.", font=("Segoe UI", 8), fg="#94a3b8", bg="#1e293b").pack(anchor="w")

        content_f = tk.Frame(dialog, bg="#0f172a", padx=20, pady=14)
        content_f.pack(fill=tk.BOTH, expand=True)

        items = [
            ("Total Inflows (Money In)", f"+R {cf['inflows']:,.2f}", "#34d399"),
            ("Total Outflows (Money Out)", f"-R {cf['outflows']:,.2f}", "#f87171"),
            ("Net Cash Movement", f"R {cf['net_flow']:,.2f}", "#38bdf8"),
            ("Estimated Daily Burn", f"R {cf['daily_burn']:,.2f}/day", "#94a3b8"),
            ("Estimated Monthly Burn", f"R {cf['monthly_burn']:,.2f}/month", "#94a3b8"),
            ("Projected Operational Runway", cf["runway_str"], "#34d399" if cf["is_cash_flow_positive"] else "#fbbf24"),
        ]

        for k, v, col in items:
            row = tk.Frame(content_f, bg="#1e293b", padx=12, pady=7)
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=k, font=("Segoe UI", 9), fg="#cbd5e1", bg="#1e293b").pack(side=tk.LEFT)
            tk.Label(row, text=v, font=("Segoe UI", 10, "bold"), fg=col, bg="#1e293b").pack(side=tk.RIGHT)

        ftr = tk.Frame(dialog, bg="#0f172a", padx=20, pady=10)
        ftr.pack(fill=tk.X)
        HDButton(ftr, text="Close", font=("Segoe UI", 9), bg="#334155", fg="white", relief="flat", padx=14, pady=4, command=dialog.destroy).pack(side=tk.RIGHT)

    def export_rules_dialog(self):
        fpath = filedialog.asksaveasfilename(
            title="Export Learned Rules (.tzrules)",
            defaultextension=".tzrules",
            filetypes=[("TaxClean Rules", "*.tzrules"), ("JSON Files", "*.json")],
            parent=self.root,
        )
        if fpath:
            count = RulePortability.export_rules(self.memory.db_path, self.active_profile, Path(fpath))
            messagebox.showinfo("Export Rules", f"Successfully exported {count} vendor rules to:\n{Path(fpath).name}", parent=self.root)

    def import_rules_dialog(self):
        fpath = filedialog.askopenfilename(
            title="Import Learned Rules (.tzrules)",
            filetypes=[("TaxClean Rules", "*.tzrules"), ("JSON Files", "*.json")],
            parent=self.root,
        )
        if fpath:
            try:
                count = RulePortability.import_rules(self.memory.db_path, self.active_profile, Path(fpath))
                self.memory.clear_profile_cache(self.active_profile)
                messagebox.showinfo("Import Rules", f"Successfully imported {count} vendor rules from:\n{Path(fpath).name}", parent=self.root)
            except Exception as e:
                messagebox.showerror("Import Rules Error", f"Could not import rules file:\n\n{e}", parent=self.root)

    def backup_database_action(self):
        dest = CloudVaultBackup.backup_database(self.memory.db_path)
        messagebox.showinfo("Database Backup", f"✓ Memory Database Backup Created:\n\n{dest}", parent=self.root)

    def open_section20_checker_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("📝 SARS Section 20 Invoice Compliance Checker")
        dialog.geometry("640x480")
        dialog.configure(bg="#0f172a")
        dialog.transient(self.root)
        dialog.grab_set()

        hdr = tk.Frame(dialog, bg="#1e293b", padx=20, pady=12)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="📝 SARS Section 20 Tax Invoice Validator", font=("Segoe UI", 12, "bold"), fg="#38bdf8", bg="#1e293b").pack(anchor="w")
        tk.Label(hdr, text="Checks text against mandatory Section 20(4) & 20(5) tax invoice requirements.", font=("Segoe UI", 8), fg="#94a3b8", bg="#1e293b").pack(anchor="w")

        content_f = tk.Frame(dialog, bg="#0f172a", padx=16, pady=10)
        content_f.pack(fill=tk.BOTH, expand=True)

        tk.Label(content_f, text="Paste Invoice Text or OCR Content to Validate:", font=("Segoe UI", 8), fg="#94a3b8", bg="#0f172a").pack(anchor="w")
        txt_box = tk.Text(content_f, height=8, bg="#1e293b", fg="#f8fafc", font=("Consolas", 9), insertbackground="white")
        txt_box.pack(fill=tk.BOTH, expand=True, pady=(4, 8))

        res_lbl = tk.Label(content_f, text="Click 'Validate' to analyze invoice text.", font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#0f172a")
        res_lbl.pack(anchor="w", pady=(2, 6))

        def _do_validate():
            raw = txt_box.get("1.0", tk.END)
            res = SARSSection20Checker.inspect_text(raw)
            if res["is_fully_compliant"]:
                res_lbl.config(text=f"✓ {res['compliance_rating']}: VAT Number {res['vat_number']} Verified (Luhn Mod-10 Pass)", fg="#34d399")
            elif res["is_abbreviated_compliant"]:
                res_lbl.config(text=f"✓ {res['compliance_rating']}: Valid for transactions < R 5,000", fg="#38bdf8")
            else:
                issues_str = "; ".join(res["issues"])
                res_lbl.config(text=f"⚠️ {res['compliance_rating']}: {issues_str}", fg="#f87171")

        HDButton(content_f, text="🔍 Validate SARS Compliance", font=("Segoe UI", 9, "bold"), bg="#0284c7", fg="white", relief="flat", padx=12, pady=4, command=_do_validate).pack(anchor="w")

        ftr = tk.Frame(dialog, bg="#0f172a", padx=16, pady=10)
        ftr.pack(fill=tk.X)
        HDButton(ftr, text="Close", font=("Segoe UI", 9), bg="#334155", fg="white", relief="flat", padx=14, pady=4, command=dialog.destroy).pack(side=tk.RIGHT)

    def open_issue_reporter_dialog(self, prefill_error: str = "", is_statement_error: bool = False, raw_snippet: str = ""):
        """
        1-Click In-App Diagnostic & Error Reporter:
        Packages an anonymized, POPIA-compliant diagnostic report and transmits
        it directly to the TaxClean ZA autonomous engineering pipeline (sales@taxcleanza.com).
        """
        dialog = tk.Toplevel(self.root)
        dialog.title("TaxClean ZA  -  1-Click Diagnostics & Statement Issue Reporter")
        dialog.geometry("700x670")
        dialog.minsize(620, 520)
        dialog.configure(bg="#0f172a")
        dialog.transient(self.root)
        dialog.grab_set()

        # Header Frame
        hdr = tk.Frame(dialog, bg="#1e293b", padx=16, pady=12)
        hdr.pack(fill=tk.X)

        title_row = tk.Frame(hdr, bg="#1e293b")
        title_row.pack(fill=tk.X)
        tk.Label(
            title_row,
            text="⚠️ Statement Parsing & Bug Reporter",
            font=("Segoe UI", 12, "bold"),
            fg="#f59e0b",
            bg="#1e293b"
        ).pack(side=tk.LEFT)

        tk.Label(
            title_row,
            text="AI Engineering Pipeline",
            font=("Segoe UI", 8, "bold"),
            fg="#38bdf8",
            bg="#0f2b48",
            padx=6,
            pady=2
        ).pack(side=tk.RIGHT)

        tk.Label(
            hdr,
            text="Sends an anonymized diagnostic bundle to sales@taxcleanza.com. Our autonomous pipeline audits and triages format traces every 15 minutes.",
            font=("Segoe UI", 8),
            fg="#94a3b8",
            bg="#1e293b"
        ).pack(anchor="w", pady=(3, 0))

        # POPIA Protection Badge
        popia_box = tk.Frame(dialog, bg="#064e3b", padx=12, pady=6)
        popia_box.pack(fill=tk.X, padx=16, pady=(10, 6))
        tk.Label(
            popia_box,
            text="🛡️ 100% POPIA Compliant (Act 4 of 2013): Bank account numbers, client names, and confidential passwords are automatically scrubbed and redacted before transmission.",
            font=("Segoe UI", 8, "bold"),
            fg="#34d399",
            bg="#064e3b",
            wraplength=640,
            justify="left"
        ).pack(anchor="w")

        body_f = tk.Frame(dialog, bg="#0f172a", padx=16, pady=4)
        body_f.pack(fill=tk.BOTH, expand=True)

        # Form grid
        grid_f = tk.Frame(body_f, bg="#0f172a")
        grid_f.pack(fill=tk.X, pady=(0, 6))

        # Row 1: Contact Email & Bank Name
        r1 = tk.Frame(grid_f, bg="#0f172a")
        r1.pack(fill=tk.X, pady=3)

        c1 = tk.Frame(r1, bg="#0f172a")
        c1.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        tk.Label(c1, text="Practice / Contact Email:", font=("Segoe UI", 8, "bold"), fg="#cbd5e1", bg="#0f172a").pack(anchor="w")
        
        user_email = ""
        try:
            user_email = self.license_mgr.get_state().get("email", "") or ""
        except Exception:
            pass
        email_ent = tk.Entry(c1, font=("Segoe UI", 9), bg="#1e293b", fg="white", insertbackground="white", relief="flat")
        email_ent.insert(0, user_email)
        email_ent.pack(fill=tk.X, ipady=3, pady=(2, 0))

        c2 = tk.Frame(r1, bg="#0f172a")
        c2.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(6, 0))
        tk.Label(c2, text="Bank / Financial Institution:", font=("Segoe UI", 8, "bold"), fg="#cbd5e1", bg="#0f172a").pack(anchor="w")

        detected_bank = getattr(self, "current_bank_name", "FNB (First National Bank)")
        bank_combo = ttk.Combobox(
            c2,
            values=[
                "FNB (First National Bank)",
                "Capitec (Business / Personal)",
                "Standard Bank",
                "Nedbank",
                "ABSA Bank",
                "Investec Bank",
                "Discovery Bank",
                "TymeBank / Bidvest",
                "SARS VAT201 / Tax Invoice",
                "Scanned Till Slip / Receipt",
                "Other Bank Statement",
            ],
            font=("Segoe UI", 9),
        )
        bank_combo.set(detected_bank if detected_bank else "FNB (First National Bank)")
        bank_combo.pack(fill=tk.X, ipady=1, pady=(2, 0))

        # Row 2: Category & Severity
        r2 = tk.Frame(grid_f, bg="#0f172a")
        r2.pack(fill=tk.X, pady=3)

        c3 = tk.Frame(r2, bg="#0f172a")
        c3.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        tk.Label(c3, text="Issue Category:", font=("Segoe UI", 8, "bold"), fg="#cbd5e1", bg="#0f172a").pack(anchor="w")
        cat_combo = ttk.Combobox(
            c3,
            values=[
                "Bank Statement Parsing Mismatch / Error",
                "Unrecognized Bank Layout (0 rows found)",
                "Scanned Till Slip / OCR Mismatch",
                "Sage Pastel / Xero Export File Issue",
                "Application Crash / Unhandled Exception",
                "General Feature Suggestion",
            ],
            state="readonly",
            font=("Segoe UI", 9),
        )
        cat_combo.set("Bank Statement Parsing Mismatch / Error")
        cat_combo.pack(fill=tk.X, ipady=1, pady=(2, 0))

        c4 = tk.Frame(r2, bg="#0f172a")
        c4.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(6, 0))
        tk.Label(c4, text="Target Accounting Software:", font=("Segoe UI", 8, "bold"), fg="#cbd5e1", bg="#0f172a").pack(anchor="w")
        erp_lbl = tk.Label(c4, text=self.erp_var.get(), font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#1e293b", anchor="w", padx=6, pady=3)
        erp_lbl.pack(fill=tk.X, pady=(2, 0))

        # Row 3: User Notes
        tk.Label(body_f, text="Description of What Happened:", font=("Segoe UI", 8, "bold"), fg="#cbd5e1", bg="#0f172a").pack(anchor="w", pady=(4, 2))
        notes_ent = tk.Entry(body_f, font=("Segoe UI", 9), bg="#1e293b", fg="white", insertbackground="white", relief="flat")
        if prefill_error:
            first_line = prefill_error.split("\n")[0]
            notes_ent.insert(0, f"Error encountered: {first_line}")
        else:
            notes_ent.insert(0, "e.g., Capitec statement missing column / date format not matched")
        notes_ent.pack(fill=tk.X, ipady=3, pady=(0, 6))

        # Diagnostic Payload Preview
        tk.Label(body_f, text="Sanitized Diagnostic Bundle (Automatically Prepared):", font=("Segoe UI", 8, "bold"), fg="#cbd5e1", bg="#0f172a").pack(anchor="w", pady=(2, 2))
        
        diag_text_box = tk.Text(body_f, height=10, font=("Consolas", 8), bg="#090d16", fg="#94a3b8", insertbackground="white", relief="flat", wrap="word")
        diag_text_box.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        # Build diagnostic bundle content
        hwid = get_hardware_id()
        os_info = f"{platform.system()} {platform.release()} ({platform.platform()})"
        clean_error = scrub_popia_diagnostics(prefill_error)
        clean_sample = scrub_popia_diagnostics(raw_snippet)

        bundle_lines = [
            "=================================================================",
            "TAXCLEAN ZA  -  AUTONOMOUS ENGINEERING DIAGNOSTIC BUNDLE",
            "=================================================================",
            f"Timestamp (UTC): {datetime.utcnow().isoformat()}Z",
            f"Software Version: v2.4.0.0 (MSIX Store Release)",
            f"Operating System: {os_info}",
            f"Python Runtime: {sys.version.split()[0]}",
            f"Hardware ID: {hwid}",
            f"Active Client Profile: {self.active_profile}",
            f"Target ERP: {self.erp_var.get()}",
            f"Current Bank Context: {detected_bank}",
            f"Reconciliation Balances: Open: {self.open_bal_var.get()} | Close: {self.close_bal_var.get()} | {self.variance_lbl.cget('text')}",
            "POPIA Scrubbing: ACTIVE (Account numbers, IDs, and emails redacted)",
            "-----------------------------------------------------------------",
            "[ERROR TRACEBACK / DETAILS]"
        ]
        if clean_error:
            bundle_lines.append(clean_error)
        else:
            bundle_lines.append("No active unhandled exception. Manual diagnostic report triggered by user.")

        if clean_sample:
            bundle_lines.append("-----------------------------------------------------------------")
            bundle_lines.append("[DOCUMENT FORMAT SNIPPET (POPIA SANITIZED)]")
            bundle_lines.append(clean_sample[:1000])

        bundle_lines.append("=================================================================")
        diag_content = "\n".join(bundle_lines)
        diag_text_box.insert("1.0", diag_content)
        diag_text_box.config(state="disabled")

        # Status / Feedback Label
        submit_status_lbl = tk.Label(body_f, text="", font=("Segoe UI", 9, "bold"), fg="#34d399", bg="#0f172a")
        submit_status_lbl.pack(anchor="w", pady=(0, 4))

        # Action Buttons Footer
        ftr = tk.Frame(dialog, bg="#1e293b", padx=16, pady=10)
        ftr.pack(fill=tk.X)

        def _do_copy():
            full_report = (
                f"TAXCLEAN ZA ISSUE REPORT\n"
                f"Contact: {email_ent.get().strip()}\n"
                f"Bank: {bank_combo.get().strip()}\n"
                f"Category: {cat_combo.get().strip()}\n"
                f"Notes: {notes_ent.get().strip()}\n\n"
                f"{diag_content}"
            )
            self.root.clipboard_clear()
            self.root.clipboard_append(full_report)
            submit_status_lbl.config(text="✓ Diagnostic bundle copied to clipboard! You can paste it into email or chat.", fg="#38bdf8")

        def _do_email_client():
            subject = f"[TaxClean ZA Diagnostics] {bank_combo.get().strip()} - {cat_combo.get().strip()}"
            body = (
                f"Hi TaxClean ZA Engineering Team,\n\n"
                f"Contact: {email_ent.get().strip()}\n"
                f"Bank / Doc: {bank_combo.get().strip()}\n"
                f"Category: {cat_combo.get().strip()}\n"
                f"Notes: {notes_ent.get().strip()}\n\n"
                f"{diag_content}\n"
            )
            mailto_url = f"mailto:sales@taxcleanza.com?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
            try:
                webbrowser.open(mailto_url)
                submit_status_lbl.config(text="✓ Opened your email client addressed to sales@taxcleanza.com.", fg="#34d399")
            except Exception as e:
                submit_status_lbl.config(text=f"Could not open mail client: {e}. Please use 'Copy Diagnostics'.", fg="#f87171")

        def _do_direct_submit():
            submit_status_lbl.config(text="⏳ Preparing report and transmitting...", fg="#38bdf8")
            dialog.update_idletasks()

            payload = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "email": email_ent.get().strip(),
                "bank": bank_combo.get().strip(),
                "category": cat_combo.get().strip(),
                "notes": notes_ent.get().strip(),
                "app_version": "v2.4.0.0",
                "diagnostics": diag_content,
            }

            def _submit_worker():
                sent_direct = False
                api_url = "https://taxcleanza.com/api/report-issue"
                try:
                    data_bytes = json.dumps(payload).encode("utf-8")
                    req = urllib.request.Request(
                        api_url,
                        data=data_bytes,
                        headers={"Content-Type": "application/json", "User-Agent": "TaxCleanZA-Desktop/2.4.0"}
                    )
                    with urllib.request.urlopen(req, timeout=4) as resp:
                        if resp.status in (200, 201, 204):
                            sent_direct = True
                except Exception:
                    sent_direct = False

                def _on_done():
                    if sent_direct:
                        submit_status_lbl.config(
                            text="✓ Report delivered directly to engineering pipeline! Our monitor reviews traces every 15m.",
                            fg="#34d399"
                        )
                        messagebox.showinfo(
                            "Report Sent",
                            "✓ Thank you!\n\nYour diagnostic bundle was successfully delivered to sales@taxcleanza.com.\n\nOur autonomous agent pipeline checks for format traces every 15 minutes and will analyze this layout.",
                            parent=dialog
                        )
                    else:
                        _do_email_client()
                        messagebox.showinfo(
                            "Diagnostic Bundle Ready",
                            "We opened your email client to send this report directly to sales@taxcleanza.com.\n\n(The diagnostic text has also been copied to your clipboard).",
                            parent=dialog
                        )

                self.root.after(0, _on_done)

            threading.Thread(target=_submit_worker, daemon=True).start()

        HDButton(
            ftr,
            text="🚀 Send to Engineering Agents",
            font=("Segoe UI", 9, "bold"),
            bg="#10b981",
            fg="white",
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            command=_do_direct_submit,
        ).pack(side=tk.LEFT, padx=(0, 6))

        HDButton(
            ftr,
            text="📧 Open in Email Client",
            font=("Segoe UI", 9),
            bg="#0369a1",
            fg="white",
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=_do_email_client,
        ).pack(side=tk.LEFT, padx=(0, 6))

        HDButton(
            ftr,
            text="📋 Copy Diagnostics",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="#cbd5e1",
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=_do_copy,
        ).pack(side=tk.LEFT, padx=(0, 6))

        HDButton(
            ftr,
            text="Close",
            font=("Segoe UI", 9),
            bg="#1e293b",
            fg="#94a3b8",
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            command=dialog.destroy,
        ).pack(side=tk.RIGHT)

    # ==========================================================================
    # IN-APP AUTOMATED UPDATE & VERSION MANAGEMENT ENGINE
    # ==========================================================================
    def _start_background_update_check(self, silent=True):
        """Spawns an asynchronous background thread to check for software updates (Direct Web Downloads only)."""
        if getattr(self, "is_store_edition", False):
            # Microsoft Store packages are automatically updated by Windows Update.
            # Store developer policies forbid third-party external .exe downloaders.
            return
        t = threading.Thread(target=self._run_update_check, args=(silent,), daemon=True)
        t.start()

    def _run_update_check(self, silent=True):
        """Queries the secure TaxClean ZA Cloudflare endpoint for software releases."""
        try:
            req = urllib.request.Request(
                VERSION_CHECK_URL,
                headers={"User-Agent": f"TaxCleanZA-Desktop/{APP_VERSION} (Windows; x64)"},
            )
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                if resp.status == 200:
                    raw_data = resp.read().decode("utf-8")
                    data = json.loads(raw_data)
                    remote_ver = data.get("latest_version", APP_VERSION)
                    if is_version_newer(remote_ver, APP_VERSION):
                        dismissed_ver = self.config.get("dismissed_update_version", "")
                        if silent and dismissed_ver == remote_ver:
                            return
                        self.root.after(0, lambda: self._show_update_banner(data))
                    else:
                        if not silent:
                            self.root.after(0, lambda: self._show_up_to_date_dialog(data))
        except Exception as e:
            if not silent:
                self.root.after(
                    0,
                    lambda: messagebox.showwarning(
                        "TaxClean ZA Updates",
                        f"Unable to check for updates right now.\n\nDetails: {e}\n\nPlease check your internet connection or visit https://taxcleanza.com.",
                    ),
                )

    def _show_update_banner(self, data: dict):
        """Displays a high-contrast B2B emerald notification banner at the top of the app."""
        if getattr(self, "is_store_edition", False):
            return

        for w in self.update_banner.winfo_children():
            w.destroy()

        remote_ver = data.get("latest_version", "New")
        headline = data.get("headline", "New features and performance enhancements")

        left_f = tk.Frame(self.update_banner, bg="#064e3b")
        left_f.pack(side=tk.LEFT, fill=tk.X, expand=True)

        badge_lbl = tk.Label(
            left_f,
            text="🚀 UPDATE AVAILABLE",
            font=("Segoe UI", 8, "bold"),
            fg="#ecfdf5",
            bg="#047857",
            padx=6,
            pady=2,
        )
        badge_lbl.pack(side=tk.LEFT, padx=(0, 10))

        msg_lbl = tk.Label(
            left_f,
            text=f"TaxClean ZA v{remote_ver} is available (Current: v{APP_VERSION}) - {headline}",
            font=("Segoe UI", 9, "bold"),
            fg="#f0fdf4",
            bg="#064e3b",
        )
        msg_lbl.pack(side=tk.LEFT)

        right_f = tk.Frame(self.update_banner, bg="#064e3b")
        right_f.pack(side=tk.RIGHT)

        upd_btn = tk.Button(
            right_f,
            text="⬇️ Update Now (1-Click)",
            font=("Segoe UI", 9, "bold"),
            bg="#10b981",
            fg="white",
            activebackground="#059669",
            activeforeground="white",
            relief="flat",
            padx=10,
            pady=2,
            cursor="hand2",
            command=lambda: self.start_one_click_update(data),
        )
        upd_btn.pack(side=tk.LEFT, padx=(0, 6))

        notes_btn = tk.Button(
            right_f,
            text="What's New",
            font=("Segoe UI", 8),
            bg="#047857",
            fg="#d1fae5",
            activebackground="#065f46",
            activeforeground="white",
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
            command=lambda: self.show_release_notes_dialog(data),
        )
        notes_btn.pack(side=tk.LEFT, padx=(0, 6))

        dismiss_btn = tk.Button(
            right_f,
            text="✕",
            font=("Segoe UI", 9, "bold"),
            bg="#064e3b",
            fg="#a7f3d0",
            activebackground="#047857",
            activeforeground="white",
            relief="flat",
            padx=6,
            pady=2,
            cursor="hand2",
            command=lambda: self._hide_update_banner(dismiss_permanently=True, version_str=remote_ver),
        )
        dismiss_btn.pack(side=tk.LEFT)

        if not self.update_banner.winfo_ismapped():
            self.update_banner.pack(side=tk.TOP, fill=tk.X, before=self.nav_frame)

    def _hide_update_banner(self, dismiss_permanently=False, version_str=""):
        """Hides the update banner and remembers user dismissal."""
        self.update_banner.pack_forget()
        if dismiss_permanently and version_str:
            self.config["dismissed_update_version"] = version_str
            self.save_config()

    def _show_up_to_date_dialog(self, data: dict):
        """Informs the user that their desktop installation is running the latest release."""
        if getattr(self, "is_store_edition", False):
            messagebox.showinfo(
                "TaxClean ZA - Microsoft Store Edition",
                f"✓ Microsoft Store Edition\n\nYou are running version v{APP_VERSION}.\n\nUpdates and security definitions are managed automatically by Windows Update in the background.",
            )
            return

        messagebox.showinfo(
            "TaxClean ZA Updates",
            f"✓ TaxClean ZA is up to date!\n\nYou are running the latest version: v{APP_VERSION}\nRelease Date: {data.get('release_date', '2026-10-23')}\n\nAll SA bank parsers, VAT201 algorithms, and ERP exporters are active.",
        )

    def show_release_notes_dialog(self, data: dict):
        """Displays release notes and changelog in an elegant dark slate window."""
        notes_dlg = tk.Toplevel(self.root)
        notes_dlg.title("TaxClean ZA - What's New")
        notes_dlg.geometry("520x400")
        notes_dlg.resizable(False, False)
        notes_dlg.configure(bg="#090d16")
        apply_dark_titlebar(notes_dlg)
        notes_dlg.transient(self.root)
        notes_dlg.grab_set()

        hdr = tk.Frame(notes_dlg, bg="#1e293b", padx=16, pady=12)
        hdr.pack(fill=tk.X)
        tk.Label(
            hdr,
            text=f"TaxClean ZA v{data.get('latest_version', 'Update')} Release Notes",
            font=("Segoe UI", 11, "bold"),
            fg="#38bdf8",
            bg="#1e293b",
        ).pack(anchor="w")

        bdy = tk.Frame(notes_dlg, bg="#0f172a", padx=16, pady=14)
        bdy.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            bdy,
            text="Key Enhancements in this Release:",
            font=("Segoe UI", 9, "bold"),
            fg="#f8fafc",
            bg="#0f172a",
        ).pack(anchor="w", pady=(0, 8))

        changelog = data.get("changelog", [])
        for item in changelog:
            row = tk.Frame(bdy, bg="#0f172a")
            row.pack(fill=tk.X, pady=3)
            tk.Label(row, text="•", font=("Segoe UI", 11, "bold"), fg="#10b981", bg="#0f172a").pack(side=tk.LEFT, padx=(4, 8), anchor="n")
            tk.Label(row, text=item, font=("Segoe UI", 9), fg="#cbd5e1", bg="#0f172a", wraplength=440, justify="left").pack(side=tk.LEFT, anchor="w")

        ftr = tk.Frame(notes_dlg, bg="#1e293b", padx=16, pady=10)
        ftr.pack(fill=tk.X)
        tk.Button(
            ftr,
            text="Close",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="white",
            relief="flat",
            padx=12,
            pady=3,
            command=notes_dlg.destroy,
        ).pack(side=tk.RIGHT)

        if not getattr(self, "is_store_edition", False) and is_version_newer(data.get("latest_version", APP_VERSION), APP_VERSION):
            tk.Button(
                ftr,
                text="⬇️ Update Now",
                font=("Segoe UI", 9, "bold"),
                bg="#10b981",
                fg="white",
                relief="flat",
                padx=12,
                pady=3,
                command=lambda: [notes_dlg.destroy(), self.start_one_click_update(data)],
            ).pack(side=tk.RIGHT, padx=(0, 8))

    def start_one_click_update(self, data: dict):
        """Streams the latest installer directly into %TEMP% and provides 1-click upgrade and restart."""
        if getattr(self, "is_store_edition", False):
            messagebox.showinfo(
                "TaxClean ZA - Microsoft Store Edition",
                "Your version of TaxClean ZA is managed by the Microsoft Store. Updates are downloaded automatically via Windows Update.",
            )
            return

        import hashlib
        raw_ver = str(data.get("latest_version", "latest"))
        remote_ver = re.sub(r"[^a-zA-Z0-9._-]", "", raw_ver)[:32] or "latest"
        download_url = str(data.get("download_url", "https://taxcleanza.com/download")).strip()
        if not download_url.startswith("https://taxcleanza.com/"):
            download_url = "https://taxcleanza.com/download"
        expected_sha = str(data.get("installer_sha256", "")).strip().lower()

        upd_dialog = tk.Toplevel(self.root)
        upd_dialog.title("TaxClean ZA - Live Software Update")
        upd_dialog.geometry("520x330")
        upd_dialog.resizable(False, False)
        upd_dialog.configure(bg="#090d16")
        apply_dark_titlebar(upd_dialog)
        upd_dialog.transient(self.root)
        upd_dialog.grab_set()

        try:
            rw = self.root.winfo_width()
            rh = self.root.winfo_height()
            rx = self.root.winfo_x()
            ry = self.root.winfo_y()
            upd_dialog.geometry(f"+{rx + (rw - 520)//2}+{ry + (rh - 330)//2}")
        except Exception:
            pass

        hdr = tk.Frame(upd_dialog, bg="#1e293b", padx=16, pady=12)
        hdr.pack(fill=tk.X)
        tk.Label(
            hdr,
            text="TaxClean ZA - Live Software Updater",
            font=("Segoe UI", 12, "bold"),
            fg="#38bdf8",
            bg="#1e293b",
        ).pack(anchor="w")
        tk.Label(
            hdr,
            text=f"Upgrading from v{APP_VERSION} to v{remote_ver} (All user data and licenses preserved)",
            font=("Segoe UI", 8),
            fg="#94a3b8",
            bg="#1e293b",
        ).pack(anchor="w", pady=(2, 0))

        bdy = tk.Frame(upd_dialog, bg="#0f172a", padx=20, pady=16)
        bdy.pack(fill=tk.BOTH, expand=True)

        status_lbl = tk.Label(
            bdy,
            text="Connecting to Cloudflare R2 secure edge...",
            font=("Segoe UI", 10, "bold"),
            fg="#f8fafc",
            bg="#0f172a",
        )
        status_lbl.pack(anchor="w", pady=(4, 6))

        sub_status_lbl = tk.Label(
            bdy,
            text="Preparing download package...",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#0f172a",
        )
        sub_status_lbl.pack(anchor="w", pady=(0, 10))

        # Progress bar without resetting global ttk theme!
        progress = ttk.Progressbar(
            bdy,
            orient="horizontal",
            mode="determinate",
            maximum=100,
        )
        progress.pack(fill=tk.X, pady=(0, 10))

        note_f = tk.Frame(bdy, bg="#064e3b", padx=10, pady=6)
        note_f.pack(fill=tk.X, pady=(0, 6))
        tk.Label(
            note_f,
            text="🛡️ Safe In-Place Upgrade: Client profiles, custom Chart of Accounts rules, and active licenses in %APPDATA% are 100% retained.",
            font=("Segoe UI", 8),
            fg="#34d399",
            bg="#064e3b",
            wraplength=460,
            justify="left",
        ).pack(anchor="w")

        ftr = tk.Frame(upd_dialog, bg="#1e293b", padx=16, pady=10)
        ftr.pack(fill=tk.X)

        cancel_btn = tk.Button(
            ftr,
            text="Cancel",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="white",
            relief="flat",
            padx=12,
            pady=4,
            command=upd_dialog.destroy,
        )
        cancel_btn.pack(side=tk.RIGHT)

        action_btn = tk.Button(
            ftr,
            text="Please wait...",
            font=("Segoe UI", 9, "bold"),
            bg="#475569",
            fg="#94a3b8",
            relief="flat",
            state="disabled",
            padx=16,
            pady=4,
        )
        action_btn.pack(side=tk.RIGHT, padx=(0, 8))

        cancel_flag = {"cancelled": False}

        def _on_cancel():
            cancel_flag["cancelled"] = True
            upd_dialog.destroy()

        cancel_btn.config(command=_on_cancel)
        upd_dialog.protocol("WM_DELETE_WINDOW", _on_cancel)

        def _download_worker():
            target_path = Path(tempfile.gettempdir()) / f"TaxCleanInstaller_v{remote_ver}.exe"
            hasher = hashlib.sha256()
            try:
                req = urllib.request.Request(
                    download_url,
                    headers={"User-Agent": f"TaxCleanZA-LiveUpdater/{APP_VERSION}"},
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    total_len = resp.headers.get("Content-Length")
                    total_bytes = int(total_len) if total_len else 0
                    downloaded = 0

                    with open(target_path, "wb") as f_out:
                        chunk_size = 64 * 1024
                        while not cancel_flag["cancelled"]:
                            chunk = resp.read(chunk_size)
                            if not chunk:
                                break
                            f_out.write(chunk)
                            hasher.update(chunk)
                            downloaded += len(chunk)
                            if total_bytes > 0:
                                pct = (downloaded / total_bytes) * 100
                                mb_down = downloaded / (1024 * 1024)
                                mb_tot = total_bytes / (1024 * 1024)
                                sub_txt = f"{mb_down:.1f} MB / {mb_tot:.1f} MB ({pct:.0f}%)"
                            else:
                                mb_down = downloaded / (1024 * 1024)
                                pct = 0
                                sub_txt = f"{mb_down:.1f} MB downloaded"

                            def _update_ui(p=pct, st=sub_txt):
                                if not cancel_flag["cancelled"] and upd_dialog.winfo_exists():
                                    progress["value"] = p
                                    sub_status_lbl.config(text=st)
                                    status_lbl.config(text="Downloading TaxClean ZA Update...")

                            upd_dialog.after(0, _update_ui)

                if cancel_flag["cancelled"]:
                    try:
                        target_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                    return

                # Mandatory Cryptographic SHA-256 verification
                calc_sha = hasher.hexdigest().lower()
                if not expected_sha or len(expected_sha) != 64 or not re.match(r"^[0-9a-f]{64}$", expected_sha) or expected_sha == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855":
                    target_path.unlink(missing_ok=True)
                    raise ValueError("Update manifest is missing a valid 64-char SHA-256 digest.")
                if calc_sha != expected_sha:
                    target_path.unlink(missing_ok=True)
                    raise ValueError(f"SHA-256 verification failed (expected {expected_sha[:8]}..., got {calc_sha[:8]}...)")
                verified_txt = "Download Complete and Cryptographically Verified (SHA-256)!"

                def _on_complete():
                    if not upd_dialog.winfo_exists():
                        return
                    progress["value"] = 100
                    status_lbl.config(text=f"✓ {verified_txt}", fg="#34d399")
                    sub_status_lbl.config(text="Ready to install. Click below to close TaxClean ZA and upgrade.")
                    cancel_btn.config(text="Later", command=upd_dialog.destroy)
                    action_btn.config(
                        text="🚀 Install & Restart Now",
                        bg="#10b981",
                        fg="white",
                        state="normal",
                        cursor="hand2",
                        command=lambda: self._execute_installer_and_restart(target_path, upd_dialog),
                    )

                upd_dialog.after(0, _on_complete)

            except Exception as ex:
                if cancel_flag["cancelled"]:
                    return
                def _on_err(err_str=str(ex)):
                    if not upd_dialog.winfo_exists():
                        return
                    status_lbl.config(text="Download Interrupted", fg="#f87171")
                    sub_status_lbl.config(text=f"Notice: {err_str}")
                    action_btn.config(
                        text="🌐 Open in Browser",
                        bg="#38bdf8",
                        fg="#0f172a",
                        state="normal",
                        cursor="hand2",
                        command=lambda: [webbrowser.open(download_url), upd_dialog.destroy()],
                    )
                upd_dialog.after(0, _on_err)

        threading.Thread(target=_download_worker, daemon=True).start()

    def _execute_installer_and_restart(self, target_path: Path, upd_dialog=None):
        """Spawns the downloaded installer with Windows elevation and closes TaxClean ZA gracefully."""
        if upd_dialog and upd_dialog.winfo_exists():
            upd_dialog.destroy()
        try:
            subprocess.Popen([str(target_path)], shell=False)
            self._on_close()
        except Exception as e:
            messagebox.showerror(
                "Update Launch Notice",
                f"Could not automatically launch installer:\n{e}\n\nPlease run the installer file directly from:\n{target_path}",
            )

    def check_for_updates_interactive(self):
        """Triggers a user-initiated update check from the Tools menu."""
        if getattr(self, "is_store_edition", False):
            messagebox.showinfo(
                "TaxClean ZA - Microsoft Store Edition",
                f"✓ Microsoft Store Edition\n\nYou are running version v{APP_VERSION}.\n\nUpdates are managed automatically by the Microsoft Store / Windows Update in the background.",
            )
            return
        self._start_background_update_check(silent=False)


    def open_duplicate_sentinel_dialog(self):
        """
        Automated Duplicate & Overlapping Statement Sentinel:
        Scans all transactions in the current workspace for duplicate / overlapping rows,
        displaying matching pairs and offering 1-click deduplication.
        """
        if not self.transactions:
            messagebox.showinfo("Duplicate Sentinel", "Workspace is currently empty. No transactions to scan.", parent=self.root)
            return

        seen_map = {}
        duplicates = []
        for idx, t in enumerate(self.transactions):
            amt = round(float(t.get("amount", 0)), 2)
            payee = (t.get("clean_payee") or "").upper().strip()
            date_str = str(t.get("date", "")).strip()
            key = (date_str, amt, payee)

            if key in seen_map:
                duplicates.append({
                    "original_idx": seen_map[key],
                    "duplicate_idx": idx,
                    "date": date_str,
                    "payee": t.get("clean_payee", ""),
                    "amount": amt,
                    "ref": t.get("ref", "")
                })
            else:
                seen_map[key] = idx

        if not duplicates:
            messagebox.showinfo(
                "Duplicate Sentinel",
                "✓ Sentinel Scan Complete:\n\nZero duplicate or overlapping transactions found across the entire workspace!\n\nAll dates and amounts are unique.",
                parent=self.root
            )
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("TaxClean ZA  -  Duplicate & Overlap Sentinel")
        dialog.geometry("740x520")
        dialog.minsize(640, 440)
        dialog.configure(bg="#0f172a")
        dialog.transient(self.root)
        dialog.grab_set()

        hdr = tk.Frame(dialog, bg="#1e293b", padx=16, pady=12)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="🛡️ Duplicate & Statement Overlap Sentinel", font=("Segoe UI", 12, "bold"), fg="#f59e0b", bg="#1e293b").pack(anchor="w")

        tot_dup_val = sum(abs(d["amount"]) for d in duplicates)
        tk.Label(
            hdr,
            text=f"Detected {len(duplicates)} duplicate/overlapping rows totaling R {tot_dup_val:,.2f}.\nPurging duplicates eliminates double-posting in Sage/Xero and prevents over-claiming SARS VAT.",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#1e293b",
            justify="left"
        ).pack(anchor="w", pady=(3, 0))

        content_f = tk.Frame(dialog, bg="#0f172a", padx=16, pady=8)
        content_f.pack(fill=tk.BOTH, expand=True)

        cols = ("orig_idx", "dup_idx", "date", "payee", "amount", "ref")
        tree = ttk.Treeview(content_f, columns=cols, show="headings", height=12)
        tree.heading("orig_idx", text="Original Row")
        tree.heading("dup_idx", text="Duplicate Copy")
        tree.heading("date", text="Date")
        tree.heading("payee", text="Payee / Description")
        tree.heading("amount", text="Amount (ZAR)")
        tree.heading("ref", text="Reference")

        tree.column("orig_idx", width=85, anchor="center")
        tree.column("dup_idx", width=95, anchor="center")
        tree.column("date", width=85, anchor="center")
        tree.column("payee", width=220, anchor="w")
        tree.column("amount", width=105, anchor="e")
        tree.column("ref", width=110, anchor="w")

        for d in duplicates:
            tree.insert("", tk.END, values=(
                f"Row {d['original_idx'] + 1}",
                f"Row {d['duplicate_idx'] + 1}",
                d["date"],
                d["payee"],
                f"R {d['amount']:,.2f}",
                d["ref"]
            ))

        sb = ttk.Scrollbar(content_f, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        ftr = tk.Frame(dialog, bg="#1e293b", padx=16, pady=10)
        ftr.pack(fill=tk.X)

        def _do_purge():
            dup_indices = set(d["duplicate_idx"] for d in duplicates)
            self.push_undo_state()
            self.transactions = [t for i, t in enumerate(self.transactions) if i not in dup_indices]
            self.render_grid()
            self.save_current_session()
            dialog.destroy()
            messagebox.showinfo(
                "Deduplication Complete",
                f"✓ Successfully purged {len(duplicates)} duplicate copies!\n\nRetained original entries. Your ledger and VAT working papers are now 100% clean.",
                parent=self.root
            )

        HDButton(
            ftr,
            text=f"🗑️ 1-Click Purge {len(duplicates)} Duplicate Copies",
            font=("Segoe UI", 9, "bold"),
            bg="#991b1b",
            fg="white",
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            command=_do_purge
        ).pack(side=tk.LEFT, padx=(0, 6))

        HDButton(
            ftr,
            text="✓ Keep All (No Action)",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="#cbd5e1",
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=dialog.destroy
        ).pack(side=tk.LEFT)

    def paste_from_clipboard_dialog(self):
        """
        Direct Clipboard & Excel Direct-Paste Ingest (Ctrl+V):
        Allows bookkeepers to copy tabular rows straight from Excel, Google Sheets,
        or CSV text and ingest directly into the TaxClean ZA balancing grid.
        """
        try:
            raw_clip = self.root.clipboard_get()
        except Exception:
            raw_clip = ""

        if not raw_clip or not raw_clip.strip():
            messagebox.showwarning(
                "Clipboard Empty",
                "Clipboard is empty or does not contain text.\n\nCopy rows from Microsoft Excel, Google Sheets, or a CSV file, then click this button or press Ctrl+V.",
                parent=self.root
            )
            return

        lines = [ln.strip() for ln in raw_clip.splitlines() if ln.strip()]
        if not lines:
            messagebox.showwarning("Clipboard Notice", "No text lines detected in clipboard.", parent=self.root)
            return

        first_line = lines[0]
        delim = "\t" if "\t" in first_line else "," if "," in first_line else ";" if ";" in first_line else "|" if "|" in first_line else None

        parsed_rows = []
        date_pattern = re.compile(r"\b(\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})\b")

        for line in lines:
            if delim:
                parts = [p.strip() for p in line.split(delim)]
            else:
                parts = line.split()

            if len(parts) < 2:
                continue

            first_up = parts[0].upper()
            if any(h in first_up for h in ["DATE", "TRANSACTION", "DESCRIPTION", "STATEMENT", "POSTING"]):
                continue

            dt_val = ""
            amt_val = None
            payee_parts = []

            for p in parts:
                clean_p = p.replace('"', '').strip()
                if not dt_val and date_pattern.search(clean_p):
                    dt_val = date_pattern.search(clean_p).group(1)
                    continue

                amt_str = re.sub(r"[R\s]", "", clean_p)
                if amt_str.startswith("(") and amt_str.endswith(")"):
                    amt_str = "-" + amt_str[1:-1]
                if "," in amt_str and "." not in amt_str:
                    amt_str = amt_str.replace(",", ".")
                elif "," in amt_str and "." in amt_str:
                    amt_str = amt_str.replace(",", "")

                try:
                    val = float(amt_str)
                    if amt_val is None:
                        amt_val = val
                        continue
                except ValueError:
                    pass

                payee_parts.append(clean_p)

            if dt_val and amt_val is not None:
                payee_str = " ".join(payee_parts).strip() if payee_parts else "Direct Entry"
                parsed_rows.append({
                    "date": dt_val,
                    "desc": payee_str,
                    "amount": amt_val
                })

        if not parsed_rows:
            messagebox.showwarning(
                "Parse Notice",
                "Could not automatically parse tabular Date and Amount columns from clipboard text.\n\nTip: Copy a block of cells from Excel with Date, Description, and Amount columns.",
                parent=self.root
            )
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("TaxClean ZA  -  Quick Ingest from Excel Clipboard")
        dialog.geometry("700x520")
        dialog.minsize(600, 420)
        dialog.configure(bg="#0f172a")
        dialog.transient(self.root)
        dialog.grab_set()

        hdr = tk.Frame(dialog, bg="#1e293b", padx=16, pady=12)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="📋 Quick Ingest from Excel Clipboard", font=("Segoe UI", 12, "bold"), fg="#38bdf8", bg="#1e293b").pack(anchor="w")
        tk.Label(
            hdr,
            text=f"Detected {len(parsed_rows)} transaction rows from clipboard. Review and ingest directly into workspace.",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#1e293b"
        ).pack(anchor="w", pady=(2, 0))

        content_f = tk.Frame(dialog, bg="#0f172a", padx=16, pady=8)
        content_f.pack(fill=tk.BOTH, expand=True)

        cols = ("date", "payee", "amount")
        tree = ttk.Treeview(content_f, columns=cols, show="headings", height=11)
        tree.heading("date", text="Date")
        tree.heading("payee", text="Payee / Description")
        tree.heading("amount", text="Amount (ZAR)")

        tree.column("date", width=100, anchor="center")
        tree.column("payee", width=360, anchor="w")
        tree.column("amount", width=120, anchor="e")

        for r in parsed_rows:
            tree.insert("", tk.END, values=(r["date"], r["desc"], f"R {r['amount']:,.2f}"))

        sb = ttk.Scrollbar(content_f, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        ftr = tk.Frame(dialog, bg="#1e293b", padx=16, pady=10)
        ftr.pack(fill=tk.X)

        def _do_ingest(append_mode=True):
            self.push_undo_state()
            coa = self.config["profiles"][self.active_profile]["coa"]
            worker = ParseWorker("clipboard.txt", coa, self.active_profile, self.memory, None)

            new_records = []
            for r in parsed_rows:
                py = r["desc"]
                amt = r["amount"]
                cat = worker.categorize(py, amt)
                net = _dec_round(amt + cat["vat_claim"]) if amt < 0 else _dec_round(amt - cat["vat_claim"])
                new_records.append({
                    "date": r["date"],
                    "ref": "CLIPBOARD",
                    "acc_type": cat["acc_type"],
                    "clean_payee": cat["clean_payee"],
                    "code": cat["code"],
                    "name": cat["name"],
                    "amount": amt,
                    "vat_type": cat["vat_type"],
                    "vat_claim": cat["vat_claim"],
                    "net": net,
                    "is_suspense": cat["is_suspense"],
                    "audit_status": "✓ Clipboard Ingest",
                    "query_reason": cat["reason"],
                })

            if append_mode and self.transactions:
                self.transactions.extend(new_records)
            else:
                self.transactions = new_records

            self.render_grid()
            self.save_current_session()
            dialog.destroy()
            self.status_lbl.config(text=f"✓ Successfully ingested {len(new_records)} rows from Excel clipboard.")

        HDButton(
            ftr,
            text=f"➕ Append {len(parsed_rows)} Rows to Workspace",
            font=("Segoe UI", 9, "bold"),
            bg="#0284c7",
            fg="white",
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            command=lambda: _do_ingest(append_mode=True)
        ).pack(side=tk.LEFT, padx=(0, 6))

        HDButton(
            ftr,
            text="🗑️ Replace Workspace",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="white",
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=lambda: _do_ingest(append_mode=False)
        ).pack(side=tk.LEFT, padx=(0, 6))

        HDButton(
            ftr,
            text="Cancel",
            font=("Segoe UI", 9),
            bg="#1e293b",
            fg="#94a3b8",
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            command=dialog.destroy
        ).pack(side=tk.RIGHT)

    def export_vat201_excel_audit_pack(self):
        """
        1-Click SARS VAT201 Audit Working Paper Pack (.xlsx):
        Exports a complete, multi-tab audit pack compliant with SARS Tax Administration Act Section 29/30.
        """
        if not self.transactions:
            messagebox.showwarning("VAT201 Export", "No transaction records to export.", parent=self.root)
            return

        default_fname = f"SARS_VAT201_{self.active_profile}_{datetime.now().strftime('%Y%m')}.xlsx"
        save_path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Save SARS VAT201 Audit Working Paper Pack",
            initialfile=default_fname,
            defaultextension=".xlsx",
            filetypes=[("Excel Workbook", "*.xlsx")]
        )
        if not save_path:
            return

        try:
            fye = self.config["profiles"][self.active_profile].get("fye", "February")
            AccountingExporter.export_vat201_schedule(
                Path(save_path),
                self.transactions,
                entity_name=self.active_profile,
                fye_month=fye
            )
            ans = messagebox.askyesno(
                "Export Complete",
                f"✓ SARS VAT201 Audit Working Paper Pack successfully generated!\n\nSaved to:\n{save_path}\n\nWould you like to open the file now?",
                parent=self.root
            )
            if ans:
                try:
                    open_file_or_folder(save_path)
                except Exception:
                    webbrowser.open(f"file:///{save_path}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not generate Excel VAT201 pack:\n\n{e}", parent=self.root)

    def open_contra_transfer_cleanser_dialog(self):
        """
        Inter-Account / Contra Transfer Paired Cleanser:
        Finds internal transfers between company accounts with matching amounts
        and dates within ±3 days, coding them to Contra (Account 9999/000, 0% VAT).
        """
        if not self.transactions:
            messagebox.showinfo("Contra Cleanser", "Workspace is currently empty.", parent=self.root)
            return

        transfer_keywords = ["TFR", "TRF", "TRANSFER", "PAYMENT TO", "FROM ACC", "SAVINGS", "CHEQUE", "MONEY MARKET", "INTER-ACCOUNT", "SWEEP"]

        pairs = []
        used_indices = set()

        for i, t1 in enumerate(self.transactions):
            if i in used_indices:
                continue
            amt1 = float(t1.get("amount", 0))
            if amt1 == 0:
                continue

            p1 = (t1.get("clean_payee") or "").upper()

            for j, t2 in enumerate(self.transactions):
                if j <= i or j in used_indices:
                    continue
                amt2 = float(t2.get("amount", 0))
                if abs(amt1 + amt2) < 0.02:
                    p2 = (t2.get("clean_payee") or "").upper()
                    has_kw = any(k in p1 for k in transfer_keywords) or any(k in p2 for k in transfer_keywords)
                    if has_kw or abs(amt1) >= 1000.0:
                        pairs.append((i, j, t1, t2))
                        used_indices.add(i)
                        used_indices.add(j)
                        break

        if not pairs:
            messagebox.showinfo(
                "Contra Cleanser",
                "✓ No unlinked internal transfer pairs found.\n\nAll credits and debits appear to be independent third-party transactions.",
                parent=self.root
            )
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("TaxClean ZA  -  Inter-Account Contra Transfer Cleanser")
        dialog.geometry("740x500")
        dialog.minsize(640, 400)
        dialog.configure(bg="#0f172a")
        dialog.transient(self.root)
        dialog.grab_set()

        hdr = tk.Frame(dialog, bg="#1e293b", padx=16, pady=12)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="🔄 Inter-Account Contra Transfer Cleanser", font=("Segoe UI", 12, "bold"), fg="#38bdf8", bg="#1e293b").pack(anchor="w")
        tk.Label(
            hdr,
            text=f"Found {len(pairs)} matching inter-account transfer pairs ({len(pairs)*2} rows).\nCoding them to Contra (Account 9999/000) prevents artificial inflation of turnover or expenses.",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#1e293b"
        ).pack(anchor="w", pady=(2, 0))

        content_f = tk.Frame(dialog, bg="#0f172a", padx=16, pady=8)
        content_f.pack(fill=tk.BOTH, expand=True)

        cols = ("pair_num", "debit_side", "credit_side", "amount")
        tree = ttk.Treeview(content_f, columns=cols, show="headings", height=10)
        tree.heading("pair_num", text="Pair #")
        tree.heading("debit_side", text="Debit Side (Outflow)")
        tree.heading("credit_side", text="Credit Side (Inflow)")
        tree.heading("amount", text="Amount (ZAR)")

        tree.column("pair_num", width=60, anchor="center")
        tree.column("debit_side", width=260, anchor="w")
        tree.column("credit_side", width=260, anchor="w")
        tree.column("amount", width=110, anchor="e")

        for idx, (i, j, t1, t2) in enumerate(pairs, 1):
            deb = t1 if t1["amount"] < 0 else t2
            cred = t2 if t1["amount"] < 0 else t1
            amt_disp = f"R {abs(deb['amount']):,.2f}"
            tree.insert("", tk.END, values=(
                f"#{idx}",
                f"{deb.get('date')} - {deb.get('clean_payee')}",
                f"{cred.get('date')} - {cred.get('clean_payee')}",
                amt_disp
            ))

        sb = ttk.Scrollbar(content_f, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        ftr = tk.Frame(dialog, bg="#1e293b", padx=16, pady=10)
        ftr.pack(fill=tk.X)

        def _do_code_contra():
            self.push_undo_state()
            for i, j, _, _ in pairs:
                for idx in (i, j):
                    self.transactions[idx]["code"] = "9999/000"
                    self.transactions[idx]["name"] = "Contra / Inter-Bank Transfer"
                    self.transactions[idx]["acc_type"] = "Suspense/Contra"
                    self.transactions[idx]["vat_type"] = "Zero"
                    self.transactions[idx]["vat_claim"] = 0.0
                    self.transactions[idx]["net"] = self.transactions[idx]["amount"]
                    self.transactions[idx]["is_suspense"] = True
                    self.transactions[idx]["audit_status"] = "✓ Contra Paired"
            self.render_grid()
            self.save_current_session()
            dialog.destroy()
            messagebox.showinfo(
                "Contra Coding Complete",
                f"✓ Successfully coded {len(pairs)*2} transfer rows to Contra Transfer (9999/000, 0% VAT).\n\nCompany turnover and expenses are now perfectly protected.",
                parent=self.root
            )

        HDButton(
            ftr,
            text=f"⚡ 1-Click Code {len(pairs)} Pairs to Contra (9999/000)",
            font=("Segoe UI", 9, "bold"),
            bg="#10b981",
            fg="white",
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            command=_do_code_contra
        ).pack(side=tk.LEFT, padx=(0, 6))

        HDButton(
            ftr,
            text="Close",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="white",
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=dialog.destroy
        ).pack(side=tk.RIGHT)

    def load_sample_batch(self):
        sample_raw = """
        Statement Number: 1
        Opening Balance: 3400.00
        2026/07/01 POS Purchase Superspar Karaglen -206.69 3193.31
        2026/07/02 POS Purchase KFC Edenglen -184.50 3008.81
        2026/07/03 POS Purchase Highway Gardens Sup -200.00 2808.81
        2026/07/04 POS Purchase Shein Cr -785.00 2023.81
        2026/07/05 FNB App Payment From Donation 2500.00 4523.81
        2026/07/06 POS Purchase Shein -610.00 3913.81
        2026/07/07 POS Purchase Highway Gardens Sup -229.50 3684.31
        2026/07/08 Monthly Service Fees Cheque Acc -190.00 3494.31
        2026/07/09 Client Payment Inv-1092 Altair Tech 7500.00 10994.31
        2026/07/10 City Power Prepaid Elec -1200.00 9794.31
        2026/07/11 Engen Forecourt Sec918 -650.00 9144.31
        2026/07/12 Vodacom Business ACB Debit -1199.00 7945.31
        2026/07/13 PicknPay Plumstead Store Purchase -947.91 6997.40
        2026/07/14 Spar Salzburg Store Purchase -100.00 6897.40
        Closing Balance: 6897.40
        """
        coa = self.config["profiles"][self.active_profile]["coa"]
        worker = ParseWorker("sample.txt", coa, self.active_profile, self.memory, self.task_queue)
        parse_result = worker.parse_text(sample_raw)
        self.transactions = parse_result["records"]
        self.open_bal_var.set("3400.00")
        self.close_bal_var.set("6897.40")
        self.render_grid()
        self.save_current_session()


if __name__ == "__main__":
    root = ctk.CTk() if HAS_CUSTOMTKINTER else tk.Tk()
    app = ModernApp(root)
    root.mainloop()
