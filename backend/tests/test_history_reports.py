import os

import pytest

from app.ml.text_detection.service import get_detector
from app.services import files

from .conftest import API, ARTICLE, make_image_bytes

needs_model = pytest.mark.skipif(not get_detector().available, reason="text model not trained")


def add_text(client, user, headline="Headline", text=ARTICLE):
    r = client.post(f"{API}/analysis/text", json={"headline": headline, "text": text}, headers=user.headers)
    assert r.status_code == 201, r.text
    return r.json()


def add_image(client, user, name="pic.jpg"):
    r = client.post(f"{API}/analysis/image", files={"file": (name, make_image_bytes(), "image/jpeg")}, headers=user.headers)
    assert r.status_code == 201, r.text
    return r.json()


@needs_model
def test_history_lists_only_own_items_newest_first_with_paging(client, alice, bob):
    ids = [add_text(client, alice, f"Story {i}")["id"] for i in range(5)]
    add_text(client, bob, "Bob story")
    page1 = client.get(f"{API}/analysis?page=1&page_size=2", headers=alice.headers).json()
    page3 = client.get(f"{API}/analysis?page=3&page_size=2", headers=alice.headers).json()
    assert page1["total"] == 5 and [i["id"] for i in page1["items"]] == ids[::-1][:2]
    assert len(page3["items"]) == 1
    assert all(i["details"] is None for i in page1["items"])  # list view is light; details only on the detail endpoint
    assert client.get(f"{API}/analysis?page_size=1000", headers=alice.headers).status_code == 422


@needs_model
def test_history_filters_and_search(client, alice):
    add_text(client, alice, "Budget vote")
    add_image(client, alice, "flood.jpg")
    assert client.get(f"{API}/analysis?analysis_type=image", headers=alice.headers).json()["total"] == 1
    assert client.get(f"{API}/analysis?analysis_type=text", headers=alice.headers).json()["total"] == 1
    assert client.get(f"{API}/analysis?q=flood", headers=alice.headers).json()["total"] == 1
    assert client.get(f"{API}/analysis?q=budget", headers=alice.headers).json()["total"] == 1
    assert client.get(f"{API}/analysis?q=nothing-matches", headers=alice.headers).json()["total"] == 0
    assert client.get(f"{API}/analysis?analysis_type=bogus", headers=alice.headers).status_code == 422
    verdict = client.get(f"{API}/analysis?analysis_type=image", headers=alice.headers).json()["items"][0]["verdict"]
    assert client.get(f"{API}/analysis?verdict={verdict}", headers=alice.headers).json()["total"] == 1


@needs_model
def test_other_users_and_admins_cannot_read_or_delete_an_analysis(client, alice, bob, admin):
    a = add_text(client, alice)["id"]
    for who in (bob, admin):
        assert client.get(f"{API}/analysis/{a}", headers=who.headers).status_code == 404
        assert client.get(f"{API}/analysis/{a}/report.pdf", headers=who.headers).status_code == 404
        assert client.delete(f"{API}/analysis/{a}", headers=who.headers).status_code == 404
    assert client.get(f"{API}/analysis/{a}", headers=alice.headers).status_code == 200


def test_delete_removes_the_record_and_its_files(client, alice):
    a = add_image(client, alice)["id"]
    assert os.listdir(files.media_dir("images")) and os.listdir(files.media_dir("heatmaps"))
    assert client.delete(f"{API}/analysis/{a}", headers=alice.headers).status_code == 204
    assert client.get(f"{API}/analysis/{a}", headers=alice.headers).status_code == 404
    assert not os.listdir(files.media_dir("images")) and not os.listdir(files.media_dir("heatmaps"))


@needs_model
def test_pdf_report_for_text_and_image(client, alice):
    t = add_text(client, alice)["id"]
    i = add_image(client, alice)["id"]
    for aid in (t, i):
        r = client.get(f"{API}/analysis/{aid}/report.pdf", headers=alice.headers)
        assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
        assert r.content.startswith(b"%PDF") and r.content.rstrip().endswith(b"%%EOF") and len(r.content) > 1500
        assert "attachment" in r.headers["content-disposition"]


@needs_model
def test_pdf_report_survives_non_latin_and_markup_text(client, alice):
    nasty = "<b>bold</b> & <script>alert(1)</script> " + "یہ اردو ہے " * 10 + ARTICLE
    a = add_text(client, alice, "<i>Hdl</i> & more", nasty)["id"]
    r = client.get(f"{API}/analysis/{a}/report.pdf", headers=alice.headers)
    assert r.status_code == 200 and r.content.startswith(b"%PDF")


def test_unknown_analysis_is_404(client, alice):
    assert client.get(f"{API}/analysis/99999", headers=alice.headers).status_code == 404
    assert client.get(f"{API}/analysis/abc", headers=alice.headers).status_code == 422
