# Prediction Highlights

The current service does not implement LIME or SHAP. It scans tokens against the same English keyword sets used by prediction heuristics and reports the matched word and rule category. These are indicators only; they are not causal explanations of the transformer sentiment output.

The UI and API call these results **Keyword Rule Highlights**. Do not describe them as feature attributions or as proof that a submission violated policy. For empty text or text without a configured keyword match, the service returns no highlighted terms.
