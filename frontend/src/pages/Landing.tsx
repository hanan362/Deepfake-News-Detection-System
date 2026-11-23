import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ShieldCheck, CircleHelp, ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { CHECKS } from "@/config/checks";
import { useAuth } from "@/context/AuthContext";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { useModels } from "@/hooks/useModels";
import { saveDraft } from "@/utils/draft";

const ANSWERS = [
  { band: "band-real", Icon: ShieldCheck, word: "Likely Real", line: "The writing reads like real reporting, or a well-known news site published it. That does not prove every claim in it is true." },
  { band: "band-unsure", Icon: CircleHelp, word: "Unverified", line: "The check cannot tell. This is the honest answer when a story is short, unusual, or when the signals disagree." },
  { band: "band-fake", Icon: ShieldAlert, word: "Likely Fake", line: "The writing reads like articles that were labelled fake. It is a warning to look closer, not proof." },
];

/** The thing people come to do, right on the home page. A visitor who is not signed in is asked to sign in first and finds the text waiting. */
function Composer() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [kind, setKind] = useState<"text" | "url">("text");
  const [value, setValue] = useState("");

  function submit(e: FormEvent) {
    e.preventDefault();
    if (value.trim()) saveDraft(kind, value.trim());
    navigate(kind === "text" ? "/analyze/text" : "/analyze/url");
  }

  return (
    <form onSubmit={submit} className="rounded-[1.4rem] border-2 border-ink bg-panel p-4 shadow-[7px_7px_0_rgb(var(--ink))] dark:shadow-[7px_7px_0_rgb(var(--primary))] sm:p-5" aria-label="Start a check">
      <div role="tablist" aria-label="What to check" className="flex gap-1 rounded-full bg-raised p-1 text-sm font-semibold">
        {([["text", "Article text"], ["url", "News link"]] as const).map(([k, label]) => (
          <button key={k} type="button" role="tab" aria-selected={kind === k} onClick={() => setKind(k)} className={`flex-1 rounded-full px-4 py-1.5 ${kind === k ? "bg-ink text-canvas" : "text-ink-2 hover:text-ink"}`}>{label}</button>
        ))}
      </div>
      <label htmlFor="hero-input" className="sr-only">{kind === "text" ? "Paste the article" : "Paste the address of the article"}</label>
      {kind === "text" ? (
        <textarea id="hero-input" value={value} onChange={(e) => setValue(e.target.value)} rows={7} className="field mt-3 resize-none" placeholder="Paste the whole article here. Longer is better: a few paragraphs at least." />
      ) : (
        <input id="hero-input" type="url" value={value} onChange={(e) => setValue(e.target.value)} className="field mt-3" placeholder="https://news-site.example/story" />
      )}
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <p className="min-w-[12rem] flex-1 text-[0.8125rem] text-ink-2">{user ? "Your check is saved to your account." : "You need a free account to run a check. Your text will be waiting."}</p>
        <Button type="submit" size="lg">{user ? "Check it" : "Sign in and check"}</Button>
      </div>
    </form>
  );
}

export default function Landing() {
  useDocumentTitle("Deepfake News Detection System");
  const { user } = useAuth();
  const { byModule } = useModels();

  return (
    <>
      <section className="border-b border-line">
        <div className="mx-auto grid max-w-6xl gap-12 px-4 py-14 sm:px-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,30rem)] lg:items-center lg:py-20">
          <div>
            <h1>Check a story before you share it</h1>
            <p className="mt-6 max-w-xl text-lg text-ink-2">
              Paste an article or a news link, or upload a photo or a video. You get a plain answer, the reasons behind it, and a clear warning whenever the answer is only a hint.
            </p>
            <p className="mt-4 max-w-xl text-ink-2">When it cannot tell, it says <strong className="text-ink">Unverified</strong> and does not guess.</p>
            <p className="mt-8 flex flex-wrap gap-x-5 gap-y-2 text-sm font-semibold">
              <Link to={user ? "/analyze/image" : "/login"}>Check a photo</Link>
              <Link to={user ? "/analyze/video" : "/login"}>Check a video</Link>
              <Link to="/about">How this project works</Link>
            </p>
          </div>
          <Composer />
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6" aria-labelledby="answers-h">
        <h2 id="answers-h" className="max-w-2xl">What an answer looks like</h2>
        <p className="mt-3 max-w-2xl text-ink-2">Every result opens with one of these, in its own colour, followed by the reasons and what the check cannot tell you.</p>
        <ul className="mt-8 space-y-3">
          {ANSWERS.map(({ band, Icon, word, line }) => (
            <li key={word} className={`band ${band} grid items-center gap-x-8 gap-y-2 rounded-panel px-6 py-6 sm:grid-cols-[17rem_1fr] sm:px-8`}>
              <p className="flex items-center gap-3 font-display text-[2rem] font-extrabold leading-none tracking-tight"><Icon className="h-7 w-7 shrink-0" aria-hidden />{word}</p>
              <p className="max-w-xl text-[0.97rem] text-white/95">{line}</p>
            </li>
          ))}
        </ul>
      </section>

      <section className="border-y border-line bg-panel" aria-labelledby="checks-h">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
          <h2 id="checks-h">What you can check</h2>
          <ul className="mt-8 grid gap-x-10 gap-y-7 md:grid-cols-2">
            {CHECKS.map(({ module, title, to, Icon }) => {
              const m = byModule(module);
              const off = m?.status === "unavailable";
              return (
                <li key={module} className="flex gap-4">
                  <span className="mt-0.5 grid h-10 w-10 shrink-0 place-items-center rounded-control bg-primary text-on-primary"><Icon className="h-5 w-5" aria-hidden /></span>
                  <div>
                    <h3 className="flex flex-wrap items-center gap-2">
                      <Link to={user ? to : "/login"} className="!text-ink">{title}</Link>
                      {m?.status === "experimental" && <span className="pill border-line bg-raised text-ink-2">Experimental</span>}
                      {off && <span className="pill border-line bg-raised text-ink-2">Not available right now</span>}
                    </h3>
                    <p className="mt-1 max-w-md text-[0.95rem] text-ink-2">{off ? "This check is switched off on this server at the moment." : m?.description ?? ""}</p>
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      </section>

      <section className="mx-auto grid max-w-6xl gap-10 px-4 py-16 sm:px-6 md:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]" aria-labelledby="cannot-h">
        <div>
          <h2 id="cannot-h">What it cannot do</h2>
          <p className="mt-3 text-ink-2">Knowing the limits is part of using it well.</p>
        </div>
        <ul className="space-y-5 text-[0.97rem]">
          <li><strong>It does not check facts.</strong> <span className="text-ink-2">It reads how a text is written, so a true story can come out Unverified and a well-written lie can slip through.</span></li>
          <li><strong>It can be wrong.</strong> <span className="text-ink-2">It is a student project, tested on small collections. Treat every answer as a reason to look closer, never as proof.</span></li>
          <li><strong>It works best on long English articles.</strong> <span className="text-ink-2">Very short texts and other languages usually get Unverified.</span></li>
          <li><strong>Your checks are private.</strong> <span className="text-ink-2">Only you can open what you check. Not even administrators can read it.</span></li>
        </ul>
      </section>
    </>
  );
}
