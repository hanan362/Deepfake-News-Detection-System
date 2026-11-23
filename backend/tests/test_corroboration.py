"""The headline-against-news check: the rules, how they change a verdict, the feed reader and the API integration.
No test reaches the internet: the search and the inference model are replaced by small stand-ins."""
import httpx
import pytest

from app.core.config import get_settings
from app.ml.corroboration import check, news_search
from app.ml.corroboration.news_search import GoogleNewsSearch, NewsHit, SearchUnavailable
from app.services import analysis_service as svc
from tests.conftest import API, ARTICLE

HEADLINE = "City council approves new transport budget after months of public hearings"
SAME = "City council approves new transport budget following public hearings"


def hit(title, site="https://www.dawn.com", outlet="Dawn"):
    return NewsHit(title=title, outlet=outlet, site_url=site, link="https://news.example/story", published="Sat, 14 Nov 2026 07:00:00 GMT")


class FakeSearch:
    name = "fake search"

    def __init__(self, hits=None, error=None):
        self.hits, self.error, self.queries = hits or [], error, []

    def search(self, query, limit=12):
        self.queries.append(query)
        if self.error:
            raise self.error
        return self.hits


class ScriptedNli:
    """Answers by headline: {title: (entailment, contradiction)}; anything else is neutral."""
    model_id = "scripted"
    available = True

    def __init__(self, table=None):
        self.table, self.asked = table or {}, []

    def predict(self, pairs):
        self.asked += [p for p, _h in pairs]
        return [{"entailment": self.table.get(p, (0.02, 0.02))[0], "contradiction": self.table.get(p, (0.02, 0.02))[1], "neutral": 0.5} for p, _h in pairs]


class NoNli(ScriptedNli):
    available = False


# ---- the rules ----------------------------------------------------------------------------------------------

def test_a_listed_outlet_with_the_same_story_corroborates():
    r = check.corroborate(HEADLINE, FakeSearch([hit(SAME)]), ScriptedNli({SAME: (0.9, 0.01)}))
    assert r["status"] == "corroborated"
    assert [o["name"] for o in r["outlets"]] == ["Dawn"] and r["outlets"][0]["relation"] == "same_story"
    assert "Dawn" in r["message"] and r["rules"] and r["limits"]


def test_an_outlet_that_is_not_in_the_directory_is_never_counted():
    r = check.corroborate(HEADLINE, FakeSearch([hit(SAME, "https://www.dailyunknownpost.example", "Daily Unknown Post")]), ScriptedNli({SAME: (0.99, 0.0)}))
    assert r["status"] == "not_found" and r["listed_outlet_results"] == 0 and r["results_read"] == 1


def test_a_satire_site_is_never_counted():
    r = check.corroborate(HEADLINE, FakeSearch([hit(SAME, "https://www.theonion.com", "The Onion")]), ScriptedNli({SAME: (0.99, 0.0)}))
    assert r["status"] == "not_found" and r["listed_outlet_results"] == 0


def test_related_coverage_is_listed_when_nothing_matches_but_never_changes_the_status():
    related = "Council debates how to spend the transport budget"   # shares some words, says something else
    far = "Heavy rain expected in coastal areas"
    r = check.corroborate(HEADLINE, FakeSearch([hit(related, "https://www.dawn.com", "Dawn"), hit(far, "https://www.bbc.com", "BBC")]), ScriptedNli())
    assert r["status"] == "not_found"
    assert [x["name"] for x in r["related"]] == ["Dawn"] and r["related"][0]["title"] == related and 0.3 <= r["related"][0]["overlap"] < 0.5
    assert r["rules"]["related"]


def test_related_coverage_is_one_headline_per_outlet_from_listed_outlets_only_and_at_most_three():
    hits = [hit("Council debates how to spend the transport budget", "https://www.dawn.com", "Dawn"),
            hit("Council transport budget talks continue", "https://www.dawn.com", "Dawn"),
            hit("Transport budget row at the council", "https://www.bbc.com", "BBC"),
            hit("Council transport budget vote delayed", "https://www.theguardian.com", "The Guardian"),
            hit("Council transport budget row deepens", "https://www.reuters.com", "Reuters"),
            hit("Council transport budget row at an unlisted site", "https://www.dailyunknownpost.example", "Daily Unknown Post")]
    r = check.corroborate(HEADLINE, FakeSearch(hits), ScriptedNli())
    names = [x["name"] for x in r["related"]]
    assert len(names) == 3 == len(set(names)) and "Daily Unknown Post" not in names


