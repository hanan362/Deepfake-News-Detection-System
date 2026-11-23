import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ReadingMeter } from "@/components/ReadingMeter";
import { VerdictBadge, VerdictRuling } from "@/components/VerdictRuling";
import { RequireAdmin } from "@/layouts/guards";
import { plainLimits } from "@/utils/plainLimits";
import { saveDraft, takeDraft } from "@/utils/draft";
import { verdictBand } from "@/utils/format";

let role: "user" | "admin" = "user";
vi.mock("@/context/AuthContext", () => ({ useAuth: () => ({ user: { id: 1, role }, loading: false }) }));

function at(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<RequireAdmin />}><Route path="/admin" element={<p>console</p>} /></Route>
        <Route path="/dashboard" element={<p>home</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("the administrator console", () => {
  it("sends an ordinary user home instead of showing it", () => {
    role = "user";
    at("/admin");
    expect(screen.getByText("home")).toBeInTheDocument();
    expect(screen.queryByText("console")).not.toBeInTheDocument();
  });
  it("opens for an administrator", () => {
    role = "admin";
    at("/admin");
    expect(screen.getByText("console")).toBeInTheDocument();
  });
});

describe("what an ordinary reader is shown of a score", () => {
  it("is a bar with words and no percentages", () => {
    render(<ReadingMeter probFake={0.03} threshold={0.8} plain />);
    expect(screen.getByRole("img")).toHaveAccessibleName(/leans clearly towards real/);
    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
    expect(screen.queryByText(/The model puts/)).not.toBeInTheDocument();
  });
  it("says so in words when the reading does not lean", () => {
    render(<ReadingMeter probFake={0.5} threshold={0.8} plain />);
    expect(screen.getByRole("img")).toHaveAccessibleName(/does not lean clearly/);
  });
  it("keeps the percentages for an administrator's view", () => {
    render(<ReadingMeter probFake={0.03} threshold={0.8} />);
    expect(screen.getByText(/The model puts/)).toBeInTheDocument();
  });
});

describe("the verdict band", () => {
  it.each([["Likely Real", "real", "band-real"], ["Supported", "real", "band-real"], ["Likely Fake", "fake", "band-fake"], ["Contradicted", "fake", "band-fake"],
    ["Unverified", "unsure", "band-unsure"], ["Insufficient Evidence", "unsure", "band-unsure"], ["Mismatch Flagged", "flag", "band-flag"]])(
    "gives %s the %s colour", (verdict, band, cls) => {
      expect(verdictBand(verdict)).toBe(band);
      const { container } = render(<VerdictRuling analysis={{ verdict, analysis_type: "text", details: null }} />);
      expect(container.firstElementChild).toHaveClass(cls);
      expect(screen.getByTestId("verdict")).toHaveTextContent(verdict);
    });
  it("writes the verdict out in a list tag, as well as colouring it", () => {
    render(<VerdictBadge verdict="Likely Fake" />);
    expect(screen.getByText("Likely Fake")).toBeInTheDocument();
  });
});

describe("plain limits", () => {
  it("never carry a measured number or a model name, and always say it is not a fact check where that is true", () => {
    for (const t of ["text", "url", "image", "video", "multimodal", "evidence"] as const) {
      const text = plainLimits({ analysis_type: t }).join(" ");
      expect(text).not.toMatch(/\d\.\d|ROC|AUC|LIAR|TF-IDF|CLIP/);
      expect(text.length).toBeGreaterThan(40);
    }
    expect(plainLimits({ analysis_type: "text" }).join(" ")).toMatch(/does not check whether the claims are true/);
  });
});

describe("the draft typed on the home page", () => {
  beforeEach(() => sessionStorage.clear());
  it("is handed over once, to the page for the same kind of check", () => {
    saveDraft("text", "The harbour authority said");
    expect(takeDraft("url")).toBe("");
    expect(takeDraft("text")).toBe("The harbour authority said");
    expect(takeDraft("text")).toBe("");
  });
  it("is empty when nothing was saved or the stored value is damaged", () => {
    expect(takeDraft("text")).toBe("");
    sessionStorage.setItem("ddn.draft", "{not json");
    expect(takeDraft("text")).toBe("");
  });
});
