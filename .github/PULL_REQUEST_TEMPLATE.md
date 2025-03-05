## **Pull Request Description Template:**

Use Markdown for formatting.

**Markdown**

\`## Description

\[Clearly and concisely describe the changes introduced by this pull request. Explain the "why" behind the changes and the approach taken. Provide context where necessary.\]

**Key changes:**

* \[List the most important changes made. Be specific. Use bullet points or numbered lists.\]
* \[Example: Implemented two-factor authentication using TOTP.\]
* \[Example: Fixed a bug where dates were displayed in the wrong format in the user profile section.\]
* \[Example: Added a new setting to allow users to switch between light and dark mode.\]

**Related issue(s)/ticket(s):**

* \[Link to any related issues or tickets. Use keywords like "Fixes," "Resolves," "Closes," or "Relates to."\]
* \[The link preferably should be a link to a GitLab issue. If possible, also add a link to the Mattermost thread. The important thing is to have enough context to review the Pull Request.\]
* \[Example: GitLab Issue ]
* \[Example: Mattermost Thread ]
* \[Example: Fixes #123, Closes #456\]

**Testing done:**

* \[Describe the testing performed to ensure the changes are working as expected. Be specific about the test cases and scenarios covered.\]
* \[Example: Manually tested login with two-factor authentication enabled and disabled.\]
* \[Example: Ran unit tests and integration tests for the date formatting functionality.\]
* \[Example: Tested dark mode on Chrome, Firefox, and Safari.\]

**Screenshots & GIFs (if applicable):**

* \[Include screenshots to visually demonstrate the changes, especially for UI changes.\]
* \[The screenshot should be marked with highlighters, rectangles, arrows, or any form of visual representation to focus on the area of the image that matters.\]
* \[Make sure not to include any screenshots that show real customer data, for example: addresses, names, numbers, etc.\]
* \[Include GIFs to understand the workflow and process better.\]

**Further comments/notes (optional):**

* \[Add any additional information that might be helpful for reviewers. This could include potential edge cases, limitations, or alternative approaches considered.\]
* \[Example: Considered using SMS-based authentication but decided to go with TOTP for better security.\]

**Checklist:**

* [ ] I have performed a self-review of my code.
* [ ] I have added or updated unit tests.
* [ ] I have updated the documentation (if necessary).
* [ ] I have followed the project's coding style guidelines.