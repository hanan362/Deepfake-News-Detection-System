/** Shapes returned by the backend (see backend/app/schemas). */

export interface User {
  id: number;
  email: string;
  username: string;
  full_name: string | null;
  role: "user" | "admin";
  is_active: boolean;
  has_avatar: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_at: string;
  user: User;
}

export interface MessageResponse {
  message: string;
  reset_token?: string | null;
}

export type ModuleStatus = "trained_baseline" | "pretrained" | "heuristic" | "experimental" | "unavailable" | "planned";
export type ModuleKey = "text" | "text_ur" | "image" | "video" | "multimodal" | "evidence" | "url";

export interface ClassMetrics {
  accuracy: number;
  precision_fake: number;
  recall_fake: number;
  f1_fake: number;
  roc_auc: number;
  pr_auc: number;
  confusion_matrix: { tn: number; fp: number; fn: number; tp: number };
  n: number;
}

export interface ModelEntry {
  module: ModuleKey;
  name: string;
  version: string;
  status: ModuleStatus;
  description?: string;
  limitations?: string[];
  algorithm?: string;
  language?: string;
  trained_at?: string;
  metrics?: { test: ClassMetrics; external_liar2: ClassMetrics; calibration: Record<string, number> };
}

export interface Limits {
  min_text_words: number;
  max_text_chars: number;
  max_image_mb: number;
  max_image_pixels: number;
  max_video_mb?: number;
  max_video_seconds?: number;
  video_sample_frames?: number;
  video_min_face_frames?: number;
  text_confidence_threshold: number;
  text_languages?: string[];
}

/** One check as an ordinary visitor sees it: whether it runs and what it does, with no model names or numbers. */
export interface PublicModule {
  module: ModuleKey;
  status: ModuleStatus;
  description: string;
}

export interface PublicLimits {
  min_text_words: number;
  max_text_chars: number;
  max_image_mb: number;
  max_image_pixels: number;
  max_video_mb?: number;
  max_video_seconds?: number;
  text_languages?: string[];
}

export interface ModulesResponse {
  models: PublicModule[];
  limits: PublicLimits;
}

export interface ModelsResponse {
  models: ModelEntry[];
  limits: Limits;
  status_meanings: Record<string, string>;
}

export interface TermWeight {
  term: string;
  weight: number;
}

export interface CorroborationOutlet {
  name: string;
  title: string;
  url: string | null;
  published: string | null;
  relation: "same_story" | "different_report";
  overlap: number;
  entailment: number;
  contradiction: number;
}

/** A listed outlet's headline on the same subject that does not say the same thing. Shown for the reader; it never changes a verdict. */
export interface CorroborationRelated {
  name: string;
  title: string;
  url: string | null;
  published: string | null;
  overlap: number;
}

/** The headline-against-news check. 'skipped' and 'unavailable' carry a reason and a message instead of outlets. */
export interface Corroboration {
  status: "corroborated" | "disputed" | "not_found" | "skipped" | "unavailable";
  reason: string | null;
  message: string | null;
  query: string | null;
  outlets: CorroborationOutlet[];
  related?: CorroborationRelated[];
  results_read: number;
  listed_outlet_results: number;
  excluded_outlet: string | null;
  provider: string | null;
  rules: { compares: string; corroborated: string; disputed: string; not_found: string; related?: string };
  limits: string;
}

/** The text of an article compared with its own headline. Every status other than 'consistent' and 'not_stated' stops a Likely Real. */
export interface TextMatch {
  status: "consistent" | "contradicts" | "unrelated" | "details_differ" | "not_stated" | "skipped" | "unavailable";
  reason: string | null;
  message: string | null;
  best: { text: string; overlap: number; entailment: number; contradiction: number } | null;
  missing: string[];
  sentences_read: number;
  rules: { reads: string; consistent: string; contradicts: string; unrelated: string; details_differ: string; not_stated: string };
  limits: string;
  /** Set when a difference between headline and text is shown but does not change the result (a page on a listed outlet's own website). */
  effect_note?: string | null;
}

export interface TextDetails {
  token_count: number;
  script_hint: string;
  reason: "model_leans_fake" | "model_leans_real" | "low_confidence" | "too_short" | "unsupported_language" | "article_not_readable" | "declared_satire" | "corroborated" | "published_by_listed_outlet" | "signals_differ" | "disputed" | "headline_text_mismatch";
  language?: string;
  corroboration?: Corroboration;
  text_match?: TextMatch;
  message?: string;
  probabilities?: { fake: number; real: number };
  decision_rule?: { threshold: number; min_tokens: number };
  explanation?: { method: string; toward_fake: TermWeight[]; toward_real: TermWeight[]; intercept: number; caution: string };
}

