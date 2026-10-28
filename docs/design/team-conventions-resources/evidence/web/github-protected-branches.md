# About protected branches - GitHub Docs
URL: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
Retrieved: 2026-10-26T16:43Z (workstation clock, UTC) through the WebFetch tool. The excerpts below are verbatim; the label of each says where it sits on the page.

## Excerpt 1: What a rule enforces
You can enforce certain workflows or requirements before a collaborator can push changes to a branch in your repository, including merging a pull request into the branch, by creating a branch protection rule.

## Excerpt 2: Settings
- Require pull request reviews before merging
- Require status checks before merging
- Require conversation resolution before merging
- Require signed commits
- Require linear history
- Require merge queue
- Require deployments to succeed before merging

## Excerpt 3: Status checks
Required status checks must have a `successful`, `skipped`, or `neutral` status before collaborators can make changes to a protected branch. Required status checks can be checks or commit statuses.

## Excerpt 4: Admins are not bound by default
By default, the restrictions of a branch protection rule do not apply to people with admin permissions to the repository or custom roles with the "bypass branch protections" permission in a repository.

## Excerpt 5: Code owners
Optionally, you can choose to require reviews from code owners. If you do, any pull request that affects code with a code owner must be approved by that code owner before the pull request can be merged into the protected branch.

## Excerpt 6: Linear history
Enforcing a linear commit history prevents collaborators from pushing merge commits to the branch. This means that any pull requests merged into the protected branch must use a squash merge or a rebase merge.
