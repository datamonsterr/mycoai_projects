from fastapi import APIRouter

from .admin import router as admin_router
from .auth import router as auth_router
from .dashboard import router as dashboard_router
from .feedback import router as feedback_router
from .images import router as images_router
from .index import router as index_router
from .models import router as models_router
from .retrieval import router as retrieval_router
from .species import router as species_router
from .strains import router as strains_router
from .training import router as training_router

router = APIRouter()
router.include_router(auth_router, prefix="/auth", tags=["Auth"])
router.include_router(images_router, prefix="/images", tags=["Images"])
router.include_router(retrieval_router, prefix="/retrieval", tags=["Retrieval"])
router.include_router(species_router, prefix="/species", tags=["Species"])
router.include_router(strains_router, prefix="/strains", tags=["Strains"])
router.include_router(feedback_router, prefix="/feedback", tags=["Feedback"])
router.include_router(training_router, prefix="/training", tags=["Training"])
router.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
router.include_router(admin_router, prefix="/admin", tags=["Admin"])
router.include_router(index_router, prefix="/index", tags=["Index"])
router.include_router(models_router, prefix="/models", tags=["Models"])