def test_nothing_is_related_when_the_outlet_is_excluded_or_the_search_failed():
    own = "Council debates how to spend the transport budget"
    assert check.corroborate(HEADLINE, FakeSearch([hit(own, "https://www.dawn.com", "Dawn")]), ScriptedNli(), exclude_outlet="Dawn")["related"] == []
    assert check.corroborate(HEADLINE, FakeSearch(error=SearchUnavailable("x")), ScriptedNli())["related"] == []
    assert check.corroborate(None, FakeSearch(), ScriptedNli())["related"] == []


def test_related_coverage_does_not_appear_next_to_a_match():
    r = check.corroborate(HEADLINE, FakeSearch([hit(SAME)]), ScriptedNli({SAME: (0.9, 0.01)}))
    assert r["status"] == "corroborated" and r["related"] == []


def test_a_changed_name_or_number_is_not_confirmed_even_when_the_model_says_the_same():
    """Seen on a real distorted headline: "Iraq wants diplomacy ..." was read as saying what "Iran wants diplomacy ..." says."""
    real = "Iran wants diplomacy to end war, says foreign minister as US rejects terms"
    for changed in ("Iraq wants diplomacy to end war, says foreign minister as US rejects terms",
                    "Iran wants diplomacy to end war, says foreign minister as Russia rejects terms"):
        assert check.missing_specifics(changed, real)
        r = check.corroborate(changed, FakeSearch([hit(real)]), ScriptedNli({real: (0.97, 0.01)}))
        assert r["status"] == "not_found" and r["outlets"] == []
    r = check.corroborate("Council approves 36 million dollar transport budget after public hearings",
                          FakeSearch([hit("Council approves 12 million dollar transport budget after public hearings")]),
                          ScriptedNli({"Council approves 12 million dollar transport budget after public hearings": (0.97, 0.01)}))
    assert r["status"] == "not_found"


def test_the_name_and_number_rule_does_not_block_a_faithful_copy_or_a_title_case_headline():
    real = "Iran wants diplomacy to end war, says foreign minister as US rejects terms"
    assert check.missing_specifics(real, real) == set()
    assert check.corroborate(real, FakeSearch([hit(real)]), ScriptedNli({real: (0.97, 0.01)}))["status"] == "corroborated"
    # Title Case capitalises every word, so a capital says nothing there; the user's own capitals are not "names" either
    assert check.specifics("Council Approves New Transport Budget After Months Of Public Hearings") == set()
    assert check.missing_specifics("Council approves new transport budget after public hearings",
                                   "Council Approves New Transport Budget After Public Hearings") == set()
    assert check.missing_specifics("Councils approve budgets", "Council approves budget") == set()   # plurals and tenses still match


def test_a_headline_that_shares_too_few_words_is_not_even_compared():
    other = "Council debates parking fees"
    nli = ScriptedNli({other: (0.99, 0.0)})
    r = check.corroborate(HEADLINE, FakeSearch([hit(other)]), nli)
    assert r["status"] == "not_found" and nli.asked == []


def test_a_similar_headline_the_model_does_not_judge_to_say_the_same_does_not_corroborate():
    r = check.corroborate(HEADLINE, FakeSearch([hit(SAME)]), ScriptedNli({SAME: (0.59, 0.1)}))
    assert r["status"] == "not_found"


def test_a_near_identical_headline_that_says_the_opposite_is_disputed_not_ruled_false():
    opposite = "City council rejects new transport budget after months of public hearings"
    r = check.corroborate(HEADLINE, FakeSearch([hit(opposite)]), ScriptedNli({opposite: (0.01, 0.97)}))
    assert r["status"] == "disputed" and r["outlets"][0]["relation"] == "different_report"


