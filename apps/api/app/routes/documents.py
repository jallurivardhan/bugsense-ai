import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List
from uuid import UUID

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.db.models import Document
from app.schemas import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.services.rag_service import rag_service

UPLOAD_DIR = "data/uploads"

router = APIRouter()


def _to_document_response(model: Document) -> DocumentResponse:
    return DocumentResponse(
        id=model.id,
        filename=model.filename,
        file_type=model.file_type,
        file_size=model.file_size,
        status=model.status,
        chunk_count=model.chunk_count,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    """Upload and index a document."""
    # Validate file type
    file_ext = os.path.splitext(file.filename)[1].lower()
    allowed_extensions = {".pdf", ".txt", ".md", ".docx"}

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=(
                f"File type {file_ext} not supported. "
                f"Allowed: {', '.join(sorted(allowed_extensions))}"
            ),
        )

    # Save file
    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid.uuid4())
    file_path = upload_dir / f"{file_id}{file_ext}"

    content = await file.read()
    file_size = len(content)

    async with aiofiles.open(file_path, "wb") as out_file:
        await out_file.write(content)

    now = datetime.utcnow()

    # Create database record with status "processing"
    db_document = Document(
        filename=file.filename,
        file_type=file_ext.replace(".", ""),
        file_size=file_size,
        status="processing",
        chunk_count=0,
        created_at=now,
        updated_at=now,
    )

    db.add(db_document)
    await db.commit()
    await db.refresh(db_document)

    # Index document with RAG
    try:
        result = rag_service.index_document(
            document_id=str(db_document.id),
            file_path=str(file_path),
            filename=file.filename,
        )

        if result["success"]:
            db_document.status = "indexed"
            db_document.chunk_count = result["chunks"]
        else:
            db_document.status = "failed"
            # Log error for observability
            print(f"Indexing failed: {result.get('error')}")

        db_document.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(db_document)
    except Exception as exc:  # defensive
        db_document.status = "failed"
        db_document.updated_at = datetime.utcnow()
        await db.commit()
        print(f"RAG indexing error: {exc}")

    return DocumentUploadResponse(
        id=db_document.id,
        filename=db_document.filename,
        status=db_document.status,
        chunks=db_document.chunk_count or 0,
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    total_stmt: Select[tuple[int]] = select(func.count(Document.id))
    total_result = await db.execute(total_stmt)
    total = total_result.scalar_one()

    stmt: Select[tuple[Document]] = (
        select(Document)
        .order_by(Document.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows: List[Document] = list(result.scalars().all())

    return DocumentListResponse(
        items=[_to_document_response(row) for row in rows],
        total=total,
    )


@router.get("/{id}", response_model=DocumentResponse)
async def get_document(
    id: UUID, db: AsyncSession = Depends(get_db)
) -> DocumentResponse:
    stmt = select(Document).where(Document.id == id)
    result = await db.execute(stmt)
    instance = result.scalar_one_or_none()

    if instance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return _to_document_response(instance)


@router.delete("/{document_id}")
async def delete_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a document and its index."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete from vector store
    try:
        rag_service.delete_document(str(document_id))
    except Exception as exc:
        print(f"Error deleting from vector store: {exc}")

    # Delete file from disk
    if getattr(document, "file_path", None) and os.path.exists(document.file_path):
        os.remove(document.file_path)

    # Delete from database
    await db.delete(document)
    await db.commit()

    return {"status": "deleted", "id": str(document_id)}

