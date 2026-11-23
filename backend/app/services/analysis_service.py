"""Create, read and serialise analyses."""
from __future__ import annotations

import hashlib
import logging
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.errors import APIError
from app.ml.fact_checking import claims as claim_picker
from app.ml.fact_checking import verify as evidence_verify
from app.ml.fact_checking.nli import get_nli
from app.ml.fact_checking.providers import GoogleFactCheckProvider, WikipediaProvider
from app.ml.corroboration import check as corroboration
from app.ml.corroboration import consistency, text_match_verdict
from app.ml.corroboration.news_search import get_news_search
from app.ml.image_detection import ela
from app.ml.multimodal import clip_consistency, fusion
from app.ml.text_detection.preprocess import clean_text
from app.ml.url_analysis import fetch as url_fetch
from app.ml.url_analysis import source as url_source
from app.ml.url_analysis.extract import Extracted, decode_html, extract as extract_article
from app.ml.text_detection.service import TextModelUnavailable, choose_detector
from app.models import AnalysisResult, Claim, EvidenceSource, ImagePrediction, NewsSubmission, TextPrediction, User
from app.middleware.rate_limit import limiter
from app.services import files
from app.ml.video_detection import frames as video_frames
from app.ml.video_detection import pipeline as video_pipeline
from app.services.registry import get_text_limitations, get_video_limitations, model_version_id

IMAGE_VERDICT = "Indicators Only"
IMAGE_LIMITATIONS = (
    "These are forensic indicators, not a verdict. Error Level Analysis and metadata cannot reliably tell AI-generated "
    "or edited images from authentic ones, and they say nothing about whether the image is used truthfully in a story. "
    "Verify the image's origin (for example with a reverse image search) before relying on it."
)


def _load_options():
    return (joinedload(AnalysisResult.submission), joinedload(AnalysisResult.model_version),
            joinedload(AnalysisResult.image_prediction), joinedload(AnalysisResult.text_prediction))


def _corroboration(user: User, headline: str | None, language: str, result: dict[str, Any], own_outlet: str | None = None) -> dict[str, Any]:
    """Compare the headline with recent reports by listed news organisations. It never fails the analysis."""
    s = get_settings()
    # A settings file from before this check existed has no such fields: the check then stays off instead of failing the analysis.
    if not getattr(s, "corroboration_enabled", False):
        return corroboration.skipped("disabled", "Comparing headlines with news reports is switched off on this server.")
    if language != "en" or result.get("reason") == "unsupported_language":
        return corroboration.skipped("english_only", "Comparing headlines with news reports works for English headlines only.")
    if not corroboration.clean_query(headline):
        return corroboration.corroborate(headline, get_news_search(), get_nli(), own_outlet)  # answers 'no headline' without any search
    if not limiter.check(f"user:{user.id}", "corroboration", getattr(s, "corroboration_rate_limit_per_minute", 10)):
        return corroboration._result("unavailable", corroboration.clean_query(headline), reason="rate_limited",
                                     message="Too many news comparisons in a short time. Please wait a minute and try again.")
    return corroboration.corroborate(headline, get_news_search(), get_nli(), own_outlet)


def _text_match_strict() -> bool:
    return bool(getattr(get_settings(), "text_match_strict", False))   # a settings file from before this option leaves it off


def _text_match(headline: str | None, text: str, language: str, result: dict[str, Any]) -> dict[str, Any]:
    """Compare the text with its headline. It runs on the server and sends nothing out. It never fails the analysis."""
    # A settings file from before this check existed has no such field: the check then stays on, as it has no network use.
    if not getattr(get_settings(), "text_match_enabled", True):
        return consistency.skipped("disabled", "Comparing the text with its headline is switched off on this server.")
    if language != "en" or result.get("reason") == "unsupported_language":
        return consistency.skipped("english_only", "Comparing the text with its headline works for English only.")
    try:
        return consistency.check(headline, text, get_nli())
    except Exception:  # an inference fault must never fail the analysis
        logging.getLogger(__name__).exception("Headline and text comparison failed")
        return consistency._result("unavailable", reason="model_failed", message="The text could not be compared with the headline.")


