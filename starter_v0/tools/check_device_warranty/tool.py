from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from tools._shared import ROOT, err


ASSET_FILE = ROOT / "helpdesk_data" / "assets.json"


def check_device_warranty(asset_id: str = "") -> dict[str, Any]:
    try:
        data = json.loads(ASSET_FILE.read_text(encoding="utf-8"))
        wanted_id = (asset_id or "").strip().upper()
        if not wanted_id:
            return {"tool": "check_device_warranty", "error": "missing_asset_id", "message": "Vui lòng cung cấp asset_id"}

        device = next((item for item in data["assets"] if item["asset_id"] == wanted_id), None)
        if device is None:
            return {"tool": "check_device_warranty", "asset_id": wanted_id, "error": "asset_not_found"}

        purchase_date_str = device.get("purchase_date")
        warranty_until_str = device.get("warranty_until")

        # Snapshot date from dataset as the reference timeline (2026-09-14)
        ref_date = datetime.fromisoformat(data["snapshot_at"]).date()
        warranty_end = datetime.fromisoformat(warranty_until_str).date() if warranty_until_str else None

        days_remaining = (warranty_end - ref_date).days if warranty_end else 0
        if days_remaining < 0:
            status = "expired"
        elif days_remaining <= 90:
            status = "expiring_soon"
        else:
            status = "active"

        mfg = device.get("manufacturer", "")
        support_tier = (
            "Lenovo Premier Support Plus" if mfg == "Lenovo"
            else "AppleCare+ for Enterprise" if mfg == "Apple"
            else "Dell ProSupport Plus" if mfg == "Dell"
            else "HP Care Pack 24x7"
        )

        return {
            "tool": "check_device_warranty",
            "asset_id": wanted_id,
            "manufacturer": device.get("manufacturer"),
            "model": device.get("model"),
            "purchase_date": purchase_date_str,
            "warranty_until": warranty_until_str,
            "warranty_status": status,
            "days_remaining": days_remaining,
            "support_tier": support_tier,
            "service_coverage": "On-site next-business-day hardware repair & battery replacement",
            "snapshot_at": data["snapshot_at"],
        }
    except Exception as exc:
        return err("check_device_warranty", exc)
