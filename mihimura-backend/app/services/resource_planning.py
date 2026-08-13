from __future__ import annotations

from typing import Any


def _item(item: str, need: str, stage: str, priority: str, ownership: str, verify: str = "") -> dict[str, Any]:
    return {
        "item": item,
        "need": need,
        "stage": stage,
        "priority": priority,
        "ownership_strategy": ownership,
        "verification": verify,
    }


def build_resource_plan(crop: str) -> dict[str, Any]:
    key = (crop or "").strip().lower()
    common_tools = [
        {"item": "Measuring tape / field markers", "priority": "recommended"},
        {"item": "Basic hand tools for bund/drain maintenance", "priority": "required_as_needed"},
        {"item": "Buckets / containers for field operations", "priority": "recommended"},
        {"item": "Record sheet or MihiMura task log", "priority": "recommended"},
        {"item": "Appropriate PPE whenever a product label or field task requires it", "priority": "required_for_relevant_task"},
    ]
    if key in {"paddy", "rice"}:
        equipment = [
            _item("Tractor or two-wheel tractor with suitable land-preparation implement", "hire/own", "land preparation", "usually_required", "hire unless utilization justifies ownership", "Match implement to field condition and access."),
            _item("Puddling / levelling equipment where the establishment method requires it", "hire/own", "land preparation", "method_dependent", "usually hire", "Not every establishment method requires the same operation."),
            _item("Seed broadcaster, drum seeder or transplanter as applicable", "method-dependent", "establishment", "method_dependent", "hire/share/own", "Choose only after establishment method is fixed."),
            _item("Irrigation control / pump equipment where pumping is required", "water-source dependent", "through season", "field_dependent", "hire/share/own", "Verify water source, head, fuel/electricity and scheme rules."),
            _item("Knapsack/power sprayer only when a verified treatment is actually required", "conditional", "crop protection", "conditional", "share/own", "Application equipment must match the current approved product label and PPE requirements."),
            _item("Combine harvester or harvest/threshing service", "hire/own", "harvest", "usually_required", "usually hire", "Book early and verify field accessibility, service rate and losses."),
            _item("Moisture meter / weighing access for quality and marketing evidence", "recommended", "post-harvest / sale", "recommended", "share/service", "Useful for buyer negotiation and quality evidence."),
        ]
        return {
            "status": "planning_template",
            "crop": crop,
            "equipment": equipment,
            "tools": common_tools + [
                {"item": "Sickle as manual harvest backup", "priority": "optional_backup"},
                {"item": "Drain/bund repair tools", "priority": "required_as_needed"},
                {"item": "Clean sample bags / labels for seed or crop evidence", "priority": "recommended"},
            ],
            "inputs": [
                {"category": "Certified/quality seed", "priority": "required", "guidance": "Select variety and seed class for the intended season, maturity period and market; verify current availability."},
                {"category": "Nutrient inputs", "priority": "conditional_on_recommendation", "guidance": "Use current RRDI/Department of Agriculture recommendation for the zone, establishment method and available soil information; do not infer rates from this report."},
                {"category": "Weed management", "priority": "required_management", "guidance": "Prefer prevention/mechanical/cultural options where practical; any herbicide must be selected from a current approved label for the crop/weed situation."},
                {"category": "Pest / disease management", "priority": "monitor_then_act", "guidance": "Use scouting and diagnosis first. Chemical active ingredient, product, dose, interval and pre-harvest requirements must come from current verified guidance/label."},
                {"category": "PPE / safe handling", "priority": "required_when_applicable", "guidance": "Match PPE and handling to the actual task and product label; maintain clean water and safe storage/transport."},
            ],
            "labour_operations": [
                "Field clearing, bund/drain preparation and levelling support",
                "Seed preparation / nursery / establishment",
                "Gap filling and crop establishment checks",
                "Irrigation and drainage monitoring",
                "Weed, pest and disease scouting",
                "Input application only after verified recommendation",
                "Harvest, handling, bagging and loading",
                "Post-harvest quality checking and transport coordination",
            ],
            "costing_guidance": [
                "For hireable machinery, collect at least two local quotations and record whether fuel/operator/transport are included.",
                "Separate one-time equipment purchases from per-season operating costs.",
                "Do not add pesticide/fertilizer products to the budget until the agronomic need and current approved recommendation are verified.",
            ],
        }

    return {
        "status": "planning_template",
        "crop": crop,
        "equipment": [
            _item("Crop-appropriate land-preparation equipment", "field-dependent", "land preparation", "field_dependent", "hire/share/own"),
            _item("Irrigation equipment where required", "water-source dependent", "through season", "field_dependent", "hire/share/own"),
            _item("Application equipment only for verified inputs", "conditional", "crop protection", "conditional", "share/own"),
            _item("Harvest/handling equipment appropriate to the crop", "crop-dependent", "harvest", "crop_dependent", "hire/share/own"),
        ],
        "tools": common_tools,
        "inputs": [
            {"category": "Seed / planting material", "priority": "required", "guidance": "Use certified or verified planting material where available."},
            {"category": "Nutrients", "priority": "conditional_on_recommendation", "guidance": "Use current crop-specific official guidance and soil/field evidence."},
            {"category": "Crop protection", "priority": "monitor_then_act", "guidance": "Select only after diagnosis/target identification and current label verification."},
        ],
        "labour_operations": ["Land preparation", "Establishment", "Field monitoring", "Water management", "Harvest and handling"],
        "costing_guidance": ["Collect current local hire/purchase quotations before financial commitment."],
    }