def create_text_analysis(db: Session, user: User, headline: str | None, text: str) -> AnalysisResult:
    s = get_settings()
    if len(text) > s.max_text_chars:
        raise APIError(413, "PAYLOAD_TOO_LARGE", f"The text is longer than {s.max_text_chars:,} characters.")
    detector = choose_detector(headline, text)
    try:
        result = detector.analyse(headline, text)
    except TextModelUnavailable as exc:
        raise APIError(503, "MODEL_UNAVAILABLE", str(exc))
    corr = _corroboration(user, headline, detector.language, result)
    match = _text_match(headline, text, detector.language, result)
    # the headline check can lift a verdict; the text-against-headline check then stops a lift when the text is about another story
    result, match = text_match_verdict.apply(corroboration.combine(result, corr), match, strict=_text_match_strict())
    result = {**result, "corroboration": corr, "text_match": match}

    submission = NewsSubmission(
        user_id=user.id, submission_type="text", headline=(headline or "").strip() or None, content=text,
        content_sha256=hashlib.sha256(clean_text(text).encode("utf-8")).hexdigest())
    db.add(submission)
    db.flush()

    analysis = AnalysisResult(
        user_id=user.id, submission_id=submission.id, analysis_type="text", verdict=result["verdict"],
        confidence=result["confidence"], status="completed",
        model_version_id=model_version_id(db, "text_ur" if detector.language == "ur" else "text"),
        details={k: v for k, v in result.items() if k not in ("verdict", "confidence")},
        limitations=get_text_limitations(detector.language), is_demo=False)
    db.add(analysis)
    db.flush()
    if "probabilities" in result:
        db.add(TextPrediction(
            analysis_id=analysis.id, prob_fake=result["probabilities"]["fake"], prob_real=result["probabilities"]["real"],
            token_count=result["token_count"], language=detector.language, top_features=result["explanation"]["toward_fake"]
            + result["explanation"]["toward_real"]))
    db.commit()
    return get_analysis(db, analysis.id)


URL_LIMITATIONS = (
    "The article text was read from the page automatically and may include or leave out parts of it, so the writing-style "
    "result applies to what was extracted, shown below. The website assessment describes the site, not the article: it uses "
    "a small hand-made directory and never calls an unfamiliar website fake. Neither part checks whether the claims are true."
)


def _plain_text_article(text: str) -> Extracted:
    paragraphs = [" ".join(p.split()) for p in text.replace("\r\n", "\n").split("\n\n")]
    body = "\n\n".join(p for p in paragraphs if p)
    return Extracted(text=body, word_count=len(body.split()), method="plain_text", paragraphs=len([p for p in paragraphs if p]))


