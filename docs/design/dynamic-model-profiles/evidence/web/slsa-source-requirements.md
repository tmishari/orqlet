# SLSA v1.2: Source requirements (two-party review)

URL: https://slsa.dev/spec/v1.2/source-requirements
Retrieved: 2026-11-04, between 18:20 and 19:10 (UTC+2); the tool returns no time for each page
Tool: WebSearch (Cursor), which saved the full page text to a file; the excerpts come from that file
Processed: unknown (the tool does not say whether a model processed the text)
Data class: public

Excerpts are verbatim from the text the tool returned.

1. Level 4 - "Level 4: Two-party review"
2. Summary - "The SCS requires two trusted persons to review all changes to protected branches."
3. Requirement - "Changes in protected branches MUST be agreed to by two or more trusted persons prior to submission. The following combinations are acceptable: Uploader and reviewer are two different trusted persons. Two different reviewers are trusted persons. Reviews SHOULD cover, at least, security relevant properties of the code."
4. Final revision - "This requirement applies to the final revision submitted. I.e., if additional changes are made during the review process, those changes MUST be reviewed as well."
5. Context - "Approvals are for a specific context, such as a repo + branch in git."
