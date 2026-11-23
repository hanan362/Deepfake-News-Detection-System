"""Run analyses and read the signed-in user's history."""
from __future__ import annotations

from starlette.concurrency import run_in_threadpool
from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.errors import APIError
from app.db.session import get_db
from app.models import User
from app.middleware.rate_limit import limiter
from app.schemas.analysis import AnalysisOut, AnalysisPage, EvidenceRequest, TextAnalysisRequest, UrlAnalysisRequest
from app.services import analysis_service as svc
from app.services import files
from app.services.reports import build_report
from app.utils.audit import audit

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/text", response_model=AnalysisOut, status_code=201, summary="Analyse the writing of a news article")
def analyse_text(body: TextAnalysisRequest, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = svc.create_text_analysis(db, user, body.headline, body.text)
    audit(db, request, user, "analysis.text", "analysis", row.id, {"verdict": row.verdict})
    return svc.serialise(row)


@router.post("/url", response_model=AnalysisOut, status_code=201,
             summary="Read a news article from its web address, analyse its text and describe its website")
def analyse_url(body: UrlAnalysisRequest, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = get_settings()
    if not limiter.check(f"user:{user.id}", "url_fetch", s.url_fetch_rate_limit_per_minute):
        raise APIError(429, "RATE_LIMITED", "Too many web addresses in a short time. Please wait a minute and try again.")
    row = svc.create_url_analysis(db, user, body.url)
    # Only the host is written to the audit trail: the address itself can carry tokens in its query string.
    audit(db, request, user, "analysis.url", "analysis", row.id, {"verdict": row.verdict, "host": (row.details or {}).get("source", {}).get("host")})
    return svc.serialise(row)


@router.post("/evidence", response_model=AnalysisOut, status_code=201,
             summary="Check a claim against Wikipedia and published fact-checks")
def analyse_evidence(body: EvidenceRequest, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = get_settings()
    if not limiter.check(f"user:{user.id}", "evidence", s.url_fetch_rate_limit_per_minute):
        raise APIError(429, "RATE_LIMITED", "Too many evidence checks in a short time. Please wait a minute and try again.")
    row = svc.create_evidence_analysis(db, user, body.text)
    audit(db, request, user, "analysis.evidence", "analysis", row.id, {"verdict": row.verdict})
    return svc.serialise(row)


@router.post("/multimodal", response_model=AnalysisOut, status_code=201,
             summary="An image and its text analysed together (either may be left out)")
async def analyse_multimodal(request: Request, file: UploadFile | None = File(None), text: str | None = Form(None, max_length=60000),
                             headline: str | None = Form(None, max_length=500), user: User = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    data = await files.read_limited(file, get_settings().max_image_mb * 1024 * 1024) if file is not None and file.filename else None
    # CLIP can take minutes to download and load on first use. Run it in a worker thread: calling it here would freeze the
    # event loop and the whole API (login, history, health) would stop answering until it finished.
    row = await run_in_threadpool(svc.create_multimodal_analysis, db, user, data, file.filename if file is not None else None, headline, text)
    audit(db, request, user, "analysis.multimodal", "analysis", row.id, {"verdict": row.verdict})
    return svc.serialise(row)


@router.post("/image", response_model=AnalysisOut, status_code=201, summary="Forensic indicators for an image (ELA + metadata)")
async def analyse_image(request: Request, file: UploadFile = File(...), user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    data = await files.read_limited(file, get_settings().max_image_mb * 1024 * 1024)
    row = await run_in_threadpool(svc.create_image_analysis, db, user, data, file.filename)
    audit(db, request, user, "analysis.image", "analysis", row.id)
    return svc.serialise(row)


@router.post("/video", response_model=AnalysisOut, status_code=201, summary="Frame-based analysis of a video")
async def analyse_video(request: Request, file: UploadFile = File(...), user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    data = await files.read_limited(file, get_settings().max_video_mb * 1024 * 1024)
    row = await run_in_threadpool(svc.create_video_analysis, db, user, data, file.filename)
    audit(db, request, user, "analysis.video", "analysis", row.id, {"verdict": row.verdict})
    return svc.serialise(row)


@router.get("", response_model=AnalysisPage, summary="History of your analyses")
def history(page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100),
            analysis_type: str | None = Query(None, pattern="^(text|image|video|multimodal|url|evidence)$"),
            verdict: str | None = Query(None, max_length=60), q: str | None = Query(None, max_length=100),
            user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows, total = svc.list_analyses(db, user, page, page_size, analysis_type, verdict, q)
    return AnalysisPage(items=[svc.serialise(r, include_details=False) for r in rows], total=total, page=page, page_size=page_size)


@router.get("/{analysis_id}", response_model=AnalysisOut, summary="One analysis with full details")
def read_analysis(analysis_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.serialise(svc.get_owned_analysis(db, user, analysis_id))


@router.delete("/{analysis_id}", status_code=204, summary="Delete an analysis and its files")
def remove_analysis(analysis_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = svc.get_owned_analysis(db, user, analysis_id)
    svc.delete_analysis(db, row)
    audit(db, request, user, "analysis.delete", "analysis", analysis_id)
    return Response(status_code=204)


@router.get("/{analysis_id}/report.pdf", summary="Download a PDF report")
def report(analysis_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = svc.get_owned_analysis(db, user, analysis_id)
    owner = row.user
    pdf = build_report(row, owner)
    audit(db, request, user, "analysis.report", "analysis", analysis_id)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="analysis-{analysis_id}.pdf"',
                             "Cache-Control": "private, no-store"})


@router.get("/{analysis_id}/heatmap", summary="Error Level Analysis map (images)")
def heatmap(analysis_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = svc.get_owned_analysis(db, user, analysis_id)
    if not row.image_prediction or not row.image_prediction.heatmap_filename:
        raise APIError(404, "NOT_FOUND", "This analysis has no map.")
    return FileResponse(files.resolve_media("heatmaps", row.image_prediction.heatmap_filename), media_type="image/png",
                        headers={"Cache-Control": "private, no-store"})


@router.get("/{analysis_id}/frames/{index}", summary="A sampled frame of an analysed video, with the face box")
def video_frame(analysis_id: int, index: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = svc.get_owned_analysis(db, user, analysis_id)
    return FileResponse(files.resolve_media("video_frames", svc.video_frame_file(row, index)), media_type="image/jpeg",
                        headers={"Cache-Control": "private, no-store"})


@router.get("/{analysis_id}/video", summary="The video you uploaded")
def original_video(analysis_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = svc.get_owned_analysis(db, user, analysis_id)
    sub = row.submission
    if not sub or not sub.media_filename or row.analysis_type != "video":
        raise APIError(404, "NOT_FOUND", "This analysis has no video.")
    media_type = {"mp4": "video/mp4", "mov": "video/quicktime", "webm": "video/webm", "avi": "video/x-msvideo"}.get(sub.media_filename.rsplit(".", 1)[-1], "application/octet-stream")
    return FileResponse(files.resolve_media("videos", sub.media_filename), media_type=media_type,
                        headers={"Cache-Control": "private, no-store", "Content-Disposition": "inline"})


@router.get("/{analysis_id}/image", summary="The image you uploaded")
def original_image(analysis_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = svc.get_owned_analysis(db, user, analysis_id)
    sub = row.submission
    if not sub or not sub.media_filename or row.analysis_type not in ("image", "multimodal"):
        raise APIError(404, "NOT_FOUND", "This analysis has no image.")
    media_type = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(sub.media_filename.rsplit(".", 1)[-1], "application/octet-stream")
    return FileResponse(files.resolve_media("images", sub.media_filename), media_type=media_type,
                        headers={"Cache-Control": "private, no-store", "Content-Disposition": "inline"})
