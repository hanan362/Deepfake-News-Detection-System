"""Evidence checking: claim picking, providers, the verdict rules and the API. Retrieval is replaced by canned passages
(the tests need no internet); the inference model is real where the packages are installed, a stub for the rules."""
import io
import urllib.error

import pytest

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.ml.fact_checking import providers as prov
from app.ml.fact_checking import verify as ver
from app.ml.fact_checking.claims import extract_claims
from app.ml.fact_checking.nli import NliModel, get_nli
from app.ml.fact_checking.providers import Evidence, ProviderResult
from app.models import AuditLog, Claim, EvidenceSource
from app.services import analysis_service
from tests.conftest import API, ARTICLE

needs_nli = pytest.mark.skipif(not get_nli().available, reason="NLI packages or model not available (pip install -r backend/requirements-ml.txt)")

JACKIE = "Jackie is a 2016 biographical drama film directed by Pablo Larraín and written by Noah Oppenheim. It stars Natalie Portman as Jacqueline Kennedy."


class StubNli:
    """Entails when the passage contains the word 'confirmed', contradicts when it contains 'denied'."""
    model_id = "stub"
    available = True

    def predict(self, pairs):
        return [{"entailment": 0.95 if "confirmed" in p else 0.02, "contradiction": 0.95 if "denied" in p else 0.02,
                 "neutral": 0.1} for p, _h in pairs]


class NoNli(StubNli):
    available = False
    model_id = "none"


class FakeProvider:
    def __init__(self, result: ProviderResult, name="fake"):
        self.result, self.name = result, name

    def search(self, claim):
        return self.result


def passage(text, title="Council budget", kind="encyclopedia", **kw):
    return Evidence("fake", kind, title, "https://en.wikipedia.org/wiki/Council_budget", text, **kw)


CLAIM = "The city council approved the new transport budget on Tuesday."


# ------------------------------------------------------------------ claim picking

def test_checkable_sentences_are_picked_and_opinions_and_questions_are_not():
    text = ("What will the council do next? I think the plan is too ambitious for the city. "
            "The city council approved a 12 million dollar budget on Tuesday in Karachi. "
            "Mayor Ali Khan said the project would finish in 2028. It was a nice day.")
    picked = extract_claims(text)
    assert picked == ["The city council approved a 12 million dollar budget on Tuesday in Karachi.", "Mayor Ali Khan said the project would finish in 2028."]


def test_no_claims_in_a_text_without_facts():
    assert extract_claims("Wow. So nice. I think we should all relax and enjoy the weather today everyone.") == []
    assert len(extract_claims(" ".join([f"Officer Smith arrested {n} suspects in Lahore on Monday." for n in range(10)]), limit=3)) == 3


# ------------------------------------------------------------------ providers

def test_wikipedia_results_are_parsed_in_search_order(monkeypatch):
    monkeypatch.setattr(prov, "_get_json", lambda url: {"query": {"pages": {
        "2": {"index": 2, "title": "B", "fullurl": "https://en.wikipedia.org/wiki/B", "extract": "Second page text."},
        "1": {"index": 1, "title": "A", "fullurl": "https://en.wikipedia.org/wiki/A", "extract": "First page text."},
        "3": {"index": 3, "title": "C", "fullurl": "u", "extract": ""}}}})
    r = prov.WikipediaProvider().search("Some claim about A and B")
    assert r.status == "ok" and [e.title for e in r.evidence] == ["A", "B"]


@pytest.mark.parametrize("claim,subject", [
    ("The Eiffel Tower is located in Rome, Italy.", "Eiffel Tower"),
    ("Apollo 11 landed on the Moon in 1975.", "Apollo 11"),
    ("The Pyramids of Giza are located in Mexico.", "Pyramids of Giza"),
    ("Leonardo da Vinci painted the Mona Lisa.", "Leonardo da Vinci"),
    ("Mount Fuji is the highest mountain in China.", "Mount Fuji"),
    ("Beethoven composed The Four Seasons.", "Beethoven"),
    ("the city council approved a budget", None),
    ("12 million people live there.", None),
])
def test_the_subject_a_claim_starts_with_is_found_by_spelling(claim, subject):
    assert prov.subject_phrase(claim) == subject


def _page(title, text="Some text."):
    return prov.Evidence("wikipedia", "encyclopedia", title, "u", text)


