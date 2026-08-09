from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from app.agents.orchestrator import orchestrator
from app.agents.vision import analyze_crop_images
from app.core.auth import get_current_user
from app.core.config import settings
from app.db import audit
from app.services.dashboard import get_dashboard_payload
from app.services.weather import get_weather
from app.services.climate_history import get_nasa_power
from app.services.satellite import catalog_search, configured as satellite_configured
from app.services.voice import create_voice_session_token
from app.services.platform import *

router=APIRouter()
class AnyPayload(BaseModel): data: dict[str,Any]=Field(default_factory=dict)
class AIRequest(BaseModel): question:str; context:dict[str,Any]=Field(default_factory=dict)
class VoiceSessionRequest(BaseModel):
    language: str = "English"
    project_id: str | None = None
class TaskPatch(BaseModel): status:str|None=None; due_at:str|None=None; assigned_to:str|None=None; completion_note:str|None=None; schedule_reason:str|None=None

@router.get('/health')
def health(): return {"status":"ok","version":settings.VERSION,"ai_configured":bool(settings.GEMINI_API_KEY),"firebase_admin_configured":bool(settings.firebase_credentials_path and settings.firebase_credentials_path.exists()),"sentinel_configured":satellite_configured()}
@router.get('/users/me')
def me(u=Depends(get_current_user)): return u
@router.put('/users/me')
def put_me(payload:AnyPayload,u=Depends(get_current_user)): return update_profile(u['uid'],payload.data)
@router.delete('/users/me')
def delete_me(u=Depends(get_current_user)): return request_account_deletion(u['uid'])
@router.get('/admin/users')
def admin_users(u=Depends(get_current_user)):
    data=list_users_for_admin(u)
    if not data and not (u.get('provider')=='demo' or u.get('role')=='admin'):
        raise HTTPException(403,'Verified administrator access required')
    return data
@router.patch('/admin/users/{uid}/verification')
def admin_verify_user(uid:str,payload:AnyPayload,u=Depends(get_current_user)):
    try:
        result=set_professional_verification(u,uid,bool(payload.data.get('verified',True)))
    except PermissionError as exc:
        raise HTTPException(403,str(exc)) from exc
    if not result: raise HTTPException(404,'User not found')
    return result
@router.get('/dashboard')
def dashboard(u=Depends(get_current_user)): return get_dashboard_payload(u['uid'])
@router.get('/weather')
def weather(lat:float=7.291,lon:float=81.674,days:int=14): return get_weather(lat,lon,days)
@router.get('/climate-history')
def climate_history(lat:float=7.291,lon:float=81.674,days:int=30): return get_nasa_power(lat,lon,days)
@router.get('/satellite/catalog')
def satellite(lat:float=7.291,lon:float=81.674): return catalog_search(lat,lon)

@router.get('/farms')
def farms(u=Depends(get_current_user)): return list_farms(u['uid'])
@router.post('/farms')
def add_farm(payload:AnyPayload,u=Depends(get_current_user)): return create_farm(u['uid'],payload.data)
@router.patch('/farms/{farm_id}')
def patch_farm(farm_id:str,payload:AnyPayload,u=Depends(get_current_user)): return update_farm(u['uid'],farm_id,payload.data)
@router.get('/projects')
def projects(u=Depends(get_current_user)): return list_projects(u['uid'])
@router.post('/projects')
def add_project(payload:AnyPayload,u=Depends(get_current_user)): return create_project(u['uid'],payload.data)
@router.get('/tasks')
def tasks(u=Depends(get_current_user)): return list_tasks(u['uid'])
@router.post('/tasks')
def add_task(payload:AnyPayload,u=Depends(get_current_user)): return create_task(u['uid'],payload.data)
@router.patch('/tasks/{task_id}')
def patch_task(task_id:str,payload:TaskPatch,u=Depends(get_current_user)): return update_task(u['uid'],task_id,{k:v for k,v in payload.model_dump().items() if v is not None})
@router.get('/observations')
def observations(u=Depends(get_current_user)): return list_observations(u['uid'])
@router.post('/observations')
def add_observation(payload:AnyPayload,u=Depends(get_current_user)): return create_observation(u['uid'],payload.data)
@router.get('/expenses')
def expenses(u=Depends(get_current_user)): return list_expenses(u['uid'])
@router.post('/expenses')
def add_expense(payload:AnyPayload,u=Depends(get_current_user)): return create_expense(u['uid'],payload.data)
@router.get('/harvests')
def harvests(u=Depends(get_current_user)): return list_harvests(u['uid'])
@router.post('/harvests')
def add_harvest(payload:AnyPayload,u=Depends(get_current_user)): return create_harvest(u['uid'],payload.data)
@router.get('/products')
def products(): return PRODUCTS
@router.get('/suppliers')
def suppliers(): return SUPPLIERS
@router.get('/orders')
def orders(u=Depends(get_current_user)): return list_orders(u['uid'])
@router.post('/orders')
def add_order(payload:AnyPayload,u=Depends(get_current_user)):
    if not payload.data.get('confirmed'): raise HTTPException(400,'Explicit purchase confirmation is required')
    return create_order(u['uid'],payload.data)
