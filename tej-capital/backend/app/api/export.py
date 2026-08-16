"""API routes for data exports: CSV, PDF tearsheet, and DDQ pack."""
from calendar import monthrange
from datetime import date

from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import select

from app.api.deps import SessionDep
from app.domain.audit import CorrectionLedger
from app.domain.metrics import MetricSnapshot
from app.export.csv_exports import audit_csv, returns_csv, trades_csv
from app.export.ddq_pack import build as build_ddq_pack
from app.export.tearsheet_pdf import render_html, render_pdf
from app.services.snapshot import _load_series, compute_tearsheet

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/returns.csv")
async def export_returns_csv(db: SessionDep, response: Response):
    """Export composite returns as CSV."""
    returns, _trades, _n = await _load_series(db, "composite", None)

    csv_data = returns_csv(returns)
    response.media_type = "text/csv"
    response.headers["Content-Disposition"] = "attachment; filename=returns.csv"
    return Response(content=csv_data, media_type="text/csv")


@router.get("/trades.csv")
async def export_trades_csv(db: SessionDep, response: Response):
    """Export trades as CSV."""
    _returns, trades, _n = await _load_series(db, "composite", None)

    csv_data = trades_csv(trades)
    response.media_type = "text/csv"
    response.headers["Content-Disposition"] = "attachment; filename=trades.csv"
    return Response(content=csv_data, media_type="text/csv")


@router.get("/audit.csv")
async def export_audit_csv(db: SessionDep, response: Response):
    """Export audit trail of corrections as CSV."""
    corrections = (await db.execute(
        select(CorrectionLedger).order_by(CorrectionLedger.corrected_at.desc())
    )).scalars().all()

    audit_records = [
        {
            "timestamp": c.corrected_at.isoformat() if hasattr(c.corrected_at, "isoformat") else str(c.corrected_at),
            "table": c.table_name,
            "row_id": str(c.row_id),
            "superseded_by_row_id": str(c.superseded_by_row_id),
            "reason": c.reason,
        }
        for c in corrections
    ]

    csv_data = audit_csv(audit_records)
    response.media_type = "text/csv"
    response.headers["Content-Disposition"] = "attachment; filename=audit.csv"
    return Response(content=csv_data, media_type="text/csv")


@router.get("/tearsheet/{year}/{month}.pdf")
async def export_tearsheet_pdf(
    db: SessionDep,
    year: int,
    month: int,
    response: Response = None,
):
    """Export tearsheet as PDF if Playwright is available, else as HTML.

    Returns PDF bytes if Playwright is installed, otherwise returns HTML
    with a warning header. The caller can check for the X-Tej-Warning header
    to know whether they got PDF or HTML.
    """
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])

    # Try to load frozen snapshot first
    frozen = (await db.execute(
        select(MetricSnapshot).where(
            MetricSnapshot.scope == "composite",
            MetricSnapshot.account_id.is_(None),
            MetricSnapshot.as_of_date >= start,
            MetricSnapshot.as_of_date <= end,
        ).order_by(MetricSnapshot.as_of_date.desc())
    )).scalars().first()

    if frozen is not None:
        tearsheet = frozen.metrics
    else:
        tearsheet = await compute_tearsheet(db, "composite", None)

    # Try to render as PDF first
    pdf_bytes = await render_pdf(tearsheet)

    if pdf_bytes is not None:
        response.media_type = "application/pdf"
        response.headers["Content-Disposition"] = f"attachment; filename=tearsheet-{year}-{month:02d}.pdf"
        return Response(content=pdf_bytes, media_type="application/pdf")

    # Fall back to HTML
    html_content = render_html(tearsheet)
    response.media_type = "text/html"
    response.headers["X-Tej-Warning"] = "install Chromium to enable PDF export"
    response.headers["Content-Disposition"] = f"inline; filename=tearsheet-{year}-{month:02d}.html"
    return Response(content=html_content, media_type="text/html")


@router.get("/ddq.zip")
async def export_ddq_pack(
    db: SessionDep,
    response: Response,
    year: int = Query(None),
    month: int = Query(None),
):
    """Export DDQ (Due Diligence Questionnaire) pack as ZIP.

    Includes strategy summary, policy document, performance metrics,
    attribution analysis, and audit trail of corrections.

    Optional year/month parameters to include a frozen snapshot for that period.
    """
    # Load current tearsheet
    if year is not None and month is not None:
        start = date(year, month, 1)
        end = date(year, month, monthrange(year, month)[1])
        frozen = (await db.execute(
            select(MetricSnapshot).where(
                MetricSnapshot.scope == "composite",
                MetricSnapshot.account_id.is_(None),
                MetricSnapshot.as_of_date >= start,
                MetricSnapshot.as_of_date <= end,
            ).order_by(MetricSnapshot.as_of_date.desc())
        )).scalars().first()
        tearsheet = frozen.metrics if frozen else await compute_tearsheet(db, "composite", None)
    else:
        tearsheet = await compute_tearsheet(db, "composite", None)

    # Load corrections/audit trail
    corrections = (await db.execute(
        select(CorrectionLedger).order_by(CorrectionLedger.corrected_at)
    )).scalars().all()
    corrections_list = [
        {
            "timestamp": c.corrected_at.isoformat() if hasattr(c.corrected_at, "isoformat") else str(c.corrected_at),
            "table": c.table_name,
            "reason": c.reason,
        }
        for c in corrections
    ]

    # Build ZIP
    zip_bytes = build_ddq_pack(
        tearsheet=tearsheet,
        corrections=corrections_list,
        policy_doc="# Trading Strategy Policy\n\nNo policy document configured.",
        attribution={},
    )

    response.media_type = "application/zip"
    response.headers["Content-Disposition"] = "attachment; filename=ddq-pack.zip"
    return Response(content=zip_bytes, media_type="application/zip")