def test_pages_about_the_subject_come_first_and_a_page_found_twice_is_kept_once():
    merged = prov.merge_evidence([_page("Eiffel Tower"), _page("Gustave Eiffel")], [_page("Mini-Europe"), _page("eiffel tower"), _page("Seven Wonders Park")])
    assert [e.title for e in merged] == ["Eiffel Tower", "Gustave Eiffel", "Mini-Europe", "Seven Wonders Park"]


def test_a_second_search_for_the_subject_finds_the_page_the_wrong_details_hid(monkeypatch):
    urls = []

    def fake(url):
        urls.append(url)
        if "gsrsearch=Eiffel+Tower" in url:
            return {"query": {"pages": {"1": {"index": 1, "title": "Eiffel Tower", "fullurl": "u1", "extract": "A lattice tower in Paris, France."}}}}
        return {"query": {"pages": {"2": {"index": 1, "title": "Mini-Europe", "fullurl": "u2", "extract": "A miniature park in Brussels."}}}}

    monkeypatch.setattr(prov, "_get_json", fake)
    r = prov.WikipediaProvider().search("The Eiffel Tower is located in Rome, Italy.")
    assert [e.title for e in r.evidence] == ["Eiffel Tower", "Mini-Europe"]
    assert len(urls) == 2 and "gsrlimit=2" in urls[1] and "rome" not in urls[1].lower()


def test_if_the_subject_search_fails_the_first_search_still_counts(monkeypatch):
    calls = []

    def fake(url):
        calls.append(url)
        if len(calls) == 2:
            raise urllib.error.URLError("down")
        return {"query": {"pages": {"1": {"index": 1, "title": "Mini-Europe", "fullurl": "u", "extract": "A miniature park."}}}}

    monkeypatch.setattr(prov, "_get_json", fake)
    r = prov.WikipediaProvider().search("The Eiffel Tower is located in Rome, Italy.")
    assert r.status == "ok" and [e.title for e in r.evidence] == ["Mini-Europe"]


@pytest.mark.parametrize("exc,expected", [
    (urllib.error.HTTPError("u", 429, "Too Many", {}, io.BytesIO()), "limiting requests"),
    (urllib.error.HTTPError("u", 500, "x", {}, io.BytesIO()), "error (500)"),
    (urllib.error.URLError("down"), "could not be reached"),
])
def test_provider_failures_are_reported_not_hidden(monkeypatch, exc, expected):
    def boom(url):
        raise exc
    monkeypatch.setattr(prov, "_get_json", boom)
    r = prov.WikipediaProvider().search("Some claim about something")
    assert r.status == "error" and expected in r.message and r.evidence == []


class _FakeResponse:
    def __init__(self, body: bytes):
        self._body = body

    def read(self, n=-1):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _http_error(code, retry_after=None):
    headers = {"Retry-After": retry_after} if retry_after is not None else {}
    return urllib.error.HTTPError("u", code, "x", headers, io.BytesIO())