def create_url_analysis(db: Session, user: User, url: str) -> AnalysisResult:
    """Fetch a news page, read its text, run the text model on it and describe the website it came from."""
    s = get_settings()
    if not s.url_fetch_enabled:
        raise APIError(503, "URL_FETCH_DISABLED", "Reading web addresses is switched off on this server. Paste the article text instead.")
    try:
        fetched = url_fetch.fetch(url)
    except url_fetch.FetchError as exc:
        raise APIError(exc.status, exc.code, exc.message)
    if fetched.content_type == "text/plain":
        article = _plain_text_article(decode_html(fetched.body, fetched.charset))
    else:
        article = extract_article(decode_html(fetched.body, fetched.charset))
    text = article.text[: s.max_text_chars]
    headline = article.headline[:500] if article.headline else None
    source = url_source.assess(fetched.requested_url, fetched.final_url, article)

    if article.word_count < 20:
        result: dict[str, Any] = {
            "verdict": "Unverified", "confidence": None, "reason": "article_not_readable", "language": None,
            "token_count": article.word_count,
            "message": "Not enough article text could be read from this page. It may build its text with JavaScript, sit "
                       "behind a login or subscription, or not be an article. Paste the text instead.",
        }
        detector = None
    else:
        detector = choose_detector(headline, text)
        try:
            result = detector.analyse(headline, text)
        except TextModelUnavailable as exc:
            raise APIError(503, "MODEL_UNAVAILABLE", str(exc))
    if source["assessment"] == "declared_satire":
        result = {**result, "verdict": "Unverified", "confidence": None, "reason": "declared_satire",
                  "message": source["summary"]}
        corr = corroboration.skipped("declared_satire", "The website declares itself satire, so its headlines are not compared with news reports.")
    else:
        own = source["matched"]["name"] if source.get("matched") else None  # a site confirming its own headline proves nothing
        corr = _corroboration(user, headline or article.title, detector.language if detector else "en", result, own)
        result = corroboration.combine(result, corr)
        result = corroboration.combine_publisher(result, source, corr)  # only if the headline check changed nothing and found no difference
    if detector is None:
        match = consistency.skipped("article_not_readable", "No article text could be read, so it could not be compared with the headline.")
    elif source["assessment"] == "declared_satire":
        match = consistency.skipped("declared_satire", "The website declares itself satire, so its text is not compared with its headline.")
    else:
        match = _text_match(headline or article.title, text, detector.language, result)
        if source["assessment"] == "recognised_publisher" and match.get("status") in consistency.MISMATCH:
            match = consistency.same_publisher(match, source["matched"]["name"])   # one publisher wrote both: shown, not decisive
        else:
            result, match = text_match_verdict.apply(result, match, strict=_text_match_strict())
    result = {**result, "corroboration": corr, "text_match": match}

    submission = NewsSubmission(
        user_id=user.id, submission_type="url", headline=headline, content=text or None, source_url=fetched.requested_url,
        content_sha256=hashlib.sha256(clean_text(text).encode("utf-8")).hexdigest() if text else None)
    db.add(submission)
    db.flush()
    language = detector.language if detector else "en"
    details = {k: v for k, v in result.items() if k not in ("verdict", "confidence")}
    details["url"] = {
        "requested": fetched.requested_url, "final": fetched.final_url, "redirects": fetched.redirects,
        "http_status": fetched.status, "content_type": fetched.content_type, "bytes_read": len(fetched.body),
        "truncated": fetched.truncated, "fetch_ms": fetched.elapsed_ms,
        "extraction": {"method": article.method, "words": article.word_count, "paragraphs": article.paragraphs,
                       "title": article.title, "headline": article.headline, "author": article.author,
                       "published": article.published, "site_name": article.site_name, "language": article.language,
                       "notes": article.notes},
    }
    details["source"] = source
    analysis = AnalysisResult(
        user_id=user.id, submission_id=submission.id, analysis_type="url", verdict=result["verdict"],
        confidence=result.get("confidence"), status="completed",
        model_version_id=model_version_id(db, "text_ur" if language == "ur" else "text"), details=details,
        limitations=URL_LIMITATIONS + " " + get_text_limitations(language), is_demo=False)
    db.add(analysis)
    db.flush()
    if "probabilities" in result:
        db.add(TextPrediction(
            analysis_id=analysis.id, prob_fake=result["probabilities"]["fake"], prob_real=result["probabilities"]["real"],
            token_count=result["token_count"], language=language, top_features=result["explanation"]["toward_fake"]
            + result["explanation"]["toward_real"]))
    db.commit()
    return get_analysis(db, analysis.id)


EVIDENCE_LIMITATIONS = (
    "Evidence comes from Wikipedia (an encyclopedia, so recent events are often missing) and, when an API key is set, from "
    "published fact-checks. A passage counts only when it is clearly about the claim and the inference model is at least 85% "
    "sure of its stance. The model compares two short texts; it cannot tell whether the evidence itself is correct. "
    "'Insufficient Evidence' is the normal outcome and does not mean the claim is false."
)


def create_evidence_analysis(db: Session, user: User, text: str, providers=None, nli=None) -> AnalysisResult:
    """Check a claim (or up to five claims picked from a passage) against retrieved evidence."""
    s = get_settings()
    if not s.evidence_enabled:
        raise APIError(503, "EVIDENCE_DISABLED", "Evidence checking is switched off on this server.")
    text = " ".join(text.split())
    picked = [text] if len(text.split()) <= 45 else claim_picker.extract_claims(text)
    if not picked:
        raise APIError(422, "NO_CLAIMS_FOUND", "No checkable factual statement was found in this text. Paste one specific claim, for example a sentence with a name, a place or a number.")
    providers = providers or [WikipediaProvider(), GoogleFactCheckProvider(s.google_fact_check_api_key)]
    nli = nli or get_nli()
    results = [evidence_verify.verify_claim(c, providers, nli) for c in picked]
    verdict = evidence_verify.overall_verdict(results)

    submission = NewsSubmission(user_id=user.id, submission_type="evidence", headline=picked[0][:500] if len(picked) == 1 else None,
                                content=text, content_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest())
    db.add(submission)
    db.flush()
    details = {"claims": results, "claims_picked_automatically": len(picked) > 1 or picked[0] != text,
               "stance_model": results[0]["stance_model"], "rules": results[0]["rules"],
               "reason": "evidence_checked", "message": results[0]["reason"] if len(results) == 1 else None}
    analysis = AnalysisResult(user_id=user.id, submission_id=submission.id, analysis_type="evidence", verdict=verdict, confidence=None,
                              status="completed", model_version_id=model_version_id(db, "evidence"), details=details,
                              limitations=EVIDENCE_LIMITATIONS, is_demo=False)
    db.add(analysis)
    db.flush()
    for r in results:
        claim = Claim(analysis_id=analysis.id, claim_text=r["claim"][:5000], verdict=r["verdict"])
        db.add(claim)
        db.flush()
        for ev in r["evidence"]:
            db.add(EvidenceSource(claim_id=claim.id, url=(ev["url"] or "")[:1000], title=(ev["title"] or None) and ev["title"][:500],
                                  published_at=None, stance=(ev["stance"] if ev["stance"] in ("supports", "contradicts") else "related")[:20],
                                  relevance=ev["relevance"]))
    db.commit()
    return get_analysis(db, analysis.id)


