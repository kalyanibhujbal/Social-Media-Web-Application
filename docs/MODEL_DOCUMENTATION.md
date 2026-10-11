# Model and Moderation Transparency

## Current runtime

The active default is `distilbert-base-uncased-finetuned-sst-2-english`, an English sentiment model. The inference service first applies English keyword lists. Otherwise it uses the sentiment model if its files are already available in the local model cache; `MODEL_LOCAL_FILES_ONLY=true` by default prevents runtime model-hub requests. If the model cannot load, a keyword/heuristic fallback is used.

The service maps these inputs into three labels: `Hate Speech`, `Offensive`, and `Normal`. The sentiment model itself is not trained or validated as a three-class hate-speech detector. Its scores are mapped into application probabilities; the returned confidence is not calibrated and must not be treated as a validated likelihood.

## Language handling and preprocessing

Language labels are inferred from scripts and a small set of word patterns. This is not a multilingual classifier. Preprocessing normalizes Unicode and whitespace, replaces URLs and mentions, unpacks hashtags, converts emoji to text, and compresses repeated characters. These transformations can remove context.

## Explanations

The application shows words that match the same heuristic keyword lists. These are rule indicators only. They are not LIME, SHAP, causal attribution, or an explanation of the sentiment model.

## Review and limitations

Predictions may be wrong because of context, sarcasm, reclaimed terms, dialect, language, and group identity. False positives and false negatives are expected risks. Flagged content can be inspected by an authorized reviewer and users can appeal post decisions. Outputs are automated predictions, not legal determinations.

Evaluation metrics are shown only when a result file includes dataset provenance, a dataset hash, metrics, and a confusion matrix. The bundled unprovenanced values were removed; the dashboard therefore displays “Model evaluation data not available.” Run `backend/ml_pipeline/train_eval.py` with an actual labeled CSV to create a provenance-bearing evaluation record.
