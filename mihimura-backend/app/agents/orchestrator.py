from __future__ import annotations
import json, time
from datetime import datetime, timezone
from typing import Any
from app.core.ai import get_gemini_client
from app.core.config import settings
from app.services.weather import get_weather
from app.services.climate_history import get_nasa_power
from app.agents.context import load_farmer_context
from app.agents.agronomy import retrieve_approved_knowledge
from app.agents.soil_water import calculate_water_budget
from app.agents.safety import precheck, enforce

SYSTEM_PROMPT="""You are MihiMura, a Sri Lanka-focused climate-resilient agriculture decision-support orchestrator.
You support agricultural decisions; you do not impersonate a certified agronomist. Use ONLY the trusted context and tool evidence supplied below. Official emergency warnings and current approved agricultural protocols have precedence over model suggestions. Never invent pesticide/fertilizer doses, label claims, stock, official alerts, laboratory diagnoses, or precise field measurements that are not in evidence. If evidence is insufficient, conflicting, rate-sensitive, or potentially harmful, explain the uncertainty and recommend expert/official verification.

When trusted_context.language is Sinhala, Tamil, or English, write farmer-facing summary, recommended_action, why, alternatives, do_not_do, counterfactual and follow_up in that language while preserving quantities, dates, units and warnings accurately.

Return VALID JSON ONLY with fields:
summary (string), recommended_action (string), why (string), confidence (0-1), alternatives (array strings), do_not_do (array strings), sources (array objects with name, freshness, url optional), confirmation_required (boolean), follow_up (string), risk_level (low|watch|action|emergency), counterfactual (string), agent_trace (array objects with agent, action, status)."""


def _rain_probability(weather:dict[str,Any]) -> float:
    vals=(weather.get("daily") or {}).get("precipitation_probability_max") or []
    if not vals: return 0
    idx=1 if len(vals)>1 else 0
    try:return float(vals[idx] or 0)
    except:return 0


def _source_objects(weather:dict,nasa:dict,knowledge:dict)->list[dict[str,Any]]:
    items=[
        {"name":weather.get("source","Open-Meteo"),"freshness":weather.get("retrieved_at","current request")},
        {"name":nasa.get("source","NASA POWER"),"freshness":(nasa.get("period") or {}).get("end","recent baseline")},
    ]
    for d in knowledge.get("documents",[])[:4]:
        items.append({"name":f"{d.get('authority')}: {d.get('title')}","freshness":"reference metadata — verify current source version before consequential use","url":d.get("url")})
    return items


def _demo(question:str,ctx:dict[str,Any],weather:dict,nasa:dict,knowledge:dict,water:dict,safety:dict)->dict[str,Any]:
    lower=question.lower(); rain=_rain_probability(weather); fertilizer=any(k in lower for k in ['fertil','urea','nitrogen','npk'])
    if fertilizer and rain>=60:
        action="Delay the exposed fertilizer task and re-check the next lower-rain operating window against the current approved crop protocol."
        why=f"The next-day forecast rain probability is about {rain:.0f}% in this request, which can increase runoff or nutrient-loss risk. The exact application rate is intentionally not generated."
        level='action'; conf=.88; confirm=True
    elif any(k in lower for k in ['pesticide','fungicide','insecticide','dose','rate']):
        action="Do not select a chemical or dose from this chat alone. Confirm the crop, target problem and current approved label/protocol, and escalate if the condition is uncertain."
        why="This request is rate- or treatment-sensitive, so MihiMura applies a deterministic safety gate before any model explanation."
        level='action';conf=.94;confirm=True
    else:
        action="Inspect the highest-risk field condition, record a fresh observation, and use the digital twin plus current weather before changing a field operation."
        why="A field decision is safer when current weather, crop stage and direct field evidence agree instead of relying on one signal."
        level='watch'; conf=.81; confirm=False
    crop=ctx.get('crop') or 'selected crop'
    out={"summary":action,"recommended_action":action,"why":why,"confidence":conf,
         "alternatives":["Record another field observation before treatment",f"Ask an agricultural instructor to review the {crop} evidence package"],
         "do_not_do":["Do not treat an uncertain image result as a confirmed diagnosis","Do not use an invented chemical or fertilizer dose"],
         "sources":_source_objects(weather,nasa,knowledge),"confirmation_required":confirm,"follow_up":"Recheck weather and field condition within 12–24 hours, then record what happened in the field diary.","risk_level":level,
         "counterfactual":"If forecast exposure falls and field evidence does not show saturation or stress, the operating window may change after protocol verification.",
         "agent_trace":[
             {"agent":"Farmer Context & Memory","action":f"Resolved {ctx.get('context_scope','general')} context without trusting unauthorized project IDs","status":"complete"},
             {"agent":"Micro-Climate Prediction","action":"Retrieved the coordinate-based forecast and uncertainty-relevant variables","status":"complete"},
             {"agent":"Climate Baseline","action":"Retrieved a NASA POWER recent historical baseline","status":"complete"},
             {"agent":"Soil & Water","action":f"Built a transparent water-context proxy; 3-day forecast rain {water.get('forecast_rain_3d_mm','?')} mm","status":"complete"},
             {"agent":"Agronomy Knowledge","action":f"Retrieved {len(knowledge.get('documents',[]))} approved-source metadata records","status":"complete"},
             {"agent":"Intervention & Safety","action":"Applied confirmation, rate-sensitive and no-invented-dose guardrails","status":"complete"},
         ],"provider":"deterministic-demo","model":"policy+tools"}
    return enforce(out,safety)


