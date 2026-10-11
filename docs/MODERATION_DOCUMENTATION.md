# Moderation Workflow

The current runtime is a prototype. It combines English keyword rules and, when locally cached, an English sentiment model. It maps results to Hate Speech, Offensive, and Normal, but has not been validated as a three-class hate-speech detector. Confidence values are not calibrated evaluation probabilities. See [Model Documentation](MODEL_DOCUMENTATION.md).

## Decision status

The policy engine maps the application's prediction and confidence thresholds into `APPROVED`, `FLAGGED_FOR_REVIEW`, or `BLOCKED`. Unsupported language or low-confidence outcomes may be flagged. A label or automated status is not a legal determination.

## User appeals and administrator review

Users can appeal their own post through `/api/v1/posts/{post_id}/appeal`. Backend authorization ensures the post belongs to the requesting account. Administrators access review APIs only when the current database account has role `ADMIN`. The queue includes moderation content without author account fields. A review can approve, block/reject, flag, or mark an item reviewed; state changes are audited. Non-marking decisions require explicit confirmation.

Rule highlights are keyword matches. They do not explain the model output. Free-form review notes are not collected.

## Accessibility note

Statuses include text; color is supplemental. See [Accessibility Practices and Verification Status](ACCESSIBILITY_CHECKLIST.md). WCAG conformance has not been independently verified.
