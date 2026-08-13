from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def get_market_options(crop: str, location: str = "") -> dict[str, Any]:
    key = (crop or "").strip().lower()
    channels: list[dict[str, Any]] = [
        {
            "channel": "Local producer / farmer organizations",
            "type": "cooperative",
            "availability": "verify_currently_active",
            "how_to_use": "Compare collection schedules, grading requirements, transport sharing and payment terms with local farmer organizations.",
            "verification": "Confirm the organization, current buying window and payment terms locally before committing produce.",
        },
        {
            "channel": "Nearby wholesale aggregators and processors",
            "type": "business buyer",
            "availability": "verify_currently_active",
            "how_to_use": "Request at least two or three quotations for grade, moisture/quality requirement, quantity, pickup and settlement terms.",
            "verification": "Buyer availability and prices are time-sensitive and must be checked at sale time.",
        },
        {
            "channel": "Verified MihiMura marketplace partners",
            "type": "digital marketplace",
            "availability": "only_if_verified_partner_exists",
            "how_to_use": "Publish quantity, expected harvest window, quality evidence and delivery radius only to verified partners configured in the platform.",
            "verification": "Only partners marked verified in the live marketplace should be treated as active buyers.",
        },
        {
            "channel": "Direct institutional / retailer contracts",
            "type": "direct sale",
            "availability": "verify_currently_active",
            "how_to_use": "For consistent volumes, compare forward/offtake arrangements with processors, retailers, hotels or institutional buyers where appropriate.",
            "verification": "Use written specifications and payment terms; do not assume a buyer will accept the crop without prior agreement.",
        },
    ]
    if key in {"paddy", "rice"}:
        channels.insert(0, {
            "channel": "Paddy Marketing Board procurement channel",
            "type": "government procurement",
            "availability": "verify_current_programme",
            "how_to_use": "Check whether an official procurement programme is active for the relevant season and whether nearby purchasing/collection arrangements apply.",
            "verification": "Procurement status, eligibility, quality rules, locations and prices are time-sensitive; verify the current official announcement before relying on this channel.",
        })
        channels.insert(1, {
            "channel": "Rice mills / paddy collectors",
            "type": "processor",
            "availability": "verify_currently_active",
            "how_to_use": "Compare mill or collector quotations based on variety, moisture, cleanliness, quantity, transport and payment timing.",
            "verification": "Collect fresh quotations close to harvest; avoid relying on an old seasonal price.",
        })

    return {
        "status": "channel_registry_only",
        "crop": crop,
        "location": location or "not specified",
        "price_feed": "not_connected",
        "buyer_feed": "not_connected",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "data_class": "planning_guidance",
        "channels": channels,
        "quotation_checklist": [
            "Buyer/business name and verified contact",
            "Crop/variety/grade specification",
            "Quantity accepted and minimum lot",
            "Quoted price and unit",
            "Quotation date/time and validity period",
            "Moisture/quality deductions",
            "Bags/loading/transport responsibility",
            "Pickup or delivery location",
            "Payment timing and method",
        ],
        "selling_strategy": [
            "Start buyer discovery before harvest rather than after the crop is already stored.",
            "Compare net price after grading deductions, bags, loading, transport and payment delay—not only the headline price.",
            "Prepare basic evidence: crop/variety, expected quantity, harvest date, moisture/quality where measured, photos and location.",
            "Split sales only when it improves risk/price without creating excessive logistics cost.",
        ],
        "source": {
            "name": "MihiMura market-channel registry",
            "freshness": "static planning registry; live buyer and price connectors are not configured",
            "source_type": "market_planning_registry",
        },
        "limitations": [
            "MihiMura does not currently have a live verified national buyer/price feed in this local build.",
            "Specific buyer availability, procurement programmes and prices must be refreshed from current authoritative/business sources before sale.",
            "No current price should be inferred from this registry.",
        ],
    }