export interface ImageDetails {
  observations: string[];
  image: { width: number; height: number; format: string };
  metadata: { has_exif: boolean; make?: string; model?: string; software?: string; datetime?: string; has_icc_profile?: boolean };
  ela: { mean: number; max: number; block_cv: number; quality: number; grid: number };
  map_note: string;
}

export interface EvidenceItem {
  provider: string;
  kind: "encyclopedia" | "fact_check";
  title: string;
  url: string;
  published: string | null;
  rating: string | null;
  publisher: string | null;
  relevance: number;
  excerpt: string;
  stance: "supports" | "contradicts" | "unclear" | "not_relevant" | "other_subject" | "not_assessed" | "published_rating";
  stance_probabilities: { entailment: number; neutral: number; contradiction: number } | null;
  best_sentence: string | null;
}

export interface EvidenceClaim {
  claim: string;
  verdict: string;
  reason: string;
  evidence: EvidenceItem[];
  providers: { provider: string; status: "ok" | "not_configured" | "error" | "no_results"; message: string; count: number }[];
  stance_model: string | null;
  rules: { stance_threshold: number; relevance_min: number };
}

export interface EvidenceDetails {
  claims: EvidenceClaim[];
  claims_picked_automatically: boolean;
  stance_model: string | null;
  rules: { stance_threshold: number; relevance_min: number };
}

export interface ConsistencyResult {
  status: "assessed" | "not_assessed" | "not_possible";
  label: "consistent" | "unclear" | "inconsistent" | "not_calibrated" | null;
  similarity: number | null;
  caption_used: string | null;
  caption_source: string | null;
  thresholds: { consistent_min: number; inconsistent_max: number; target_precision?: number } | null;
  model: string;
  note: string;
}

export interface MultimodalDetails {
  modalities: { text: string; image: "analysed" | "not_provided"; consistency: ConsistencyResult["status"] };
  text_result: TextDetails | null;
  image_result: ImageDetails | null;
  consistency: ConsistencyResult;
  fusion: { verdict: string; base_verdict: string; rule: string; notes: string[]; inputs: { text_verdict: string | null; consistency: string | null; image_present: boolean } };
}

export interface VideoFrame {
  index: number; t: number; face_found: boolean; face_size: number | null; p_fake: number | null;
  sharpness: number | null; ela_mean: number | null; has_image: boolean;
}

export interface VideoDetails {
  video: { width: number; height: number; fps: number; frame_count: number; duration_seconds: number; container: string };
  sampling: { requested: number; sampled: number; with_face: number; min_face_frames: number };
  frames: VideoFrame[];
  temporal: {
    frames_scored: number; mean: number; median: number; min: number; max: number; std: number; flagged_share: number;
    longest_flagged_run: number; jumpiness: number; aggregator: string; video_score: number; suspicious_moments: { t: number; p_fake: number }[];
  } | null;
  decision: { status: "decided" | "undecided" | "not_enough_faces" | "not_calibrated" | "classifier_unavailable"; rule: string; thresholds: { fake_min: number | null; real_max: number | null; target_precision: number } | null };
  model: { kind: string; id: string | null; temporal_model: boolean; note: string; problem: string | null };
  observations: string[];
}

export interface SourceSignal {
  id: string;
  label: string;
  effect: "supporting" | "neutral" | "caution";
  detail: string;
}

export interface DirectoryEntry {
  domain: string;
  name: string;
  category: "wire_service" | "broadcaster" | "newspaper" | "satire";
  reason?: string;
}

export interface SourceAssessment {
  host: string;
  assessment: "recognised_publisher" | "declared_satire" | "lookalike" | "unknown";
  label: string;
  summary: string;
  matched: DirectoryEntry | null;
  resembles: DirectoryEntry | null;
  signals: SourceSignal[];
  not_checked: string[];
  caveat: string;
  directory: { version: string; entries: number; meaning: string };
}

export interface UrlDetails {
  url: {
    requested: string;
    final: string;
    redirects: string[];
    http_status: number;
    content_type: string;
    bytes_read: number;
    truncated: boolean;
    fetch_ms: number;
    extraction: {
      method: "article_element" | "paragraphs" | "plain_text" | "none";
      words: number;
      paragraphs: number;
      title: string | null;
      headline: string | null;
      author: string | null;
      published: string | null;
      site_name: string | null;
      language: string | null;
      notes: string[];
    };
  };
  source: SourceAssessment;
}

