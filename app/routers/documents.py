"""
Document Management API Endpoints
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import logging
import os
from pathlib import Path
from uuid import UUID, uuid4

from app.database import get_db
from app.db_models import Document as DocumentModel
from app.models.schemas import DocumentResponse
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

DOCUMENTS_DIR = Path("./documents_storage")
DOCUMENTS_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "jpg", "jpeg", "png", "txt"}

@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload and process document"""
    try:
        # Validate file type
        file_ext = file.filename.split(".")[-1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type .{file_ext} not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        # Validate file size
        contents = await file.read()
        file_size = len(contents)

        if file_size > settings.MAX_UPLOAD_SIZE:
            max_mb = settings.MAX_UPLOAD_SIZE / (1024 * 1024)
            actual_mb = file_size / (1024 * 1024)
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {max_mb:.0f}MB, actual: {actual_mb:.2f}MB"
            )

        if file_size == 0:
            raise HTTPException(
                status_code=400,
                detail="File is empty"
            )

        # Save file
        file_path = DOCUMENTS_DIR / f"{uuid4()}_{file.filename}"
        with open(file_path, "wb") as f:
            f.write(contents)

        # Create document record
        doc = DocumentModel(
            filename=file.filename,
            file_type=file_ext,
            file_path=str(file_path),
            status="pending"
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        # Queue document processing as background task
        try:
            from app.tasks.document_tasks import process_document
            task = process_document.delay(
                str(doc.id),
                str(file_path),
                file_ext
            )
            logger.info(f"Uploaded document: {doc.id} ({file.filename}), queued for processing (task: {task.id})")
        except Exception as e:
            logger.warning(f"Failed to queue document processing for {doc.id}: {e}")
            # Document is still created, just processing is queued asynchronously

        return doc
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail="Error uploading document")

@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    status: str = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """List all documents with optional status filter"""
    try:
        stmt = select(DocumentModel)
        if status:
            stmt = stmt.where(DocumentModel.status == status)
        stmt = stmt.offset(skip).limit(limit).order_by(DocumentModel.created_at.desc())
        result = await db.execute(stmt)
        documents = result.scalars().all()
        return documents
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail="Error listing documents")

@router.post("/search")
async def search_documents(
    query: str,
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """Search documents by text content"""
    try:
        stmt = select(DocumentModel).where(
            DocumentModel.searchable_text.ilike(f"%{query}%")
        ).offset(skip).limit(limit)
        result = await db.execute(stmt)
        documents = result.scalars().all()

        return {
            "query": query,
            "results": documents,
            "total_count": len(documents)
        }
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        raise HTTPException(status_code=500, detail="Error searching documents")