MULTIMODAL_LIMITATIONS = (
    "The verdict follows a fixed, written rule (shown below), not a learned model. The text result is a writing-style reading, the "
    "image result is forensic indicators only, and the consistency check shows whether a caption resembles the image, using thresholds "
    "measured on everyday Flickr photos rather than news. About one in ten matching captions is still flagged as a mismatch. A mismatch "
    "or a match says nothing about whether the photo is from the event the text describes, or whether either is true."
)


def create_multimodal_analysis(db: Session, user: User, data: bytes | None, original_filename: str | None,
                               headline: str | None, text: str | None, clip=None) -> AnalysisResult:
    """An image and/or text analysed together. Each modality is analysed on its own, then combined by a fixed rule."""
    s = get_settings()
    text = (text or "").strip() or None
    headline = (headline or "").strip() or None
    if data is None and not (text or headline):
        raise APIError(422, "NOTHING_TO_ANALYSE", "Give an image, some text, or both.")
    if text and len(text) > s.max_text_chars:
        raise APIError(413, "PAYLOAD_TOO_LARGE", f"The text is longer than {s.max_text_chars:,} characters.")

    image_result = None
    if data is not None:
        try:
            image_result = ela.analyse(data, s.max_image_pixels)
        except ela.ImageRejected as exc:
            raise APIError(415, "UNSUPPORTED_MEDIA_TYPE", str(exc))

    text_result = detector = None
    text_status = "not_provided"
    if text or headline:
        detector = choose_detector(headline, text or "")
        try:
            text_result = detector.analyse(headline, text or "")
        except TextModelUnavailable as exc:
            raise APIError(503, "MODEL_UNAVAILABLE", str(exc))
        text_status = "analysed" if "probabilities" in text_result else text_result.get("reason", "declined")
    consistency = clip_consistency.assess(data, headline, text, clip)
    fused = fusion.fuse(text_result["verdict"] if text_result else None, data is not None, consistency.get("label"))

    stored = files.save_bytes("images", data, ela.extension_for(image_result.image_format)) if data is not None else None
    heatmap = files.save_bytes("heatmaps", image_result.heatmap_png, "png") if image_result else None
    submission = NewsSubmission(user_id=user.id, submission_type="multimodal", headline=headline, content=text, media_filename=stored,
                                original_filename=files.safe_display_name(original_filename) if data is not None else None,
                                content_sha256=hashlib.sha256((data or b"") + clean_text(text or "").encode("utf-8")).hexdigest())
    db.add(submission)
    db.flush()
    image_details = None
    if image_result:
        image_details = {"observations": image_result.observations, "metadata": image_result.metadata,
                         "image": {"width": image_result.width, "height": image_result.height, "format": image_result.image_format},
                         "ela": {"mean": image_result.ela_mean, "max": image_result.ela_max, "block_cv": image_result.ela_block_cv,
                                 "quality": ela.ELA_QUALITY, "grid": ela.GRID},
                         "map_note": "The map shows JPEG recompression error. It is not an AI attention map."}
    details = {
        "modalities": {"text": text_status, "image": "analysed" if image_result else "not_provided", "consistency": consistency["status"]},
        "text_result": text_result, "image_result": image_details, "consistency": consistency, "fusion": fused,
        "reason": "fusion_rule", "message": "; ".join(fused["notes"]) or None,
    }
    mv_module = "multimodal"
    language = detector.language if detector else "en"
    analysis = AnalysisResult(
        user_id=user.id, submission_id=submission.id, analysis_type="multimodal", verdict=fused["verdict"],
        confidence=(text_result or {}).get("confidence") if fused["verdict"] in ("Likely Fake", "Likely Real") else None,
        status="completed", model_version_id=model_version_id(db, mv_module), details=details,
        limitations=MULTIMODAL_LIMITATIONS + (" " + get_text_limitations(language) if text_result else ""), is_demo=False)
    db.add(analysis)
    db.flush()
    if text_result and "probabilities" in text_result:
        db.add(TextPrediction(analysis_id=analysis.id, prob_fake=text_result["probabilities"]["fake"], prob_real=text_result["probabilities"]["real"],
                              token_count=text_result["token_count"], language=language,
                              top_features=text_result["explanation"]["toward_fake"] + text_result["explanation"]["toward_real"]))
    if image_result:
        db.add(ImagePrediction(analysis_id=analysis.id, width=image_result.width, height=image_result.height, image_format=image_result.image_format,
                               ela_mean=image_result.ela_mean, ela_max=image_result.ela_max, ela_block_cv=image_result.ela_block_cv,
                               heatmap_filename=heatmap, metadata_summary=image_result.metadata))
    db.commit()
    return get_analysis(db, analysis.id)


