# Frontend Page Map and Accessibility Status

The application switches views using internal page keys; it does not define browser URL routes. Pages requiring sign-in or administrator rights also have backend authorization on their API endpoints.

| Page key | Page | Access level | Description |
|---|---|---|---|
| home | Home and approved feed | Public | View/search approved posts, use the non-persisting moderation sandbox, and create text posts while signed in. Search filters the public posts returned by the existing endpoint. |
| network | My network | Public | Layout preview with fictional sample profiles. The backend does not provide connection or invitation endpoints, so those controls are disabled and no network actions are simulated. |
| notifications | Notifications | Public | Empty state. The backend does not provide a notifications endpoint; personal moderation results remain available in the signed-in dashboard. |
| messages | Messages | Public | Messaging layout preview. The backend does not provide conversation or message endpoints; compose controls are disabled. |
| login, register | Sign-in and account creation | Public | Authenticate or create an account. |
| profile | Profile | Signed-in account | Display the current user's backend account fields and own posts. Headline, location, experience, education, skills, and profile photo are not exposed by the current API. |
| dashboard | User dashboard | Signed-in account | View the current user's own posts, comments, predictions, confidence, review state, and history. |
| admin | Admin dashboard | Administrator; API authorization enforced by backend | Review content, inspect minimized audit/user records, and view database-backed summaries, model metadata, available evaluation output, and reports. |
| account-settings | Account settings | Signed-in account | Correct username/email after password confirmation and manage account deletion. |
| privacy-policy, terms, cookies-policy, refund-policy, consent, data-rights, grievance, ai-transparency, accessibility, copyright | Legal and privacy information | Public, except account data/request controls require sign-in | Privacy notice, user rights, preferences, grievances, moderation limitations, accessibility statement, and project notices. |

## Navigation and responsive layout

Navigation is managed with internal page keys rather than browser URL routes. The desktop header includes feed search, and the mobile layout provides a compact top bar and fixed bottom navigation. Search is local filtering over approved feed results; user-directory search is not available in the API.

## Accessibility practices and verification status

Source includes native controls, labels, visible focus styling, text labels for statuses, semantic table headers, and text alternatives for dashboard charts. These practices have not been independently verified across browsers or assistive technology. Contrast ratios, dialog focus management, keyboard-only navigation, zoom, and responsive layout need manual verification. No WCAG conformance is claimed. See Accessibility Practices and Verification Status in ACCESSIBILITY_CHECKLIST.md.