def test_a_contradiction_needs_a_closer_match_than_support():
    loose = "Council rejects budget amid public hearings"
    assert check.overlap(HEADLINE, loose) < check.CONTRADICT_OVERLAP
    r = check.corroborate(HEADLINE, FakeSearch([hit(loose)]), ScriptedNli({loose: (0.01, 0.99)}))
    assert r["status"] == "not_found"


def test_support_wins_over_a_contradiction():
    opposite = "City council rejects new transport budget after months of public hearings"
    r = check.corroborate(HEADLINE, FakeSearch([hit(opposite, "https://www.bbc.com", "BBC"), hit(SAME)]),
                          ScriptedNli({opposite: (0.01, 0.97), SAME: (0.9, 0.01)}))
    assert r["status"] == "corroborated" and [o["name"] for o in r["outlets"]] == ["Dawn"]


def test_one_organisation_with_two_addresses_counts_once():
    r = check.corroborate(HEADLINE, FakeSearch([hit(SAME, "https://www.bbc.com", "BBC"), hit(SAME + " today", "https://www.bbc.co.uk", "BBC")]),
                          ScriptedNli({SAME: (0.9, 0), SAME + " today": (0.9, 0)}))
    assert [o["name"] for o in r["outlets"]] == ["BBC"]


@pytest.mark.parametrize("headline,reason", [(None, "no_headline"), ("   ", "no_headline"), ("Council votes today", "too_short")])
def test_nothing_is_searched_without_a_usable_headline(headline, reason):
    search = FakeSearch([hit(SAME)])
    r = check.corroborate(headline, search, ScriptedNli())
    assert r["status"] == "skipped" and r["reason"] == reason and search.queries == []


def test_without_the_model_headlines_that_need_comparing_are_reported_as_not_compared():
    r = check.corroborate(HEADLINE, FakeSearch([hit(SAME)]), NoNli())
    assert r["status"] == "unavailable" and r["reason"] == "model_missing" and r["listed_outlet_results"] == 1


def test_the_model_is_not_touched_when_nothing_is_close_enough_to_compare():
    class Untouchable(ScriptedNli):
        @property
        def available(self):  # reading it would load the model, which is slow the first time
            raise AssertionError("the model was loaded although no headline needed comparing")

    r = check.corroborate(HEADLINE, FakeSearch([hit("Council debates parking fees"), hit(SAME, "https://www.dailyunknownpost.example", "Unknown")]), Untouchable())
    assert r["status"] == "not_found"
    assert check.corroborate(HEADLINE, FakeSearch([]), Untouchable())["status"] == "not_found"


@pytest.mark.parametrize("error", [SearchUnavailable("The news search could not be reached."), RuntimeError("boom")])
def test_a_failing_search_is_reported_and_never_raised(error):
    r = check.corroborate(HEADLINE, FakeSearch(error=error), ScriptedNli())
    assert r["status"] == "unavailable" and r["reason"] == "search_failed" and r["message"]


@pytest.mark.parametrize("raw,expected", [
    ("New ferry terminal to open in March | Harbour Gazette", "New ferry terminal to open in March"),
    ("New ferry terminal to open in March - Harbour Gazette", "New ferry terminal to open in March"),
    ("Pre-trial hearing set for Monday in Karachi court", "Pre-trial hearing set for Monday in Karachi court"),
    ("Home | Dawn", "Home | Dawn"),
])
def test_the_searched_headline_loses_a_trailing_site_name(raw, expected):
    assert check.clean_query(raw) == expected


def test_a_long_headline_is_cut_before_it_is_sent():
    assert len(check.clean_query("word " * 100)) <= check.MAX_QUERY_CHARS


def test_the_outlet_the_article_came_from_is_not_counted_as_confirming_itself():
    r = check.corroborate(HEADLINE, FakeSearch([hit(SAME)]), ScriptedNli({SAME: (0.9, 0.0)}), exclude_outlet="Dawn")
    assert r["status"] == "not_found" and r["excluded_outlet"] == "Dawn" and r["listed_outlet_results"] == 0
    other = check.corroborate(HEADLINE, FakeSearch([hit(SAME), hit(SAME, "https://www.bbc.com", "BBC")]), ScriptedNli({SAME: (0.9, 0.0)}), exclude_outlet="Dawn")
    assert [o["name"] for o in other["outlets"]] == ["BBC"]


