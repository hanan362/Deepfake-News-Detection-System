"""The text-against-headline check: the rules, how a result changes a verdict, and the API and PDF. No test loads the inference
model: it is replaced by a small stand-in that answers from the words of the sentence."""
import pytest

from app.core.config import get_settings
from app.ml.corroboration import consistency, text_match_verdict
from app.services import analysis_service as svc
from tests.conftest import API, ARTICLE
from tests.test_corroboration import HEADLINE, SAME, ScriptedNli, hit, news, post_text, served_page, post_url  # noqa: F401


class RuleNli:
    """Entailment 0.9 when the premise contains `says`; contradiction 0.95 when it contains `denies`; otherwise neutral. Headline-to-headline
    comparisons (the news check) are answered from `table` like the other tests."""
    model_id = "rule"
    available = True

    def __init__(self, says=None, denies=None, table=None):
        self.says, self.denies, self.table = says, denies, table or {}

    def predict(self, pairs):
        out = []
        for premise, _hyp in pairs:
            if premise in self.table:
                e, c = self.table[premise]
            elif self.says and self.says in premise:
                e, c = 0.9, 0.02
            elif self.denies and self.denies in premise:
                e, c = 0.02, 0.95
            else:
                e, c = 0.02, 0.02
            out.append({"entailment": e, "contradiction": c, "neutral": max(0.0, 1 - e - c)})
        return out


class Broken(RuleNli):
    def predict(self, pairs):
        raise RuntimeError("boom")


class NotInstalled(RuleNli):
    available = False


H = "City council approves new transport budget after months of public hearings"
TEXT = (
    "The city council voted on Tuesday evening to approve a new budget that increases funding for public transport, road repairs and "
    "local libraries over the next two years. Council members from both parties said the plan followed months of public hearings and "
    "reviews by independent auditors. The mayor told reporters that the measure would be paid for through a modest increase in parking "
    "fees. Opposition members argued that the schedule was too ambitious and asked for quarterly progress reports."
)
ELSEWHERE = (
    "A swimmer crossed the channel on Saturday in a record time of nine hours, according to the organisers of the event. Rough seas and "
    "cold water slowed the early part of the swim, but the weather improved after midday. Supporters followed the swimmer by boat and "
    "cheered from the shore when the crossing was completed late in the evening."
)


def run(headline, text, nli):
    return consistency.check(headline, text, nli)


# ---- the rules -------------------------------------------------------------------------------------------------------

def test_a_text_that_says_what_the_headline_says_is_consistent():
    r = run(H, TEXT, RuleNli(says="voted on Tuesday evening to approve"))
    assert r["status"] == "consistent" and "approve a new budget" in r["best"]["text"] and r["missing"] == []


def test_a_text_about_another_story_is_unrelated():
    r = run(H, ELSEWHERE, RuleNli())
    assert r["status"] == "unrelated" and r["best"]["overlap"] < consistency.UNRELATED_OVERLAP


def test_a_text_that_says_the_opposite_is_flagged():
    text = TEXT.replace("to approve a new budget", "to reject a new budget")
    r = run(H, text, RuleNli(denies="to reject a new budget"))
    assert r["status"] == "contradicts" and r["best"]["contradiction"] >= consistency.CONTRADICT_PROBABILITY


def test_a_changed_number_or_name_is_flagged_when_the_model_sees_nothing_wrong():
    headline = "Seven people died in the Springfield plant explosion on Tuesday"
    text = ("Three people died in the Springfield plant explosion on Tuesday, officials said, and the cause is being investigated by the "
            "fire service. The plant makes car parts and employs about two hundred people in the town. The company said it would help "
            "the families of those affected and would cooperate fully with the investigation into what happened.")
    r = run(headline, text, RuleNli())
    assert r["status"] == "details_differ" and r["missing"] == ["7"]


def test_the_same_numbers_and_names_written_another_way_are_the_same():
    headline = "Five killed as U.S. strike hits Gaza hospital, officials say"
    text = ("Officials said 5 people were killed when a strike by the United States hit a hospital in Gaza on Monday morning. Rescue teams "
            "were still searching the building, and the health ministry said the number could rise. The hospital had been treating more "
            "than two hundred patients when the strike happened.")
    r = run(headline, text, RuleNli(says="people were killed"))
    assert r["status"] == "consistent", r


