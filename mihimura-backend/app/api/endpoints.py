from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, Response, UploadFile
from pydantic import BaseModel, Field

from app.agents import i18n
from app.agents.orchestrator import orchestrator
from app.agents.vision import analyze_crop_images
from app.core.auth import get_current_user
from app.core.config import settings
from app.db import audit
from app.services.climate_history import get_nasa_power
from app.services.conversations import (
    append_message,
    archive_conversation,
    create_conversation,
    get_memory,
    list_conversations,
    list_messages,
    recent_history,
    require_conversation,
    resolve_conversation_context,
    update_conversation_project,
    update_conversation_title,
    update_memory,
)
from app.services.dashboard import get_dashboard_payload
from app.services.platform import (
    PRODUCTS, SUPPLIERS, audit_log_for_actor, create_community_report, create_expense, create_expert_case,
    create_farm, create_harvest, create_notification, create_observation, create_order, create_project, create_task,
    list_agent_runs_for_actor, list_community_reports, list_device_tokens, list_expenses, list_expert_cases_for_actor,
    list_farms, list_harvests, list_notifications, list_observations, list_orders, list_projects, list_tasks,
    list_users_for_admin, record_agent_run, request_account_deletion, save_device_token, set_professional_verification,
    set_user_status, update_expert_case_for_actor, update_farm, update_notification, update_profile, update_task,
)
from app.services.reports import generate_conversation_report, list_reports, multilingual_pdf_runtime_status
from app.services.evaluation import (
    evaluation_runtime_status,
    get_evaluation_run,
    list_evaluation_runs,
    load_evaluation_cases,
    run_evaluation_suite,
)
from app.services.knowledge_base import (
    create_ingestion_job,
    create_retry_job,
    delete_knowledge_document,
    get_ingestion_job,
    ingestion_jobs_database_ready,
    knowledge_configured,
    knowledge_database_ready,
    list_ingestion_jobs,
    list_knowledge_documents,
    load_job_document_bytes,
    request_ingestion_cancel,
    run_ingestion_job,
    search_knowledge,
    update_knowledge_document,
)
from app.services.satellite import catalog_search, configured as satellite_configured
from app.services.voice import create_voice_session_token, synthesize_voice
from app.services.weather import get_weather
from app.supabase_client import supabase_configured

router = APIRouter()


class AnyPayload(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)


class AIRequest(BaseModel):
    question: str = Field(default="", max_length=4000)
    context: dict[str, Any] = Field(default_factory=dict)
    conversation_id: str | None = None
    clarification_answers: dict[str, Any] = Field(default_factory=dict)
    mode: str = "auto"
    allow_mode_mismatch: bool = False
    resume_route: bool = False


class EvaluationRunRequest(BaseModel):
    mode: str = "policy"
    case_ids: list[str] = Field(default_factory=list)
    persist: bool = True


class ConversationCreateRequest(BaseModel):
    project_id: str | None = None
    title: str | None = None


class VoiceSessionRequest(BaseModel):
    language: str = "English"
    project_id: str | None = None


class VoiceTTSRequest(BaseModel):
    text: str
    language: str = "English"


class TaskPatch(BaseModel):
    status: str | None = None
    due_at: str | None = None
    assigned_to: str | None = None
    completion_note: str | None = None
    schedule_reason: str | None = None


def _require_knowledge_editor(user: dict[str, Any]) -> None:
    role = str(user.get("role") or "farmer").lower()
    if user.get("provider") == "demo" or role == "admin":
        return
    if role in {"agronomist", "expert"} and bool(user.get("professional_verified")):
        return
    raise HTTPException(403, "Admin or verified agronomist/expert access required for knowledge ingestion")


def _require_evaluation_admin(user: dict[str, Any]) -> None:
    role = str(user.get("role") or "farmer").lower()
    if user.get("provider") == "demo" or (role == "admin" and bool(user.get("professional_verified"))):
        return
    raise HTTPException(403, "Administrator access is required for AI evaluation runs")


