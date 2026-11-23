"""Print the measured evaluation of the deployed text model from its metrics file.

Usage: python scripts/evaluation/print_text_metrics.py
The numbers are read from ai_models/evaluation/results/text_baseline_en_metrics.json, which the training script writes.
Nothing is computed or estimated here.
"""
import json
import sys
from pathlib import Path

PATH = Path(__file__).resolve().parents[2] / "ai_models" / "evaluation" / "results" / "text_baseline_en_metrics.json"


def main() -> int:
    if not PATH.exists():
        print(f"No metrics file at {PATH}. Train the model first: bash scripts/training/train_text_model.sh")
        return 1
    data = json.loads(PATH.read_text(encoding="utf-8"))
    print(f"Model: {data['model']} {data['version']}  (deployed: {data['deployed_model']}, trained {data['trained_at']})")
    header = f"{'model':<20}{'set':<16}{'n':>7}{'acc':>8}{'f1':>8}{'auc':>8}"
    print(header)
    print("-" * len(header))
    for name, sets in data["comparison"].items():
        for key in ("validation", "test", "external_liar2"):
            m = sets[key]
            print(f"{name:<20}{key:<16}{m['n']:>7}{m['accuracy']:>8.3f}{m['f1_fake']:>8.3f}{m['roc_auc']:>8.3f}")
    cal = data.get("calibration_logistic_regression", {})
    if cal:
        print("\nCalibration (logistic regression):", ", ".join(f"{k}={v}" for k, v in cal.items()))
    print("\n" + data.get("interpretation", ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