def test_a_text_on_the_subject_that_does_not_state_the_headline_is_not_stated_and_not_a_mismatch():
    text = ("The city council met on Tuesday to discuss transport and other matters of the budget for the coming year. Members spoke about "
            "libraries, roads and the cost of hearings for the public. The mayor was not available for comment on the day of the meeting. "
            "A vote is expected at a later date once the auditors have finished their reviews.")
    r = run(H, text, RuleNli())
    assert r["status"] == "not_stated"
    assert consistency.combine_text_match({"verdict": "Likely Real", "reason": "corroborated"}, r)["verdict"] == "Likely Real"


def test_a_line_that_only_repeats_the_headline_is_not_evidence():
    r = run(H, H + ". " + ELSEWHERE, RuleNli(says=H))
    assert r["status"] == "unrelated"          # the repeated headline does not make an unrelated text consistent


def test_the_first_word_of_a_headline_counts_when_it_is_a_name_but_not_when_it_only_opens_the_headline():
    assert consistency.missing_specifics("Iraq wants diplomacy over Iran talks", "Iran wants diplomacy over its talks") == ["iraq"]
    assert consistency.missing_specifics("How a teen gamer helped rescue a missing girl", "A teen gamer helped rescue a girl who was missing") == []
    assert consistency.missing_specifics("Nvidia chief meets minister", "The chief of Nvidia met the minister") == []


def test_abbreviations_and_possessives_do_not_cause_false_alarms():
    assert consistency.missing_specifics(consistency._normalise("UK’s PM visits Korea’s capital"), consistency._normalise("The British prime minister visited the Korean capital")) == []


def test_an_amount_is_the_same_amount_however_it_is_written():
    n = consistency._normalise
    assert n("Pakistan and Oman seal $200m energy deal") == "Pakistan and Oman seal 200000000 energy deal"
    assert n("worth 200 million dollars") == "worth 200000000 dollars" and n("two million") == "2000000" and n("$1.5bn") == "1500000000"
    assert consistency.missing_specifics(n("Oman seals $200m deal"), n("Oman signed an agreement worth 200 million dollars")) == []
    assert consistency.missing_specifics(n("Oman seals $200m deal"), n("Oman signed an agreement worth 300 million dollars")) == ["200000000"]
    assert n("a 50km road") == "a 50km road"          # a distance is not an amount


def test_a_title_before_a_name_is_not_a_name_but_the_name_is():
    h = "India and Finland seek closer ties, says Envoy Mikko Kivinen"
    assert consistency.missing_specifics(h, "The ambassador, Mikko Kivinen, said India and Finland want closer ties") == []
    assert consistency.missing_specifics(h, "The ambassador, Pekka Virtanen, said India and Finland want closer ties") == ["kivinen", "mikko"]


def test_a_number_or_name_that_comes_after_the_sentences_that_were_read_still_counts_as_in_the_text():
    headline = "Seven people died in the Springfield plant explosion on Tuesday"
    early = ("People died in the Springfield plant explosion on Tuesday, officials said, and the cause is being investigated by the fire "
             "service. The plant makes car parts and employs about two hundred people in the town. ")
    filler = " ".join(f"Another sentence about the town and its history, part {'abcdefghijkl'[i]}." for i in range(12))
    later = " The final toll was confirmed late on Wednesday: seven people died."
    r = run(headline, early + filler + later, RuleNli(says="People died in the Springfield"))
    assert r["status"] == "consistent" and r["missing"] == []
    r = run(headline, early + filler, RuleNli())
    assert r["missing"] == ["7"]


def test_a_first_word_that_is_an_ordinary_word_is_not_a_name_but_a_name_is():
    spec = consistency.missing_specifics
    assert spec("Widowed amid war and displacement, mothers struggle to survive", "Mothers lost their husbands and struggle to survive") == []
    assert spec("Like Tesla, Rivian ran an unusual stock market listing and annoyed some bankers", "Rivian ran an unusual stock market listing") == ["tesla"]   # a name later in the headline still counts
    assert spec("Centre releases funds for flood relief", "The government released funds for flood relief") == []   # British spelling
    assert spec("Ex-UK PM Theresa May tells successor to move on", "Theresa May told her successor to move on") == []
    assert spec("Trump says tariffs will rise", "The president said tariffs will rise") == ["trump"]      # an ordinary word that is also a name stays a name
    assert spec("Sudan accuses neighbour of arming militia", "A neighbour is accused of arming a militia") == ["sudan"]
    assert spec("Iraq wants diplomacy over Iran talks", "Iran wants diplomacy over its talks") == ["iraq"]


