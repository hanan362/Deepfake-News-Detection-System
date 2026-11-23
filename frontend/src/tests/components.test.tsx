import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { CorroborationPanel } from "@/components/CorroborationPanel";
import { TextMatchPanel } from "@/components/TextMatchPanel";
import { PasswordRules } from "@/components/PasswordRules";
import { ReadingMeter } from "@/components/ReadingMeter";
import { StatusPill } from "@/components/ui/StatusPill";
import { Pagination } from "@/components/ui/Pagination";
import { VerdictRuling, rulingLine } from "@/components/VerdictRuling";
import { vi } from "vitest";
import userEvent from "@testing-library/user-event";

describe("VerdictRuling", () => {
  it("always says what a verdict does not mean", () => {
    expect(rulingLine({ verdict: "Likely Fake", details: null, analysis_type: "text" })).toMatch(/not proof/);
    expect(rulingLine({ verdict: "Likely Real", details: null, analysis_type: "text" })).toMatch(/does not confirm/);
    expect(rulingLine({ verdict: "Indicators Only", details: null, analysis_type: "image" })).toMatch(/not a verdict/);
  });
  it("shows the server's reason when the model declines", () => {
    render(<VerdictRuling analysis={{ verdict: "Unverified", analysis_type: "text", details: { reason: "too_short", message: "Only 12 words were given." } as never }} />);
    expect(screen.getByTestId("verdict")).toHaveTextContent("Unverified");
    expect(screen.getByText("Only 12 words were given.")).toBeInTheDocument();
  });
});

describe("headline corroboration", () => {
  const base = {
    reason: null, message: "The headline matches a report by 1 listed news organisation: Dawn.", query: "City council approves budget", outlets: [],
    results_read: 9, listed_outlet_results: 3, excluded_outlet: null, provider: "Google News RSS (unofficial)",
    rules: { compares: "headlines only, not article text", corroborated: "50% words and 60% sure", disputed: "70% words and 80% sure", not_found: "anything else" },
    limits: "Only the headline is compared, not the article.",
  };
  const outlet = { name: "Dawn", title: "Council approves budget", url: "https://news.example/a", published: null, relation: "same_story" as const, overlap: 0.8, entailment: 0.93, contradiction: 0.01 };

  it("explains a corroborated verdict as 'reported', never as 'true'", () => {
    const line = rulingLine({ verdict: "Likely Real", analysis_type: "text", details: { reason: "corroborated" } as never });
    expect(line).toMatch(/reported, not that it is accurate/);
    expect(line).not.toMatch(/does not confirm that any claim/);
  });
  it("explains a verdict that rests on the website as 'who published it', never as 'accurate'", () => {
    const line = rulingLine({ verdict: "Likely Real", analysis_type: "url", details: { reason: "published_by_listed_outlet" } as never });
    expect(line).toMatch(/shows who published it, not that what it says is accurate/);
  });
  it("uses the server's wording when the two readings disagree or the report differs", () => {
    for (const reason of ["signals_differ", "disputed"] as const) {
      expect(rulingLine({ verdict: "Unverified", analysis_type: "text", details: { reason, message: "Read it before relying on this one." } as never })).toBe("Read it before relying on this one.");
    }
  });
  it("lists the matching outlet with its figures and a link to the report", () => {
    render(<CorroborationPanel c={{ ...base, status: "corroborated", outlets: [outlet] }} />);
    expect(screen.getByTestId("corroboration-status")).toHaveTextContent("Reported by listed outlets");
    expect(screen.getByTestId("corroboration-outlet")).toHaveTextContent(/Dawn.*Council approves budget.*Words in common 80%.*Says the same 93%/s);
    expect(screen.getByRole("link", { name: /Open report/ })).toHaveAttribute("rel", "noopener noreferrer");
  });
  it("says a difference is a difference, and names the site that was not counted", () => {
    render(<CorroborationPanel c={{ ...base, status: "disputed", message: "A listed news organisation reports something different.", excluded_outlet: "BBC", outlets: [{ ...outlet, relation: "different_report", contradiction: 0.97 }] }} />);
    expect(screen.getByTestId("corroboration-status")).toHaveTextContent("A listed outlet reports something different");
    expect(screen.getByTestId("corroboration-outlet")).toHaveTextContent("Says the opposite 97%");
    expect(screen.getByText(/BBC, the site this article came from, was not counted/)).toBeInTheDocument();
  });
  it("lists related coverage as a different claim when nothing matched, and keeps it out of every other state", () => {
    const related = [{ name: "BBC", title: "Council talks on the budget go on", url: "https://news.example/b", published: "Sun, 22 Nov 2026", overlap: 0.4 }];
    const { rerender } = render(<CorroborationPanel c={{ ...base, status: "not_found", message: "No listed news organisation was found.", related }} />);
    expect(screen.getByTestId("corroboration-related")).toHaveTextContent(/Related coverage, a different claim.*BBC.*Council talks on the budget go on.*Words in common 40%/s);
    expect(screen.getByTestId("corroboration-related")).toHaveTextContent(/do not make your headline true or false/);
    rerender(<CorroborationPanel c={{ ...base, status: "not_found", message: "No listed news organisation was found.", related: [] }} />);
    expect(screen.queryByTestId("corroboration-related")).not.toBeInTheDocument();
    rerender(<CorroborationPanel c={{ ...base, status: "corroborated", outlets: [outlet], related }} />);
    expect(screen.queryByTestId("corroboration-related")).not.toBeInTheDocument();
  });
  it("shows only the reason when nothing was checked, and always keeps the limits one click away", () => {
    render(<CorroborationPanel c={{ ...base, status: "skipped", message: "No headline was given.", query: null }} />);
    expect(screen.getByTestId("corroboration")).toHaveAttribute("data-status", "skipped");
    expect(screen.queryByText(/headlines read/)).not.toBeInTheDocument();
    expect(screen.getByText(/How this is decided and what it cannot show/)).toBeInTheDocument();
    expect(screen.getByText("Only the headline is compared, not the article.")).toBeInTheDocument();
  });
});