def _script_urlopen(monkeypatch, outcomes):
    """Make urlopen return or raise the given outcomes in order; record the waits instead of sleeping."""
    calls, waits = [], []

    def fake_urlopen(req, timeout=None):
        calls.append(1)
        outcome = outcomes[len(calls) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return _FakeResponse(outcome)

    monkeypatch.setattr(prov.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(prov, "_sleep", waits.append)
    return calls, waits


def test_a_short_429_is_retried_and_the_answer_is_used(monkeypatch):
    calls, waits = _script_urlopen(monkeypatch, [_http_error(429), _http_error(503, "2"), b'{"ok": true}'])
    assert prov._get_json("https://example.org/x") == {"ok": True}
    assert len(calls) == 3
    assert waits == [1.0, 2.0]  # first: plain back-off; second: the server's Retry-After


def test_retry_after_is_capped_and_the_retries_are_bounded(monkeypatch):
    calls, waits = _script_urlopen(monkeypatch, [_http_error(429, "3600")] * 5)
    with pytest.raises(urllib.error.HTTPError) as caught:
        prov._get_json("https://example.org/x")
    assert caught.value.code == 429
    assert len(calls) == prov.MAX_ATTEMPTS
    assert waits and max(waits) <= prov.MAX_WAIT_SECONDS


def test_other_errors_are_not_retried(monkeypatch):
    calls, waits = _script_urlopen(monkeypatch, [_http_error(404), b"{}"])
    with pytest.raises(urllib.error.HTTPError):
        prov._get_json("https://example.org/x")
    assert len(calls) == 1 and waits == []


def test_wikipedia_still_says_so_when_the_limit_does_not_clear(monkeypatch):
    _script_urlopen(monkeypatch, [_http_error(429)] * 5)
    r = prov.WikipediaProvider().search("Some claim about something")
    assert r.status == "error" and "limiting requests" in r.message


def test_the_fact_check_provider_needs_a_key_and_reports_ratings_as_published(monkeypatch):
    assert prov.GoogleFactCheckProvider(None).search("x claim").status == "not_configured"
    monkeypatch.setattr(prov, "_get_json", lambda url: {"claims": [{"text": "Claim text", "claimReview": [
        {"publisher": {"name": "Some Checker"}, "url": "https://checker.example/1", "title": "Checked", "textualRating": "Mostly false", "reviewDate": "2026-01-02"}]}]})
    r = prov.GoogleFactCheckProvider("key").search("Claim text here")
    assert r.status == "ok" and r.evidence[0].rating == "Mostly false" and r.evidence[0].publisher == "Some Checker"


# ------------------------------------------------------------------ verdict rules

def run(passages, nli=None, results=None):
    provs = [FakeProvider(ProviderResult("fake", "ok" if passages else "no_results", "", passages))] + [FakeProvider(r) for r in (results or [])]
    return ver.verify_claim(CLAIM, provs, nli or StubNli())


def test_support_contradiction_mixed_and_insufficient():
    assert run([passage("The city council confirmed it approved the new transport budget on Tuesday.")])["verdict"] == "Supported"
    assert run([passage("The city council denied it approved the new transport budget on Tuesday.")])["verdict"] == "Contradicted"
    mixed = run([passage("The city council confirmed it approved the new transport budget on Tuesday."),
                 passage("The council denied that it approved the new transport budget on Tuesday.", title="Other")])
    assert mixed["verdict"] == "Mixed Evidence"
    assert run([passage("The council met on Tuesday to discuss the transport budget and other matters.")])["verdict"] == "Insufficient Evidence"


def test_nothing_found_is_insufficient_evidence_never_a_guess():
    r = run([])
    assert r["verdict"] == "Insufficient Evidence" and r["evidence"] == [] and "No evidence was found" in r["reason"]


def test_passages_that_are_not_about_the_claim_are_ignored_even_if_the_model_is_sure():
    r = run([passage("Giraffes confirmed their place as the tallest animals in the savanna.", title="Giraffe")])
    assert r["evidence"][0]["stance"] == "not_relevant" and r["verdict"] == "Insufficient Evidence"


def test_without_the_inference_model_evidence_is_listed_but_not_judged():
    r = run([passage("The city council confirmed it approved the new transport budget on Tuesday.")], nli=NoNli())
    assert r["verdict"] == "Insufficient Evidence" and r["evidence"][0]["stance"] == "not_assessed" and "not available" in r["reason"] and r["stance_model"] is None


def test_an_unreachable_or_unconfigured_source_is_named_in_the_result():
    r = run([passage("The council met on Tuesday to discuss the transport budget and other matters.")],
            results=[ProviderResult("google_fact_check", "not_configured", "No API key is set")])
    assert r["verdict"] == "Insufficient Evidence" and "could not be searched" in r["reason"]
    assert {p["status"] for p in r["providers"]} == {"ok", "not_configured"}


def test_published_fact_checks_keep_their_own_rating_and_do_not_decide_the_verdict():
    fc = ProviderResult("fc", "ok", "", [passage("The city council approved the new transport budget on Tuesday.", title="Fact check", kind="fact_check", rating="False", publisher="Checker")])
    r = ver.verify_claim(CLAIM, [FakeProvider(fc)], StubNli())
    assert r["evidence"][0]["stance"] == "published_rating" and r["evidence"][0]["rating"] == "False" and r["verdict"] == "Insufficient Evidence"
    assert "fact-checks" in r["reason"]


def test_overall_verdict_across_claims():
    v = lambda *x: ver.overall_verdict([{"verdict": i} for i in x])  # noqa: E731
    assert v() == "Insufficient Evidence" and v("Insufficient Evidence", "Insufficient Evidence") == "Insufficient Evidence"
    assert v("Supported", "Insufficient Evidence") == "Supported" and v("Contradicted", "Insufficient Evidence") == "Contradicted"
    assert v("Supported", "Contradicted") == "Mixed Evidence"


@needs_nli
def test_the_real_inference_model_contradicts_a_wrong_claim_and_supports_a_right_one():
    nli = get_nli()
    wrong, right = nli.predict([(JACKIE, "Jackie (2016 film) was directed by Peter Jackson."), (JACKIE, "Jackie is a 2016 film directed by Pablo Larraín.")])
    assert wrong["contradiction"] > 0.85 and right["entailment"] > 0.85


# ------------------------------------------------------------------ the API

@pytest.fixture
def canned(monkeypatch):
    """Evidence providers replaced by canned passages. Returns a list the test can fill."""
    store: list[Evidence] = []
    monkeypatch.setattr(analysis_service, "WikipediaProvider", lambda: FakeProvider(ProviderResult("wikipedia", "ok" if store else "no_results", "", list(store)), "wikipedia"))
    monkeypatch.setattr(analysis_service, "GoogleFactCheckProvider", lambda key: FakeProvider(ProviderResult("google_fact_check", "not_configured", "No API key is set"), "google_fact_check"))
    monkeypatch.setattr(analysis_service, "get_nli", lambda: StubNli())
    return store


def _post(client, user, text):
    return client.post(f"{API}/analysis/evidence", json={"text": text}, headers=user.headers)


def test_a_claim_is_checked_stored_with_its_evidence_and_listed(client, alice, canned):
    canned.append(passage("The city council confirmed it approved the new transport budget on Tuesday."))
    r = _post(client, alice, CLAIM)
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["analysis_type"] == "evidence" and a["verdict"] == "Supported" and a["confidence"] is None
    c = a["details"]["claims"][0]
    assert c["claim"] == CLAIM and c["evidence"][0]["stance"] == "supports" and c["evidence"][0]["stance_probabilities"]["entailment"] > 0.85
    assert {p["provider"]: p["status"] for p in c["providers"]} == {"wikipedia": "ok", "google_fact_check": "not_configured"}
    with SessionLocal() as db:
        assert db.query(Claim).one().verdict == "Supported" and db.query(EvidenceSource).one().stance == "supports"
    assert client.get(f"{API}/analysis?analysis_type=evidence", headers=alice.headers).json()["total"] == 1
    assert client.get(f"{API}/dashboard/stats", headers=alice.headers).json()["by_type"] == {"evidence": 1}
    pdf = client.get(f"{API}/analysis/{a['id']}/report.pdf", headers=alice.headers)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert client.delete(f"{API}/analysis/{a['id']}", headers=alice.headers).status_code == 204
    with SessionLocal() as db:
        assert db.query(Claim).count() == 0 and db.query(EvidenceSource).count() == 0  # nothing is left behind


def test_nothing_found_gives_insufficient_evidence_through_the_api(client, alice, canned):
    a = _post(client, alice, CLAIM).json()
    assert a["verdict"] == "Insufficient Evidence" and a["details"]["claims"][0]["evidence"] == []
    assert "No evidence was found" in a["details"]["message"] and "does not mean the claim is false" in a["limitations"]


def test_a_passage_gives_up_to_five_claims_and_says_they_were_picked_automatically(client, alice, canned):
    text = " ".join(f"Officer Smith arrested {n + 2} suspects in Lahore on Monday." for n in range(8))
    a = _post(client, alice, text).json()
    assert len(a["details"]["claims"]) == 5 and a["details"]["claims_picked_automatically"] is True


def test_text_without_a_checkable_claim_is_refused_clearly(client, alice, canned):
    # a short text is taken as the claim itself; a long passage is searched for claims, and this one has none
    r = _post(client, alice, " ".join(["I think we should all relax and enjoy the weather today everyone, really."] * 6))
    assert r.status_code == 422 and r.json()["error"]["code"] == "NO_CLAIMS_FOUND"
    assert client.get(f"{API}/analysis", headers=alice.headers).json()["total"] == 0


def test_validation_auth_privacy_audit_switch_and_rate_limit(client, alice, bob, canned, monkeypatch):
    assert client.post(f"{API}/analysis/evidence", json={"text": CLAIM}).status_code == 401
    assert _post(client, alice, "short").status_code == 422
    a = _post(client, alice, CLAIM).json()
    assert client.get(f"{API}/analysis/{a['id']}", headers=bob.headers).status_code == 404
    with SessionLocal() as db:
        assert db.query(AuditLog).filter(AuditLog.action == "analysis.evidence").count() == 1
    monkeypatch.setattr(get_settings(), "url_fetch_rate_limit_per_minute", 2)
    assert [_post(client, alice, CLAIM).status_code for _ in range(2)] == [201, 429]
    monkeypatch.setattr(get_settings(), "evidence_enabled", False)
    assert _post(client, bob, CLAIM).status_code == 503


def test_registry_entry_is_honest_about_what_it_needs(client, admin):
    m = {x["module"]: x for x in client.get(f"{API}/models", headers=admin.headers).json()["models"]}["evidence"]
    assert m["status"] in {"pretrained", "heuristic"} and "never invented" in m["description"]
    assert any("GOOGLE_FACT_CHECK_API_KEY" in x for x in m["limitations"])


def test_unused_text_model_import_is_not_needed():
    assert ARTICLE and NliModel  # keeps the shared imports used


# ------------------------------------------------------------------ preparing evidence before it is judged

def test_pronunciation_brackets_are_removed_but_other_brackets_stay():
    eiffel = "The Eiffel Tower (  EYE-fəl; French: Tour Eiffel [tuʁ ɛfɛl] ) is a lattice tower on the Champ de Mars in Paris, France."
    assert ver.strip_pronunciation(eiffel) == "The Eiffel Tower is a lattice tower on the Champ de Mars in Paris, France."
    dated = "Muhammad Ali Jinnah (25 December 1876 – 11 September 1948) was a barrister and statesman."
    assert ver.strip_pronunciation(dated) == dated
    assert ver.strip_pronunciation("Zürich (German: Zürich) is a city in Switzerland.") == "Zürich (German: Zürich) is a city in Switzerland."


@pytest.mark.parametrize("sentence,title,expected", [
    ("She shared the 1903 Nobel Prize in Physics.", "Marie Curie", "Marie Curie shared the 1903 Nobel Prize in Physics."),
    ("It was held in Australia and New Zealand.", "1992 Cricket World Cup", "1992 Cricket World Cup was held in Australia and New Zealand."),
    ("His work changed physics.", "Isaac Newton", "Isaac Newton's work changed physics."),
    ("It stars Natalie Portman.", "Jackie (2016 film)", "Jackie stars Natalie Portman."),
    ("Italy is a country in Europe.", "Italy", "Italy is a country in Europe."),       # "It" inside a word is not a pronoun
    ("The tower is 330 metres tall.", "Eiffel Tower", "The tower is 330 metres tall."),
    ("They won.", "", "They won."),
])
def test_a_leading_pronoun_is_replaced_by_the_page_subject(sentence, title, expected):
    assert ver.name_the_subject(sentence, title) == expected


def test_a_page_about_a_namesake_does_not_count_unless_the_claim_names_it():
    titles = ["Eiffel Tower", "Eiffel Tower (Paris, Texas)", "Eiffel Tower (Paris, Tennessee)", "Eiffel Tower replicas and derivatives"]
    assert ver.namesake_titles(titles, "The Eiffel Tower is located in Paris, France.") == {"Eiffel Tower (Paris, Texas)", "Eiffel Tower (Paris, Tennessee)"}
    assert ver.namesake_titles(titles, "The Eiffel Tower in Paris, Texas is a scale model.") == {"Eiffel Tower (Paris, Tennessee)"}
    # a bracketed title with no plain twin among the results is the only page on the subject and is kept
    assert ver.namesake_titles(["Mercury (planet)", "Solar System"], "Mercury is the closest planet to the Sun.") == set()


def test_the_verdict_ignores_a_namesake_page_and_says_so():
    right = passage("The city council confirmed it approved the new transport budget on Tuesday.", title="Council budget")
    namesake = passage("The council denied it approved the new transport budget on Tuesday.", title="Council budget (Springfield)")
    r = run([right, namesake])
    assert r["verdict"] == "Supported"
    assert [e["stance"] for e in r["evidence"]] == ["supports", "other_subject"]


def test_the_sentence_given_to_the_model_names_its_subject():
    seen = []

    class Recording(StubNli):
        def predict(self, pairs):
            seen.extend(pairs)
            return super().predict(pairs)

    run([passage("She confirmed the city council approved the new transport budget on Tuesday.", title="Mayor Ali Khan")], nli=Recording())
    assert seen and seen[0][0].startswith("Mayor Ali Khan confirmed")


@needs_nli
def test_the_real_model_is_not_thrown_by_a_pronunciation_guide():
    claim = "The Eiffel Tower is located in Paris, France."
    raw = "The Eiffel Tower (  EYE-fəl; French: Tour Eiffel [tuʁ ɛfɛl] ) is a lattice tower on the Champ de Mars in Paris, France."
    p = get_nli().predict([(ver.strip_pronunciation(raw), claim)])[0]
    assert p["contradiction"] < 0.5 and p["entailment"] > p["contradiction"]