def test_without_the_word_list_a_capitalised_first_word_counts_as_a_name_as_before(monkeypatch):
    monkeypatch.setattr(consistency, "_ordinary_words", lambda: frozenset())
    assert consistency.missing_specifics("Like Tesla, Rivian ran an unusual stock market listing and annoyed some bankers", "Rivian ran an unusual stock market listing") == ["like", "tesla"]


def test_a_year_in_the_headline_is_not_required_in_the_text_but_other_numbers_are():
    spec = consistency.missing_specifics
    assert spec("States agree to talks on killer robots by 2028", "The states agreed to hold talks on killer robots") == []
    n = consistency._normalise
    assert spec(n("Seven people died in the 2024 floods"), n("People died in the floods")) == ["7"]


def test_a_headline_that_is_a_question_cannot_be_contradicted():
    class Opposite(RuleNli):
        def predict(self, pairs):
            return [{"entailment": 0.0, "contradiction": 0.95, "neutral": 0.05} for _ in pairs]
    text = ("Not long ago the world was talking about the rise of the far right in many countries and what it meant for politics. "
            "Voters in several countries have since turned away from the parties that led that surge and elections went another way. ")
    assert run("Is the global far right really in retreat after the elections?", text, Opposite())["status"] != "contradicts"
    assert run("The global far right is in retreat after the elections", text, Opposite())["status"] == "contradicts"


@pytest.mark.parametrize("a,b", [("Nigerian", "Nigeria"), ("Korea", "Korean")])
def test_words_that_start_alike_count_as_the_same_name(a, b):
    assert consistency._same(a.lower(), b.lower())


@pytest.mark.parametrize("headline,text,reason", [
    (None, TEXT, "no_headline"), ("", TEXT, "no_headline"), ("Council approves budget", TEXT, "headline_too_short"),
    (H, "Short text.", "text_too_short"), (H, "", "text_too_short"), (H, "One long sentence " + "word " * 40, "text_too_short"),
])
def test_input_too_thin_to_compare_is_skipped(headline, text, reason):
    r = run(headline, text, RuleNli())
    assert r["status"] == "skipped" and r["reason"] == reason and r["message"]


def test_a_missing_or_failing_model_gives_an_explained_result_not_an_exception():
    assert run(H, TEXT, NotInstalled())["reason"] == "model_missing"
    r = run(H, TEXT, Broken())
    assert r["status"] == "unavailable" and r["reason"] == "model_failed"


def test_only_the_first_sentences_are_read():
    text = ELSEWHERE + " " + " ".join(f"Another sentence number {i} about nothing in particular." for i in range(20)) + " " + TEXT
    r = run(H, text, RuleNli(says="voted on Tuesday evening to approve"))
    assert r["sentences_read"] == consistency.LEAD_SENTENCES and r["status"] == "unrelated"


# ---- how the result changes a verdict -----------------------------------------------------------------------------------

@pytest.mark.parametrize("status", ["contradicts", "unrelated", "details_differ"])
def test_a_mismatch_stops_a_likely_real_and_nothing_else(status):
    m = {"status": status, "message": "They differ."}
    out = consistency.combine_text_match({"verdict": "Likely Real", "confidence": None, "reason": "corroborated", "message": "x"}, m)
    assert out["verdict"] == "Unverified" and out["reason"] == "headline_text_mismatch" and out["confidence"] is None
    assert "They differ." in out["message"]
    for before in ("Unverified", "Likely Fake"):
        r = {"verdict": before, "reason": "low_confidence"}
        assert consistency.combine_text_match(r, m) == r          # it never lowers an Unverified further and never creates Likely Fake


@pytest.mark.parametrize("status", ["consistent", "not_stated", "skipped", "unavailable"])
@pytest.mark.parametrize("verdict", ["Likely Real", "Unverified", "Likely Fake"])
def test_other_results_leave_the_verdict_alone(status, verdict):
    r = {"verdict": verdict, "reason": "x"}
    assert consistency.combine_text_match(r, {"status": status, "message": "m"}) == r


@pytest.mark.parametrize("status", sorted(consistency.MISMATCH | {"consistent", "not_stated", "skipped", "unavailable"}))
@pytest.mark.parametrize("verdict", ["Likely Real", "Unverified", "Likely Fake"])
def test_the_check_can_never_produce_likely_fake(status, verdict):
    out = consistency.combine_text_match({"verdict": verdict, "reason": "x", "confidence": 0.9}, {"status": status, "message": "m"})
    assert out["verdict"] == verdict or (verdict == "Likely Real" and out["verdict"] == "Unverified")


