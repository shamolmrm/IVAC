from fastapi import APIRouter

from app.api.v1 import health
from app.modules.applicants.router import router as applicants_router
from app.modules.auth.phone_router import router as phone_router
from app.modules.auth.router import router as auth_router
from app.modules.documents.router import router as documents_router
from app.modules.ocr.router import router as ocr_router
from app.modules.organizations.admin_router import router as org_admin_router
from app.modules.organizations.router import router as org_router

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth_router)
api_router.include_router(phone_router)
api_router.include_router(org_router)
api_router.include_router(org_admin_router)
api_router.include_router(applicants_router)
api_router.include_router(documents_router)
api_router.include_router(ocr_router)
