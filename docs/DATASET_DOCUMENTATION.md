# Dataset and Evaluation Status

No labeled evaluation dataset is bundled or configured in this repository. Dataset name, source, license, language coverage, and split details are therefore not claimed here. Operators must verify dataset provenance, permissions, and suitability before running an evaluation.

The backend/ml_pipeline/train_eval.py evaluator accepts caller-supplied labeled rows or a CSV containing text and label columns. It does not train a model. It makes a deterministic, stratified 80/20 partition and evaluates the active inference service on the 20% holdout. It writes accuracy, macro and class-wise precision/recall/F1, a confusion matrix, the supplied dataset filename, and a SHA-256 digest when persistence is enabled. The model name and version come from the active inference service.

The filename and hash identify the input but do not independently verify its source, license, quality, or the correctness of the labels. Evaluation output is available to the dashboard only when a persisted result contains the required provenance and metric fields. The bundled evaluation_results.json currently reports:

> Model evaluation data not available.

Do not treat metrics from a small, synthetic, or unsuitable dataset as evidence of real-world moderation performance.