# ---- the API -----------------------------------------------------------------------------------------------------------

@pytest.fixture
def match_on(monkeypatch, news):
    """The corroboration stand-ins plus the text check switched on, answering from `RuleNli`."""
    monkeypatch.setattr(get_settings(), "text_match_enabled", True)

    def setup(nli, reading=("Unverified", "low_confidence"), hits=None, table=None):
        state = news(hits if hits is not None else [hit(SAME)], {}, reading)
        state["nli"] = nli
        nli.table.update(table or {SAME: (0.9, 0.0)})
        return state
    return setup


def test_a_real_headline_over_a_text_that_says_something_else_is_not_called_real(client, alice, match_on):
    """The case this check exists for: the headline is corroborated by a listed outlet, the text under it is about something else."""
    match_on(RuleNli())
    r = client.post(f"{API}/analysis/text", json={"headline": HEADLINE, "text": ELSEWHERE}, headers=alice.headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["details"]["corroboration"]["status"] == "corroborated"
    assert body["details"]["text_match"]["status"] == "unrelated"
    assert body["verdict"] == "Unverified" and body["details"]["reason"] == "headline_text_mismatch"
    assert client.get(f"{API}/analysis/{body['id']}", headers=alice.headers).json()["details"]["text_match"]["status"] == "unrelated"


def test_a_real_headline_over_its_own_text_is_still_called_real(client, alice, match_on):
    match_on(RuleNli(says="voted on Tuesday evening to approve"))
    body = post_text(client, alice, H)
    assert body["details"]["text_match"]["status"] == "consistent"
    assert body["verdict"] == "Likely Real" and body["details"]["reason"] == "corroborated"


def test_a_headline_no_outlet_reports_over_a_text_that_does_not_match_stays_unverified_and_says_why(client, alice, match_on):
    match_on(RuleNli(), hits=[])
    r = client.post(f"{API}/analysis/text", json={"headline": HEADLINE, "text": ELSEWHERE}, headers=alice.headers).json()
    assert r["verdict"] == "Unverified" and r["details"]["text_match"]["status"] == "unrelated"


def test_the_text_check_can_be_switched_off(client, alice, match_on, monkeypatch):
    match_on(RuleNli())
    monkeypatch.setattr(get_settings(), "text_match_enabled", False)
    body = client.post(f"{API}/analysis/text", json={"headline": HEADLINE, "text": ELSEWHERE}, headers=alice.headers).json()
    assert body["details"]["text_match"]["reason"] == "disabled" and body["verdict"] == "Likely Real"


def test_a_settings_file_from_before_the_check_leaves_it_on(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(svc, "get_settings", lambda: SimpleNamespace())
    monkeypatch.setattr(svc, "get_nli", lambda: RuleNli(says="voted on Tuesday evening to approve"))
    assert svc._text_match(H, TEXT, "en", {})["status"] == "consistent"


def test_a_failing_model_does_not_fail_the_analysis(client, alice, match_on):
    match_on(Broken())
    r = client.post(f"{API}/analysis/text", json={"headline": HEADLINE, "text": ARTICLE}, headers=alice.headers)
    assert r.status_code == 201
    assert r.json()["details"]["text_match"]["status"] == "unavailable"


def test_urdu_text_is_not_compared(client, alice, match_on, monkeypatch):
    from tests.test_corroboration import StubDetector
    match_on(RuleNli())
    monkeypatch.setattr(StubDetector, "language", "ur")
    assert post_text(client, alice)["details"]["text_match"]["reason"] == "english_only"


def test_a_web_address_whose_text_does_not_match_its_headline_is_not_called_real(client, alice, match_on, served_page, monkeypatch):
    from app.ml.url_analysis.fetch import FetchResult
    match_on(RuleNli())
    monkeypatch.setattr(svc.url_fetch, "fetch", lambda url: FetchResult(
        requested_url=url, final_url=url, status=200, content_type="text/html", charset="utf-8", truncated=False,
        body=("<html lang='en'><head><title>" + HEADLINE + "</title><script type=\"application/ld+json\">{\"@type\":\"NewsArticle\",\"headline\":\""
              + HEADLINE + "\"}</script></head><body><article>" + "".join(f"<p>{s.strip()}.</p>" for s in ELSEWHERE.split(".") if s.strip())
              + "</article></body></html>").encode()))
    body = post_url(client, alice, "https://blog.example.org/story")
    assert body["details"]["corroboration"]["status"] == "corroborated"
    assert body["details"]["text_match"]["status"] == "unrelated" and body["verdict"] == "Unverified"


def test_a_difference_on_a_listed_outlets_own_page_is_shown_but_does_not_change_the_result(client, alice, match_on, monkeypatch):
    """One publisher wrote both the headline and the text of its own page, so nobody put a real headline over another text."""
    from app.ml.url_analysis.fetch import FetchResult
    match_on(RuleNli())
    monkeypatch.setattr(svc.url_fetch, "fetch", lambda url: FetchResult(
        requested_url=url, final_url=url, status=200, content_type="text/html", charset="utf-8", truncated=False,
        body=("<html lang='en'><head><title>" + HEADLINE + "</title><script type=\"application/ld+json\">{\"@type\":\"NewsArticle\",\"headline\":\""
              + HEADLINE + "\"}</script></head><body><article>" + "".join(f"<p>{s.strip()}.</p>" for s in ELSEWHERE.split(".") if s.strip())
              + "</article></body></html>").encode()))
    own = post_url(client, alice, "https://www.dawn.com/news/12345/story")
    assert own["details"]["text_match"]["status"] == "unrelated"
    assert "Dawn" in own["details"]["text_match"]["effect_note"] and own["details"]["reason"] != "headline_text_mismatch"
    assert own["verdict"] == "Likely Real"
    other = post_url(client, alice, "https://blog.example.org/story")     # the same page on a site that is not a listed outlet
    assert other["verdict"] == "Unverified" and other["details"]["reason"] == "headline_text_mismatch"
    assert "effect_note" not in other["details"]["text_match"]


# ---- what each result does to a verdict by default: only a text about another story stops a Likely Real ----------------------------

@pytest.mark.parametrize("status", sorted(consistency.MISMATCH | {"consistent", "not_stated", "skipped", "unavailable"}))
@pytest.mark.parametrize("verdict", ["Likely Real", "Unverified", "Likely Fake"])
@pytest.mark.parametrize("strict", [False, True])
def test_the_verdict_policy_by_result(status, verdict, strict):
    result = {"verdict": verdict, "confidence": None, "reason": "corroborated", "message": "m"}
    out, match = text_match_verdict.apply(result, {"status": status, "message": "x"}, strict=strict)
    stopped = verdict == "Likely Real" and status in (consistency.MISMATCH if strict else {"unrelated"})
    assert out["verdict"] == ("Unverified" if stopped else verdict)
    assert (out["reason"] == "headline_text_mismatch") == stopped
    assert out["verdict"] != "Likely Fake" or verdict == "Likely Fake"          # it never produces Likely Fake
    warned = not strict and status in {"contradicts", "details_differ"}
    assert ("effect_note" in match) == warned


def test_a_text_that_says_the_opposite_is_a_warning_by_default_and_stops_a_likely_real_when_strict(client, alice, match_on, monkeypatch):
    match_on(RuleNli(denies="voted on Tuesday evening"), table={SAME: (0.9, 0.0)})
    body = post_text(client, alice, H)
    assert body["details"]["text_match"]["status"] == "contradicts"
    assert body["verdict"] == "Likely Real" and "result above is unchanged" in body["details"]["text_match"]["effect_note"]
    monkeypatch.setattr(get_settings(), "text_match_strict", True)
    strict = post_text(client, alice, H)
    assert strict["verdict"] == "Unverified" and strict["details"]["reason"] == "headline_text_mismatch"


def test_a_settings_file_from_before_the_strict_option_leaves_it_off(monkeypatch):
    class Old:
        text_match_enabled = True
    monkeypatch.setattr(svc, "get_settings", lambda: Old())
    assert svc._text_match_strict() is False


def test_the_pdf_report_carries_the_result(client, alice, match_on):
    match_on(RuleNli())
    body = client.post(f"{API}/analysis/text", json={"headline": HEADLINE, "text": ELSEWHERE}, headers=alice.headers).json()
    r = client.get(f"{API}/analysis/{body['id']}/report.pdf", headers=alice.headers)
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    import io

    from pypdf import PdfReader  # noqa: PLC0415  (only the report tests need it)
    text = " ".join(pg.extract_text() for pg in PdfReader(io.BytesIO(r.content)).pages)
    assert "Text compared with its headline" in text and "Unrelated" in text and "swimmer" in text
