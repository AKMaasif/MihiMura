from __future__ import annotations
from datetime import datetime, timezone
from app.services.platform import list_tasks,list_projects

PROVINCES={
"Western":{"id":"WP","healthScore":82,"trend":4,"rainfallRisk":32,"pestRisk":24,"activeAlerts":1,"atRiskArea":24,"rainfall7d":112,"rainfallAvgDiff":5,"cropCoverage":45,"soilMoisture":44,"topCrop":"Coconut","nextAction":"Routine monitoring"},
"Central":{"id":"CP","healthScore":76,"trend":2,"rainfallRisk":48,"pestRisk":31,"activeAlerts":2,"atRiskArea":39,"rainfall7d":96,"rainfallAvgDiff":8,"cropCoverage":60,"soilMoisture":41,"topCrop":"Tea","nextAction":"Watch slope runoff"},
"Southern":{"id":"SP","healthScore":55,"trend":-2,"rainfallRisk":57,"pestRisk":46,"activeAlerts":3,"atRiskArea":74,"rainfall7d":83,"rainfallAvgDiff":-5,"cropCoverage":50,"soilMoisture":35,"topCrop":"Cinnamon","nextAction":"Inspect stressed blocks"},
"Northern":{"id":"NP","healthScore":74,"trend":1,"rainfallRisk":28,"pestRisk":42,"activeAlerts":2,"atRiskArea":48,"rainfall7d":31,"rainfallAvgDiff":-10,"cropCoverage":55,"soilMoisture":29,"topCrop":"Onion","nextAction":"Monitor water budget"},
"Eastern":{"id":"EP","healthScore":48,"trend":-6,"rainfallRisk":76,"pestRisk":69,"activeAlerts":5,"atRiskArea":124,"rainfall7d":68,"rainfallAvgDiff":-12,"cropCoverage":71,"soilMoisture":22,"topCrop":"Paddy","nextAction":"Delay exposed operations"},
"North Western":{"id":"NW","healthScore":44,"trend":-5,"rainfallRisk":41,"pestRisk":58,"activeAlerts":5,"atRiskArea":92,"rainfall7d":47,"rainfallAvgDiff":-18,"cropCoverage":65,"soilMoisture":27,"topCrop":"Coconut","nextAction":"Scout pest hotspots"},
"North Central":{"id":"NC","healthScore":58,"trend":-3,"rainfallRisk":23,"pestRisk":47,"activeAlerts":4,"atRiskArea":88,"rainfall7d":29,"rainfallAvgDiff":-25,"cropCoverage":80,"soilMoisture":24,"topCrop":"Paddy","nextAction":"Review irrigation windows"},
"Uva":{"id":"UP","healthScore":42,"trend":-4,"rainfallRisk":62,"pestRisk":71,"activeAlerts":6,"atRiskArea":83,"rainfall7d":74,"rainfallAvgDiff":-9,"cropCoverage":55,"soilMoisture":31,"topCrop":"Tea","nextAction":"Prioritize pest inspection"},
"Sabaragamuwa":{"id":"SG","healthScore":64,"trend":-1,"rainfallRisk":54,"pestRisk":38,"activeAlerts":2,"atRiskArea":53,"rainfall7d":105,"rainfallAvgDiff":4,"cropCoverage":65,"soilMoisture":39,"topCrop":"Rubber","nextAction":"Watch rainfall anomaly"}}


def get_dashboard_payload(uid:str):
    return {
        "generatedAt":datetime.now(timezone.utc).isoformat(),
        "source":"MihiMura demo national snapshot",
        "reportingPeriod":"Demo baseline · replace with scheduled DCS/DoA ingestion",
        "confidence":"Demonstration data — not an official live statistic",
        "summary":{"cropHealth":64,"cropHealthChange":2.4,"atRiskArea":625,"newlyAtRiskArea":18,"waterDeficit":18,"irrigationNeed":36400,"activeThreats":17,"criticalThreats":2,"yieldProtected":14.8,"yieldProtectedChange":1.7},
        "provinces":{k:{"name":k,**v} for k,v in PROVINCES.items()},
        "priorityActions":[
            {"id":"a1","severity":"Critical","title":"Delay fertilizer timing","province":"Eastern","deadline":"Before 08:00","description":"Rain probability and runoff exposure are elevated across exposed paddy blocks.","reason":"Rain probability and runoff exposure are elevated.","evidence":"76/100 rainfall risk · drainage context · current forecast","impact":"Reduce avoidable nutrient runoff","buttonText":"Review action"},
            {"id":"a2","severity":"High","title":"Inspect chilli pest cluster","province":"Uva / Eastern","deadline":"Due today","description":"Climate conditions and privacy-threshold community reports indicate increasing pest pressure.","reason":"Climate conditions and reports increase pest pressure.","evidence":"Community reports + humidity + pest-risk layer","impact":"Earlier field verification","buttonText":"Assign scout"},
            {"id":"a3","severity":"High","title":"Prepare irrigation window","province":"North Central","deadline":"Within 48h","description":"The water budget is declining while forecast rainfall remains below crop-stage demand.","reason":"Water budget is declining while rainfall is below crop-stage demand.","evidence":"24% soil-moisture proxy · rainfall deficit · field context","impact":"Reduce water stress","buttonText":"Schedule"}
        ],
        "changes":[
            {"id":"c1","tone":"danger","title":"18 acres moved into higher risk","detail":"Most of the change occurred in Eastern and North Western provinces.","province":"National"},
            {"id":"c2","tone":"warning","title":"Rain probability increased","detail":"Eastern Province now has the highest rainfall-risk score in the demonstration layer.","province":"Eastern"},
            {"id":"c3","tone":"positive","title":"Moisture recovered after irrigation","detail":"A monitored Western Province block returned toward the target range.","province":"Western"},
            {"id":"c4","tone":"info","title":"Community pest threshold reached","detail":"An anonymized Ampara chilli cluster crossed the publication threshold.","province":"Eastern"}
        ],
        "agentActivity":[
            {"id":"g1","agent":"Satellite Perception","action":"Updated vegetation condition proxy","time":"2m ago","status":"complete"},
            {"id":"g2","agent":"Micro-Climate","action":"Re-ranked rainfall risk for Ampara","time":"3m ago","status":"complete"},
            {"id":"g3","agent":"Community Sentinel","action":"Cluster threshold reached for pest watch","time":"6m ago","status":"working"},
            {"id":"g4","agent":"Intervention & Safety","action":"Blocked risky fertilizer timing","time":"7m ago","status":"complete"}
        ],
        "taskCount":len(list_tasks(uid)),
        "projectCount":len(list_projects(uid)),
    }