# ---- how the result changes the verdict --------------------------------------------------------------------

def base(verdict, reason):
    return {"verdict": verdict, "confidence": 0.9 if verdict != "Unverified" else None, "reason": reason, "message": None}


CORROBORATED = {"status": "corroborated", "message": "The headline matches a report by 1 listed news organisation: Dawn."}
DISPUTED = {"status": "disputed", "message": "A listed news organisation reports something different."}


@pytest.mark.parametrize("before,reason,corr,verdict,new_reason", [
    ("Unverified", "low_confidence", CORROBORATED, "Likely Real", "corroborated"),
    ("Unverified", "too_short", CORROBORATED, "Likely Real", "corroborated"),
    ("Likely Real", "model_leans_real", CORROBORATED, "Likely Real", "model_leans_real"),
    ("Likely Fake", "model_leans_fake", CORROBORATED, "Unverified", "signals_differ"),
    ("Likely Real", "model_leans_real", DISPUTED, "Unverified", "disputed"),
    ("Likely Fake", "model_leans_fake", DISPUTED, "Likely Fake", "model_leans_fake"),
    ("Unverified", "low_confidence", DISPUTED, "Unverified", "low_confidence"),
])
def test_the_verdict_moves_only_in_the_documented_ways(before, reason, corr, verdict, new_reason):
    out = check.combine(base(before, reason), corr)
    assert (out["verdict"], out["reason"]) == (verdict, new_reason)


@pytest.mark.parametrize("reason", ["declared_satire", "unsupported_language", "article_not_readable"])
def test_a_verdict_that_has_its_own_reason_is_never_overridden(reason):
    assert check.combine(base("Unverified", reason), CORROBORATED)["verdict"] == "Unverified"
    assert check.combine(base("Unverified", reason), CORROBORATED)["reason"] == reason


PUBLISHER = {"assessment": "recognised_publisher", "matched": {"name": "Dawn"}}


@pytest.mark.parametrize("before,reason,verdict,new_reason", [
    ("Unverified", "low_confidence", "Likely Real", "published_by_listed_outlet"),
    ("Unverified", "too_short", "Likely Real", "published_by_listed_outlet"),
    ("Likely Real", "model_leans_real", "Likely Real", "model_leans_real"),
    ("Likely Fake", "model_leans_fake", "Unverified", "signals_differ"),
    ("Unverified", "article_not_readable", "Unverified", "article_not_readable"),
    ("Unverified", "corroborated", "Unverified", "corroborated"),
    ("Unverified", "disputed", "Unverified", "disputed"),
])
def test_a_listed_outlets_own_site_changes_the_reading_only_in_the_documented_ways(before, reason, verdict, new_reason):
    out = check.combine_publisher(base(before, reason), PUBLISHER)
    assert (out["verdict"], out["reason"]) == (verdict, new_reason)


def test_a_difference_reported_by_another_outlet_blocks_the_site_rule():
    r = base("Unverified", "low_confidence")
    assert check.combine_publisher(r, PUBLISHER, {"status": "disputed"}) == r
    assert check.combine_publisher(r, PUBLISHER, {"status": "not_found"})["verdict"] == "Likely Real"


@pytest.mark.parametrize("source", [{"assessment": "unknown", "matched": None}, {"assessment": "declared_satire", "matched": {"name": "The Onion"}},
                                    {"assessment": "lookalike", "matched": None}, {}])
def test_only_a_recognised_publisher_counts(source):
    r = base("Unverified", "low_confidence")
    assert check.combine_publisher(r, source) == r


@pytest.mark.parametrize("status", ["not_found", "unavailable", "skipped"])
def test_no_news_result_leaves_the_reading_alone(status):
    r = base("Likely Fake", "model_leans_fake")
    assert check.combine(r, {"status": status, "message": "x"}) == r


# ---- the feed reader ------------------------------------------------------------------------------------------

FEED = b"""<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>q</title>
<item><title>Council approves budget - Dawn</title><link>https://news.google.com/rss/articles/abc</link><pubDate>Sat, 14 Nov 2026 07:00:00 GMT</pubDate>
<source url="https://www.dawn.com">Dawn</source></item>
<item><title>Something else entirely - The Guardian</title><link>https://news.google.com/rss/articles/def</link><source url="https://www.theguardian.com">The Guardian</source></item>
<item><title></title></item></channel></rss>"""