def _normalize(out:dict[str,Any],weather:dict,nasa:dict,knowledge:dict,safety:dict,ctx:dict[str,Any])->dict[str,Any]:
    out.setdefault('summary',out.get('recommended_action') or 'Review the evidence before acting.')
    out.setdefault('recommended_action',out['summary'])
    out.setdefault('why','The recommendation is based on the available project and environmental evidence.')
    try: out['confidence']=max(0.0,min(1.0,float(out.get('confidence',0.5))))
    except: out['confidence']=0.5
    out.setdefault('alternatives',[]);out.setdefault('do_not_do',[]);out.setdefault('follow_up','Recheck after conditions change.');out.setdefault('risk_level','watch');out.setdefault('counterfactual','Materially different field or forecast evidence can change this recommendation.')
    if not out.get('sources'): out['sources']=_source_objects(weather,nasa,knowledge)
    trace=out.setdefault('agent_trace',[])
    required=[
        ("Farmer Context & Memory",f"Trusted context scope: {ctx.get('context_scope','general')}"),
        ("Micro-Climate Prediction","Current coordinate-based weather retrieved"),
        ("Agronomy Knowledge",f"Approved-source metadata retrieved: {len(knowledge.get('documents',[]))}"),
        ("Intervention & Safety","Deterministic safety policy applied after model output"),
    ]
    names={x.get('agent') for x in trace if isinstance(x,dict)}
    for agent,action in required:
        if agent not in names: trace.append({"agent":agent,"action":action,"status":"complete"})
    return enforce(out,safety)


class OrchestratorAgent:
    def process_farmer_request(self,question:str,context:dict[str,Any],uid:str="demo_farmer_001")->dict[str,Any]:
        t0=time.perf_counter()
        trusted=load_farmer_context(uid,context)
        lat=float(trusted.get('lat') or 7.291);lon=float(trusted.get('lon') or 81.674)
        weather=get_weather(lat,lon,14);nasa=get_nasa_power(lat,lon,30)
        knowledge=retrieve_approved_knowledge(trusted.get('crop',''),question)
        water=calculate_water_budget({**trusted,**{k:v for k,v in context.items() if k in {'soil_moisture'}}},weather)
        safety=precheck(question,trusted)
        client=get_gemini_client()
        if client is None:
            out=_demo(question,trusted,weather,nasa,knowledge,water,safety);out['latency_ms']=round((time.perf_counter()-t0)*1000);return out
        evidence={"trusted_context":trusted,"weather":weather,"climate_history":nasa,"water_budget_proxy":water,"approved_knowledge":knowledge,"safety_precheck":safety}
        prompt=SYSTEM_PROMPT+"\nQUESTION: "+question+"\nTOOL_EVIDENCE: "+json.dumps(evidence,default=str)
        try:
            response=client.models.generate_content(model=settings.GEMINI_MODEL,contents=prompt)
            text=(response.text or '').strip()
            if text.startswith('```'):
                text=text.strip('`').strip();text=text[4:].strip() if text.lower().startswith('json') else text
            out=json.loads(text);out=_normalize(out,weather,nasa,knowledge,safety,trusted)
            out['provider']='gemini';out['model']=settings.GEMINI_MODEL;out['generated_at']=datetime.now(timezone.utc).isoformat();out['latency_ms']=round((time.perf_counter()-t0)*1000);return out
        except Exception as exc:
            out=_demo(question,trusted,weather,nasa,knowledge,water,safety);out['provider']='deterministic-fallback';out['provider_error']=str(exc);out['latency_ms']=round((time.perf_counter()-t0)*1000);return out

orchestrator=OrchestratorAgent()
