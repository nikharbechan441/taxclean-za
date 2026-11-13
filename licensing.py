"""
TaxClean ZA — Asymmetric Cryptographic Licensing & Hardware-Bound Anti-Piracy Engine
Adheres to:
1. Consumer Protection Act 68 of 2008 (Clear terms, transparent limits)
2. Electronic Communications and Transactions Act 25 of 2002 (Asymmetric RSA-1024 Digital Signatures)
3. 100% Offline Verification (Only the Public Key is embedded in the client; Private Key never leaves vendor)
4. Hardware-Bound Trial Anchors (Prevents trial resets via DB deletion or reinstallation)
"""

import base64
from datetime import datetime
import hashlib
import hmac
import os
from pathlib import Path
import platform
import re
import sqlite3
import sys
from typing import Any, Dict, Optional, Tuple
import uuid

try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False

MAX_TRIAL_STATEMENTS = 5

# ==============================================================================
# ASYMMETRIC RSA-1024 PUBLIC VERIFICATION KEY (PUBLIC KEY ONLY)
# The corresponding Private Exponent (D) is held strictly offline in issue_license.py
# and is NEVER bundled into the distributed executable.
# ==============================================================================
PUBLIC_MODULUS_HEX = (
    "bf0e923229a2fdf38fa67e29bc5be4c52ae8e0f38e3ee3d688554efa3bf7fb77"
    "b4c0b38e2696d052e11ea637849c54c794d75cb52780491708e2a90ba2750680"
    "d22bd739e6e50a576d8d8c6a7719f6929b514f1aa96050fffcf09f3355802a52"
    "e73ac84d07e0e24b205bb2ece5c53009368b6445e85a6e433cb4439e3804ea69"
)
PUBLIC_MODULUS_N = int(PUBLIC_MODULUS_HEX, 16)
PUBLIC_EXPONENT_E = 65537

_ANCHOR_REG_PATH = r"Software\Classes\CLSID\{8B1D4F3C-9A5A-4B2C-9C08-6E2A5B8E1D9F}"


def get_hardware_id() -> str:
    """
    Generates a deterministic 8-character Hardware ID (e.g. '8F4A2C91')
    bound to the underlying Windows OS installation and hardware node.
    """
    raw_parts = []
    if HAS_WINREG:
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
                0,
                winreg.KEY_READ | getattr(winreg, "KEY_WOW64_64KEY", 0),
            ) as k:
                guid, _ = winreg.QueryValueEx(k, "MachineGuid")
                if guid:
                    raw_parts.append(str(guid).strip())
        except Exception:
            pass

    if not raw_parts:
        raw_parts.append(str(uuid.getnode()))
        raw_parts.append(os.environ.get("COMPUTERNAME") or platform.node() or "TCZA-PC")

    digest = hashlib.sha256("|".join(raw_parts).encode("utf-8")).hexdigest().upper()
    return digest[:8]


def _pkcs1_v15_sha256_int(payload_str: str) -> int:
    """Constructs deterministic PKCS#1 v1.5 padded 1024-bit integer for SHA-256 digest."""
    digest = hashlib.sha256(payload_str.encode("utf-8")).digest()
    # 128 bytes total: 0x00 || 0x01 || (93 bytes of 0xFF) || 0x00 || (32-byte SHA-256 digest)
    padded = b"\x00\x01" + (b"\xff" * 93) + b"\x00" + digest
    return int.from_bytes(padded, "big")


VALID_LICENSE_PLANS = {"PASS", "SOLO", "PRO", "PRACTICE", "FIRM", "ENTERPRISE"}