def test_the_feed_is_read_and_the_outlet_name_is_removed_from_the_headline():
    hits = news_search.parse_feed(FEED)
    assert [(h.title, h.outlet, h.site_url) for h in hits] == [("Council approves budget", "Dawn", "https://www.dawn.com"),
                                                              ("Something else entirely", "The Guardian", "https://www.theguardian.com")]


@pytest.mark.parametrize("body", [b"<!DOCTYPE rss [<!ENTITY a 'b'>]><rss/>", b"<rss><channel><item><title>&a;</title></item></channel>", b"not xml"])
def test_documents_that_could_expand_or_are_not_feeds_are_refused(body):
    with pytest.raises(SearchUnavailable):
        news_search.parse_feed(body)


def provider_with(handler, sleeps=None):
    return GoogleNewsSearch(client=httpx.Client(transport=httpx.MockTransport(handler)),
                            sleep=(sleeps.append if sleeps is not None else (lambda seconds: None)))


def test_the_provider_asks_for_the_headline_only_and_remembers_the_answer():
    seen = []

    def handler(request):
        seen.append(dict(request.url.params))
        return httpx.Response(200, content=FEED)

    p = provider_with(handler)
    assert len(p.search("Council approves budget")) == 2 and len(p.search("council approves budget")) == 2
    assert len(seen) == 1 and seen[0]["q"] == "Council approves budget" and set(seen[0]) == {"q", "hl", "gl", "ceid"}


@pytest.mark.parametrize("response,text", [(httpx.Response(429), "limiting"), (httpx.Response(503), "error"),
                                           (httpx.Response(200, content=b"x" * (news_search.MAX_BYTES + 1)), "larger")])
def test_provider_problems_are_explained(response, text):
    with pytest.raises(SearchUnavailable, match=text):
        provider_with(lambda request: response).search("Council approves budget")


def test_one_429_is_retried_once_after_a_short_pause():
    answers = [httpx.Response(429), httpx.Response(200, content=FEED)]
    sleeps = []
    p = provider_with(lambda request: answers.pop(0), sleeps)
    assert len(p.search("Council approves budget")) == 2
    assert sleeps == [news_search.RETRY_WAIT_SECONDS] and not answers


def test_a_retry_after_header_is_honoured_but_capped_so_a_request_never_hangs():
    answers = [httpx.Response(429, headers={"Retry-After": "120"}), httpx.Response(200, content=FEED)]
    sleeps = []
    provider_with(lambda request: answers.pop(0), sleeps).search("Council approves budget")
    assert sleeps == [news_search.RETRY_AFTER_CAP_SECONDS]


def test_two_429s_pause_the_search_so_a_blocked_server_stops_asking(monkeypatch):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(429)

    clock = {"now": 1000.0}
    monkeypatch.setattr(news_search.time, "monotonic", lambda: clock["now"])
    p = provider_with(handler)
    with pytest.raises(SearchUnavailable, match="paused for about 60 seconds"):
        p.search("Council approves budget")
    assert len(calls) == 2                       # the first try and the single retry
    with pytest.raises(SearchUnavailable, match="paused"):
        p.search("A different headline entirely")   # any query is held back, with no request sent
    assert len(calls) == 2
    clock["now"] += news_search.COOLDOWN_SECONDS + 1
    answers = [httpx.Response(200, content=FEED)]
    p._client = httpx.Client(transport=httpx.MockTransport(lambda request: answers.pop(0)))
    assert len(p.search("A different headline entirely")) == 2   # asks again once the pause is over


def test_a_very_long_retry_after_cannot_switch_the_check_off_for_hours(monkeypatch):
    clock = {"now": 1000.0}
    monkeypatch.setattr(news_search.time, "monotonic", lambda: clock["now"])
    p = provider_with(lambda request: httpx.Response(429, headers={"Retry-After": "86400"}))
    with pytest.raises(SearchUnavailable):
        p.search("Council approves budget")
    assert p._paused_until - clock["now"] == news_search.COOLDOWN_CAP_SECONDS


