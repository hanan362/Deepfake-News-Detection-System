import { Link } from "react-router-dom";
import { useAsync } from "@/hooks/useAsync";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { useAdminModels } from "@/hooks/useModels";
import { api } from "@/services/api";
import { datasetLabel, formatNumber, formatPercent } from "@/utils/format";

const STACK: [string, string][] = [
  ["Interface", "React, TypeScript, Vite, Tailwind CSS, Framer Motion, Recharts"],
  ["Server", "FastAPI, Pydantic, SQLAlchemy, JWT sessions, bcrypt password hashing"],
  ["Machine learning", "scikit-learn (TF-IDF and logistic regression), Pillow and NumPy for image forensics"],
  ["Data", "SQLite by default, PostgreSQL through the database URL setting"],
  ["Testing", "pytest and httpx for the server, Vitest for the interface, Playwright for end-to-end runs"],
];


function Step({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="border-t border-line pt-8"><h2 className="text-2xl">{title}</h2><div className="mt-3 max-w-prose space-y-3 text-ink-2">{children}</div></section>;
}

export default function Methodology() {
  useDocumentTitle("Research methodology");
  const { data: models } = useAdminModels();
  const ev = useAsync(() => api.evaluation(), []);
  const limits = models?.limits;
  const d = ev.data?.dataset;
  const lr = ev.data ? ev.data.evaluation.comparison[ev.data.evaluation.deployed_model] : null;

  return (
    <div className="mx-auto max-w-4xl">
      <h1>Research methodology</h1>
      <p className="mt-4 max-w-2xl text-lg text-ink-2">How each result is produced, how it was tested, and where the method stops being reliable. Figures below are read from the saved evaluation.</p>

      <div className="mt-10 space-y-10">
        <Step title="Text analysis: data">
          <p>The text model was trained on {d ? `${datasetLabel(d.name)}, ${formatNumber(d.rows_clean.train + d.rows_clean.validation + d.rows_clean.test)} cleaned articles (${d.license})` : "a public dataset of labelled news articles"}. Before training, the labels were checked rather than assumed: real articles in the set carry a wire-service tag far more often than fake ones{d ? ` (${formatPercent(d.reuters_tag_rate_by_label["1"] ?? 0, 0)} against ${formatPercent(d.reuters_tag_rate_by_label["0"] ?? 0, 2)})` : ""}, which confirmed which label means real.</p>
          <p>Very short rows and duplicates across splits were removed so that no article appears in both training and test data.</p>
        </Step>

        <Step title="Text analysis: preprocessing">
          <p>Web addresses, wire-service datelines and the names of news agencies are stripped before the text is scored. Without this the model could learn to recognise a publisher instead of how the article is written, which would inflate the test score and fail on real use.</p>
        </Step>

        <Step title="Text analysis: model">
          <p>Words and word pairs are turned into TF-IDF weights, fitted on the training set only. A logistic regression classifier then gives a score between 0 and 1. Naive Bayes, a linear SVM and a random forest were trained on the same features for comparison. Logistic regression was deployed because the contribution of each term to the score can be computed exactly.</p>
        </Step>

        <Step title="Text analysis: when it answers">
          <p>The model calls an article Likely Fake or Likely Real only when its score is at least {formatPercent(limits?.text_confidence_threshold ?? 0.8)} on one side. Anything in between is Unverified. Articles under {limits?.min_text_words ?? 60} words and text in a language other than English or Urdu are also Unverified, because the training data contained neither. The model never outputs "Misleading", because it was never trained to tell misleading from false.</p>
        </Step>

        <Step title="Text analysis: explanation">
          <p>The marked words are not an approximation. For a linear model the score is the sum of each term's TF-IDF weight times its learned coefficient, plus an intercept, and the interface shows the largest of those terms. A test in the code checks that these parts add up to the model's own output.</p>
        </Step>

        <Step title="Text analysis: testing">
          <p>The model was tested on held-out articles from its own dataset{lr ? `: ${formatPercent(lr.test.accuracy, 1)} accuracy, AUC ${lr.test.roc_auc.toFixed(3)}` : ""}. It was then tested on {d ? datasetLabel(d.external_test_set.name) : "a second dataset"}, which has different topics, length and labelling{lr ? `: ${formatPercent(lr.external_liar2.accuracy, 1)} accuracy, AUC ${lr.external_liar2.roc_auc.toFixed(3)}` : ""}. The drop shows that the model learned the style of its training articles more than anything that carries over to other kinds of misinformation.</p>
          <p>For this reason the first number is never reported alone. <Link to="/admin/models">The full comparison is on the Models page</Link>.</p>
        </Step>

        <Step title="Image inspection">
          <p>Error level analysis saves the image again as a JPEG at quality 90 and measures how much each region changes. Edited regions can differ from the rest of the picture, but so can sharp edges, text and areas with different compression histories. The map is a measurement for a person to look at. It is not an attention map from a neural network and it does not produce a verdict.</p>
          <p>The system also reads the file's metadata. Missing metadata is common for images that were shared on messaging apps and proves nothing by itself. Image inspection has not been validated against a labelled set of manipulated images, which is why no confidence score is given.</p>
        </Step>

        <Step title="Urdu text">
          <p>Urdu articles are scored by a separate model trained on one small Urdu collection. It is labelled experimental: it was measured on that collection only, and no second Urdu collection exists here to test it on. The same rule applies as for English, so a result is given only when the model is confident.</p>
        </Step>

        <Step title="News web address">
          <p>The server fetches the page itself, under strict limits: only public web addresses, no internal networks, a size and time limit, and every redirect re-checked. The article text is then scored by the text model for its language. The website is compared with a short, hand-made list of known news and satire sites. A site that is not on the list is reported as unknown. It is never called fake for that reason, and pages that need a script, a login or a subscription cannot be read.</p>
        </Step>

        <Step title="Headline check">
          <p>The headline is searched in recent news. Results from a small, hand-made list of well-known news organisations are compared with it by the same language-inference model that the evidence check uses, and only headlines are compared, never article text. The result is "reported by listed outlets", "a listed outlet reports something different", or "no matching report", and it never makes a verdict <em>Likely Fake</em>. On 126 fresh real headlines (two independent sets), 75% were found at a listed outlet (15% when the outlet the headline came from is not counted); none of 12 invented and none of 39 distorted headlines were confirmed. A number or name in the headline must also appear in the headline that confirms it, because the language model once read "Iraq" for "Iran" as the same statement. When nothing matches, related headlines of listed outlets are shown for you to compare; they do not make the headline true or false. These sets are small and the invented headlines were written by the developers, a news search finds recent news only (3% of older real headlines), a paraphrased story is usually not matched, and a real headline pasted over a false article passes this check on its own (the next check reads the text). A page that was actually served from a listed outlet's own website is treated as published by it, which is a rule and not a measured model.</p>
          <p>A separate check reads the first ten sentences of the text against its headline and compares the headline's numbers and names. If the text is about another story, a <em>Likely Real</em> is withheld and the result is <em>Unverified</em>; it never makes a verdict <em>Likely Fake</em>. Over four sets of real articles it called a real article &quot;another story&quot; 1 time in 242, and a text taken from another story 95% of the time. A text that says something different, or lacks a name or number of the headline, is shown as a warning only: on 59 new real articles, 8 (14%) got such a result, because a headline can be updated, a figure rounded or a sentence misread by the model. So a real headline over an altered version of the same story is not caught, and neither is a text that agrees with its headline and then adds false details. On a page from a listed outlet's own website nothing changes the verdict. The altered and written texts were made by the developers, the samples are small, and it works for English only.</p>
        </Step>

        <Step title="Evidence">
          <p>Claims are picked from the text and searched on Wikipedia, and in published fact-checks when the server has a key. A pretrained language-inference model reads each passage and reports whether it supports, contradicts or says nothing about the claim, and a stance is shown only when the model is confident. Every result lists its sources. When nothing reliable is found the answer is Insufficient Evidence. The stance step was measured on a public claim set with gold evidence, and the whole check on 80 short, well-known claims written by the developers. Neither tests news or recent events, and the check still sometimes calls a true statement Contradicted. <Link to="/admin/models">Numbers are on the Models page</Link>.</p>
        </Step>

        <Step title="Image with text">
          <p>A pretrained model compares the image with the text and a similarity score is read against thresholds measured on a captioned-photo collection, not on news. A fixed, written rule combines this with the text result. A clear mismatch can raise a flag, but image inspection never changes the verdict.</p>
        </Step>

        <Step title="Video">
          <p>Sixteen frames are taken across the video, the main face in each is cropped, and a pretrained face-swap detector scores each crop. The scores are combined into one video score and compared with thresholds chosen on separate videos. A video is never judged from one frame, and a video with too few usable faces gets no verdict. This is a frame-based method. It does not learn motion or timing and it does not analyse audio. It was measured on tens of videos from two research datasets and may not work on other footage. <Link to="/admin/models">The measurements, including the weaker result on a second dataset, are on the Models page</Link>.</p>
        </Step>

        <Step title="What is not built">
          <p>A detector for generated or edited images, a model that learns motion, audio and lip-sync analysis, and a trained source-reliability model are not part of this build. The interface does not offer them.</p>
        </Step>

        <Step title="Privacy and misuse">
          <p>Analyses and uploads belong to the account that created them. They are served only to that user, including when an administrator is logged in. Passwords are stored as bcrypt hashes. Uploaded files are checked by content and stored under random names. The writing-style reading of text, the comparison of a text with its headline, and image and video analysis, run on the server and send nothing out. Four features contact other services: a news web address is fetched from its own site, the headline check sends the headline to a news search (Google News RSS) and can be switched off, the evidence check sends the main words of each claim to Wikipedia (and to a fact-check search when the server has a key), and the first use of a downloaded model fetches it from its public host.</p>
          <p>The main risk of a tool like this is false confidence: a wrong label on real news, or a clean label on a fake. That is the reason for the refusal rules above, for the visible measurements, and for the notice on every result.</p>
        </Step>
        <Step title="Built with">
          <dl className="divide-y divide-line rounded-panel border border-line text-sm">
            {STACK.map(([k, v]) => <div key={k} className="flex flex-col gap-1 px-4 py-3 sm:flex-row sm:justify-between sm:gap-6"><dt className="shrink-0 text-ink-2">{k}</dt><dd className="sm:text-right">{v}</dd></div>)}
          </dl>
        </Step>
      </div>
    </div>
  );
}
