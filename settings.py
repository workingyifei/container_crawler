import os
import warnings
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Repo root (directory containing this file), so .env loads even when cwd differs
# (e.g. `python -m container_checker.cli` from another folder).
_PROJECT_ROOT = Path(__file__).resolve().parent
for _name in (".env", "credentials.env"):
    load_dotenv(_PROJECT_ROOT / _name, override=False)


def _require_env(key: str) -> str:
    value = os.environ.get(key, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {key}")
    return value


def _require_env_any(*keys: str) -> str:
    for key in keys:
        value = os.environ.get(key, "").strip()
        if value:
            if key.startswith("STO_"):
                warnings.warn(
                    f"{key} is deprecated; use STE_* in .env instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )
            return value
    raise ValueError(f"Missing required environment variable: one of {', '.join(keys)}")


@dataclass(frozen=True)
class Credentials:
    username: str
    password: str


@dataclass(frozen=True)
class WMSSettings:
    username: str
    password: str
    login_url: str
    inbound_url: str
    outbound_url: str
    gdrive_service_account_file: str
    gdrive_file_id: str


def get_ste_creds() -> Credentials:
    return Credentials(
        username=_require_env_any("STE_USERNAME", "STO_USERNAME"),
        password=_require_env_any("STE_PASSWORD", "STO_PASSWORD"),
    )


def get_oict_creds() -> Credentials:
    return Credentials(
        username=_require_env("OICT_USERNAME"),
        password=_require_env("OICT_PASSWORD"),
    )


def get_wms_settings() -> WMSSettings:
    return WMSSettings(
        username=_require_env("WMS_USERNAME"),
        password=_require_env("WMS_PASSWORD"),
        login_url=_require_env("WMS_LOGIN_URL"),
        inbound_url=_require_env("WMS_INBOUND_URL"),
        outbound_url=_require_env("WMS_OUTBOUND_URL"),
        gdrive_service_account_file=_require_env("WMS_GDRIVE_SERVICE_ACCOUNT_FILE"),
        gdrive_file_id=_require_env("WMS_GDRIVE_FILE_ID"),
    )
