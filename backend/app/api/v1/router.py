from fastapi import APIRouter
from app.modules.identity.router    import router as identity_router
from app.modules.zunde.router       import router as zunde_router
from app.modules.zunde.alerts_router import router as alerts_router
from app.modules.mvura.router       import router as mvura_router
from app.modules.simba.router       import router as simba_router
from app.modules.musika.router      import router as musika_router
from app.modules.livestock.router   import router as livestock_router
from app.modules.community.router   import router as community_router
from app.modules.analytics.router   import router as analytics_router
from app.modules.ussd.router        import router as ussd_router
from app.modules.settings_module.router import router as settings_router
from app.modules.intelligence.router import router as intelligence_router

api_router = APIRouter()

api_router.include_router(identity_router,  prefix="/auth",       tags=["Identity & Auth"])
api_router.include_router(alerts_router,    prefix="/alerts",     tags=["Alerts"])
api_router.include_router(zunde_router,     prefix="/zunde",      tags=["Zunde — Agriculture"])
api_router.include_router(mvura_router,     prefix="/mvura",      tags=["Mvura — Water"])
api_router.include_router(simba_router,     prefix="/simba",      tags=["Simba — Energy"])
api_router.include_router(musika_router,    prefix="/musika",     tags=["Musika — Marketplace"])
api_router.include_router(livestock_router, prefix="/livestock",  tags=["Livestock Health"])
api_router.include_router(community_router, prefix="/community",  tags=["Community & Validation"])
api_router.include_router(analytics_router, prefix="/analytics",  tags=["Analytics"])
api_router.include_router(ussd_router,      prefix="/ussd",       tags=["USSD Gateway"])
api_router.include_router(settings_router,  prefix="/settings",   tags=["Platform Settings"])
api_router.include_router(intelligence_router, prefix="/intelligence", tags=["Cross-Pillar Intelligence"])
