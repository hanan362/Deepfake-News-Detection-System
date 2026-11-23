"""Every timestamp the API returns must say it is UTC. A bare "2026-11-21T08:21:37" is read by a browser as local
time, which shows the wrong hour to anyone outside UTC (for example Pakistan, UTC+5)."""
from datetime import datetime, timezone

from tests.conftest import API, ARTICLE


def _walk(value, path=""):
    """Yield (path, value) for every string that looks like an ISO timestamp (a date, a 'T', and a time)."""
    if isinstance(value, dict):
        for k, v in value.items():
            yield from _walk(v, f"{path}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from _walk(v, f"{path}[{i}]")
    elif isinstance(value, str) and len(value) >= 19 and value[4] == "-" and value[10] == "T":
        yield path, value


def _assert_all_utc(payload):
    found = list(_walk(payload))
    assert found, "expected at least one timestamp in the payload"
    for path, text in found:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0, f"{path}={text} has no UTC offset"


def test_timestamps_carry_a_utc_offset_everywhere(client, make_user):
    admin = make_user("root", admin=True)
    user = make_user("alice")
    client.post(f"{API}/analysis/text", json={"text": ARTICLE}, headers=user.headers)
    client.post(f"{API}/feedback", json={"category": "bug", "message": "Something to check."}, headers=user.headers)
    login = client.post(f"{API}/auth/login", json={"identifier": "alice", "password": user.password}).json()

    payloads = [
        login,
        client.get(f"{API}/users/me", headers=user.headers).json(),
        client.get(f"{API}/analysis", headers=user.headers).json(),
        client.get(f"{API}/analysis/1", headers=user.headers).json(),
        client.get(f"{API}/dashboard/stats", headers=user.headers).json(),
        client.get(f"{API}/feedback", headers=user.headers).json(),
        client.get(f"{API}/admin/users", headers=admin.headers).json(),
        client.get(f"{API}/admin/feedback", headers=admin.headers).json(),
        client.get(f"{API}/admin/audit-logs", headers=admin.headers).json(),
        client.get(f"{API}/admin/models", headers=admin.headers).json(),
    ]
    for payload in payloads:
        _assert_all_utc(payload)


def test_a_value_stored_without_a_timezone_is_read_back_as_utc():
    from app.models.entities import UTCDateTime

    t = UTCDateTime()
    naive = datetime(2026, 1, 2, 3, 4, 5)
    assert t.process_result_value(naive, None) == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    assert t.process_bind_param(naive, None).tzinfo is not None
    assert t.process_bind_param(None, None) is None and t.process_result_value(None, None) is None