@router.get('/expert-cases')
def expert_cases(u=Depends(get_current_user)): return list_expert_cases_for_actor(u)
@router.post('/expert-cases')
def add_case(payload:AnyPayload,u=Depends(get_current_user)): return create_expert_case(u['uid'],payload.data)
@router.patch('/expert-cases/{case_id}')
def patch_case(case_id:str,payload:AnyPayload,u=Depends(get_current_user)):
    result=update_expert_case_for_actor(u,case_id,payload.data)
    if not result: raise HTTPException(404,'Expert case not found or access denied')
    return result
@router.get('/notifications')
def notifications(u=Depends(get_current_user)): return list_notifications(u['uid'])
@router.post('/notifications')
def add_notification(payload:AnyPayload,u=Depends(get_current_user)): return create_notification(u['uid'],payload.data)
@router.patch('/notifications/{notification_id}')
def patch_notification(
    notification_id: str,
    payload: AnyPayload,
    u=Depends(get_current_user)
):
    try:
        return update_notification(
            u['uid'],
            notification_id,
            payload.data
        )
    except PermissionError as exc:
        raise HTTPException(
            404,
            str(exc)
        ) from exc

@router.get('/community')
def community(): return list_community_reports()
@router.post('/community')
def add_community(payload:AnyPayload,u=Depends(get_current_user)): return create_community_report(u['uid'],payload.data)
@router.post('/device-tokens')
def device_token(payload:AnyPayload,u=Depends(get_current_user)): return save_device_token(u['uid'],payload.data['token'],payload.data.get('platform','web'))
@router.get('/device-tokens')
def device_tokens(u=Depends(get_current_user)): return list_device_tokens(u['uid'])
@router.get('/audit')
def read_audit(u=Depends(get_current_user)): return audit_log_for_actor(u)
@router.get('/agent-runs')
def agent_runs(u=Depends(get_current_user)): return list_agent_runs_for_actor(u)

@router.post('/voice/session-token')
def voice_session_token(
    req: VoiceSessionRequest,
    u=Depends(get_current_user)
):
    try:
        return create_voice_session_token(
            u,
            req.language
        )
    except RuntimeError as exc:
        raise HTTPException(
            503,
            str(exc)
        ) from exc
@router.post('/ask-ai')
def ask_ai(req:AIRequest,u=Depends(get_current_user)):
    context={"location":u.get('district') or 'Ampara',"language":u.get('language') or 'English',**req.context}; result=orchestrator.process_farmer_request(req.question.strip(),context,u['uid']); run_id=record_agent_run(u['uid'],req.question,result,context); result['run_id']=run_id; audit(u['uid'],'ai_recommendation','chat',{"question":req.question,"provider":result.get('provider'),"confidence":result.get('confidence'),"run_id":run_id}); return result

@router.post('/diagnose-image')
async def diagnose_image(images:list[UploadFile]=File(...),crop_hint:str=Form(''),project_id:str=Form(''),symptoms:str=Form(''),u=Depends(get_current_user)):
    if not images or len(images)>4: raise HTTPException(400,'Upload between 1 and 4 guided images')
    prepared=[]; names=[]; total=0
    for image in images:
        if image.content_type not in {'image/jpeg','image/png','image/webp'}: raise HTTPException(400,'Upload JPEG, PNG or WebP')
        data=await image.read(); total+=len(data)
        if len(data)>settings.MAX_UPLOAD_MB*1024*1024: raise HTTPException(400,f'Each image must be below {settings.MAX_UPLOAD_MB} MB')
        prepared.append((data,image.content_type or 'image/jpeg')); names.append(image.filename or 'image')
    if total>settings.MAX_UPLOAD_MB*4*1024*1024: raise HTTPException(400,'Combined upload is too large')
    result=analyze_crop_images(prepared,crop_hint,symptoms)
    audit(u['uid'],'crop_image_analysis',project_id or 'unassigned',{'filenames':names,'image_count':len(images),'provider':result.get('provider'),'expert_review':result.get('expert_review')})
    return result
