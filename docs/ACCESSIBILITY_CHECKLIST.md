# Accessibility Practices and Verification Status

Reviewed 27 September 2026. This project has not been independently audited and does not claim WCAG conformance or certification.

| Area | Implemented in source | Verification status / remaining work |
| --- | --- | --- |
| Keyboard access | Native buttons, links, form controls; `:focus-visible` outline; skip link | Test all pages with keyboard-only use, including modal focus return and consent controls |
| Structure | Main/header/nav/footer landmarks, heading structure, native tables | Check screen-reader navigation and heading order in rendered pages |
| Forms | Explicit labels on registration, profile, and privacy request controls; `role=alert/status` on selected feedback | Audit every error/success path and required-field description |
| Dialogs | Content review modal has accessible name and keyboard handlers | Verify behavior with screen readers and keyboard at runtime |
| Charts | Confidence distribution includes a text summary; evaluation uses a data table | Verify chart fallback text and matrix headers after actual evaluation data is supplied |
| Status | Moderation states are displayed as words; colors are supplementary | Check every badge and report for color-independent status |
| Contrast | Dark palette and focus styling are defined in `frontend/src/index.css` | Contrast ratios have not been measured for all text, controls, and hover/focus states |
| Responsive design | Flexible grids, wrapping action groups, horizontally scrollable tables, narrow-screen cookie layout | Test on actual viewport sizes and zoom; no automated responsive test suite exists |
| Images | No remote or informative images are used by core screens; favicon is decorative | Keep meaningful image alternatives if images are added later |

Keyboard access, screen-reader behavior, contrast, browser zoom, reduced motion, and responsive layout require manual verification before making conformance claims.
