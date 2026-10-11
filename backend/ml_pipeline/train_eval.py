import os
import json
import logging
import csv
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List

from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_fscore_support, accuracy_score

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ml_pipeline.train_eval")

EVALUATION_FILE = os.path.join(os.path.dirname(__file__), "evaluation_results.json")

class ModelTrainerEvaluator:
    """
    Evaluate the active inference service on caller-supplied labeled data.

    This class does not train a model or provide/approve a dataset. It evaluates
    the current inference service on a stratified 20% holdout and records the
    supplied dataset's filename and SHA-256 digest when results are persisted.
    """

    def __init__(self, dataset_path: str = None):
        self.dataset_path = dataset_path
        self.classes = ["Hate Speech", "Offensive", "Normal"]

    def run_benchmark(
        self,
        sample_data: List[Dict[str, str]] = None,
        *,
        persist: bool = True,
    ) -> Dict[str, Any]:
        """Evaluate supplied labeled data; never manufacture a benchmark set."""
        dataset_source = "provided labeled data"
        if sample_data is None and self.dataset_path:
            with open(self.dataset_path, newline="", encoding="utf-8") as dataset_file:
                sample_data = list(csv.DictReader(dataset_file))
            dataset_source = os.path.basename(self.dataset_path)
        if not sample_data:
            raise ValueError("Provide labeled evaluation data or configure a CSV dataset_path.")
        if any(not item.get("text") or not item.get("label") for item in sample_data):
            raise ValueError("Every evaluation row must include non-empty text and label fields.")

        texts = [item["text"] for item in sample_data]
        y_true = [item["label"] for item in sample_data]

        # Hold out 20% for evaluation. The active model is not trained here.
        _, test_texts, _, test_labels = train_test_split(
            texts, y_true, test_size=0.2, random_state=42, stratify=y_true
        )

        # Import inference service for evaluation predictions
        from app.services.model_inference import inference_service

        y_pred = [inference_service.predict(t)["predicted_class"] for t in test_texts]

        acc = accuracy_score(test_labels, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(test_labels, y_pred, average="macro", zero_division=0)
        conf_matrix = confusion_matrix(test_labels, y_pred, labels=self.classes).tolist()
        class_report = classification_report(test_labels, y_pred, labels=self.classes, output_dict=True, zero_division=0)

        results = {
            "model_name": inference_service.model_name,
            "model_version": inference_service.model_version,
            "dataset_source": dataset_source,
            "dataset_sha256": hashlib.sha256(
                "\n".join(f"{item['label']}\0{item['text']}" for item in sample_data).encode("utf-8")
            ).hexdigest(),
            "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
            "total_eval_samples": len(test_labels),
            "metrics": {
                "accuracy": round(float(acc), 4),
                "macro_precision": round(float(precision), 4),
                "macro_recall": round(float(recall), 4),
                "macro_f1_score": round(float(f1), 4)
            },
            "confusion_matrix": {
                "labels": self.classes,
                "matrix": conf_matrix
            },
            "class_wise_metrics": class_report,
            "evaluation_status": "COMPLETED"
        }

        if persist:
            with open(EVALUATION_FILE, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)

        logger.info("Evaluation completed on %d held-out rows for %s.", len(test_labels), inference_service.model_name)
        return results

def get_latest_evaluation() -> Dict[str, Any]:
    """Return only evaluation results with labeled-dataset provenance."""
    if os.path.exists(EVALUATION_FILE):
        try:
            with open(EVALUATION_FILE, "r", encoding="utf-8") as f:
                results = json.load(f)
            if (
                results.get("evaluation_status") == "COMPLETED"
                and results.get("dataset_source")
                and results.get("dataset_sha256")
                and results.get("metrics")
                and results.get("confusion_matrix")
            ):
                return results
        except Exception:
            pass
    return {
        "evaluation_status": "NOT_AVAILABLE",
        "notice": "Model evaluation data not available."
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Evaluate the active moderation model on labeled CSV data.")
    parser.add_argument("dataset_csv", help="CSV file with text and label columns")
    args = parser.parse_args()
    evaluator = ModelTrainerEvaluator(dataset_path=args.dataset_csv)
    res = evaluator.run_benchmark()
    print(json.dumps(res, indent=2))
