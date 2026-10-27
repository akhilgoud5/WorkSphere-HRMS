
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import allow_roles, current_user
from app.models import Notification, User

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"]
)


class NotificationCreate(BaseModel):
    user_id: int
    title: str = Field(..., min_length=1, max_length=150)
    message: str = Field(..., min_length=1, max_length=1000)


@router.post("/", status_code=201)
def create_notification(
    data: NotificationCreate,
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN")),
):
    recipient = db.query(User).filter(
        User.id == data.user_id
    ).first()

    if not recipient:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    notification = Notification(
        user_id=data.user_id,
        title=data.title,
        message=data.message,
        is_read=False,
        created_at=datetime.utcnow(),
    )

    db.add(notification)
    db.commit()
    db.refresh(notification)

    return notification


@router.get("/me")
def get_my_notifications(
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    return db.query(Notification).filter(
        Notification.user_id == user.id
    ).order_by(
        Notification.created_at.desc()
    ).all()


@router.put("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user.id
    ).first()

    if not notification:
        raise HTTPException(
            status_code=404,
            detail="Notification not found"
        )

    notification.is_read = True
    db.commit()
    db.refresh(notification)

    return {
        "message": "Notification marked as read",
        "notification": notification
    }

def send_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
):
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        is_read=False,
        created_at=datetime.utcnow(),
    )

    db.add(notification)
    db.commit()
    db.refresh(notification)

    return notification