def verify_license_key(
    email: str, license_key: str, current_hw_id: Optional[str] = None
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Verifies a TaxClean ZA license key cryptographically offline using the RSA-1024 Public Key.
    Format: TCZA-{PLAN}-{YYYYMMDD}-{HW_LOCK}-{RSA_SIGNATURE}
    """
    clean_email = email.strip().lower()
    raw_key = license_key.strip()
    parts = raw_key.split("-")
    if len(parts) < 5 or parts[0].upper() != "TCZA":
        return False, "Invalid license key format. Expected TCZA-PLAN-YYYYMMDD-HWID-SIGNATURE.", {}

    plan = parts[1].upper()
    exp_str = parts[2]
    hw_lock = parts[3].upper()
    # Signature may contain '-' because urlsafe_b64encode uses '-' and '_'
    sig_b64 = "-".join(parts[4:])

    if plan not in VALID_LICENSE_PLANS:
        return False, f"Unrecognized license plan tier '{plan}'.", {}
    if hw_lock != "ANY" and not re.match(r"^[A-F0-9]{8}$", hw_lock):
        return False, "Invalid hardware lock format in license key.", {}

    # 1. Verify Hardware ID lock if key is bound to a specific machine
    local_hwid = (current_hw_id.strip().upper() if current_hw_id else "") or get_hardware_id()
    if hw_lock != "ANY" and hw_lock != local_hwid:
        return (
            False,
            f"This license key is hardware-locked to machine [{hw_lock}], "
            f"which does not match this PC's Hardware ID [{local_hwid}].",
            {},
        )

    # 2. Verify Asymmetric RSA-1024 Digital Signature using Public Key (N, E)
    try:
        pad_len = (4 - len(sig_b64) % 4) % 4
        sig_bytes = base64.urlsafe_b64decode(sig_b64 + ("=" * pad_len))
        if len(sig_bytes) != 128:
            return False, "Invalid cryptographic signature block length.", {}
        sig_int = int.from_bytes(sig_bytes, "big")
    except Exception:
        return False, "Malformed cryptographic signature encoding.", {}

    payload = f"{clean_email}:{plan}:{exp_str}:{hw_lock}"
    expected_int = _pkcs1_v15_sha256_int(payload)
    recovered_int = pow(sig_int, PUBLIC_EXPONENT_E, PUBLIC_MODULUS_N)

    if recovered_int != expected_int:
        return False, "Cryptographic signature verification failed for this email address.", {}

    # 3. Verify Expiry Date
    try:
        exp_dt = datetime.strptime(exp_str, "%Y%m%d").replace(hour=23, minute=59, second=59)
        if datetime.now() > exp_dt:
            return False, f"License key expired on {exp_dt.strftime('%d %B %Y')}.", {}
    except ValueError:
        return False, "Invalid expiry date encoded in license key.", {}

    return True, f"Valid {plan} License active until {exp_dt.strftime('%d %B %Y')} (Node: {local_hwid}).", {
        "email": clean_email,
        "plan": plan,
        "expiry": exp_dt.strftime("%Y-%m-%d"),
        "license_key": raw_key,
        "bound_hwid": local_hwid,
    }


class LicenseManager:
    """
    Manages statement count limits and license persistence across SQLite,
    Windows Registry, and hidden AppData anchors to prevent trial reset tampering.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.hwid = get_hardware_id()
        self.init_db()

    def _sign_anchor(self, count: int) -> str:
        secret = f"TCZA-HW-VAULT-{self.hwid}-2026".encode("utf-8")
        msg = f"STATEMENTS_USED:{count}:{self.hwid}".encode("utf-8")
        return hmac.new(secret, msg, hashlib.sha256).hexdigest()[:20]

    def _get_anchor_file_path(self) -> Path:
        if sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support" / "TaxCleanZA_Data"
            base.mkdir(parents=True, exist_ok=True)
            return base / ".tcza_sys_vault.dat"
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
        return Path(base) / ".tcza_sys_vault.dat"

    def _read_system_trial_anchors(self) -> int:
        """
        Reads hardware-signed trial counters from Windows Registry and LocalAppData.
        If tampering is detected (invalid HMAC signature), returns MAX_TRIAL_STATEMENTS.
        """
        counts = [0]

        # 1. Check Windows Registry Anchor
        if HAS_WINREG:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _ANCHOR_REG_PATH, 0, winreg.KEY_READ) as k:
                    val, _ = winreg.QueryValueEx(k, "SysMetric")
                    if val and ":" in str(val):
                        c_str, sig = str(val).split(":", 1)
                        c_val = int(c_str)
                        if hmac.compare_digest(sig, self._sign_anchor(c_val)):
                            counts.append(c_val)
                        else:
                            # Tampered registry value -> exhaust trial immediately
                            counts.append(MAX_TRIAL_STATEMENTS)
            except FileNotFoundError:
                pass
            except Exception:
                pass

        # 2. Check Hidden LocalAppData File Anchor
        anchor_file = self._get_anchor_file_path()
        if anchor_file.exists():
            try:
                raw = anchor_file.read_text(encoding="utf-8").strip()
                if ":" in raw:
                    c_str, sig = raw.split(":", 1)
                    c_val = int(c_str)
                    if hmac.compare_digest(sig, self._sign_anchor(c_val)):
                        counts.append(c_val)
                    else:
                        counts.append(MAX_TRIAL_STATEMENTS)
            except Exception:
                pass

        return max(counts)

    def _write_system_trial_anchors(self, count: int):
        """Writes hardware-signed trial counter to both Windows Registry and LocalAppData."""
        token = f"{count}:{self._sign_anchor(count)}"

        if HAS_WINREG:
            try:
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _ANCHOR_REG_PATH) as k:
                    winreg.SetValueEx(k, "SysMetric", 0, winreg.REG_SZ, token)
            except Exception:
                pass

        try:
            anchor_file = self._get_anchor_file_path()
            anchor_file.write_text(token, encoding="utf-8")
        except Exception:
            pass

    def init_db(self):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS app_license (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    email TEXT,
                    license_key TEXT,
                    plan TEXT DEFAULT 'TRIAL',
                    expiry TEXT,
                    statements_processed INTEGER DEFAULT 0,
                    activated_at TEXT,
                    bound_hwid TEXT
                )
            """)
            # Ensure bound_hwid column exists on older DBs
            try:
                cursor.execute("ALTER TABLE app_license ADD COLUMN bound_hwid TEXT")
            except Exception:
                pass

            cursor.execute("SELECT statements_processed FROM app_license WHERE id = 1")
            row = cursor.fetchone()
            anchor_count = self._read_system_trial_anchors()
            if not row:
                cursor.execute("""
                    INSERT INTO app_license (id, plan, statements_processed)
                    VALUES (1, 'TRIAL', ?)
                """, (anchor_count,))
                if anchor_count > 0:
                    self._write_system_trial_anchors(anchor_count)
            else:
                db_count = row[0] or 0
                true_count = max(db_count, anchor_count)
                if true_count != db_count:
                    cursor.execute("UPDATE app_license SET statements_processed = ? WHERE id = 1", (true_count,))
                if true_count > anchor_count:
                    self._write_system_trial_anchors(true_count)

    def get_state(self) -> Dict[str, Any]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT email, license_key, plan, expiry, statements_processed, bound_hwid FROM app_license WHERE id = 1"
        )
        row = cursor.fetchone()
        if not row:
            return {
                "plan": "TRIAL",
                "statements_processed": 0,
                "is_licensed": False,
                "remaining": MAX_TRIAL_STATEMENTS,
                "hwid": self.hwid,
            }

        email, key, plan, expiry, db_count, bound_hwid = row
        db_count = db_count or 0
        anchor_count = self._read_system_trial_anchors()
        count = max(db_count, anchor_count)
        if count != db_count:
            with self.conn:
                self.conn.execute("UPDATE app_license SET statements_processed = ? WHERE id = 1", (count,))

        is_pro = False
        if key and email:
            valid, _, _ = verify_license_key(email, key)
            # Also verify that the database wasn't copied from another PC!
            if valid and (not bound_hwid or bound_hwid == self.hwid):
                is_pro = True

        remaining = max(0, MAX_TRIAL_STATEMENTS - count) if not is_pro else 999999
        return {
            "email": email or "",
            "license_key": key or "",
            "plan": (plan if is_pro else "TRIAL"),
            "expiry": expiry or "",
            "statements_processed": count,
            "is_licensed": is_pro,
            "remaining": remaining,
            "hwid": self.hwid,
        }

    def can_process_statement(self) -> Tuple[bool, str]:
        state = self.get_state()
        if state["is_licensed"]:
            return True, "Active License"
        if state["remaining"] > 0:
            return True, f"Trial Mode ({state['remaining']} statements remaining)"
        return False, "Trial statement limit reached. Please activate your TaxClean ZA Pro license key."

    def record_statement_processed(self):
        state = self.get_state()
        new_count = state["statements_processed"] + 1
        with self.conn:
            self.conn.execute("UPDATE app_license SET statements_processed = ? WHERE id = 1", (new_count,))
        self._write_system_trial_anchors(new_count)

    def activate_license(self, email: str, license_key: str) -> Tuple[bool, str]:
        valid, msg, info = verify_license_key(email, license_key)
        if not valid:
            return False, msg

        with self.conn:
            self.conn.execute("""
                UPDATE app_license SET
                    email = ?,
                    license_key = ?,
                    plan = ?,
                    expiry = ?,
                    activated_at = ?,
                    bound_hwid = ?
                WHERE id = 1
            """, (
                info["email"],
                info["license_key"],
                info["plan"],
                info["expiry"],
                datetime.now().isoformat(),
                self.hwid,
            ))

        return True, f"Success! {info['plan']} License activated and bound to this PC ({self.hwid})."