@router.get("/health")
def health():
    return {
        "status": "ok",
        "version": settings.VERSION,
        "ai_configured": bool(settings.GEMINI_API_KEY),
        "ai_models": {
            "reasoning": settings.reasoning_models,
            "fast": settings.fast_models,
            "live_voice": settings.GEMINI_LIVE_MODEL,
            "tts": settings.GEMINI_TTS_MODEL,
        },
        "supabase_configured": supabase_configured(),
        "auth_provider": "supabase",
        "database": "supabase-postgres",
        "rag_configured": knowledge_configured(),
        "rag_database_ready": knowledge_database_ready(),
        "rag_ingestion_jobs_ready": ingestion_jobs_database_ready(),
        "embedding_model": settings.GEMINI_EMBEDDING_MODEL,
        "embedding_dimension": settings.EMBEDDING_DIMENSION,
        "sentinel_configured": satellite_configured(),
        "decision_intelligence": "phase3-v1",
        "confidence_engine": "deterministic-evidence-weighting-v1",
        "market_live_price_feed": False,
        "multilingual_pdf": multilingual_pdf_runtime_status(),
        "evaluation": evaluation_runtime_status(),
    }


@router.get("/evaluation/status")
def evaluation_status(u=Depends(get_current_user)):
    _require_evaluation_admin(u)
    return evaluation_runtime_status()


@router.get("/evaluation/cases")
def evaluation_cases(u=Depends(get_current_user)):
    _require_evaluation_admin(u)
    return load_evaluation_cases()


@router.post("/evaluation/run")
def evaluation_run(req: EvaluationRunRequest, u=Depends(get_current_user)):
    _require_evaluation_admin(u)
    try:
        result = run_evaluation_suite(
            u["uid"],
            mode=req.mode,
            case_ids=req.case_ids or None,
            persist=bool(req.persist),
        )
        audit(u["uid"], "phase4a_evaluation_run", result.get("id", "evaluation"), {
            "mode": result.get("mode"),
            "status": result.get("status"),
            "summary": result.get("summary"),
            "persisted": result.get("persisted"),
        })
        return result
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"Evaluation run failed: {exc}") from exc


@router.get("/evaluation/runs")
def evaluation_runs(limit: int = 20, u=Depends(get_current_user)):
    _require_evaluation_admin(u)
    return list_evaluation_runs(limit)


@router.get("/evaluation/runs/{run_id}")
def evaluation_run_detail(run_id: str, u=Depends(get_current_user)):
    _require_evaluation_admin(u)
    result = get_evaluation_run(run_id)
    if not result:
        raise HTTPException(404, "Evaluation run not found")
    return result


@router.get("/users/me")
def me(u=Depends(get_current_user)):
    return u


@router.put("/users/me")
def put_me(payload: AnyPayload, u=Depends(get_current_user)):
    return update_profile(u["uid"], payload.data)


@router.delete("/users/me")
def delete_me(u=Depends(get_current_user)):
    return request_account_deletion(u["uid"])


@router.get("/admin/users")
def admin_users(u=Depends(get_current_user)):
    data = list_users_for_admin(u)
    if not data and not (u.get("provider") == "demo" or u.get("role") == "admin"):
        raise HTTPException(403, "Verified administrator access required")
    return data


@router.patch("/admin/users/{uid}/verification")
def admin_verify_user(uid: str, payload: AnyPayload, u=Depends(get_current_user)):
    try:
        result = set_professional_verification(u, uid, bool(payload.data.get("verified", True)))
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    if not result:
        raise HTTPException(404, "User not found")
    return result


@router.patch("/admin/users/{uid}/status")
def admin_user_status(uid: str, payload: AnyPayload, u=Depends(get_current_user)):
    try:
        result = set_user_status(u, uid, str(payload.data.get("status") or ""))
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not result:
        raise HTTPException(404, "User not found")
    return result


@router.get("/dashboard")
def dashboard(u=Depends(get_current_user)):
    return get_dashboard_payload(u["uid"])