def create_image_analysis(db: Session, user: User, data: bytes, original_filename: str | None) -> AnalysisResult:
    s = get_settings()
    try:
        result = ela.analyse(data, s.max_image_pixels)
    except ela.ImageRejected as exc:
        raise APIError(415, "UNSUPPORTED_MEDIA_TYPE", str(exc))

    stored = files.save_bytes("images", data, ela.extension_for(result.image_format))
    heatmap = files.save_bytes("heatmaps", result.heatmap_png, "png")
    submission = NewsSubmission(user_id=user.id, submission_type="image", media_filename=stored,
                                original_filename=files.safe_display_name(original_filename),
                                content_sha256=hashlib.sha256(data).hexdigest())
    db.add(submission)
    db.flush()
    analysis = AnalysisResult(
        user_id=user.id, submission_id=submission.id, analysis_type="image", verdict=IMAGE_VERDICT, confidence=None,
        status="completed", model_version_id=model_version_id(db, "image"),
        details={"observations": result.observations, "metadata": result.metadata,
                 "image": {"width": result.width, "height": result.height, "format": result.image_format},
                 "ela": {"mean": result.ela_mean, "max": result.ela_max, "block_cv": result.ela_block_cv,
                         "quality": ela.ELA_QUALITY, "grid": ela.GRID},
                 "map_note": "The map shows JPEG recompression error. It is not an AI attention map."},
        limitations=IMAGE_LIMITATIONS, is_demo=False)
    db.add(analysis)
    db.flush()
    db.add(ImagePrediction(analysis_id=analysis.id, width=result.width, height=result.height, image_format=result.image_format,
                           ela_mean=result.ela_mean, ela_max=result.ela_max, ela_block_cv=result.ela_block_cv,
                           heatmap_filename=heatmap, metadata_summary=result.metadata))
    db.commit()
    return get_analysis(db, analysis.id)


def create_video_analysis(db: Session, user: User, data: bytes, original_filename: str | None) -> AnalysisResult:
    """Frame-based analysis of a video: frames and faces are measured, scored by the frame classifier when it is available,
    and summarised over time. The video and a thumbnail of each sampled frame are kept so the person can look at them."""
    s = get_settings()
    try:
        details, info, thumbs, verdict = video_pipeline.analyse(data, s.max_video_seconds, s.video_sample_frames)
    except video_frames.VideoRejected as exc:
        raise (APIError(413, "PAYLOAD_TOO_LARGE", str(exc)) if exc.too_large else APIError(415, "UNSUPPORTED_MEDIA_TYPE", str(exc)))
    except video_pipeline.Busy as exc:
        raise APIError(503, "BUSY", str(exc))
    except RuntimeError as exc:
        raise APIError(503, "MODEL_UNAVAILABLE", str(exc))

    stored = files.save_bytes("videos", data, info.extension)
    for entry in details["frames"]:
        jpeg = thumbs[entry.pop("thumbnail")]
        entry["file"] = files.save_bytes("video_frames", jpeg, "jpg") if jpeg else None
    submission = NewsSubmission(user_id=user.id, submission_type="video", media_filename=stored,
                                original_filename=files.safe_display_name(original_filename),
                                content_sha256=hashlib.sha256(data).hexdigest())
    db.add(submission)
    db.flush()
    analysis = AnalysisResult(user_id=user.id, submission_id=submission.id, analysis_type="video", verdict=verdict, confidence=None,
                              status="completed", model_version_id=model_version_id(db, "video"), details=details,
                              limitations=get_video_limitations(), is_demo=False)
    db.add(analysis)
    db.commit()
    return get_analysis(db, analysis.id)


