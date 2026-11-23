"""PDF report for a single analysis (ReportLab)."""
from __future__ import annotations

import io
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.config import get_settings
from app.models import AnalysisResult, User
from app.services import files


def _safe(text: object, limit: int | None = None) -> str:
    """Built-in PDF fonts only cover Latin-1. Replace other characters instead of printing broken boxes."""
    s = str(text if text is not None else "")
    if limit and len(s) > limit:
        s = s[:limit] + "..."
    return escape(s.encode("latin-1", "replace").decode("latin-1"))


def build_report(row: AnalysisResult, owner: User) -> bytes:
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Title"], fontSize=18, spaceAfter=6)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=12, spaceBefore=10, spaceAfter=4)
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=9.5, leading=13)
    small = ParagraphStyle("small", parent=body, fontSize=8, textColor=colors.HexColor("#555555"))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                            title=f"Analysis report #{row.id}", author=get_settings().app_name)
    story: list = [Paragraph(_safe(get_settings().app_name), small), Paragraph(f"Analysis report #{row.id}", h1)]

    mv = row.model_version
    sub = row.submission
    meta = [
        ["Type", _safe(row.analysis_type)],
        ["Result", _safe(row.verdict)],
        ["Model confidence", _safe(f"{row.confidence:.0%}") if row.confidence is not None else "n/a"],
        ["Model", _safe(f"{mv.name} {mv.version} ({mv.status})") if mv else "n/a"],
        ["Created (UTC)", _safe(row.created_at.strftime("%Y-%m-%d %H:%M"))],
        ["Requested by", _safe(owner.username)],
    ]
    if sub and sub.original_filename:
        meta.append(["File", _safe(sub.original_filename)])
    table = Table([[Paragraph(f"<b>{k}</b>", body), Paragraph(v, body)] for k, v in meta], colWidths=[40 * mm, 130 * mm])
    table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CCCCCC")),
                               ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F3F4F6")),
                               ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story += [table, Spacer(1, 4)]

    d = row.details or {}
    if sub and sub.headline:
        story += [Paragraph("Headline", h2), Paragraph(_safe(sub.headline, 500), body)]
    if row.analysis_type in ("text", "url"):
        if row.analysis_type == "url":
            u = d.get("url") or {}
            ex = u.get("extraction") or {}
            story += [Paragraph("Web address", h2), Paragraph(_safe(sub.source_url if sub else u.get("requested"), 300), body)]
            if u.get("final") and u.get("final") != (sub.source_url if sub else None):
                story.append(Paragraph("Read from: " + _safe(u["final"], 300), body))
            story.append(Paragraph(
                f"Page read {_safe(u.get('bytes_read'))} bytes{' (cut at the size limit)' if u.get('truncated') else ''}; "
                f"{_safe(ex.get('words'))} words of article text extracted by the {_safe(ex.get('method'))} method. "
                f"Declared author: {_safe(ex.get('author') or 'none found')}. Declared date: {_safe(ex.get('published') or 'none found')}.", body))
            src = d.get("source") or {}
            if src:
                story += [Paragraph("The website", h2), Paragraph(f"<b>{_safe(src.get('label'))}.</b> {_safe(src.get('summary'))}", body)]
                for sig in src.get("signals", []):
                    story.append(Paragraph("&bull; " + _safe(f"{sig['label']} ({sig['effect']}): {sig['detail']}"), small))
                story.append(Paragraph("Not checked: " + _safe(" ".join(src.get("not_checked", []))), small))
                story.append(Paragraph(_safe(src.get("caveat")), small))
        if sub and sub.content:
            story += [Paragraph("Article text (excerpt)" if row.analysis_type == "url" else "Submitted text (excerpt)", h2),
                      Paragraph(_safe(sub.content, 600), body)]
        if d.get("message"):
            story += [Paragraph("Why this result" if row.verdict != "Unverified" else "Why no verdict was given", h2), Paragraph(_safe(d["message"]), body)]
        corr = d.get("corroboration")
        if corr:
            story += [Paragraph("Headline compared with news reports", h2),
                      Paragraph(f"<b>{_safe(corr.get('status', '').replace('_', ' ').capitalize())}.</b> {_safe(corr.get('message'), 500)}", body)]
            if corr.get("query"):
                story.append(Paragraph(_safe("Searched for: " + corr["query"], 300), small))
            for o in corr.get("outlets", []):
                story.append(Paragraph("&bull; " + _safe(f"{o['name']}: \"{o['title']}\" (words in common {o['overlap']:.0%}; says the same {o['entailment']:.0%}; "
                                                            f"says the opposite {o['contradiction']:.0%})", 300), body))
                story.append(Paragraph(_safe(o.get("url"), 200), small))
            if corr.get("related"):
                story.append(Paragraph(_safe("Related coverage by listed outlets (a different claim; shown for the reader, it does not change the verdict):"), small))
                for o in corr["related"]:
                    story.append(Paragraph("&bull; " + _safe(f"{o['name']}: \"{o['title']}\" (words in common {o['overlap']:.0%})", 300), small))
            if corr.get("status") not in (None, "skipped"):
                story.append(Paragraph(_safe(f"{corr.get('results_read', 0)} headlines read, {corr.get('listed_outlet_results', 0)} from listed outlets."
                                             + (f" {corr['excluded_outlet']}, the site the article came from, was not counted." if corr.get("excluded_outlet") else "")), small))
            story.append(Paragraph(_safe(corr.get("limits"), 700), small))
        match = d.get("text_match")
        if match and match.get("status") != "skipped":
            story += [Paragraph("Text compared with its headline", h2),
                      Paragraph(f"<b>{_safe(match.get('status', '').replace('_', ' ').capitalize())}.</b> {_safe(match.get('message'), 500)}", body)]
            if match.get("effect_note"):
                story.append(Paragraph(_safe(match["effect_note"], 400), small))
            if match.get("missing"):
                story.append(Paragraph(_safe("In the headline but not in the text: " + ", ".join(match["missing"])), small))
            best = match.get("best")
            if best:
                figures = f"words in common {best['overlap']:.0%}"
                if match.get("status") != "unrelated":  # the model's figures mean nothing for a text about something else
                    figures += f"; says the same {best['entailment']:.0%}; says the opposite {best['contradiction']:.0%}"
                story.append(Paragraph("&bull; " + _safe(f"\"{best['text']}\" ({figures})", 500), small))
            story.append(Paragraph(_safe(match.get("limits"), 700), small))
        probs = d.get("probabilities")
        if probs:
            story += [Paragraph("Writing-style model output", h2),
                      Paragraph(f"P(fake) = {probs['fake']:.3f}, P(real) = {probs['real']:.3f}. "
                                f"Decision threshold {d['decision_rule']['threshold']:.2f}. These are model scores, "
                                "not the probability that the news is true.", body)]
            ex = d.get("explanation") or {}
            for title, key in (("Terms pushing towards Fake", "toward_fake"), ("Terms pushing towards Real", "toward_real")):
                items = ex.get(key) or []
                if items:
                    story.append(Paragraph(title, h2))
                    story.append(Paragraph(", ".join(f"{_safe(i['term'])} ({i['weight']:+.2f})" for i in items), body))
            if ex.get("caution"):
                story.append(Paragraph(_safe(ex["caution"]), small))
    elif row.analysis_type == "evidence":
        story.append(Paragraph("Claims checked", h2))
        for c in d.get("claims", []):
            story.append(Paragraph(f"<b>{_safe(c['verdict'])}.</b> {_safe(c['claim'], 400)}", body))
            story.append(Paragraph(_safe(c.get("reason")), small))
            for p_ in c.get("providers", []):
                story.append(Paragraph(_safe(f"Source {p_['provider']}: {p_['status']}. {p_['message']}"), small))
            for ev in c.get("evidence", []):
                line = f"{ev['title']} ({ev['kind']}; stance: {ev['stance'].replace('_', ' ')}; relevance {ev['relevance']:.2f})"
                if ev.get("rating"):
                    line += f"; published rating: {ev['rating']} by {ev.get('publisher') or 'unknown'}"
                story.append(Paragraph("&bull; " + _safe(line, 300), body))
                if ev.get("best_sentence"):
                    story.append(Paragraph(_safe("Closest sentence: " + ev["best_sentence"], 300), small))
                story.append(Paragraph(_safe(ev.get("url"), 200), small))
        if d.get("stance_model"):
            story.append(Paragraph(_safe(f"Stance model: {d['stance_model']}. A stance needs at least "
                                         f"{d['rules']['stance_threshold']:.0%} certainty and a passage that overlaps the claim."), small))
    elif row.analysis_type == "multimodal":
        mod = d.get("modalities") or {}
        story += [Paragraph("What was analysed", h2),
                  Paragraph(_safe(f"Text: {mod.get('text')}. Image: {mod.get('image')}. Image-text consistency: {mod.get('consistency')}."), body)]
        fu = d.get("fusion") or {}
        story += [Paragraph("How the verdict was reached", h2), Paragraph(_safe(fu.get("rule")), body)]
        for n in fu.get("notes", []):
            story.append(Paragraph("&bull; " + _safe(n), small))
        c = d.get("consistency") or {}
        if c.get("similarity") is not None:
            th = c.get("thresholds") or {}
            story += [Paragraph("Image-text consistency (CLIP)", h2),
                      Paragraph(_safe(f"Similarity {c['similarity']:.3f} for the {c.get('caption_source')}: \"{c.get('caption_used')}\". Result: {c.get('label')}. "
                                      f"Thresholds: consistent from {th.get('consistent_min')}, inconsistent up to {th.get('inconsistent_max')}. {c.get('note')}", 700), body)]
        elif c.get("note"):
            story += [Paragraph("Image-text consistency", h2), Paragraph(_safe(c["note"]), body)]
        tr = d.get("text_result") or {}
        if tr.get("probabilities"):
            story += [Paragraph("Text model output", h2),
                      Paragraph(f"P(fake) = {tr['probabilities']['fake']:.3f}, P(real) = {tr['probabilities']['real']:.3f}. These are model scores, not the probability that the news is true.", body)]
        elif tr.get("message"):
            story += [Paragraph("Text model", h2), Paragraph(_safe(tr["message"]), body)]
        ir = d.get("image_result") or {}
        if ir:
            e = ir.get("ela") or {}
            story += [Paragraph("Image indicators", h2), Paragraph(f"ELA mean {e.get('mean')}, ELA max {e.get('max')}, block variation {e.get('block_cv')}.", body)]
            story += [Paragraph("&bull; " + _safe(o), body) for o in ir.get("observations", [])]
    elif row.analysis_type == "video":
        v, smp, dec, mod = d.get("video") or {}, d.get("sampling") or {}, d.get("decision") or {}, d.get("model") or {}
        story += [Paragraph("The video", h2),
                  Paragraph(_safe(f"{v.get('width')}x{v.get('height')}, {v.get('duration_seconds')} s, {v.get('fps')} frames per second. "
                                  f"{smp.get('sampled')} frames were sampled evenly across the video; a face was found in {smp.get('with_face')} "
                                  f"(at least {smp.get('min_face_frames')} are needed for a call)."), body),
                  Paragraph("How the verdict was reached", h2), Paragraph(_safe(dec.get("rule")), body),
                  Paragraph(_safe(mod.get("note")), small)]
        for o in d.get("observations", []):
            story.append(Paragraph("&bull; " + _safe(o), body))
        t = d.get("temporal")
        if t:
            story += [Paragraph("Frame scores over the video", h2),
                      Paragraph(_safe(f"Video score {t['video_score']:.3f} ({t['aggregator']} of {t['frames_scored']} face frames). Share of frames scored 0.5 or higher: "
                                      f"{t['flagged_share']:.0%}; longest run of such frames: {t['longest_flagged_run']}; lowest {t['min']:.3f}, highest {t['max']:.3f}. "
                                      "The scores are model outputs, not the probability that the video is fake."), body)]
            if t.get("suspicious_moments"):
                story.append(Paragraph(_safe("Highest-scoring moments: " + ", ".join(f"{m['t']:.1f} s ({m['p_fake']:.2f})" for m in t["suspicious_moments"])), small))
        rows = [["Time (s)", "Face", "Score", "Sharpness", "Error level"]]
        for f in d.get("frames", []):
            rows.append([f"{f['t']:.1f}", "yes" if f["face_found"] else "no", "-" if f["p_fake"] is None else f"{f['p_fake']:.3f}",
                         "-" if f["sharpness"] is None else f"{f['sharpness']:.0f}", "-" if f["ela_mean"] is None else f"{f['ela_mean']:.2f}"])
        table = Table(rows, repeatRows=1)
        table.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 8), ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                                   ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke)]))
        story += [Paragraph("Sampled frames", h2), table]
    elif row.analysis_type == "image":
        e = d.get("ela") or {}
        story += [Paragraph("Measurements", h2),
                  Paragraph(f"ELA mean {e.get('mean')}, ELA max {e.get('max')}, block variation {e.get('block_cv')}.", body),
                  Paragraph("Observations", h2)]
        story += [Paragraph("&bull; " + _safe(o), body) for o in d.get("observations", [])]
        ip = row.image_prediction
        if ip and ip.heatmap_filename:
            try:
                path = files.resolve_media("heatmaps", ip.heatmap_filename)
                story += [Paragraph("Error Level Analysis map (not an AI attention map)", h2),
                          RLImage(str(path), width=110 * mm, height=110 * mm * ip.height / ip.width, kind="proportional")]
            except Exception:  # the map file may have been removed; the report is still valid without it
                pass

    story += [Paragraph("Limitations", h2), Paragraph(_safe(row.limitations or ""), body), Spacer(1, 8),
              Paragraph("This report is an automated aid, produced by a student research prototype. It is not a "
                        "fact-check and must not be treated as proof that content is real or fake.", small)]
    doc.build(story)
    return buf.getvalue()
