import html
from io import BytesIO
from typing import Any, List

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.db import get_db
from app.db.models import BugAnalysis
from app.schemas import (
    BugAnalysisCreate,
    BugAnalysisListResponse,
    BugAnalysisResponse,
    BugAnalysisResult,
)
from app.services.bug_analyzer import bug_analyzer

router = APIRouter()


def _pdf_escape(text: str | None) -> str:
    if text is None:
        return ""
    return html.escape(str(text), quote=False)


def _to_bug_analysis_response(model: BugAnalysis) -> BugAnalysisResponse:
    result = BugAnalysisResult(
        severity=model.severity,
        priority=model.priority,
        component=model.component,
        repro_steps=(model.repro_steps.split("\n") if model.repro_steps else None),
        reasoning=model.reasoning,
        missing_info=(model.missing_info.split("\n") if model.missing_info else None),
    )

    return BugAnalysisResponse(
        id=model.id,
        title=model.title,
        description=model.description,
        environment=model.environment,
        result=result,
        model_version=model.model_version,
        prompt_version=model.prompt_version,
        latency_ms=model.latency_ms,
        schema_valid=model.schema_valid,
        created_at=model.created_at,
    )


@router.post("", response_model=BugAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def create_bug_analysis(
    payload: BugAnalysisCreate,
    db: AsyncSession = Depends(get_db),
) -> BugAnalysisResponse:
    """Analyze a bug report using AI."""

    result = bug_analyzer.analyze(
        title=payload.title,
        description=payload.description,
        environment=payload.environment,
    )

    if not result["success"]:
        severity = None
        priority = None
        component = None
        repro_steps: List[str] = []
        reasoning = f"AI analysis failed: {result.get('error', 'Unknown error')}"
        missing_info: List[str] = []
        raw_response = result.get("raw_response")
        schema_valid = False
    else:
        severity = result.get("severity")
        priority = result.get("priority")
        component = result.get("component")
        repro_steps = result.get("repro_steps", [])
        reasoning = result.get("reasoning")
        missing_info = result.get("missing_info", [])
        raw_response = result.get("raw_response")
        schema_valid = result.get("schema_valid", True)

    instance = BugAnalysis(
        title=payload.title,
        description=payload.description,
        environment=payload.environment,
        severity=severity,
        priority=priority,
        component=component,
        repro_steps="\n".join(repro_steps) if repro_steps else None,
        reasoning=reasoning,
        missing_info="\n".join(missing_info) if missing_info else None,
        raw_response=raw_response,
        model_version=result.get("model_version", "unknown"),
        prompt_version=result.get("prompt_version", "v1.0"),
        latency_ms=result.get("latency_ms", 0),
        schema_valid=schema_valid,
    )

    db.add(instance)
    await db.commit()
    await db.refresh(instance)

    return _to_bug_analysis_response(instance)


@router.get("", response_model=BugAnalysisListResponse)
async def list_bug_analyses(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> BugAnalysisListResponse:
    total_stmt: Select[tuple[int]] = select(func.count(BugAnalysis.id))
    total_result = await db.execute(total_stmt)
    total = total_result.scalar_one()

    stmt: Select[tuple[BugAnalysis]] = (
        select(BugAnalysis)
        .order_by(BugAnalysis.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows: List[BugAnalysis] = list(result.scalars().all())

    return BugAnalysisListResponse(
        items=[_to_bug_analysis_response(row) for row in rows],
        total=total,
    )


@router.get("/{analysis_id}/pdf")
async def export_bug_analysis_pdf(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Export a bug analysis as a PDF report."""
    result = await db.execute(
        select(BugAnalysis).where(BugAnalysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found",
        )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )
    styles = getSampleStyleSheet()
    story: List[Any] = []

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=20,
        textColor=colors.HexColor("#1a1a1a"),
    )

    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=15,
        spaceAfter=10,
        textColor=colors.HexColor("#333333"),
    )

    body_style = ParagraphStyle(
        "CustomBody",
        parent=styles["Normal"],
        fontSize=11,
        spaceAfter=8,
        leading=14,
    )

    story.append(Paragraph("Bug Analysis Report", title_style))
    story.append(
        Paragraph(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 20))

    story.append(Paragraph("Bug Details", heading_style))
    story.append(
        Paragraph(f"<b>Title:</b> {_pdf_escape(analysis.title)}", body_style)
    )
    story.append(
        Paragraph(
            f"<b>Description:</b> {_pdf_escape(analysis.description)}",
            body_style,
        )
    )
    story.append(
        Paragraph(
            f"<b>Environment:</b> {_pdf_escape(analysis.environment or 'Not specified')}",
            body_style,
        )
    )
    story.append(Spacer(1, 15))

    story.append(Paragraph("Analysis Results", heading_style))

    results_data = [
        ["Severity", "Priority", "Component"],
        [
            analysis.severity or "N/A",
            analysis.priority or "N/A",
            analysis.component or "N/A",
        ],
    ]

    results_table = Table(results_data, colWidths=[2 * inch, 2 * inch, 2.5 * inch])
    results_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#374151")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 11),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("TOPPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, 1), colors.white),
                ("FONTSIZE", (0, 1), (-1, 1), 12),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 10),
                ("TOPPADDING", (0, 1), (-1, 1), 10),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#e5e7eb")),
            ]
        )
    )
    story.append(results_table)
    story.append(Spacer(1, 20))

    repro_steps = [
        s.strip()
        for s in (analysis.repro_steps or "").split("\n")
        if s.strip()
    ]
    if repro_steps:
        story.append(Paragraph("Reproduction Steps", heading_style))
        for i, step in enumerate(repro_steps, 1):
            story.append(
                Paragraph(f"{i}. {_pdf_escape(step)}", body_style)
            )
        story.append(Spacer(1, 10))

    if analysis.reasoning:
        story.append(Paragraph("Reasoning", heading_style))
        story.append(Paragraph(_pdf_escape(analysis.reasoning), body_style))
        story.append(Spacer(1, 10))

    missing_lines = [
        s.strip()
        for s in (analysis.missing_info or "").split("\n")
        if s.strip()
    ]
    if missing_lines:
        story.append(Paragraph("Missing Information", heading_style))
        for item in missing_lines:
            story.append(Paragraph(f"• {_pdf_escape(item)}", body_style))
        story.append(Spacer(1, 10))

    story.append(Spacer(1, 30))
    story.append(Paragraph("Analysis Metadata", heading_style))
    metadata_text = (
        f"Model: {analysis.model_version or 'N/A'} | "
        f"Latency: {analysis.latency_ms or 0:.0f}ms | "
        f"Schema Valid: {'Yes' if analysis.schema_valid else 'No'}"
    )
    story.append(Paragraph(_pdf_escape(metadata_text), styles["Normal"]))

    doc.build(story)
    buffer.seek(0)

    safe_title = "".join(
        c if c.isalnum() or c in (" ", "-", "_") else "_" for c in analysis.title[:30]
    )
    filename = f"bug_analysis_{safe_title}_{datetime.now().strftime('%Y%m%d')}.pdf"

    return StreamingResponse(
        iter([buffer.read()]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/{id}", response_model=BugAnalysisResponse)
async def get_bug_analysis(
    id: UUID, db: AsyncSession = Depends(get_db)
) -> BugAnalysisResponse:
    stmt = select(BugAnalysis).where(BugAnalysis.id == id)
    result = await db.execute(stmt)
    instance = result.scalar_one_or_none()

    if instance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bug analysis not found",
        )

    return _to_bug_analysis_response(instance)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bug_analysis(id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    stmt = select(BugAnalysis).where(BugAnalysis.id == id)
    result = await db.execute(stmt)
    instance = result.scalar_one_or_none()

    if instance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bug analysis not found",
        )

    await db.delete(instance)
    await db.commit()

    return None