def video_frame_file(row: AnalysisResult, index: int) -> str:
    frames = (row.details or {}).get("frames") or []
    if row.analysis_type != "video" or not (0 <= index < len(frames)) or not frames[index].get("file"):
        raise APIError(404, "NOT_FOUND", "This frame is not available.")
    return frames[index]["file"]


def get_analysis(db: Session, analysis_id: int) -> AnalysisResult:
    row = db.query(AnalysisResult).options(*_load_options()).filter(AnalysisResult.id == analysis_id).one_or_none()
    if row is None:
        raise APIError(404, "NOT_FOUND", "Analysis not found.")
    return row


def get_owned_analysis(db: Session, user: User, analysis_id: int) -> AnalysisResult:
    """Return the analysis only to its owner. Other users, including administrators, get a plain 404: submitted
    articles and images are private, and admins work from aggregate statistics."""
    row = get_analysis(db, analysis_id)
    if row.user_id != user.id:
        raise APIError(404, "NOT_FOUND", "Analysis not found.")
    return row


def list_analyses(db: Session, user: User, page: int, page_size: int, analysis_type: str | None,
                  verdict: str | None, query: str | None) -> tuple[list[AnalysisResult], int]:
    q = db.query(AnalysisResult).filter(AnalysisResult.user_id == user.id)
    if analysis_type:
        q = q.filter(AnalysisResult.analysis_type == analysis_type)
    if verdict:
        q = q.filter(AnalysisResult.verdict == verdict)
    if query:
        like = f"%{query.strip()}%"
        q = q.join(NewsSubmission, NewsSubmission.id == AnalysisResult.submission_id).filter(
            or_(NewsSubmission.headline.ilike(like), NewsSubmission.content.ilike(like),
                NewsSubmission.original_filename.ilike(like), NewsSubmission.source_url.ilike(like)))
    total = q.with_entities(func.count(AnalysisResult.id)).scalar() or 0
    rows = (q.options(*_load_options()).order_by(AnalysisResult.created_at.desc(), AnalysisResult.id.desc())
            .offset((page - 1) * page_size).limit(page_size).all())
    return rows, total


def delete_analysis(db: Session, row: AnalysisResult) -> None:
    sub = row.submission
    if row.image_prediction:
        files.remove_media("heatmaps", row.image_prediction.heatmap_filename)
    files.remove_media("images", sub.media_filename if sub and row.analysis_type != "video" else None)
    if row.analysis_type == "video":
        files.remove_media("videos", sub.media_filename if sub else None)
        for fr in (row.details or {}).get("frames", []):
            files.remove_media("video_frames", fr.get("file"))
    db.delete(row)
    if sub is not None:
        db.delete(sub)
    db.commit()


def _public_details(row: AnalysisResult) -> Any:
    """Details as sent to the client. Stored file names stay on the server: a video's frame images are fetched by index."""
    if row.analysis_type != "video" or not row.details:
        return row.details
    d = dict(row.details)
    d["frames"] = [{**{k: v for k, v in f.items() if k != "file"}, "has_image": bool(f.get("file"))} for f in d.get("frames", [])]
    return d


def serialise(row: AnalysisResult, include_details: bool = True) -> dict[str, Any]:
    sub = row.submission
    mv = row.model_version
    headline = sub.headline if sub else None
    if not headline and sub and sub.content:
        headline = sub.content[:120] + ("..." if len(sub.content) > 120 else "")
    if not headline and sub and sub.source_url:
        headline = sub.source_url
    return {
        "id": row.id, "analysis_type": row.analysis_type, "verdict": row.verdict, "confidence": row.confidence,
        "status": row.status, "headline": headline,
        "source_filename": sub.original_filename if sub else None,
        "source_url": sub.source_url if sub else None,
        "submitted_text": sub.content if (include_details and sub and row.analysis_type in ("text", "url", "evidence", "multimodal")) else None,
        "created_at": row.created_at,
        "model": {"module": mv.module, "name": mv.name, "version": mv.version, "status": mv.status} if mv else None,
        "details": (_public_details(row) if include_details else None),
        "limitations": row.limitations if include_details else None,
        "is_demo": row.is_demo,
        "has_heatmap": bool(row.image_prediction and row.image_prediction.heatmap_filename),
    }