describe("TextMatchPanel", () => {
  const rules = { reads: "the first 10 sentences", consistent: "a window entails the headline", contradicts: "a window says the opposite", unrelated: "few words in common", details_differ: "a number or name is missing", not_stated: "anything else" };
  const base = { reason: null, message: "The text does not seem to be about what the headline says.", best: null, missing: [] as string[], sentences_read: 6, rules, limits: "A text that agrees with its headline and then adds false details further on reads as consistent." };
  it("says in words that the text is about something else, with the closest sentence and what was missing", () => {
    render(<TextMatchPanel m={{ ...base, status: "unrelated", missing: ["seven"], best: { text: "A swimmer crossed the channel on Saturday.", overlap: 0.1, entailment: 0.02, contradiction: 0.03 } }} />);
    expect(screen.getByTestId("text-match")).toHaveAttribute("data-status", "unrelated");
    expect(screen.getByTestId("text-match-status")).toHaveTextContent("The text is about something else");
    expect(screen.getByTestId("text-match-missing")).toHaveTextContent("In the headline but not in the text: seven");
    expect(screen.getByTestId("text-match-best")).toHaveTextContent(/The sentences closest to the headline.*A swimmer crossed.*Words in common 10%/s);
    expect(screen.getByTestId("text-match-best")).not.toHaveTextContent(/Says the opposite|Says the same/);  // meaningless for an unrelated text
    expect(screen.getByText(/The first 6 sentences of the text were read/)).toBeInTheDocument();
  });
  it("labels a matching text as the sentences that say it, and always keeps the limits one click away", () => {
    render(<TextMatchPanel m={{ ...base, status: "consistent", message: "The first sentences of the text say what the headline says.", best: { text: "The council approved the budget.", overlap: 0.8, entailment: 0.93, contradiction: 0 } }} />);
    expect(screen.getByTestId("text-match-best")).toHaveTextContent("The sentences that say it");
    expect(screen.queryByTestId("text-match-missing")).not.toBeInTheDocument();
    expect(screen.getByText(/How this is decided and what it cannot show/)).toBeInTheDocument();
    expect(screen.getByText(/adds false details further on reads as consistent/)).toBeInTheDocument();
  });
  it("says when a difference is shown but did not change the result", () => {
    render(<TextMatchPanel m={{ ...base, status: "unrelated", effect_note: "This page is on the website of Dawn, which wrote both the headline and the text, so a difference between them is shown here but does not change the result." }} />);
    expect(screen.getByTestId("text-match-effect")).toHaveTextContent(/website of Dawn.*does not change the result/);
  });
  it("shows no such note for an ordinary result", () => {
    render(<TextMatchPanel m={{ ...base, status: "unrelated" }} />);
    expect(screen.queryByTestId("text-match-effect")).not.toBeInTheDocument();
  });
});

describe("ReadingMeter", () => {
  it("describes the reading in words for screen readers", () => {
    render(<ReadingMeter probFake={0.03} threshold={0.8} />);
    expect(screen.getByRole("img", { name: /3% fake, 97% real.*at least 80%/ })).toBeInTheDocument();
  });
});

describe("StatusPill", () => {
  it("writes the status out, so colour is not the only signal", () => {
    render(<StatusPill status="planned" />);
    expect(screen.getByText("Planned")).toBeInTheDocument();
  });
});

describe("PasswordRules", () => {
  it("marks each rule as met or not", () => {
    render(<PasswordRules password="abc" />);
    expect(screen.getByText("At least 8 characters")).toBeInTheDocument();
    expect(screen.getByText("Contains a digit")).toBeInTheDocument();
  });
});

describe("Pagination", () => {
  it("shows the range and moves between pages", async () => {
    const onPage = vi.fn();
    render(<Pagination page={2} pageSize={10} total={25} onPage={onPage} />);
    expect(screen.getByText(/11/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /next/i }));
    expect(onPage).toHaveBeenCalledWith(3);
    await userEvent.click(screen.getByRole("button", { name: /previous/i }));
    expect(onPage).toHaveBeenCalledWith(1);
  });
});

describe("Scoreboard", () => {
  it("reports an API failure instead of inventing numbers", async () => {
    vi.resetModules();
    vi.doMock("@/services/api", async (orig) => ({ ...(await orig<typeof import("@/services/api")>()), api: { evaluation: () => Promise.reject(new Error("offline")) } }));
    const { Scoreboard: Fresh } = await import("@/components/Scoreboard");
    render(<MemoryRouter><Fresh /></MemoryRouter>);
    expect(await screen.findByText("The measured results could not be loaded")).toBeInTheDocument();
    expect(screen.queryByText("accuracy")).not.toBeInTheDocument();
  });
});
