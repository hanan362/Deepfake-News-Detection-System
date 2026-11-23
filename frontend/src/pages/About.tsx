import { Link } from "react-router-dom";
import { PROJECT } from "@/config/project";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { useModels } from "@/hooks/useModels";
import { CHECKS } from "@/config/checks";


export default function About() {
  useDocumentTitle("About the project");
  const { byModule } = useModels();
  const hasDetails = PROJECT.institution || PROJECT.department || PROJECT.supervisor;

  return (
    <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
      <h1>About the project</h1>
      <p className="mt-4 max-w-2xl text-lg text-ink-2">{PROJECT.title} is a {PROJECT.kind.toLowerCase()} that explores how far automatic checks can go in judging news. It builds a working system, measures it honestly, and reports where it fails.</p>

      <section className="mt-12" aria-labelledby="why">
        <h2 id="why" className="text-2xl">Why it exists</h2>
        <p className="mt-3 max-w-prose text-ink-2">Manipulated text and images spread faster than fact-checkers can respond. Tools that label content as fake with false confidence make this worse. The aim here is a tool that explains what it saw, says how sure it is, and refuses to answer when it is not.</p>
      </section>

      <section className="mt-12" aria-labelledby="read">
        <h2 id="read" className="text-2xl">How to read an answer</h2>
        <ul className="mt-5 space-y-3">
          {([
            ["Likely Real", "bg-band-real", "The writing reads like real reporting, or a well-known news site published it. It does not prove every claim is true."],
            ["Unverified", "bg-band-unsure", "The check cannot tell. It is the honest answer when a story is short, unusual, or the signals disagree. It does not mean the story is false."],
            ["Likely Fake", "bg-band-fake", "The writing reads like articles that were labelled fake. It is a reason to look closer, not proof."],
          ] as const).map(([word, swatch, line]) => (
            <li key={word} className="flex gap-4">
              <span className={`mt-1 h-5 w-5 shrink-0 rounded-md ${swatch}`} aria-hidden />
              <p className="max-w-prose"><strong>{word}.</strong> <span className="text-ink-2">{line}</span></p>
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-12" aria-labelledby="state">
        <h2 id="state" className="text-2xl">What it can check</h2>
        <ul className="mt-4 divide-y divide-line rounded-panel border border-line">
          {CHECKS.map(({ module, title }) => {
            const m = byModule(module);
            return (
              <li key={module} className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 px-4 py-3">
                <span className="font-semibold">{title}</span>
                <span className="max-w-md text-sm text-ink-2">{m?.status === "unavailable" ? "Not available on this server right now." : m?.description}{m?.status === "experimental" ? " (Experimental.)" : ""}</span>
              </li>
            );
          })}
        </ul>
      </section>

      {hasDetails && (
        <section className="mt-12" aria-labelledby="inst">
          <h2 id="inst" className="text-2xl">Institution</h2>
          <dl className="mt-4 divide-y divide-line rounded-panel border border-line text-sm">
            {[["Institution", PROJECT.institution], ["Department", PROJECT.department], ["Supervisor", PROJECT.supervisor]].filter(([, v]) => v).map(([k, v]) => <div key={k} className="flex justify-between gap-6 px-4 py-3"><dt className="text-ink-2">{k}</dt><dd>{v}</dd></div>)}
          </dl>
        </section>
      )}

      {PROJECT.members.length > 0 && (
        <section className="mt-12" aria-labelledby="team">
          <h2 id="team" className="text-2xl">The team</h2>
          <ul className="mt-4 grid gap-4 sm:grid-cols-2">
            {PROJECT.members.map((m) => <li key={m.name} className="panel panel-pad"><p className="font-medium">{m.name}</p><p className="text-sm text-ink-2">{m.role}</p>{m.registration && <p className="text-sm text-ink-3">{m.registration}</p>}</li>)}
          </ul>
        </section>
      )}

      <section className="mt-12 rounded-panel border border-warn/40 bg-warn/5 p-5" aria-labelledby="disc">
        <h2 id="disc" className="text-xl">Please read</h2>
        <p className="mt-2 max-w-prose text-sm text-ink-2">This is a student research prototype. Its results are aids for a human reader, not fact-checks and not proof. Do not use them to publish accusations, to moderate content automatically, or to make decisions about people.</p>
      </section>

      <p className="mt-10 text-sm text-ink-2">Questions or problems? <Link to="/contact">Contact the team</Link>.</p>
    </div>
  );
}
