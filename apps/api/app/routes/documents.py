import os
from datetime import datetime
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
    # Ensure upload directory exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Save file
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    async with aiofiles.open(file_path, "wb") as out_file:
        content = await file.read()
        await out_file.write(content)

    now = datetime.utcnow()
    file_size = os.path.getsize(file_path)

    # Determine file_type from extension
    _, ext = os.path.splitext(file.filename)
    file_type = ext.lstrip(".").lower() or "txt"

    instance = Document(
        filename=file.filename,
        file_type=file_type,
        file_size=file_size,
        status="uploaded",
        chunk_count=0,
        created_at=now,
        updated_at=now,
    )

    db.add(instance)
    await db.commit()
    await db.refresh(instance)

    return _to_document_response(instance)


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


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    stmt = select(Document).where(Document.id == id)
    result = await db.execute(stmt)
    instance = result.scalar_one_or_none()

    if instance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    await db.delete(instance)
    await db.commit()

    return None

