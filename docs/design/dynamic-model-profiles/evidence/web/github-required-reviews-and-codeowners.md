# GitHub: required reviews, branch protection and code owners

URL: https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/approving-a-pull-request-with-required-reviews, https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule and https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners
Retrieved: 2026-11-04, between 18:20 and 19:10 (UTC+2); the tool returns no time for each page
Tool: WebSearch (Cursor), whose result carried an excerpt of each page; the pages themselves were not fetched
Processed: unknown (the tool does not say whether a model processed the text)
Data class: public

Excerpts are verbatim from the text the tool returned.

1. Author cannot approve - "Pull request authors cannot approve their own pull requests."
2. Admin bypass - "Repository owners and administrators can merge a pull request even if it hasn't received an approving review, or if a reviewer who requested changes has left the organization or is unavailable."
3. Stale approvals - "If both required reviews and stale review dismissal are enabled and a code-modifying commit is pushed to the branch of an approved pull request, the approval is dismissed."
4. Last pusher - "Optionally, to require someone other than the last person to push to a branch to approve a pull request prior to merging, select Require approval of the most recent reviewable push."
5. Code owner review - "Optionally, to require review from a code owner when the pull request affects code that has a designated owner, select Require review from Code Owners. Note that if code has multiple owners, an approval from any of the code owners will be sufficient to meet this requirement."
6. Owners need write access - "The people you choose as code owners must have write permissions for the repository."
7. Owners are requested - "Code owners are automatically requested for review when someone opens a pull request that modifies code that they own."
8. Any owner suffices - "When reviews from code owners are required, an approval from any of the owners is sufficient to meet this requirement."
