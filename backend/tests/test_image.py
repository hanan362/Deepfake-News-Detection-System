import io
import os

from PIL import Image

from app.core.config import get_settings
from app.ml.image_detection import ela
from app.services import files

from .conftest import API, make_image_bytes


def upload(client, headers, data, name="photo.jpg", ctype="image/jpeg"):
    return client.post(f"{API}/analysis/image", files={"file": (name, data, ctype)}, headers=headers)


def test_ela_values_are_real_measurements():
    flat = ela.analyse(make_image_bytes("flat", "PNG"), 40_000_000)
    noisy = ela.analyse(make_image_bytes("noise", "JPEG"), 40_000_000)
    assert 0 <= flat.ela_mean <= flat.ela_max <= 255 and flat.ela_max <= 3  # a flat image recompresses almost perfectly
    assert noisy.ela_mean > flat.ela_mean * 5  # random noise does not
    heat = Image.open(io.BytesIO(noisy.heatmap_png))
    assert heat.mode == "L" and heat.size == (160, 120)
    assert heat.getextrema()[1] > heat.getextrema()[0]  # the map is not blank


def test_image_endpoint_returns_indicators_not_a_verdict(client, alice):
    r = upload(client, alice.headers, make_image_bytes("noise"))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["verdict"] == "Indicators Only" and body["confidence"] is None
    assert body["model"]["status"] == "heuristic" and body["has_heatmap"] is True
    assert body["details"]["ela"]["grid"] == ela.GRID and body["details"]["observations"]
    assert "not a verdict" in body["limitations"] and "not an AI attention map" in body["details"]["map_note"]
    assert body["details"]["metadata"]["has_exif"] is False
    assert body["details"]["image"] == {"width": 160, "height": 120, "format": "JPEG"}


def test_heatmap_and_original_are_served_only_to_the_owner(client, alice, bob, admin):
    a = upload(client, alice.headers, make_image_bytes()).json()["id"]
    r = client.get(f"{API}/analysis/{a}/heatmap", headers=alice.headers)
    assert r.status_code == 200 and r.headers["content-type"] == "image/png" and r.content[:4] == b"\x89PNG"
    assert client.get(f"{API}/analysis/{a}/image", headers=alice.headers).headers["content-type"] == "image/jpeg"
    for who in (bob, admin):
        assert client.get(f"{API}/analysis/{a}/heatmap", headers=who.headers).status_code == 404
        assert client.get(f"{API}/analysis/{a}/image", headers=who.headers).status_code == 404
    assert client.get(f"{API}/analysis/{a}/heatmap").status_code == 401


def test_upload_is_validated_by_content_not_name_or_declared_type(client, alice):
    assert upload(client, alice.headers, b"this is a text file", "evil.jpg", "image/jpeg").status_code == 415
    assert upload(client, alice.headers, b"<?php echo 1; ?>", "shell.php", "image/png").status_code == 415
    gif = io.BytesIO()
    Image.new("RGB", (10, 10)).save(gif, format="GIF")
    assert upload(client, alice.headers, gif.getvalue(), "a.png", "image/png").status_code == 415  # unsupported format
    assert upload(client, alice.headers, make_image_bytes(), "renamed.txt", "text/plain").status_code == 201  # real JPEG
    assert upload(client, alice.headers, b"", "empty.jpg").status_code == 400


def test_size_and_pixel_limits(client, alice):
    s = get_settings()
    old_mb = s.max_image_mb
    s.max_image_mb = 1
    try:
        assert upload(client, alice.headers, b"\xff\xd8" + os.urandom(1_200_000)).status_code == 413
    finally:
        s.max_image_mb = old_mb
    old_px = s.max_image_pixels
    s.max_image_pixels = 10_000
    try:
        assert upload(client, alice.headers, make_image_bytes(size=(200, 200))).status_code == 415  # 40,000 pixels
    finally:
        s.max_image_pixels = old_px


def test_stored_names_are_random_and_original_name_is_sanitised(client, alice):
    r = upload(client, alice.headers, make_image_bytes(), "../../etc/passwd.jpg")
    assert r.status_code == 201
    assert r.json()["source_filename"] == "passwd.jpg"
    stored = os.listdir(files.media_dir("images"))
    assert stored and all(len(n.split(".")[0]) == 32 and "passwd" not in n for n in stored)


def test_display_name_strips_paths_and_control_characters():
    assert files.safe_display_name("..\\..\\windows\\system32\\x\x00y.jpg") == "xy.jpg"
    assert files.safe_display_name("a" * 500 + ".jpg") == "a" * 120
    assert files.safe_display_name("") is None and files.safe_display_name(None) is None


def test_resolve_media_refuses_path_traversal():
    import pytest
    from app.core.errors import APIError
    for bad in ("../test.db", "../../etc/passwd", "/etc/passwd", "missing.png"):
        with pytest.raises(APIError):
            files.resolve_media("images", bad)


def test_avatar_upload_is_reencoded_and_private(client, alice, bob):
    r = client.post(f"{API}/users/me/avatar", files={"file": ("me.jpg", make_image_bytes(size=(600, 300)), "image/jpeg")}, headers=alice.headers)
    assert r.status_code == 200 and r.json()["has_avatar"] is True
    got = client.get(f"{API}/users/me/avatar", headers=alice.headers)
    assert got.status_code == 200 and Image.open(io.BytesIO(got.content)).size == (256, 256)
    assert client.get(f"{API}/users/me/avatar", headers=bob.headers).status_code == 404  # bob has none; never sees alice's
    assert client.post(f"{API}/users/me/avatar", files={"file": ("x.png", b"nope", "image/png")}, headers=alice.headers).status_code == 415
    assert client.delete(f"{API}/users/me/avatar", headers=alice.headers).json()["has_avatar"] is False
