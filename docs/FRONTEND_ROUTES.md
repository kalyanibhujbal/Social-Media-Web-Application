# Frontend Page Map and Accessibility Status

The application switches views using internal page keys; it does not define browser URL routes. Pages requiring sign-in or administrator rights also have backend authorization on their API endpoints.

| Page key | Page | Access level | Description |
|---|---|---|---|
| home | Home and approved feed | Public | View/search approved posts, use the non-persisting moderation sandbox, and create text, image, video, event, or article content while signed in. |
| explore | Explore | Public | Discover approved posts from public accounts and open creator profiles; private-account posts are excluded by the backend. |
| events | Events | Public | Browse approved event posts and open/interact with event cards. |
| articles | Articles | Public | Browse approved article posts and open the reading view. |
| article-reader | Article reading/editing | Public; editing is owner-only | Read an article and use the shared like/comment controls; authors can edit or delete their own article. |
| network | My network | Signed-in account | Review connection invitations, accepted connections, private-account follow requests, and member suggestions. |
| notifications | Notifications | Public | Empty state. The backend does not provide a notifications endpoint; personal moderation results remain available in the signed-in dashboard. |
| messages | Messages | Public | Messaging layout preview. The backend does not provide conversation or message endpoints; compose controls are disabled. |
| login, register | Sign-in and account creation | Public | Authenticate or create an account. |
| profile | Profile | Public with private-account restrictions | View public profiles and approved posts. Private profile details and posts require owner access or approved-follow status. |
| dashboard | User dashboard | Signed-in account | View the current user's own posts, comments, predictions, confidence, review state, and history. |
| admin | Admin dashboard | Administrator; API authorization enforced by backend | Review content, inspect minimized audit/user records, and view database-backed summaries, model metadata, available evaluation output, and reports. |
| account-settings | Account settings | Signed-in account | Correct profile details, change public/private visibility after password confirmation, export data, and manage account deletion. |
| privacy-policy, terms, cookies-policy, refund-policy, consent, data-rights, grievance, ai-transparency, accessibility, copyright | Legal and privacy information | Public, except account data/request controls require sign-in | Privacy notice, user rights, preferences, grievances, moderation limitations, accessibility statement, and project notices. |

## Navigation and responsive layout

Navigation is managed with internal page keys rather than browser URL routes. The desktop header includes Home, Explore, Events, Articles, Network, notifications, and messaging; the mobile layout provides a compact top bar and fixed bottom navigation. Private-account follow approvals are managed in My Network.

## Accessibility practices and verification status

Source includes native controls, labels, visible focus styling, text labels for statuses, semantic table headers, and text alternatives for dashboard charts. These practices have not been independently verified across browsers or assistive technology. Contrast ratios, dialog focus management, keyboard-only navigation, zoom, and responsive layout need manual verification. No WCAG conformance is claimed. See Accessibility Practices and Verification Status in ACCESSIBILITY_CHECKLIST.md.