export interface Analysis {
  id: number;
  analysis_type: "text" | "image" | "url" | "video" | "multimodal" | "evidence";
  verdict: string;
  confidence: number | null;
  status: string;
  headline: string | null;
  source_filename: string | null;
  source_url?: string | null;
  submitted_text: string | null;
  created_at: string;
  model: { module: string; name: string; version: string; status: ModuleStatus } | null;
  details: (TextDetails & Partial<ImageDetails> & Partial<UrlDetails> & Partial<EvidenceDetails> & Partial<MultimodalDetails> & Partial<VideoDetails>) | null;
  limitations: string | null;
  is_demo: boolean;
  has_heatmap: boolean;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface DashboardStats {
  total_analyses: number;
  by_type: Record<string, number>;
  by_verdict: Record<string, number>;
  daily: { date: string; count: number }[];
  recent: Analysis[];
  modules: { module: ModuleKey; name: string; status: ModuleStatus }[];
}

export interface Feedback {
  id: number;
  analysis_id: number | null;
  category: string;
  message: string;
  status: "new" | "reviewed" | "dismissed";
  created_at: string;
  user_id: number | null;
  username: string | null;
}

export interface AdminUser extends User {
  analysis_count: number;
}

export interface AuditEntry {
  id: number;
  created_at: string;
  user: string | null;
  action: string;
  entity: string | null;
  entity_id: string | null;
  ip_address: string | null;
  detail: Record<string, unknown> | null;
}

export interface AdminStats {
  users: { total: number; active: number; admins: number; new_last_7_days: number };
  analyses: { total: number; by_type: Record<string, number>; by_verdict: Record<string, number>; daily: { date: string; count: number }[] };
  feedback: Record<string, number>;
  models: ModelEntry[];
}

export interface EvaluationResponse {
  evaluation: {
    model: string;
    version: string;
    trained_at: string;
    deployed_model: string;
    features: { type: string; ngram_range: number[]; max_features: number; vocabulary_size: number };
    comparison: Record<string, { validation: ClassMetrics; test: ClassMetrics; external_liar2: ClassMetrics; train_seconds: number; inference_ms_per_doc: number }>;
    calibration_logistic_regression: Record<string, number>;
    interpretation: string;
  };
  dataset: {
    name: string;
    source: string;
    license: string;
    notes: string;
    rows_clean: Record<string, number>;
    removed: Record<string, number>;
    label_distribution_fake_share: Record<string, number>;
    reuters_tag_rate_by_label: Record<string, number>;
    external_test_set: { name: string; source: string; license: string; rows: number; fake_share: number; median_tokens: number };
  };
}

/** The Urdu evaluation file written by ai_models/training/train_text_urdu.py. */
export interface UrduEvaluationResponse {
  evaluation: {
    model: string;
    version: string;
    trained_at: string;
    selected: string;
    features: { type: string; analyzer: string; ngram_range: number[]; vocabulary_size: number; C: number };
    test: ClassMetrics & { n: number; accuracy_ci95: number[]; roc_auc_ci95: number[] };
    decision_coverage: { threshold: number; share_decided: number; accuracy_when_decided: number; n_decided: number };
    calibration: { ece_test: number };
    baselines: { majority_accuracy: number; length_only: { accuracy: number; roc_auc: number } };
    by_category_accuracy: Record<string, { n: number; accuracy: number }>;
    interpretation: string;
  };
  dataset: {
    name: string;
    license: string;
    rows_clean: { train: number; test: number };
    pairing: { nearest_neighbour_has_opposite_label: number };
    notes: string;
  };
}

/** The evidence stance evaluation written by ai_models/training/evaluate_evidence_nli.py. */
export interface VideoSetResult {
  videos_read: number; videos_used: number; videos_unusable: number; n_fake: number; n_real: number; face_frames: number;
  frame_auc: number | null; video_auc: number | null; video_auc_ci95: [number, number] | null; video_auc_by_aggregator: Record<string, number | null>;
  single_frame_auc: number | null; constant_answer_accuracy: number;
  decision_rule: { n: number; decided: number; decided_share: number; accuracy_on_decided: number | null; fake_calls: number; fake_calls_correct: number; real_calls: number; real_calls_correct: number };
}

export interface VideoEvaluationResponse {
  evaluation: {
    model: string; revision: string; frames_per_video: number; created_at: string; aggregator: string;
    calibration: { fake_min: number | null; real_max: number | null; target_precision: number; chosen_on_videos: number };
    sets: Record<"calibration" | "test" | "fresh", string>;
    results: Partial<Record<"calibration" | "test" | "fresh", VideoSetResult>>;
  };
}

export interface EvidenceEvaluationResponse {
  evaluation: {
    model: string;
    evaluated_at: string;
    what_was_measured: string;
    n: number;
    stance_threshold: number;
    forced_choice_accuracy: number;
    at_threshold: { share_decided: number; n_decided: number; accuracy_when_decided: number; accuracy_ci95: number[] };
    baselines: { majority_accuracy: number };
    interpretation: string;
  };
  dataset: { name: string; source: string; license: string; sampling: string };
}
