"""
Celery Tasks for Async Document Processing

Background tasks for:
- Document parsing and OCR
- Searchable text extraction
- Document status updates
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from app.celery_app import app
from app.config import settings

logger = logging.getLogger(__name__)

# ============================================
# DOCUMENT PROCESSING TASKS
# ============================================

@app.task(bind=True, name='tasks.process_document')
def process_document(
    self,
    document_id: str,
    file_path: str,
    file_type: str
) -> Dict[str, Any]:
    """
    Process uploaded document asynchronously

    Handles:
    - PDF text extraction
    - Image OCR
    - DOCX parsing
    - Searchable text generation

    Args:
        document_id: UUID of the document
        file_path: Full path to document file
        file_type: File extension (pdf, docx, jpg, etc.)

    Returns:
        Task result with extracted text and status
    """
    from sqlalchemy import select, update
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.db_models import Document as DocumentModel

    start_time = datetime.utcnow()

    try:
        logger.info(f"[Task {self.request.id}] Processing document {document_id} ({file_type})")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document file not found: {file_path}")

        extracted_text = ""

        # Extract text based on file type
        if file_type.lower() == 'pdf':
            extracted_text = _extract_pdf_text(file_path)
        elif file_type.lower() in ['docx', 'doc']:
            extracted_text = _extract_docx_text(file_path)
        elif file_type.lower() in ['jpg', 'jpeg', 'png']:
            extracted_text = _extract_image_text(file_path)
        elif file_type.lower() == 'txt':
            extracted_text = _extract_txt_text(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        # Update document in database
        import asyncio
        async def _update_db():
            engine = create_async_engine(settings.DATABASE_URL, echo=False)
            async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            async with async_session() as session:
                stmt = update(DocumentModel).where(
                    DocumentModel.id == __import__('uuid').UUID(document_id)
                ).values(
                    searchable_text=extracted_text,
                    status="completed",
                    processed_at=datetime.utcnow()
                )
                await session.execute(stmt)
                await session.commit()

            await engine.dispose()

        asyncio.run(_update_db())

        logger.info(
            f"[Task {self.request.id}] ✓ Document processed {document_id} "
            f"({len(extracted_text)} chars) in {duration_ms:.1f}ms"
        )

        return {
            "status": "success",
            "document_id": document_id,
            "text_length": len(extracted_text),
            "duration_ms": duration_ms,
            "task_id": self.request.id
        }

    except Exception as e:
        logger.error(f"[Task {self.request.id}] ✗ Document processing error: {e}")

        # Update document status to failed
        try:
            import asyncio
            from sqlalchemy import select, update
            from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
            from sqlalchemy.orm import sessionmaker
            from app.db_models import Document as DocumentModel

            async def _update_status():
                engine = create_async_engine(settings.DATABASE_URL, echo=False)
                async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

                async with async_session() as session:
                    stmt = update(DocumentModel).where(
                        DocumentModel.id == __import__('uuid').UUID(document_id)
                    ).values(
                        status="failed",
                        processed_at=datetime.utcnow()
                    )
                    await session.execute(stmt)
                    await session.commit()

                await engine.dispose()

            asyncio.run(_update_status())
        except Exception as db_error:
            logger.warning(f"Failed to update document status: {db_error}")

        raise self.retry(exc=e, countdown=120 * (self.request.retries + 1))

# ============================================
# TEXT EXTRACTION HELPERS
# ============================================

def _extract_pdf_text(file_path: str) -> str:
    """Extract text from PDF file"""
    try:
        import PyPDF2

        text = ""
        with open(file_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            for page in pdf_reader.pages:
                text += page.extract_text() or ""

        return text.strip()

    except ImportError:
        logger.warning("PyPDF2 not available for PDF extraction")
        return ""
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        raise

def _extract_docx_text(file_path: str) -> str:
    """Extract text from DOCX/DOC file"""
    try:
        from docx import Document as DocxDocument

        text = ""
        doc = DocxDocument(file_path)

        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"

        return text.strip()

    except ImportError:
        logger.warning("python-docx not available for DOCX extraction")
        return ""
    except Exception as e:
        logger.error(f"DOCX extraction error: {e}")
        raise

def _extract_image_text(file_path: str) -> str:
    """Extract text from image using OCR"""
    try:
        import pytesseract
        from PIL import Image

        # This requires tesseract-ocr system package
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image, lang='deu')  # German language

        return text.strip()

    except ImportError:
        logger.warning("pytesseract or Pillow not available for OCR")
        return ""
    except Exception as e:
        logger.error(f"OCR extraction error: {e}")
        raise

def _extract_txt_text(file_path: str) -> str:
    """Extract text from plain text file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()

        return text.strip()

    except Exception as e:
        logger.error(f"Text extraction error: {e}")
        raise

