from __future__ import annotations

from urllib.parse import quote


def local_badge(label: str, status: str, color: str = "blue") -> str:
    return f"https://img.shields.io/badge/{quote(label)}-{quote(status)}-{quote(color)}"


def ecl_tracked_badge() -> str:
    return local_badge("ECL", "tracked", "blue")


def no_payload_verified_badge() -> str:
    return local_badge("no payload", "verified", "green")


def compliance_passport_badge() -> str:
    return local_badge("passport", "generated", "green")


def benchmark_risk_scanned_badge() -> str:
    return local_badge("benchmark risk", "scanned", "yellow")


def model_lineage_scanned_badge() -> str:
    return local_badge("model lineage", "scanned", "yellow")