Latitude = Query(7.291, ge=-90, le=90)
Longitude = Query(81.674, ge=-180, le=180)


@router.get("/weather")
def weather(lat: float = Latitude, lon: float = Longitude, days: int = Query(14, ge=1, le=16)):
    return get_weather(lat, lon, days)


@router.get("/climate-history")
def climate_history(lat: float = Latitude, lon: float = Longitude, days: int = Query(30, ge=1, le=365)):
    return get_nasa_power(lat, lon, days)


@router.get("/satellite/catalog")
def satellite(lat: float = Latitude, lon: float = Longitude):
    return catalog_search(lat, lon)


@router.post("/knowledge/search")
def knowledge_search(payload: AnyPayload, u=Depends(get_current_user)):
    data = payload.data
    query = str(data.get("query") or "").strip()
    if not query:
        raise HTTPException(400, "query is required")
    return search_knowledge(
        query,
        crop=str(data.get("crop") or "") or None,
        language=str(data.get("language") or "") or None,
        max_authority_tier=int(data.get("max_authority_tier") or 4),
        document_type=str(data.get("document_type") or "") or None,
        top_k=max(1, min(int(data.get("top_k") or settings.RAG_TOP_K), 20)),
        strict_language=bool(data.get("strict_language", False)),
    )


@router.get("/knowledge/documents")
def knowledge_documents(status: str | None = None, crop: str | None = None, u=Depends(get_current_user)):
    return list_knowledge_documents(status=status, crop=crop)


@router.get("/knowledge/ingestion-jobs")
def knowledge_ingestion_jobs(limit: int = 20, u=Depends(get_current_user)):
    _require_knowledge_editor(u)
    return list_ingestion_jobs(limit=limit)


@router.get("/knowledge/ingestion-jobs/{job_id}")
def knowledge_ingestion_job(job_id: str, u=Depends(get_current_user)):
    _require_knowledge_editor(u)
    row = get_ingestion_job(job_id)
    if not row:
        raise HTTPException(404, "Knowledge ingestion job not found")
    return row