def test_a_network_error_becomes_a_search_failure():
    def boom(request):
        raise httpx.ConnectError("no route")

    with pytest.raises(SearchUnavailable, match="could not be reached"):
        provider_with(boom).search("Council approves budget")


# ---- the API ------------------------------------------------------------------------------------------------------

class StubDetector:
    language = "en"

    def __init__(self, result):
        self.result = result

    def analyse(self, headline, text):
        return dict(self.result)


@pytest.fixture
def news(monkeypatch):
    """Switches the check on with stand-ins; returns a function that sets the hits, the model's table and the text reading."""
    monkeypatch.setattr(get_settings(), "corroboration_enabled", True)
    state = {"search": FakeSearch(), "nli": ScriptedNli()}
    monkeypatch.setattr(svc, "get_news_search", lambda: state["search"])
    monkeypatch.setattr(svc, "get_nli", lambda: state["nli"])

    def setup(hits, table, reading):
        state["search"], state["nli"] = FakeSearch(hits), ScriptedNli(table)
        monkeypatch.setattr(svc, "choose_detector", lambda h, t: StubDetector(
            {"verdict": reading[0], "confidence": None if reading[0] == "Unverified" else 0.9, "reason": reading[1], "message": None,
             "language": "en", "token_count": 90}))
        return state
    return setup


