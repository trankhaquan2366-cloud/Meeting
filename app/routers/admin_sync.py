"""Administrative endpoints for external directory synchronization."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.routers.admin_analytics import get_current_admin_user
from app.schemas.hrm import HRMSyncResponse
from app.services.hrm_sync_service import HRMSyncService

router = APIRouter()


@router.post(
    "/sync/hrm",
    response_model=HRMSyncResponse,
    dependencies=[Depends(get_current_admin_user)],
)
def sync_hrm_data(
    db: Session = Depends(get_db),
) -> HRMSyncResponse:
    """Synchronize the mock HRM directory; administrator access is required."""
    return HRMSyncService.sync_hrm_data(db)
