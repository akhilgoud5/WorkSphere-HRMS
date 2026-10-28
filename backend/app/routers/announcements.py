
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_user, allow_roles
from app.models import Announcement

router = APIRouter(
    prefix="/announcements",
    tags=["Announcements"]
)


class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    message: str = Field(..., min_length=1)


# HR/Admin can create announcements
@router.post("/", status_code=201)
def create_announcement(
    data: AnnouncementCreate,
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN"))
):
    announcement = Announcement(
        title=data.title,
        message=data.message,
        created_by=user.id,
        created_at=datetime.utcnow()
    )

    db.add(announcement)
    db.commit()
    db.refresh(announcement)

    return announcement


# All authenticated users can view announcements
@router.get("/")
def get_announcements(
    db: Session = Depends(get_db),
    user=Depends(current_user)
):
    return (
        db.query(Announcement)
        .order_by(Announcement.created_at.desc())
        .all()
    )


# View a specific announcement
@router.get("/{announcement_id}")
def get_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    user=Depends(current_user)
):
    announcement = db.query(Announcement).filter(
        Announcement.id == announcement_id
    ).first()

    if not announcement:
        raise HTTPException(
            status_code=404,
            detail="Announcement not found"
        )

    return announcement
