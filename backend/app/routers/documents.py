import os
import shutil
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.dependencies import current_user
from fastapi.responses import FileResponse
from app.dependencies import current_user, allow_roles


router = APIRouter(prefix="/documents", tags=["Documents"])

UPLOAD_DIR = "uploads/documents"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload", status_code=201)
def upload_document(
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(current_user)
):
    employee = db.query(models.Employee).filter(
        models.Employee.user_id == user.id
    ).first()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee profile not found"
        )

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Please select a file"
        )

    # Generate a unique filename to avoid overwriting existing files.
    safe_filename = os.path.basename(file.filename)
    stored_filename = f"{uuid4().hex}_{safe_filename}"
    file_path = os.path.join(UPLOAD_DIR, stored_filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        document = models.Document(
            employee_id=employee.id,
            file_name=safe_filename,
            file_path=file_path,
            document_type=document_type
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        return {
            "message": "Document uploaded successfully",
            "document": document
        }

    except Exception:
        db.rollback()

        if os.path.exists(file_path):
            os.remove(file_path)

        raise HTTPException(
            status_code=500,
            detail="Document upload failed"
        )

    finally:
        file.file.close()


@router.get("/me")
def get_my_documents(
    db: Session = Depends(get_db),
    user=Depends(current_user)
):
    employee = db.query(models.Employee).filter(
        models.Employee.user_id == user.id
    ).first()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee profile not found"
        )

    return db.query(models.Document).filter(
        models.Document.employee_id == employee.id
    ).order_by(
        models.Document.uploaded_at.desc()
    ).all()

@router.get("/all")
def get_all_documents(
    db: Session = Depends(get_db),
    user=Depends(allow_roles("HR", "ADMIN"))
):
    return db.query(models.Document).order_by(
        models.Document.uploaded_at.desc()
    ).all()

@router.get("/{document_id}")
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    user=Depends(current_user)
):
    employee = db.query(models.Employee).filter(
        models.Employee.user_id == user.id
    ).first()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee profile not found"
        )

    document = db.query(models.Document).filter(
        models.Document.id == document_id,
        models.Document.employee_id == employee.id
    ).first()

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    return document

@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    user=Depends(current_user)
):
    employee = db.query(models.Employee).filter(
        models.Employee.user_id == user.id
    ).first()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee profile not found"
        )

    document = db.query(models.Document).filter(
        models.Document.id == document_id,
        models.Document.employee_id == employee.id
    ).first()

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    if not os.path.isfile(document.file_path):
        raise HTTPException(
            status_code=404,
            detail="Document file not found on server"
        )

    return FileResponse(
        path=document.file_path,
        filename=document.file_name
    )