@router.post("/knowledge/documents")
async def upload_knowledge_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    authority: str = Form(...),
    authority_tier: int = Form(2),
    document_type: str = Form("guidance"),
    crop: str | None = Form(None),
    language: str = Form("English"),
    region: str | None = Form(None),
    district: str | None = Form(None),
    source_url: str | None = Form(None),
    version_label: str | None = Form(None),
    published_at: str | None = Form(None),
    status: str = Form("published"),
    u=Depends(get_current_user),
):
    _require_knowledge_editor(u)
    raw = await file.read()
    if len(raw) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"Knowledge file exceeds {settings.MAX_UPLOAD_MB} MB")
    filename = file.filename or "knowledge-document"
    mime_type = file.content_type or "application/octet-stream"
    try:
        result = create_ingestion_job(
            data=raw,
            filename=filename,
            mime_type=mime_type,
            title=title,
            authority=authority,
            authority_tier=authority_tier,
            document_type=document_type,
            crop=crop,
            language=language,
            region=region,
            district=district,
            source_url=source_url,
            version_label=version_label,
            published_at=published_at,
            uploaded_by=u["uid"],
            status=status,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc

    job = result.get("job") or {}
    if result.get("accepted") and job and not result.get("already_running"):
        background_tasks.add_task(
            run_ingestion_job,
            job_id=str(job["id"]),
            data=raw,
            filename=filename,
            mime_type=mime_type,
        )
    audit(u["uid"], "queue_knowledge_ingestion", str(result.get("document", {}).get("id") or "knowledge"), {
        "title": title,
        "authority": authority,
        "job_id": job.get("id"),
        "duplicate": result.get("duplicate", False),
        "already_running": result.get("already_running", False),
    })
    return result


@router.post("/knowledge/ingestion-jobs/{job_id}/retry")
def retry_knowledge_ingestion(job_id: str, background_tasks: BackgroundTasks, u=Depends(get_current_user)):
    _require_knowledge_editor(u)
    try:
        new_job = create_retry_job(job_id, created_by=u["uid"])
        _job, raw, filename, mime_type = load_job_document_bytes(str(new_job["id"]))
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(503, f"Could not prepare ingestion retry: {exc}") from exc
    background_tasks.add_task(
        run_ingestion_job,
        job_id=str(new_job["id"]),
        data=raw,
        filename=filename,
        mime_type=mime_type,
    )
    audit(u["uid"], "retry_knowledge_ingestion", str(new_job.get("document_id") or "knowledge"), {"job_id": new_job.get("id"), "retry_of": job_id})
    return {"accepted": True, "job": new_job}


@router.post("/knowledge/ingestion-jobs/{job_id}/cancel")
def cancel_knowledge_ingestion(job_id: str, u=Depends(get_current_user)):
    _require_knowledge_editor(u)
    row = request_ingestion_cancel(job_id)
    if not row:
        raise HTTPException(404, "Knowledge ingestion job not found")
    return row


@router.patch("/knowledge/documents/{document_id}")
def patch_knowledge_document(document_id: str, payload: AnyPayload, u=Depends(get_current_user)):
    _require_knowledge_editor(u)
    try:
        row = update_knowledge_document(document_id, payload.data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not row:
        raise HTTPException(404, "Knowledge document not found")
    audit(u["uid"], "update_knowledge", document_id, payload.data)
    return row


@router.delete("/knowledge/documents/{document_id}")
def remove_knowledge_document(document_id: str, u=Depends(get_current_user)):
    _require_knowledge_editor(u)
    if not delete_knowledge_document(document_id):
        raise HTTPException(404, "Knowledge document not found")
    audit(u["uid"], "delete_knowledge", document_id, {})
    return {"deleted": True, "id": document_id}


@router.get("/farms")
def farms(u=Depends(get_current_user)):
    return list_farms(u["uid"])


@router.post("/farms")
def add_farm(payload: AnyPayload, u=Depends(get_current_user)):
    return create_farm(u["uid"], payload.data)


@router.patch("/farms/{farm_id}")
def patch_farm(farm_id: str, payload: AnyPayload, u=Depends(get_current_user)):
    return update_farm(u["uid"], farm_id, payload.data)


@router.get("/projects")
def projects(u=Depends(get_current_user)):
    return list_projects(u["uid"])


@router.post("/projects")
def add_project(payload: AnyPayload, u=Depends(get_current_user)):
    return create_project(u["uid"], payload.data)


@router.get("/tasks")
def tasks(u=Depends(get_current_user)):
    return list_tasks(u["uid"])


@router.post("/tasks")
def add_task(payload: AnyPayload, u=Depends(get_current_user)):
    return create_task(u["uid"], payload.data)


@router.patch("/tasks/{task_id}")
def patch_task(task_id: str, payload: TaskPatch, u=Depends(get_current_user)):
    return update_task(u["uid"], task_id, {k: v for k, v in payload.model_dump().items() if v is not None})


@router.get("/observations")
def observations(u=Depends(get_current_user)):
    return list_observations(u["uid"])


@router.post("/observations")
def add_observation(payload: AnyPayload, u=Depends(get_current_user)):
    return create_observation(u["uid"], payload.data)


@router.get("/expenses")
def expenses(u=Depends(get_current_user)):
    return list_expenses(u["uid"])


@router.post("/expenses")
def add_expense(payload: AnyPayload, u=Depends(get_current_user)):
    return create_expense(u["uid"], payload.data)


@router.get("/harvests")
def harvests(u=Depends(get_current_user)):
    return list_harvests(u["uid"])


@router.post("/harvests")
def add_harvest(payload: AnyPayload, u=Depends(get_current_user)):
    return create_harvest(u["uid"], payload.data)


@router.get("/products")
def products():
    return PRODUCTS


@router.get("/suppliers")
def suppliers():
    return SUPPLIERS


@router.get("/orders")
def orders(u=Depends(get_current_user)):
    return list_orders(u["uid"])


@router.post("/orders")
def add_order(payload: AnyPayload, u=Depends(get_current_user)):
    if not payload.data.get("confirmed"):
        raise HTTPException(400, "Explicit purchase confirmation is required")
    return create_order(u["uid"], payload.data)


@router.get("/expert-cases")
def expert_cases(u=Depends(get_current_user)):
    return list_expert_cases_for_actor(u)


@router.post("/expert-cases")
def add_case(payload: AnyPayload, u=Depends(get_current_user)):
    return create_expert_case(u["uid"], payload.data)


@router.patch("/expert-cases/{case_id}")
def patch_case(case_id: str, payload: AnyPayload, u=Depends(get_current_user)):
    result = update_expert_case_for_actor(u, case_id, payload.data)
    if not result:
        raise HTTPException(404, "Expert case not found or access denied")
    return result


@router.get("/notifications")
def notifications(u=Depends(get_current_user)):
    return list_notifications(u["uid"])


@router.post("/notifications")
def add_notification(payload: AnyPayload, u=Depends(get_current_user)):
    return create_notification(u["uid"], payload.data)


@router.patch("/notifications/{notification_id}")
def patch_notification(notification_id: str, payload: AnyPayload, u=Depends(get_current_user)):
    try:
        return update_notification(u["uid"], notification_id, payload.data)
    except PermissionError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/community")
def community():
    return list_community_reports()


@router.post("/community")
def add_community(payload: AnyPayload, u=Depends(get_current_user)):
    return create_community_report(u["uid"], payload.data)


@router.post("/device-tokens")
def device_token(payload: AnyPayload, u=Depends(get_current_user)):
    token = str(payload.data.get("token") or "").strip()
    if not token:
        raise HTTPException(400, "token is required")
    return save_device_token(u["uid"], token, str(payload.data.get("platform") or "web"))


@router.get("/device-tokens")
def device_tokens(u=Depends(get_current_user)):
    return list_device_tokens(u["uid"])


@router.get("/audit")
def read_audit(u=Depends(get_current_user)):
    return audit_log_for_actor(u)


@router.get("/agent-runs")
def agent_runs(u=Depends(get_current_user)):
    return list_agent_runs_for_actor(u)


# -----------------------------
# Stateful conversations
# -----------------------------
@router.get("/conversations")
def conversations(u=Depends(get_current_user)):
    return list_conversations(u["uid"])


@router.post("/conversations")
def new_conversation(req: ConversationCreateRequest, u=Depends(get_current_user)):
    try:
        return create_conversation(u["uid"], req.project_id, req.title)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc


@router.get("/conversations/{conversation_id}/messages")
def conversation_messages(conversation_id: str, u=Depends(get_current_user)):
    return list_messages(u["uid"], conversation_id)


@router.get("/conversations/{conversation_id}/memory")
def conversation_memory(conversation_id: str, u=Depends(get_current_user)):
    return get_memory(u["uid"], conversation_id)


@router.delete("/conversations/{conversation_id}")
def close_conversation(conversation_id: str, u=Depends(get_current_user)):
    return archive_conversation(u["uid"], conversation_id)


@router.post("/voice/session-token")
def voice_session_token(req: VoiceSessionRequest, u=Depends(get_current_user)):
    try:
        return create_voice_session_token(u, req.language)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.post("/voice/tts")
def voice_tts(req: VoiceTTSRequest, u=Depends(get_current_user)):
    try:
        audio, media_type = synthesize_voice(req.text, req.language)
        return Response(content=audio, media_type=media_type, headers={"Cache-Control": "no-store"})
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


def _attach_generated_report(result: dict[str, Any], uid: str, conversation_id: str, language: str) -> dict[str, Any] | None:
    """Full Report mode returns the report itself once blocking facts are known.

    Optional unknowns remain visible as assumptions inside the report.
    """
    if not (result.get("auto_generate_report") and result.get("report_ready")):
        return None
    try:
        report = generate_conversation_report(uid, conversation_id)
    except ValueError as exc:
        # A blocking fact can still be discovered between routing and generation.
        result.update({"report_ready": False, "auto_generate_report": False, "response_type": "clarification", "summary": str(exc)})
        return None
    except Exception as exc:
        # Keep the chat answer usable even when storage or the provider fails.
        result["report_generation_error"] = str(exc)
        result["summary"] = f"{result.get('summary', '').strip()} {i18n.t('report_generated', 'failed', language)}".strip()
        return None
    result["report"] = report
    result["response_type"] = "report_ready"
    result["summary"] = f"{result.get('summary', '').strip()} {i18n.t('report_generated', 'ready', language)}".strip()
    result["recommended_action"] = i18n.t("report_generated", "action", language)
    return report


@router.post("/ask-ai")
def ask_ai(req: AIRequest, u=Depends(get_current_user)):
    question = req.question.strip()
    if not question and not req.clarification_answers:
        raise HTTPException(400, "Question is required")

    request_context = {
        **req.context,
        "interaction_mode": req.mode or "auto",
        "allow_mode_mismatch": bool(req.allow_mode_mismatch),
    }

    if req.conversation_id:
        conv = require_conversation(u["uid"], req.conversation_id)
    else:
        title = question[:72] if question else "Cultivation planning"
        try:
            conv = create_conversation(u["uid"], req.context.get("project_id") or None, title)
        except PermissionError as exc:
            raise HTTPException(403, str(exc)) from exc

    conversation_id = conv["id"]
    selected_project_id = req.context.get("project_id") or None
    if selected_project_id != (conv.get("project_id") or None):
        try:
            conv = update_conversation_project(u["uid"], conversation_id, selected_project_id)
        except PermissionError as exc:
            raise HTTPException(403, str(exc)) from exc
    if conv.get("title") == "New farm conversation" and question:
        update_conversation_title(u["uid"], conversation_id, question[:72])

    display_question = question
    if req.clarification_answers:
        answer_text = ", ".join(f"{k.replace('_', ' ')}: {v}" for k, v in req.clarification_answers.items() if v not in (None, ""))
        display_question = question or f"Here are the requested details: {answer_text}"

    # A route-resume call reuses the already persisted user question after the user
    # chooses "Switch & continue" or "Stay in this mode". This avoids duplicate
    # user messages in the conversation history.
    user_message = None
    if not req.resume_route:
        user_message = append_message(
            u["uid"],
            conversation_id,
            "user",
            display_question,
            {
                "context": request_context,
                "clarification_answers": req.clarification_answers,
                "requested_mode": req.mode,
            },
        )

    resolved_context, memory = resolve_conversation_context(
        u["uid"],
        conversation_id,
        display_question,
        request_context,
        u,
        req.clarification_answers,
    )
    history = recent_history(u["uid"], conversation_id, 18)
    result = orchestrator.process_farmer_request(
        display_question,
        resolved_context,
        u["uid"],
        history=history,
        memory=memory,
    )

    memory_patch = result.get("memory_patch") if isinstance(result.get("memory_patch"), dict) else {}
    if memory_patch:
        memory = update_memory(u["uid"], conversation_id, known_facts=memory_patch)

    # Full Report mode means the user asked for the report itself, not merely a
    # "report ready" status. Generate it immediately once the genuinely blocking
    # facts are available. Optional unknowns remain visible as assumptions.
    generated_report = _attach_generated_report(result, u["uid"], conversation_id, str(resolved_context.get("language") or "English"))

    result["response_language"] = resolved_context.get("language") or "English"
    result["detected_language"] = resolved_context.get("detected_language") or result["response_language"]
    result["language_confidence"] = resolved_context.get("language_confidence")

    assistant_metadata = {
        "response_language": result.get("response_language"),
        "detected_language": result.get("detected_language"),
        "response_type": result.get("response_type", "answer"),
        "clarification_fields": result.get("clarification_fields", []),
        "suggested_actions": result.get("suggested_actions", []),
        "report_ready": bool(result.get("report_ready")),
        "risk_level": result.get("risk_level"),
        "confidence": result.get("confidence"),
        "requested_mode": result.get("requested_mode", req.mode),
        "detected_mode": result.get("detected_mode"),
        "effective_mode": result.get("effective_mode"),
        "suggested_mode": result.get("suggested_mode"),
        "detected_intent": result.get("detected_intent"),
        "original_question": result.get("original_question"),
        "report": generated_report,
        "decision": {
            key: result.get(key)
            for key in [
                "response_type", "summary", "recommended_action", "why", "confidence",
                "alternatives", "do_not_do", "sources", "confirmation_required", "follow_up",
                "risk_level", "counterfactual", "agent_trace", "clarification_fields",
                "suggested_actions", "report_ready", "provider", "model", "requested_mode",
                "detected_mode", "effective_mode", "suggested_mode", "detected_intent",
                "mode_reason", "original_question", "planning_snapshot", "tool_plan",
                "tool_plan_detail", "tool_runtime", "weather_decision", "evidence_quality",
                "economics", "resource_plan", "rag",
                "response_language", "detected_language", "language_confidence"
            ]
        },
    }
    assistant_message = append_message(
        u["uid"],
        conversation_id,
        "assistant",
        str(result.get("summary") or result.get("recommended_action") or "MihiMura completed the request."),
        assistant_metadata,
    )

    run_id = record_agent_run(
        u["uid"],
        display_question,
        result,
        resolved_context,
        conversation_id=conversation_id,
        message_id=assistant_message["id"],
    )
    result["run_id"] = run_id
    result["conversation_id"] = conversation_id
    result["user_message_id"] = user_message["id"] if user_message else None
    result["assistant_message_id"] = assistant_message["id"]
    result["conversation_memory"] = memory
    audit(
        u["uid"],
        "ai_recommendation",
        conversation_id,
        {
            "question": display_question,
            "provider": result.get("provider"),
            "confidence": result.get("confidence"),
            "run_id": run_id,
            "requested_mode": result.get("requested_mode", req.mode),
            "detected_mode": result.get("detected_mode"),
            "effective_mode": result.get("effective_mode"),
        },
    )
    return result


@router.get("/reports")
def reports(u=Depends(get_current_user)):
    return list_reports(u["uid"])


@router.post("/conversations/{conversation_id}/reports")
def create_report(conversation_id: str, u=Depends(get_current_user)):
    try:
        report = generate_conversation_report(u["uid"], conversation_id)
        append_message(
            u["uid"],
            conversation_id,
            "assistant",
            f"Your report is ready: {report.get('title')}",
            {"response_type": "report_ready", "report": {"id": report.get("id"), "title": report.get("title"), "download_url": report.get("download_url")}},
        )
        return report
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        # Multilingual composition/font/provider failures are service-side, not bad user input.
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"Report generation failed: {exc}") from exc


@router.post("/diagnose-image")
async def diagnose_image(
    images: list[UploadFile] = File(...),
    crop_hint: str = Form(""),
    project_id: str = Form(""),
    symptoms: str = Form(""),
    u=Depends(get_current_user),
):
    if not images or len(images) > 4:
        raise HTTPException(400, "Upload between 1 and 4 guided images")
    prepared = []
    names = []
    total = 0
    for image in images:
        if image.content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise HTTPException(400, "Upload JPEG, PNG or WebP")
        data = await image.read()
        total += len(data)
        if len(data) > settings.MAX_UPLOAD_MB * 1024 * 1024:
            raise HTTPException(400, f"Each image must be below {settings.MAX_UPLOAD_MB} MB")
        prepared.append((data, image.content_type or "image/jpeg"))
        names.append(image.filename or "image")
    if total > settings.MAX_UPLOAD_MB * 4 * 1024 * 1024:
        raise HTTPException(400, "Combined upload is too large")
    result = analyze_crop_images(prepared, crop_hint, symptoms)
    audit(u["uid"], "crop_image_analysis", project_id or "unassigned", {"filenames": names, "image_count": len(images), "provider": result.get("provider"), "expert_review": result.get("expert_review")})
    return result
