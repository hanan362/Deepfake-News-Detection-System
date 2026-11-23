"""A slow analysis must not freeze the rest of the API.

On first use CLIP, the evidence model and the video model download and load for minutes. When an endpoint ran that work
directly on the event loop, login, history and the health check all stopped answering until it finished (seen on a
Windows laptop). These tests make the analysis slow on purpose and check that the event loop keeps running meanwhile."""
import asyncio
import time

import httpx
import pytest

from app.api.routers import analysis as analysis_router
from app.main import app
from tests.conftest import API, make_image_bytes

SLOW_SECONDS = 2.0
MAX_LOOP_STALL_SECONDS = 0.5


def _slow(original):
    def wrapper(*args, **kwargs):
        time.sleep(SLOW_SECONDS)
        return original(*args, **kwargs)
    return wrapper


async def _run_while_watching_the_event_loop(slow_request):
    """Run the slow request and, next to it, a ticker that wakes every 50 ms. If the request blocks the event loop, the
    ticker (and any other request) cannot run, and the longest gap between two ticks grows to about SLOW_SECONDS."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        gaps: list[float] = []
        stop = asyncio.Event()

        async def ticker():
            last = time.perf_counter()
            while not stop.is_set():
                await asyncio.sleep(0.05)
                now = time.perf_counter()
                gaps.append(now - last)
                last = now

        watcher = asyncio.create_task(ticker())
        await asyncio.sleep(0.1)
        started = time.perf_counter()
        slow_response = await slow_request(ac)
        total = time.perf_counter() - started
        health = await ac.get(f"{API}/health")
        stop.set()
        await watcher
        return health, max(gaps), slow_response, total


def test_a_slow_multimodal_check_does_not_block_other_requests(monkeypatch, alice):
    monkeypatch.setattr(analysis_router.svc, "create_multimodal_analysis", _slow(analysis_router.svc.create_multimodal_analysis))

    async def slow_request(ac):
        return await ac.post(f"{API}/analysis/multimodal", headers=alice.headers, data={"headline": "A short caption"})

    health, longest_stall, slow_response, total = asyncio.run(_run_while_watching_the_event_loop(slow_request))
    assert slow_response.status_code == 201, slow_response.text
    assert total >= SLOW_SECONDS, "the slow request was not actually slow, so the test proves nothing"
    assert health.status_code == 200
    assert longest_stall < MAX_LOOP_STALL_SECONDS, f"the event loop was frozen for {longest_stall:.2f}s by a slow analysis"


def test_a_slow_image_check_does_not_block_other_requests(monkeypatch, alice):
    monkeypatch.setattr(analysis_router.svc, "create_image_analysis", _slow(analysis_router.svc.create_image_analysis))
    jpeg = make_image_bytes("noise")

    async def slow_request(ac):
        return await ac.post(f"{API}/analysis/image", headers=alice.headers, files={"file": ("p.jpg", jpeg, "image/jpeg")})

    health, longest_stall, slow_response, total = asyncio.run(_run_while_watching_the_event_loop(slow_request))
    assert slow_response.status_code == 201, slow_response.text
    assert total >= SLOW_SECONDS
    assert health.status_code == 200
    assert longest_stall < MAX_LOOP_STALL_SECONDS, f"the event loop was frozen for {longest_stall:.2f}s by a slow analysis"


@pytest.mark.parametrize("name", ["create_multimodal_analysis", "create_image_analysis", "create_video_analysis"])
def test_the_service_functions_exist_for_the_threadpool_calls(name):
    assert callable(getattr(analysis_router.svc, name))