def post_text(client, alice, headline=HEADLINE):
    r = client.post(f"{API}/analysis/text", json={"headline": headline, "text": ARTICLE}, headers=alice.headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_a_corroborated_headline_turns_an_undecided_reading_into_likely_real(client, alice, news):
    news([hit(SAME)], {SAME: (0.9, 0.0)}, ("Unverified", "low_confidence"))
    body = post_text(client, alice)
    assert body["verdict"] == "Likely Real" and body["confidence"] is None
    assert body["details"]["reason"] == "corroborated" and body["details"]["corroboration"]["status"] == "corroborated"
    assert body["details"]["corroboration"]["outlets"][0]["name"] == "Dawn"
    assert client.get(f"{API}/analysis/{body['id']}", headers=alice.headers).json()["details"]["corroboration"]["status"] == "corroborated"


def test_a_disputed_headline_never_becomes_likely_fake(client, alice, news):
    opposite = "City council rejects new transport budget after months of public hearings"
    news([hit(opposite)], {opposite: (0.0, 0.97)}, ("Likely Real", "model_leans_real"))
    body = post_text(client, alice)
    assert body["verdict"] == "Unverified" and body["details"]["reason"] == "disputed"


def test_the_headline_is_the_only_thing_sent_to_the_search(client, alice, news):
    state = news([hit(SAME)], {SAME: (0.9, 0.0)}, ("Unverified", "low_confidence"))
    post_text(client, alice)
    assert state["search"].queries == [HEADLINE]


def test_without_a_headline_nothing_is_searched_and_the_reading_stands(client, alice, news):
    state = news([hit(SAME)], {SAME: (0.9, 0.0)}, ("Unverified", "low_confidence"))
    r = client.post(f"{API}/analysis/text", json={"text": ARTICLE}, headers=alice.headers)
    assert r.status_code == 201
    assert r.json()["verdict"] == "Unverified" and r.json()["details"]["corroboration"]["reason"] == "no_headline" and state["search"].queries == []


def test_a_search_that_fails_does_not_fail_the_analysis(client, alice, news):
    state = news([], {}, ("Unverified", "low_confidence"))
    state["search"].error = SearchUnavailable("The news search is limiting requests right now.")
    body = post_text(client, alice)
    assert body["verdict"] == "Unverified" and body["details"]["corroboration"]["status"] == "unavailable"


def test_the_check_can_be_switched_off(client, alice, news, monkeypatch):
    state = news([hit(SAME)], {SAME: (0.9, 0.0)}, ("Unverified", "low_confidence"))
    monkeypatch.setattr(get_settings(), "corroboration_enabled", False)
    body = post_text(client, alice)
    assert body["verdict"] == "Unverified" and body["details"]["corroboration"]["reason"] == "disabled" and state["search"].queries == []


def test_the_check_is_rate_limited_per_user_without_failing_the_analysis(client, alice, news, monkeypatch):
    news([hit(SAME)], {SAME: (0.9, 0.0)}, ("Unverified", "low_confidence"))
    monkeypatch.setattr(get_settings(), "corroboration_rate_limit_per_minute", 1)
    assert post_text(client, alice)["details"]["corroboration"]["status"] == "corroborated"
    second = post_text(client, alice, HEADLINE + " again")
    assert second["details"]["corroboration"]["reason"] == "rate_limited" and second["verdict"] == "Unverified"


def test_a_settings_file_from_before_the_check_leaves_it_off_instead_of_failing(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(svc, "get_settings", lambda: SimpleNamespace())  # no corroboration_* fields at all
    r = svc._corroboration(SimpleNamespace(id=1), HEADLINE, "en", {})
    assert r["status"] == "skipped" and r["reason"] == "disabled"


def test_urdu_text_is_not_compared_with_english_news(client, alice, news, monkeypatch):
    state = news([hit(SAME)], {SAME: (0.9, 0.0)}, ("Unverified", "low_confidence"))
    monkeypatch.setattr(StubDetector, "language", "ur")
    body = post_text(client, alice)
    assert body["details"]["corroboration"]["reason"] == "english_only" and state["search"].queries == []


# ---- the web-address path -----------------------------------------------------------------------------------------

def page_html(title):
    paras = "".join(f"<p>{s.strip()}.</p>" for s in ARTICLE.split(".") if s.strip())
    return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>{title}</title>"
            f"<script type=\"application/ld+json\">{{\"@type\":\"NewsArticle\",\"headline\":\"{title}\"}}</script></head>"
            f"<body><article><h1>{title}</h1>{paras}</article></body></html>").encode()


@pytest.fixture
def served_page(monkeypatch):
    """Replaces the page download: the address given is 'fetched' as an article with the headline set by the test."""
    from app.ml.url_analysis.fetch import FetchResult
    holder = {"title": HEADLINE}

    def fake_fetch(url):
        return FetchResult(requested_url=url, final_url=url, status=200, content_type="text/html", charset="utf-8",
                           body=page_html(holder["title"]), truncated=False)
    monkeypatch.setattr(svc.url_fetch, "fetch", fake_fetch)
    return holder


def post_url(client, alice, url):
    r = client.post(f"{API}/analysis/url", json={"url": url}, headers=alice.headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_an_article_from_an_unlisted_site_is_checked_against_listed_outlets(client, alice, news, served_page):
    state = news([hit(SAME)], {SAME: (0.9, 0.0)}, ("Unverified", "low_confidence"))
    body = post_url(client, alice, "https://blog.example.org/story")
    assert body["details"]["corroboration"]["status"] == "corroborated" and body["verdict"] == "Likely Real"
    assert state["search"].queries == [HEADLINE]


def test_an_article_is_not_confirmed_by_the_same_outlets_own_page(client, alice, news, served_page):
    news([hit(SAME)], {SAME: (0.9, 0.0)}, ("Likely Fake", "model_leans_fake"))
    body = post_url(client, alice, "https://www.dawn.com/news/12345/story")
    assert body["details"]["corroboration"]["status"] == "not_found" and body["details"]["corroboration"]["excluded_outlet"] == "Dawn"
    assert body["details"]["corroboration"]["listed_outlet_results"] == 0


def test_a_page_on_a_listed_outlets_own_site_turns_an_undecided_reading_into_likely_real(client, alice, news, served_page):
    news([], {}, ("Unverified", "low_confidence"))
    body = post_url(client, alice, "https://www.dawn.com/news/12345/story")
    assert body["verdict"] == "Likely Real" and body["details"]["reason"] == "published_by_listed_outlet"
    assert "Dawn" in body["details"]["message"] and "not that what it says is accurate" in body["details"]["message"]


def test_a_fake_looking_reading_on_a_listed_outlets_site_is_not_a_call_either_way(client, alice, news, served_page):
    news([], {}, ("Likely Fake", "model_leans_fake"))
    body = post_url(client, alice, "https://www.dawn.com/news/12345/story")
    assert body["verdict"] == "Unverified" and body["details"]["reason"] == "signals_differ"


def test_an_unlisted_or_look_alike_site_gets_no_credit_for_its_address(client, alice, news, served_page):
    news([], {}, ("Unverified", "low_confidence"))
    for url in ("https://blog.example.org/story", "https://www.dawn-news-live.com/story", "https://dawn.com.evil.example/story"):
        body = post_url(client, alice, url)
        assert body["verdict"] == "Unverified" and body["details"]["reason"] == "low_confidence", url


def test_a_disputed_headline_on_a_listed_outlets_site_stays_unverified(client, alice, news, served_page):
    opposite = "City council rejects new transport budget after months of public hearings"
    news([hit(opposite, "https://www.bbc.com", "BBC")], {opposite: (0.0, 0.97)}, ("Unverified", "low_confidence"))
    body = post_url(client, alice, "https://www.dawn.com/news/12345/story")
    assert body["verdict"] == "Unverified" and body["details"]["corroboration"]["status"] == "disputed"
    assert body["details"]["reason"] == "low_confidence"  # the style reading's own reason; the difference is shown in its own section


def test_the_site_rule_needs_a_readable_article(client, alice, news, served_page):
    news([], {}, ("Unverified", "low_confidence"))
    served_page["title"] = HEADLINE
    import app.services.analysis_service as module
    original = module.url_fetch.fetch

    def short_page(url):
        r = original(url)
        r.body = b"<html><head><title>x</title></head><body><p>Only a few words here.</p></body></html>"
        return r
    module.url_fetch.fetch = short_page
    try:
        body = post_url(client, alice, "https://www.dawn.com/news/12345/story")
    finally:
        module.url_fetch.fetch = original
    assert body["verdict"] == "Unverified" and body["details"]["reason"] == "article_not_readable"


def test_a_declared_satire_site_is_not_compared_with_news(client, alice, news, served_page):
    state = news([hit(SAME)], {SAME: (0.9, 0.0)}, ("Unverified", "low_confidence"))
    body = post_url(client, alice, "https://www.theonion.com/story")
    assert body["details"]["corroboration"]["reason"] == "declared_satire" and state["search"].queries == []
    assert body["verdict"] == "Unverified" and body["details"]["reason"] == "declared_satire"


def test_the_pdf_report_includes_the_headline_comparison(client, alice, news):
    news([hit(SAME)], {SAME: (0.9, 0.0)}, ("Unverified", "low_confidence"))
    aid = post_text(client, alice)["id"]
    r = client.get(f"{API}/analysis/{aid}/report.pdf", headers=alice.headers)
    assert r.status_code == 200 and r.content.startswith(b"%PDF") and r.content.rstrip().endswith(b"%%EOF")
    import io

    from pypdf import PdfReader  # noqa: PLC0415  (only the report tests need it)
    text = " ".join(pg.extract_text() for pg in PdfReader(io.BytesIO(r.content)).pages)
    assert "Headline compared with news reports" in text and "Dawn" in text and "Corroborated" in text and "Searched for" in text


def test_related_coverage_reaches_the_api_and_the_pdf_without_changing_the_verdict(client, alice, news):
    related = "Council debates how to spend the transport budget"
    news([hit(related, "https://www.bbc.com", "BBC")], {}, ("Unverified", "low_confidence"))
    body = post_text(client, alice)
    corr = body["details"]["corroboration"]
    assert corr["status"] == "not_found" and [x["name"] for x in corr["related"]] == ["BBC"]
    assert body["verdict"] == "Unverified" and body["details"]["reason"] == "low_confidence"   # shown, never counted
    r = client.get(f"{API}/analysis/{body['id']}/report.pdf", headers=alice.headers)
    import io

    from pypdf import PdfReader  # noqa: PLC0415
    text = " ".join(pg.extract_text() for pg in PdfReader(io.BytesIO(r.content)).pages)
    assert "Related coverage by listed outlets" in text and related in text


def test_a_pdf_report_is_made_when_the_check_was_unavailable(client, alice, news):
    state = news([], {}, ("Unverified", "low_confidence"))
    state["search"].error = SearchUnavailable("The news search could not be reached.")
    aid = post_text(client, alice)["id"]
    assert client.get(f"{API}/analysis/{aid}/report.pdf", headers=alice.headers).status_code == 200