# ============================================
# BATCH DOCUMENT PROCESSING
# ============================================

@app.task(bind=True, name='tasks.batch_process_documents')
def batch_process_documents(self, document_ids: list) -> Dict[str, Any]:
    """
    Process multiple documents in batch

    Args:
        document_ids: List of document UUIDs

    Returns:
        Batch processing result
    """
    import asyncio
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.db_models import Document as DocumentModel

    start_time = datetime.utcnow()

    try:
        logger.info(
            f"[Task {self.request.id}] Batch processing {len(document_ids)} documents"
        )

        successful = 0
        failed = 0
        errors = []

        async def _get_documents():
            engine = create_async_engine(settings.DATABASE_URL, echo=False)
            async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            async with async_session() as session:
                stmt = select(DocumentModel).where(DocumentModel.id.in_([
                    __import__('uuid').UUID(doc_id) for doc_id in document_ids
                ]))
                result = await session.execute(stmt)
                documents = result.scalars().all()

            await engine.dispose()
            return documents

        documents = asyncio.run(_get_documents())

        for doc in documents:
            try:
                # Process each document
                process_document(str(doc.id), doc.file_path, doc.file_type)
                successful += 1
            except Exception as e:
                failed += 1
                errors.append(f"Error processing {doc.id}: {str(e)}")

        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        logger.info(
            f"[Task {self.request.id}] ✓ Batch processing complete: "
            f"{successful} successful, {failed} failed in {duration_ms:.1f}ms"
        )

        return {
            "status": "success" if failed == 0 else "partial",
            "successful": successful,
            "failed": failed,
            "total": len(document_ids),
            "duration_ms": duration_ms,
            "errors": errors,
            "task_id": self.request.id
        }

    except Exception as e:
        logger.error(f"[Task {self.request.id}] ✗ Batch processing error: {e}")
        raise self.retry(exc=e, countdown=120 * (self.request.retries + 1))

# ============================================
# CLEANUP TASKS
# ============================================

@app.task(name='tasks.cleanup_failed_documents')
def cleanup_failed_documents() -> Dict[str, Any]:
    """
    Periodic task to clean up documents that failed processing

    Removes temporary files and updates status
    """
    import asyncio
    from datetime import timedelta
    from sqlalchemy import select, delete
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.db_models import Document as DocumentModel

    logger.info("Running scheduled cleanup of failed documents")

    try:
        async def _cleanup():
            engine = create_async_engine(settings.DATABASE_URL, echo=False)
            async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            async with async_session() as session:
                # Find failed documents older than 24 hours
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                stmt = select(DocumentModel).where(
                    (DocumentModel.status == "failed") &
                    (DocumentModel.created_at < cutoff_time)
                )
                result = await session.execute(stmt)
                failed_docs = result.scalars().all()

                # Remove physical files
                for doc in failed_docs:
                    if os.path.exists(doc.file_path):
                        try:
                            os.remove(doc.file_path)
                            logger.info(f"Deleted failed document file: {doc.file_path}")
                        except Exception as e:
                            logger.warning(f"Failed to delete file {doc.file_path}: {e}")

                # Delete records
                delete_stmt = delete(DocumentModel).where(
                    (DocumentModel.status == "failed") &
                    (DocumentModel.created_at < cutoff_time)
                )
                await session.execute(delete_stmt)
                await session.commit()

            await engine.dispose()
            return len(failed_docs)

        count = asyncio.run(_cleanup())

        logger.info(f"✓ Cleanup completed: removed {count} failed documents")

        return {
            "status": "success",
            "documents_cleaned": count
        }

    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        raise
