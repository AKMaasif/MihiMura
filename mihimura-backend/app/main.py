from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.endpoints import router
from app.core.config import settings
from app.db import init_db

app=FastAPI(title=settings.PROJECT_NAME,version=settings.VERSION,description="Agentic climate-resilient agriculture API")
app.add_middleware(CORSMiddleware,allow_origins=settings.origins,allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
@app.exception_handler(PermissionError)
async def permission_error(_:Request,exc:PermissionError): return JSONResponse(status_code=403,content={"detail":str(exc)})
@app.exception_handler(ValueError)
async def value_error(_:Request,exc:ValueError): return JSONResponse(status_code=400,content={"detail":str(exc)})
@app.on_event('startup')
def startup(): init_db()
@app.get('/')
def root(): return {"name":"MihiMura API","version":settings.VERSION,"docs":"/docs"}
app.include_router(router,prefix=settings.API_V1_STR)
