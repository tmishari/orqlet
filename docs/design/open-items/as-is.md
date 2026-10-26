---
schema: orqlet.as-is/v1
header:
  schema: orqlet.artifact-header/v1
  task: open-items
  status: draft
  workflow_version: 0.3.1
  protected_set_digest: be7723282aec5a67e8161540bfba464562fb2a53d9bc3f8245ea22b812134eec
  bound:
    base_revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    standards_lock_hash: 89a225016ff9d8b3ed977df39a70dfbe9dbc5f7c6d3762d0f2208b1b7a037a52
    applicable_rules_hash: 56502a0ec5eda3b13b4c9d97c7d4dfa41df82c86a206e36dd5d2d92aab299b97
    profile_version: 1
base_revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
scope:
  paths:
  - docs/design/orqlet-architecture-proposal.md
  - docs/design/orqlet-implementation/**
  - docs/design/orqlet-m2-workflow/**
  - docs/design/harness2-fit/**
  - .orqlet/**
  - .github/**
  - src/orqlet/application/usecases/**
  - src/orqlet/application/contracts/**
  request_ref: open-items
research_mode: parallel-subagents
size_budget:
  max_words: 5319
facts:
- id: A-1
  kind: structure
  statement: Section 17.7 defines a design or plan as approved when it is present on the protected baseline
    branch (the branch for which branch protection requires pull-request review and code-owner approval)
    and the code host shows it arrived through a pull request merged with an approving review from the
    required code owners (merge_evidence); without that evidence the result is NOT_RUN, the artifact header
    status field is informational, and CI evaluates approval against the baseline and never against the
    head of the pull request being judged.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '3037'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 2f3e12f296bbb028cea6cf8b0e4a03ce732263f2eb6165e8f5dc8fd49ca0a083
- id: A-2
  kind: flow
  statement: Phase 2 step 4 defines approval as the review and merge of the design pull request by an
    authorised human, meaning an identity the code host lists as a code owner of docs/design/** (plus
    any further owner the standards require for the class) who is neither the pull request's author nor
    the agent, states that an agent saying 'approved' is not approval, and says CI derives the approval
    record from host evidence, not from pull-request text, and that the channel and approvers are open
    question Q-03.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2926'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 758c5846bdfb4a6cc20397afd94430f8b5564bc17794b4fb58089480ddb067fd
- id: A-3
  kind: flow
  statement: Section 19.8.4 says presence on the baseline is not review (a direct push, a bypass or a
    path CODEOWNERS does not cover also puts a file there, and the Orqlet-Task and Orqlet-Phase trailers
    are written by the author), and requires stage 2 to find the last commit that touched each design
    and plan file on the baseline, the pull request that merged it and that pull request's approving reviews
    at its head commit, to check them against CODEOWNERS at the merge base (a path no owner matches counts
    as unapproved), and to report NOT_RUN if the evidence cannot be obtained.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 3815-3817
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: b992f4650081e33e3eaa6207b1e7fcb73f8d7a7ade0056e2b789dc768585d639
- id: A-4
  kind: flow
  statement: Section 19.8.4 states approval evidence is required and is not a project option, and that
    a change to the base branch between review and merge needs strict required checks or a merge queue.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '3817'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 32568603c2eef9918367bd4405a781892d4067cc1d39e32fec909a8f51c2f19e
- id: A-5
  kind: structure
  statement: Decision D-22 (status Default) records that approval is presence on the protected baseline
    with merge evidence from the code host, recorded as an approval record, with 'Looser, local-only gating'
    as the main alternative.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '5147'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 51ff392aa3cd0e555c8497cf5535998e6f674f64957e43debeaaf780fa7fd0eb
- id: A-6
  kind: structure
  statement: Question Q-03 asks where design and plan approvals live and who is an authorised human, records
    the recommendation of the merged design and plan pull request on the protected baseline approved by
    the code owners that CODEOWNERS names for docs/design/** plus a security owner for change class D3,
    asks 'which people or roles, and how many approvers?', and says a ticket workflow or local sign-off
    could only be attested, not verified.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '5090'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 6e3ce4f91818afce56b583bcbf6d9c6e44fb4518aacc7bd234f301a0a2ab74af
- id: A-7
  kind: flow
  statement: ci check item 13 requires every governed pull request to have at least one approving review
    at its head from someone who is not its author (a code owner for owned paths), and says attested evidence
    such as review notes counts only together with it.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '3760'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 8832fc6e2a44329bd86258c58b1da0400adb309f79b612e558d04ab48b2b1ccd
- id: A-8
  kind: flow
  statement: 'Approval counting in the evaluator: an approving review counts only if its author is not
    the pull request''s author, is a code owner for the owned paths, was submitted on the current head
    commit and has not been dismissed; a CHANGES_REQUESTED review from a code owner blocks until dismissed
    or superseded by a later approval on the current head; a new commit cannot reuse approval evidence
    from an earlier commit whether or not the host''s dismiss-stale-approvals setting is on.'
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '3884'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: c14cb8004d46fc4ea1d079b24be87c610f4b749802c1ea146fbaae22d7a0272b
- id: A-9
  kind: structure
  statement: Enforcement matrix row E-08 (class S) makes 'an authorised human approves the identified
    artifact versions and scope before implementation' enforced by code-host merge evidence and CODEOWNERS,
    with NOT_RUN if evidence is absent and the stated bypasses 'Bypass actors and admins, rubber-stamping,
    a compromised account, CODEOWNERS gaps (audited by doctor)'.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '3981'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: a5213f8a8130bf21b4ae32312db25946f6b4608d085c62c8481b5168fd356521
- id: A-10
  kind: structure
  statement: Enforcement matrix row E-01 (classes S, L, I) states that no merge without an approved design
    and plan is enforced by ci check stage 2 and by the gate status precondition of /orqlet-implement,
    and that 'Local implementation before approval is not prevented'.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '3974'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 2f511933376c2945270993d7d9cc588deba9ba9d00a596361181fb85b12ad4bb
- id: A-11
  kind: structure
  statement: Control class S (trusted CI and repository protection) is described as strong only if the
    code host is configured for it and nobody holds a bypass, class L (hooks, doctor, gate status, validators)
    as advisory and bypassable, and class C (client controls) as editable by whoever can write the settings.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 3960-3964
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 11d2cb40d626f7388bf176b142b9a20664fe01126f32169290fbad8f8c034805
- id: A-12
  kind: flow
  statement: The Phase 4 precondition runs orqlet gate status (the same logic as CI, including approval
    evidence, which an offline run reports as NOT_RUN) and stops unless the design and plan are approved
    on the baseline and their bound inputs are current.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '3007'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 91843bb1b2b30e26572b6f9e1dad05d03449392e42f118a329b480e375956430
- id: A-13
  kind: structure
  statement: Section 19.8.2 item 1 defines the baseline as the tip of the target branch or a pinned ref
    in a separate repository the organisation controls, defines the enforcement policy as every file under
    .orqlet/, CODEOWNERS, the workflow files that run the check and the required-check list, and says
    the first baseline is the merge commit of the approved init pull request (path A) while the baseline
    of a local bootstrap commit (path B) is NOT_RUN until a non-author code owner has merged a confirmation
    pull request.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '3771'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: ed98568c1d1a71b1b5362afd56737b65270ad92b77a30b4d8e4f9ad18d69d61d
- id: A-14
  kind: structure
  statement: W-1 fixes that implementation starts only after the design and the plan are approved.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '3365'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 48be5b7a3068de5c06172ffc9622cab37ae635e4d2dcb6c3886f37197bd1a48a
- id: A-15
  kind: structure
  statement: 'Trusted CI is the two-stage design: stage 1 runs on pull_request, runs the project''s checks,
    is pull-request-controlled for same-repository pull requests and publishes nothing; stage 2 is a default-branch
    workflow triggered by workflow_run, pushes to the default branch and a schedule, runs orqlet ci check
    at the baseline version with the credentials of a dedicated GitHub App held in an environment restricted
    to the default branch, and is the only publisher of the required check, which a ruleset requires with
    that App as expected source.'
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 3774-3779
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: ae142dfeb9202d58aff57eb59fa40e05372eeebf4e6ac825fd25c5783f82dc07
- id: A-16
  kind: operation
  statement: Section 19.8.5 rule 1 requires CODEOWNERS (or the host's ruleset) to require code-owner review
    for every path on the agent-configuration surface with an owner for CODEOWNERS itself, and rule 5
    says GitHub reads CODEOWNERS from .github/ before the repository root, that ownerless or invalid lines
    and oversized files silently void a review requirement, and that checking the effective file through
    GitHub's CODEOWNERS errors endpoint is [U] not verified.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 3838-3842
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: f00640cbd8b5089707fe181ddb79cc219545fd0392cb7b4fad589987fa6069e4
- id: A-17
  kind: operation
  statement: 'The GitHub administrator checklist asks for a dedicated GitHub App (write checks, read pull
    requests, read contents, possibly actions: read and statuses: write [U]), its credentials in an environment
    limited to the default branch, a CODEOWNERS block with an owner for CODEOWNERS itself, a ruleset that
    requires the Orqlet check with the App as expected source, requires branches to be up to date, does
    not enable a merge queue, dismisses stale approvals, requires approval of the most recent reviewable
    push by someone other than the pusher and removes bypass actors or keeps them to a named few, the
    two-step bootstrap, re-running doctor after each ruleset change, and keeping the signal workflow enabled
    and not required.'
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 3848-3856
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 55a4ff8b5b98ae5738e5730a2e5d6d03536eddac1a20c5f3444879631c287795
- id: A-18
  kind: structure
  statement: Section 19.6 records the GitHub facts [D] that required checks must pass on the latest commit
    SHA, that a required check can be restricted to an expected source (a GitHub App), that stale approvals
    can be dismissed when the diff changes, that 'require approval of the most recent reviewable push'
    requires someone other than the pusher, that code owners are read from the base branch, and that admins
    and bypass actors can merge without approval unless bypass is removed (GH-01, GH-02, GH-05).
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '3724'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 507b6087ba4676e08cc65daa40781a481115bfda3a12f53dc913f1caa616d452
- id: A-19
  kind: structure
  statement: The residual-risk paragraph of Section 19.8.2 says that Orqlet can audit but not apply host
    configuration, that a repository administrator can edit rulesets and secrets, that a bypass actor
    can merge without review (GH-05), and that 'nothing requires a second approver or an alert on a policy
    pull request unless the host is configured for it'.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '3795'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 6153f242d8ce738384afe323e889f7f57730c32b4497f3d353851ffa1ac62424
- id: A-20
  kind: structure
  statement: 'The only plan-dependent statements about hosts and plans are: GitLab approvals are removed
    on new changes by default on Premium or Ultimate and Bitbucket Cloud merge checks and approval reset
    are Premium features (Section 19.6 portability), the Q-01 rationale that GitLab status checks are
    non-blocking by default and Bitbucket Cloud approval reset is Premium-only, Q-04''s question ''and
    on which plans?'' for managed settings; the document contains no table of GitHub Free, Pro, Team or
    Enterprise capabilities for rulesets, required reviews, merge queues or required workflows.'
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '3736'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 4154e6ce1d1325c62949da7604c68b8449432727b07d56e4d18e53ef770aa8a7
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '5089'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 7e8f3263006da18cdf92e1da563d5dbddfb68d47706254e8a203fe7798134133
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '5091'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 92ef64df84ae4638e8224cb94deb76efe8bc7bed4812581dc1458a913aed4727
- id: A-21
  kind: structure
  statement: 'A search of the architecture document for ''GitHub Free'', ''GitHub Pro'', ''GitHub Team''
    and ''GitHub Enterprise'' finds three lines (2634, 2702 and 5089): two about the GitHub MCP server
    and the Q-01 list of hosts. None is a table of what each GitHub plan offers for rulesets, required
    reviews, merge queues or required workflows.'
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2634'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: a9abfd666387067c13971d37be55d3f4a7df6578926ee00af6882c5aaf0520e2
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2702'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 6f204a15ec13e409b7c9185c59efd0c036dfb4ba94f4bb59e36a1be03a3ce647
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '5089'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 7e8f3263006da18cdf92e1da563d5dbddfb68d47706254e8a203fe7798134133
- id: A-22
  kind: structure
  statement: Section 1.8 states that the CI check against the approved policy baseline is enforced only
    when an administrator has configured the code host (a ruleset requiring the check from its expected
    source, code-owner review, protected workflow files) and does not bypass it, and that managed policy
    is the only candidate for controls a developer cannot change locally.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 398-402
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: f9d374b85b0b5bd3950273031386de637d57038432f43cdf7ebb5b9993ae6d53
- id: A-23
  kind: flow
  statement: Where no supported code host or CI exists, the server-side gates are 'unavailable' and doctor
    reports reduced capability, onboarding does not fail, and no provider is imposed; the product requires
    no CI provider.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '2884'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 2ec6a330069a15442dd04b2de666461b41928a85d22377d012253fa5e321e4b3
- id: A-24
  kind: structure
  statement: Spike S-14 (repository-protection audit, whether a Checks API check from a dedicated GitHub
    App satisfies a ruleset, merge_group and bootstrap rules) and spike S-28 (publication of a changing
    verdict) both need a test repository, S-28 also a test GitHub App, both after Q-01, and Appendix C
    states none has been performed.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '6077'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 08486ee38230c2f804bb7666495e01a6e560b4870f8c823a06a5bdc935b1c937
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '6091'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: e92d5ee9fdd001d85db18caf4bdad6777892da96579a748b03462ef255b8efff
- id: A-25
  kind: structure
  statement: The question summary table gives, for Q-01 'Affects' the CI matrix in M0 and spike S-14,
    the M2 CI workflow fragment, D-13 and D-28 and 'Does not block' M1, M3, M4; for Q-03 'Affects' how
    approvals are verified in M2 and who counts as an authorised human and 'Does not block' everything
    else; for Q-04 'Affects' Guard-C, the managed-policy proposals (M7) and a managed Cursor hook for
    Q-06 and 'Does not block' M1 to M4; for Q-05 'Affects' which local guard accompanies the merge-time
    gate and 'Does not block' M1, M3, M4.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 5079-5082
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 29e8294f4469ab78f9af227437bfca0d19a0d00ee0df96f5248a7c35f021ee10
- id: A-26
  kind: structure
  statement: Q-04 asks whether an administrator can deploy managed settings for Claude Code, Codex requirements.toml
    and Cursor Enterprise or Team hooks, and on which plans, and says without them 'strict' means a fixed
    workflow, visible drift and server-side gates.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '5091'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 92ef64df84ae4638e8224cb94deb76efe8bc7bed4812581dc1458a913aed4727
- id: A-27
  kind: structure
  statement: Q-05 asks which local guard should accompany the merge-time gate (Guard-A, Guard-B or Guard-C),
    recommends Guard-B by default and Guard-C if available, and says this is the one place where a native
    IDE limitation forces a human choice.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '5092'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 0b5b57f2cdea9f062d5003646289cda5a7cd555ee4a2fb861fe03cd12647d4e7
- id: A-28
  kind: structure
  statement: 'Q-07 is recorded ''Answered on 2026-10-25: option (1)'', by the person''s ''I approve all''
    in conversation, meaning the Code Reviewer is a provided capability and not a required gate.'
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '5094'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 310cb10e53c16144ead341ff3e5850160728402d98f9a6058d9630b7257889bb
- id: A-29
  kind: structure
  statement: Q-08 is recorded as answered on 2026-10-25 with the person approving v0.5 as the basis by
    'I approve all' in conversation, and states the person did not say whether v0.4 was approved and did
    not decide whether the plans that cite v0.4 are re-based, so both stay unrecorded.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '5095'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 53e6b6c6628f12097c9c67486691ed8d5fb2276e9bf6cb28dfb0c27c38f47815
- id: A-30
  kind: structure
  statement: The Q-01 to Q-06 rows carry no answer marker in Section 25.1, and Section 0.6.3 lists the
    open questions as 'Q-01, Q-03 to Q-06 (Q-07 and Q-08 answered on 2026-10-25)', while Q-02 no longer
    exists as a question and is now a pending input (Atlassian deployment type and approval-required spaces).
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '96'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: f142a29b7c89965911e90898650ef84a2e48ed60c042beaceb88da1797be830a
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '5117'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: e2a2a82cfee965ca2ba8b68b55f593704763d369fd3982fd81f0020efa6d1d16
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 5079-5083
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 6acf8c712d1b35716216eba05c11b901372660f18065a7e8ff2d9b3eaa09bd78
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 5089-5093
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 0923b30891447936b519b2a0f2423157a758eb3b9ebeb9a3dcead97c4ad4d47e
- id: A-31
  kind: structure
  statement: 'Decision D-13 (merge-queue review policy) and decision D-28 (trusted CI policy: policy from
    the approved baseline, a two-stage workflow, a dedicated GitHub App, written for GitHub until Q-01
    is answered, re-evaluation designed and unverified until S-28) both carry the status ''Needs input
    (Q-01)''.'
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '5138'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 0ac5e8bc0c566d7dc42dd2b6847f3ce34fd9348db7d9030aa4c9bd71e14b7a97
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '5153'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 856a350376ead722ad443e88826219d1e2aa8f3f6f34b6638150a058f3f7056d
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '6091'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: e92d5ee9fdd001d85db18caf4bdad6777892da96579a748b03462ef255b8efff
- id: A-32
  kind: structure
  statement: Section 25.3 says the recorded defaults are not asked to be approved and that M0 is meant
    to begin when Q-01, Q-03, Q-04 and Q-05 are answered, adding that 'in practice milestone M1 and part
    of M2 were built before those answers; Section 22.0 records that order'.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '5122'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: ad9a7b187acf64bd0d98efa873c080a8fe568f06d3ec0a18759234355416752c
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '5179'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: c40c6166e7b9872645203926db129285e2ceaa84ccbeb53baed040832c0d69aa
- id: A-33
  kind: structure
  statement: Section 26.12.4 lists under 'Unresolved' the CI executor, approval channel, authorised identities,
    host and managed controls (Q-01, Q-03, Q-04, Q-05 and the executor's interface), Q-07 and Q-08, and
    names publication of a changing verdict (S-28).
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '5721'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 0b51bfc35a5ff149874392b9a6de7edc70e741929c7caf0c7fefd940a9a9e4d4
- id: A-34
  kind: structure
  statement: The header Status row reads 'Proposal v0.5 — approved by the person on 2026-10-25, in conversation',
    says the approval state of v0.4 is not recorded in the repository (as-is.md U-1) and the person did
    not state it, says the person wrote 'I approve all' to a list that included approval of this version
    as the basis (Q-08), the recorded defaults D-49 to D-52 and the answer to Q-07, says 'That is a statement
    in conversation, not a merged pull request, so no gate has evidence of it', says it does not re-base
    the plans that cite v0.4, and says no part of this version has been independently reviewed.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '5'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 00fb4e5c23bd0f48549cd4ed1327755a48be4ee07df55a6869e1b6a54c7c6b73
- id: A-35
  kind: structure
  statement: Section 0.3 says of v0.4 'This revision was awaiting human approval; the repository holds
    no record that v0.4 was approved (Q-08), and Section 0.6 supersedes this status'.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '130'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: b201aaa314ed6c7692cf8adc62eb554f1d9dd1791c493ac626f4443570729a8c
- id: A-36
  kind: structure
  statement: Section 26.12.3 says eight review rounds are recorded across Sections 26.4 to 26.11 and 'v0.5
    has none', produced by one author with read-only research aids, and Section 26.12.4 says none of the
    v0.5 design is built, executed or independently reviewed.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '5699'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 9d061a214746974b9d742cd0065fac3bae708dd5b66fc580d4047865bfa6bbbe
- id: A-37
  kind: structure
  statement: Section 22.0 says the repository holds an implementation 'planned and approved separately'
    (docs/design/orqlet-implementation/ and docs/design/orqlet-m2-workflow/) that built M1 and two slices
    of M2 before the M0 spikes ran and before Q-01, Q-03, Q-04 and Q-05 were answered, verified only by
    the repository's own tests (1,504 passed and 1 skipped on Python 3.12 to 3.15 on macOS), with 'no
    client was opened, there is no commit, no remote and no CI run', and with ci check, the hooks, the
    edit guard, the host evidence and the MCP generators not built.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '4480'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 3cf80ef14babbd47c7ea60425ec63c8b277504092b4c30034fb63b6b63ba626d
- id: A-38
  kind: structure
  statement: Section 22.0 is headed 'facts from the repository, 2026-10-22' and Section 23 lists the commands
    implemented at v0.5 as init, upgrade, rollback, sync, doctor, explain, release, standards for, validate,
    gate status, knowledge impact and review prepare, plus profile answer|approve and evidence cite|hash.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '4544'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 5abc4af8793438b281392956f220a88ed8402bdb10a7c80647c8c9b3102af6f3
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '4478'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 81c4d72733192600793d9c1530c224010653d888beb5e8024b28e1f05682ee8d
- id: A-39
  kind: structure
  statement: Requirement R-05 is 'Appropriate for a small team; no distributed platform for local helper
    needs' ([DC] 2026-10-20), and Section 2.2 is titled 'Fit for a 10–15 developer team' with a row '~10–15
    developers, modest shared knowledge'.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '5063'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 8c6e70a6ba65dbdd5af35ac087c01a2788ca82317673276fa628f969ba99e25f
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 448-452
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: fcb700196c3010eb949925732c5e79016cf9748f4a91a72ffe5765a0618c4f48
- id: A-40
  kind: structure
  statement: Section 2.2 is titled 'Fit for a 10–15 developer team' and its first row is '~10–15 developers,
    modest shared knowledge' with 'Standards and knowledge travel through Git and pull-request review'.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 448-452
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: fcb700196c3010eb949925732c5e79016cf9748f4a91a72ffe5765a0618c4f48
- id: A-41
  kind: flow
  statement: 'Staleness events reported by gate status, doctor and CI are: a newer version of the approved
    artifact reached the baseline; an applicable rule changed; a profile change marked as affecting; a
    base-revision change that overlaps the scope or a declared surface; an exception expiring; an answered
    question that supersedes an earlier answer; a workflow_version below the floor in an artifact header;
    and a review, test or knowledge-impact record whose input binding no longer matches.'
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: '3082'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 622fe73e91b8a83efbfd9893e010e862ae28c2a46f25ee9a8631385c0257b604
- id: A-42
  kind: flow
  statement: Table 2 of Section 17.7 makes any byte edit of an approved design or plan invalid and in
    need of a new approval pull request, makes changed requirements or a higher change class invalidate
    design and plan approval, makes a file operation outside the plan need a plan amendment, makes a knowledge
    file outside the plan need a knowledge-path amendment before it is written, makes a new or changed
    MUST rule need an impact review approved by the code owners, and makes a relaxed or removed rule,
    a change in the base revision that touches nothing in scope, and edits inside planned files need no
    approval.
  evidence:
  - path: docs/design/orqlet-architecture-proposal.md
    lines: 3067-3078
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 4de05d09ba184b295e51c6a7f937ff1e9bbb99fc2c82d3ee580621a44dddcdcf
- id: A-43
  kind: operation
  statement: GET /repos/tmishari/orqlet returned 200 with a private repository, default branch main, merge
    commits, squash merges and rebase merges all allowed, auto-merge off, delete-branch-on-merge off,
    and the calling account holding admin, maintain, push, triage and pull.
  evidence:
  - path: docs/design/open-items/evidence/github-state.yaml
    lines: 4-19
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 8c4558dfebc22982743b91c9111b27f15f24d57773a42cfd3619300be2238744
- id: A-44
  kind: operation
  statement: GET branches/main returned protected false, protection_enabled false and head_sha 2c4308ecdbed19b360fe0aee22cf7ca69a15a9be.
  evidence:
  - path: docs/design/open-items/evidence/github-state.yaml
    lines: 20-25
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: a93e0736e497879551d6eb8cff89a743bf2532c07d06bd1b4d97c37558b4b495
- id: A-45
  kind: operation
  statement: GET branches/main/protection and GET rulesets each returned HTTP 403 with the message 'Upgrade
    to GitHub Pro or make this repository public to enable this feature.'
  evidence:
  - path: docs/design/open-items/evidence/github-state.yaml
    lines: 26-31
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 6054f8cb82802866f133ddb9eef3a7c4b1d87b4d3e486e949c489e19e8d1a1c6
- id: A-46
  kind: operation
  statement: GET pulls?state=all&per_page=100 returned HTTP 200 with pull_requests_found 0.
  evidence:
  - path: docs/design/open-items/evidence/github-state.yaml
    lines: 35-37
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 4de72e35cab3d309adc0c765c4e1aae430b155e783257a7b301b25eae2cd68d7
- id: A-47
  kind: operation
  statement: 'GET collaborators returned a count of 1: login tmishari with role admin.'
  evidence:
  - path: docs/design/open-items/evidence/github-state.yaml
    lines: 38-42
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: ae46a3714ef0da0ca86a86a0be0bdf26dfde9524f8478fed6211f790eaa9ee5c
- id: A-48
  kind: operation
  statement: 'GET actions/runs lists two runs of the workflow ci, both event push on branch main: head
    2c4308ecdbed conclusion failure and head e8ef7a8832e9 conclusion cancelled.'
  evidence:
  - path: docs/design/open-items/evidence/github-state.yaml
    lines: 43-48
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: d5a67d3d1a322f710c7a8e0c7dad20b3ad130675abc4c3c8c35fb4f80f8ccf54
- id: A-49
  kind: operation
  statement: 'The capture lists as not read: whether the account is on a free or paid plan, organisation-level
    settings, required reviewers and CODEOWNERS enforcement.'
  evidence:
  - path: docs/design/open-items/evidence/github-state.yaml
    lines: 49-51
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: b574bf65038a4bf135816bce3187bba383dfbf475f7f10065be408ae4822856a
- id: A-50
  kind: operation
  statement: 'The log of main lists 22 commits (lines 5-26), all with the author name Timur Misharin,
    and no commit subject names a pull request; the only commit with two parents is e8ef7a8832e9 ''Merge
    harness2-rebuild: the rebuilt history of harness2-fit''.'
  evidence:
  - path: docs/design/open-items/evidence/git-history.txt
    lines: 5-26
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 503b25cb98d71e74f6b0b1cff5c46ba6487cebd5adf2d3be4815208873dfb00a
- id: A-51
  kind: structure
  statement: 'The log has two root commits: a18faca4ee53 (2026-10-24T09:06:42+03:00, ''Add front-matter
    checks, plain-safe emitter and workflow 0.3.1 (harness2-fit P-1 to P-6)'') and 2f2356736106 (2026-10-25T10:13:57+02:00,
    ''Baseline: Orqlet before harness2-fit (RECONSTRUCTED, not the original)'').'
  evidence:
  - path: docs/design/open-items/evidence/git-history.txt
    lines: 23-26
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 85b0288f702b3615e4116a83399de29a8448c57299a6d1651a77f59684c088b2
- id: A-52
  kind: structure
  statement: The merge commit e8ef7a8832e9 (2026-10-25T14:28:56+02:00) has first parent 0bfc2faf5f89,
    the tip of the original line (a18faca, 62dd723, 0bfc2fa), and second parent 034007cb6726, the tip
    of the rebuilt line (2f23567 ... 034007c).
  evidence:
  - path: docs/design/open-items/evidence/git-history.txt
    lines: 8-9
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 83941f891e83cdf3501884f38947f53044c891bb6f56d2cfcd9617c89a56b142
- id: A-53
  kind: flow
  statement: 'Three commit subjects record approval by the person: cf6391507b8a ''Record the person''s
    approval of the harness2-fit design set and plan'' (2026-10-25T14:14:24+02:00), 034007cb6726 ''Record
    the person''s acceptance of the rebuilt harness2-fit AS-IS'' (14:15:26) and 2c4308ecdbed ''Fix proposal
    wording from the P-5 reviews and record the approval of v0.5'' (15:03:03).'
  evidence:
  - path: docs/design/open-items/evidence/git-history.txt
    lines: '5'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 0fe176337c8129238e32d861cd6ae030139a672dd13bf6edae137c3acb23a8f5
  - path: docs/design/open-items/evidence/git-history.txt
    lines: 9-10
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 58539e22166242f8b0f091410c68335454679c72c4e8e1f328559dd681cd34ad
- id: A-54
  kind: flow
  statement: In the rebuilt line the commits for harness2-fit P-1 to P-6 are dated 2026-10-25T10:20:51
    to 10:30:26+02:00 and the design set and the plan are dated 10:16:14 and 10:16:31, all before the
    commit recording the approval of the design set and plan (14:14:24).
  evidence:
  - path: docs/design/open-items/evidence/git-history.txt
    lines: 10-21
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 60fb94e1e43cbea09a1983e7af1f26c92e5f8a8d5fc9227e83a9e74974f92d22
- id: A-55
  kind: flow
  statement: In the original line the commit for harness2-fit P-1 to P-6 is dated 2026-10-24T09:06:42+03:00
    and the commit adding the harness2-fit AS-IS, design, plan and reviews and applying the 0.3.1 versions
    proposal is dated 2026-10-24T09:23:54+03:00, one day before the approval date 2026-10-25 that the
    artifacts record.
  evidence:
  - path: docs/design/open-items/evidence/git-history.txt
    lines: 24-26
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 6b0e8241d3f77515b80688406066bd9851555cd892e8020433a9570e2c89e213
- id: A-56
  kind: operation
  statement: ci.yml triggers on push with branches [main] and on pull_request with no branch filter.
  evidence:
  - path: .github/workflows/ci.yml
    lines: 3-6
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: bfa611c996966af9dd6af40c231156f7f6af00d3b2e5b77144bbfdc1ccf528b7
- id: A-57
  kind: operation
  statement: 'ci.yml defines five jobs: lint (ruff check, ruff format --check), types (mypy), architecture
    (lint-imports, export_schemas --check, build_manifest --check), tests (pytest) and build (two wheel
    builds with equal SHA-256).'
  evidence:
  - path: .github/workflows/ci.yml
    lines: 17-107
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 7ebc3f340aa0b30896abed7fa493e654ec1fab09b19aeb62e587e59bed23df4c
- id: A-58
  kind: operation
  statement: No job in ci.yml runs an orqlet command or reads a pull request, review, approval, code owner
    or gate status; the file contains none of the strings 'orqlet', 'approv', 'review' or 'gate'.
  evidence:
  - path: .github/workflows/ci.yml
    lines: 1-107
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 58eb8448a25fdf2ee85e8ae0aed70dd8035623386cdb161c415e8e811786e1e6
- id: A-59
  kind: dependency
  statement: ci.yml pins UV_VERSION to 0.7.19, actions/checkout to commit 3d3c42e5aac5ba805825da76410c181273ba90b1
    (comment v7.0.1) and astral-sh/setup-uv to commit 1c37ad07a6a961277cf70c0d37d6f313000f5884 (comment
    v10.3.0), with persist-credentials false and enable-cache false.
  evidence:
  - path: .github/workflows/ci.yml
    lines: 14-29
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: fd9dda7e12a500b7bd815228bfa169d2f2cba1f0c26588d8cde2fbf93fffe2d6
- id: A-60
  kind: structure
  statement: The .github folder holds two files, workflows/ci.yml and pull_request_template.md, and a
    search of the whole repository found no file named CODEOWNERS, while Orqlet looks for one at .github/CODEOWNERS,
    CODEOWNERS and docs/CODEOWNERS.
  evidence:
  - path: src/orqlet/application/usecases/render_all.py
    lines: '324'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 226e87c547428c73b0e5f94dcd9ac22be31e9b57c3023461dcde7ffe9a09c67d
- id: A-61
  kind: structure
  statement: The pull request template is a managed block of workflow 0.3.1 whose fields 'Design pull
    request:', 'Plan pull request:', 'Review record:', 'Test record:' and 'Required checks:' are empty
    and whose text says a ticked box is not evidence because the checks read the committed records.
  evidence:
  - path: .github/pull_request_template.md
    lines: 1-23
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 9b40c4dab32fa3d40d6b15621885df0ec2f4dc1173d0d9389af9158630e7b8e9
- id: A-62
  kind: structure
  statement: 'versions.yaml has policy_role enforcement-baseline, cli pinned and accepted 0.1.0 with nothing
    denied, workflow version 0.3.1 with digest 5d6807e85ea2... and floor 0.3.1, controls_level_min 3,
    and change_control with the single key lowering_pin_or_floor_requires_approvals: 2.'
  evidence:
  - path: .orqlet/versions.yaml
    lines: 1-14
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 3d94a46d7b629bf39eeb3a7e8226087ddee53c540397d8a627c183b2f98dfb28
- id: A-63
  kind: structure
  statement: versions.yaml holds no key for reviewers, merge strategy, code owners, branch protection
    or approvals for raising a pin or floor.
  evidence:
  - path: .orqlet/versions.yaml
    lines: 1-14
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 3d94a46d7b629bf39eeb3a7e8226087ddee53c540397d8a627c183b2f98dfb28
- id: A-64
  kind: structure
  statement: The project profile has profile.version 1 and status draft, and no field for code owners,
    branch protection or an approving person.
  evidence:
  - path: .orqlet/project-profile.yaml
    lines: 11-12
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 6ae7ee9b1c7947972ea69833a4d0e5a6f82dd1125f322f7ccd1a9eb181cbe335
- id: A-65
  kind: structure
  statement: In the profile, pull_requests.template targets .github/pull_request_template.md with status
    team-template-unknown, reviewers is unknown and merge_strategy is unknown.
  evidence:
  - path: .orqlet/project-profile.yaml
    lines: 45-51
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 47a8c845e881a7dd939e5b28166e3b7b7f0dc67515edeb493329ed2235fdc12e
- id: A-66
  kind: structure
  statement: role-bindings.yaml binds the roles architecture-reviewer and security-reviewer to the generated
    agents orqlet-arch-reviewer and orqlet-security-reviewer for claude-code, codex and cursor with independence_capability
    I1, and holds no human reviewer or code owner.
  evidence:
  - path: .orqlet/role-bindings.yaml
    lines: 1-27
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 6f8356c02488c77e5db488921a457ea147d78af81ab181772d20e14aec5ce8b6
- id: A-67
  kind: structure
  statement: docs/design/orqlet-implementation/design.md records the architecture document v0.4 with SHA-256
    d9d5e675…b324d4 as its input, plan.md names the architecture document (v0.4, section 22 for M1) in
    its Basis and calls itself 'the approved Phase 3 text', and docs/design/orqlet-m2-workflow/plan.md
    says it is based on the design 'you approved as written' and the architecture document v0.4 sections
    it cites.
  evidence:
  - path: docs/design/orqlet-implementation/design.md
    lines: '7'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 429995439e0d1e814f94632234c4f18df968e27609841890c40d16975f9fd12d
  - path: docs/design/orqlet-implementation/plan.md
    lines: 3-9
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 49243c55e18a3da1fb6981e411d226e9b2946d20215f32da7a8abea719c429c9
  - path: docs/design/orqlet-m2-workflow/plan.md
    lines: '3'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 24a0abbb6ea73987f5f2ed4a317b92a8e6bf575a545e07b19039b80b3b87f3b5
- id: A-68
  kind: structure
  statement: 'docs/design/orqlet-implementation/plan.md states ''Status: executed. The plan below is the
    approved Phase 3 text'' and cites the architecture document as v0.4 in its inputs.'
  evidence:
  - path: docs/design/orqlet-implementation/plan.md
    lines: 3-9
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 49243c55e18a3da1fb6981e411d226e9b2946d20215f32da7a8abea719c429c9
- id: A-69
  kind: structure
  statement: docs/design/orqlet-m2-workflow/plan.md says it is based on the design approved as written
    and on 'the architecture document v0.4 sections it cites'.
  evidence:
  - path: docs/design/orqlet-m2-workflow/plan.md
    lines: '3'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 24a0abbb6ea73987f5f2ed4a317b92a8e6bf575a545e07b19039b80b3b87f3b5
- id: A-70
  kind: structure
  statement: 'docs/design/orqlet-implementation/as-is.md fact A-04 records the architecture document as
    v0.4 ''awaiting human approval'' and unknown U-1 reads ''The design''s approval status: v0.4 is not
    approved'', material, affecting ''Whether the Phase 2 design approval can be taken from it''.'
  evidence:
  - path: docs/design/orqlet-implementation/as-is.md
    lines: '20'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 5d0c40fc622c48e770e4d7bfb6930c8f039eee866716df28ec195d0274274c62
  - path: docs/design/orqlet-implementation/as-is.md
    lines: '85'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: cad2afd904a169e9ec75d928f23281ede5ed34dab1535a429290f5029aeb4fb8
- id: A-71
  kind: structure
  statement: 'docs/design/orqlet-implementation/as-is.md unknown U-1 reads ''The design''s approval status:
    v0.4 is not approved'' (material: Yes) and fact A-25 records Q-01, Q-03, Q-04, Q-05 and Q-06 as open
    in the design.'
  evidence:
  - path: docs/design/orqlet-implementation/as-is.md
    lines: 79-85
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 964d67d1380276ef7645195c08e28f03b654006a5707ef438ddf9dea55a710ee
- id: A-72
  kind: structure
  statement: design.md has no artifact header; its Phase row says 'Nothing in this folder is approved,
    and no code may be written from it until it is', its Inputs row cites the architecture architecture
    document v0.4 with SHA-256 d9d5e675…b324d4, and its Status row says 'Decisions D-1 to D-8 of section
    11 approved as recommended (2026-10-21)'.
  evidence:
  - path: docs/design/orqlet-implementation/design.md
    lines: 6-10
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 0cfe70ae80e5335caf97ebd623bb32f5e90f2775f46ced6faa2505ccd3f3190f
- id: A-73
  kind: flow
  statement: design.md section 11 is titled 'Decisions that need your approval' and lists D-1 to D-8 with
    a recommendation each; D-5 and D-8 are external writes (a published check, a Git repository and GitHub
    remote) that need the person's approval or action, and the person's words of approval are not quoted.
  evidence:
  - path: docs/design/orqlet-implementation/design.md
    lines: 333-344
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 941552151be2517325cfc61b6b1c254b4b96087060675a1058c35d1b882fd710
- id: A-74
  kind: structure
  statement: Each of adr-001 to adr-005 has the status line 'proposed (needs approval with `design.md`)'
    (adr-002 adds 'decision D-2'), and none records an approver, a date or a pull request.
  evidence:
  - path: docs/design/orqlet-implementation/adr-002-deterministic-data-and-hashing.md
    lines: '3'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 8d5b1b2fdcf1aa326cad69daf9879c1887bc0baa8e5bd6cd4116eea411afb6d8
  - path: docs/design/orqlet-implementation/adr-001-package-layout-and-layering.md
    lines: '3'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: a79f0833472b2c97cc9611ad93df69c8d6adb2873747ef8c23a6f44c88396aa8
  - path: docs/design/orqlet-implementation/adr-003-hardened-git-and-process-access.md
    lines: '3'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: a79f0833472b2c97cc9611ad93df69c8d6adb2873747ef8c23a6f44c88396aa8
  - path: docs/design/orqlet-implementation/adr-004-journalled-apply.md
    lines: '3'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: a79f0833472b2c97cc9611ad93df69c8d6adb2873747ef8c23a6f44c88396aa8
  - path: docs/design/orqlet-implementation/adr-005-deterministic-renderers-and-golden-tests.md
    lines: '3'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: a79f0833472b2c97cc9611ad93df69c8d6adb2873747ef8c23a6f44c88396aa8
- id: A-75
  kind: operation
  statement: plan.md's execution record says CI has not run because there is no remote 'as you decided
    in P-1', and that no commit was made, no remote was created and everything is untracked.
  evidence:
  - path: docs/design/orqlet-implementation/plan.md
    lines: 137-148
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: cc8dd3c5abcfae667fd199a9067c26dc5420cd895d515519586435a65258fdf7
- id: A-76
  kind: structure
  statement: plan.md, as-is.md and the ADRs of orqlet-implementation record no pull request number, merge
    commit or protected-baseline evidence.
  evidence:
  - path: docs/design/orqlet-implementation/plan.md
    lines: 1-232
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: ebddff4920234fdf941eb891a7b293787b7aabb6a42dacc987d94d713ac8b981
- id: A-77
  kind: flow
  statement: design.md says 'Approved by the user on 2026-10-22' (Phase) and 'Approved as written, decisions
    D-M2-1 to D-M2-6 as recommended (2026-10-22)' (Status), without the person's wording and without a
    pull request.
  evidence:
  - path: docs/design/orqlet-m2-workflow/design.md
    lines: 6-9
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: e19dc376c3fbde4a55125ff13a1737c95d3bd74dbcaf152f72d814c96f4fabdb
- id: A-78
  kind: operation
  statement: plan.md's execution record says CI has not run and there is no commit and no remote, that
    gate status and every revision-bound check cannot bind anything on Orqlet's own repository, that approval,
    published check results and reviewer identity are host evidence (S11) reported NOT_RUN, and that the
    D-M2-1 check was not made.
  evidence:
  - path: docs/design/orqlet-m2-workflow/plan.md
    lines: 169-174
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: a88e786608c40098cf0954be7ddc35e3085b925f61e6b5e384ccdafcbd2087c8
- id: A-79
  kind: dependency
  statement: plan.md cites proposal sections 6.14.1 (staleness table) and 17.13.3, and the orqlet-implementation
    documents cite §6.14 and §6.14.1 (adr-002 line 7), §14.9 and §14.9.2 (adr-005 line 16, design.md line
    153) and §17.13 (design.md line 141), sections that proposal line 74 lists as revised or rewritten
    by v0.5.
  evidence:
  - path: docs/design/orqlet-m2-workflow/plan.md
    lines: '96'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 8fe03f987486c53d4669ce79ebf99b8084d8e71398d9fd12d3525ff25f93e5bd
  - path: docs/design/orqlet-m2-workflow/plan.md
    lines: '109'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: b759c0c079dd00d95b5698e34d4e30832352eba6098fadc5e3a30f8d08b4cd19
- id: A-80
  kind: structure
  statement: as-is.md has an artifact header with status approved, workflow_version 0.3.0, protected_set_digest
    49ef4cd53bcb..., bound base_revision 2f235673610617120ffc0fc46824d7d7b56c6b87 (the reconstructed baseline)
    and a scope that lists docs/design/orqlet-architecture-proposal.md and .orqlet/versions.yaml.
  evidence:
  - path: docs/design/harness2-fit/as-is.md
    lines: 1-16
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: a7c2534e1ee1afdde30b5b4c01803e9b95848b642a1b203386e09fd7f7b01351
- id: A-81
  kind: flow
  statement: as-is.md's Status row says 'Accepted by you on 2026-10-23 (A-5b) in its table form' and that
    the front-matter form 'was accepted by you on 2026-10-25, in conversation', and A-5b records the acceptance
    'in the conversation on 2026-10-23'.
  evidence:
  - path: docs/design/harness2-fit/as-is.md
    lines: '164'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 74790da67afe63ab687d15ba80d5263aeaf7893e8937b3e406ea00da80a44751
  - path: docs/design/harness2-fit/as-is.md
    lines: '252'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: a41493d59d6e5576d9863b6cca7dbe244b1b9f8d63b66b82d3c39f156242c67d
- id: A-82
  kind: structure
  statement: design/manifest.yaml has header status approved, workflow_version 0.3.1, protected_set_digest
    be7723282aec..., base_revision a1bad7a644584ef9940ec433a2151d971a1b4e97 (the commit that holds the
    AS-IS), an as_is_ref with a SHA-256, and change class D2; its scope lists docs/design/orqlet-architecture-proposal.md
    and .orqlet/versions.yaml.
  evidence:
  - path: docs/design/harness2-fit/design/manifest.yaml
    lines: 1-14
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: ee09499bab89e9e39caa56031a6d290e21fcedc24e45d33b12f475a9fa4cb4a7
  - path: docs/design/harness2-fit/design/manifest.yaml
    lines: '28'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 43844b25ef553c6023e2c267364e9a0c5bbeab7f7b78aa6746a32aec0e9775b6
  - path: docs/design/harness2-fit/design/manifest.yaml
    lines: '38'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 2f27ab7caea857673a9a523be9d09db751fde795683e94754ad58c9a036baa8c
- id: A-83
  kind: flow
  statement: manifest.yaml self_check records that on 2026-10-25 the person wrote 'I approve all' about
    the non-blocking review findings, the refresh of the bound workflow values and the architecture document
    v0.5 approval, that workflow_version and protected_set_digest in the header were refreshed to the
    upgraded repository at commit e8ef7a8832e9 (workflow 0.3.1), and that base_revision still names the
    AS-IS commit so a gate run still reports it stale.
  evidence:
  - path: docs/design/harness2-fit/design/manifest.yaml
    lines: '160'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 715fe64cd6fcbb2c8203069715395cf908996892aa01c73f1bbaafdd102c1877
- id: A-84
  kind: structure
  statement: plan.yaml has header status approved, workflow_version 0.3.1, protected_set_digest be7723282aec...,
    bound base_revision 06209cdb13410548a825a6a731a2270ec7fe030f (the commit that holds the design), and
    a design_ref to manifest.yaml with a SHA-256.
  evidence:
  - path: docs/design/harness2-fit/plan.yaml
    lines: 1-14
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 011800df1c858c473f27c6267af99ef65ab728e676a798c94e152043fbee8127
- id: A-85
  kind: flow
  statement: plan.yaml self_check records, with result pass, 'the person confirmed in this session that
    the design pull request merged elsewhere; this repository has no commit or remote to show it'.
  evidence:
  - path: docs/design/harness2-fit/plan.yaml
    lines: '226'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 70fcbb511f7633f0604cebcdcbd26758b276a9d2d6b5bee3106dab4303b3c959
- id: A-86
  kind: flow
  statement: plan.yaml self_check records, with result pass, the person's words 'I approve all designs
    and plans' in conversation on 2026-10-25, 'recorded at their instruction; this is not a merge on the
    protected baseline, so a gate run still has no approval evidence', and the later 'I approve all' to
    the refresh of the bound values at base commit e8ef7a8832e9 with the statement that a gate run still
    reports base_revision stale.
  evidence:
  - path: docs/design/harness2-fit/plan.yaml
    lines: 231-232
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: f1d9ecab8cbecb72e6194148b06057ade746e79d83548462fda311adf4c0d373
- id: A-87
  kind: flow
  statement: plan.yaml P-6 acceptance criteria say orqlet gate status reports this task's own artifacts
    as stale (ORQ-W390) and that the .orqlet/versions.yaml proposal is applied or declined by the person,
    who is shown any finding about it.
  evidence:
  - path: docs/design/harness2-fit/plan.yaml
    lines: 203-208
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 06ff63ac8eebe71fe9937f228a4153ab24a6b5e7003d7824863a917857e9bc90
  - path: docs/design/harness2-fit/plan.yaml
    lines: '168'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: fa498dd364f2fd61beae08b2d24ec27dfd70948f8ac88ab7abcb99af761e44b2
- id: A-88
  kind: structure
  statement: Each of ADR-001 to ADR-005 under design/ has the status line 'accepted by the person on 2026-10-25,
    in conversation. No pull request was merged.'; ADR-001 decision 2 and ADR-002 decision 3 add that
    they were amended after the reviews and the person approved the amendment.
  evidence:
  - path: docs/design/harness2-fit/design/adr-002-packet-member-assertion.md
    lines: '3'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 59da754980cdc9515ce912f9ea398602d45f7a3547c3562c0d9c16e6d3fa99cd
  - path: docs/design/harness2-fit/design/adr-001-client-visible-front-matter.md
    lines: '3'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: f6027dba47227cd3a45412bfbebedb921cf1df2dd90f1df439b006ca5b1b9b64
  - path: docs/design/harness2-fit/design/adr-003-no-review-skill-change.md
    lines: '3'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 3be1d2b293d9e92252774ba7bdeb6bb59a55c32efff75eab76f44359498ff8e8
  - path: docs/design/harness2-fit/design/adr-004-evaluation-harness-shape.md
    lines: '3'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 3be1d2b293d9e92252774ba7bdeb6bb59a55c32efff75eab76f44359498ff8e8
  - path: docs/design/harness2-fit/design/adr-005-no-dependency-on-harness2.md
    lines: '3'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 3be1d2b293d9e92252774ba7bdeb6bb59a55c32efff75eab76f44359498ff8e8
- id: A-89
  kind: dependency
  statement: ADR-002 (line 3), plan.yaml AC-4 (line 159), sequence.md (line 39), component.md (lines 16
    and 40), container.md (line 35) and considerations.md (line 13) refer to the v0.5 packet plan as the
    place where the packet code lands; no file under docs/design is named for it.
  evidence:
  - path: docs/design/harness2-fit/design/adr-002-packet-member-assertion.md
    lines: '3'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 59da754980cdc9515ce912f9ea398602d45f7a3547c3562c0d9c16e6d3fa99cd
  - path: docs/design/harness2-fit/plan.yaml
    lines: '159'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: dc6c9095d236b879ed9a35ca28fa7e7c98c88acc1b1e52e0f49319c17e51b561
  - path: docs/design/harness2-fit/design/sequence.md
    lines: '39'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 425892f32085f9169d345e4fd14e5c92889a504adf7b76851c540fcd3ac7bf74
  - path: docs/design/harness2-fit/design/component.md
    lines: '16'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: e97c66456b2fb9b880f39126a69ec0dd159c9f547baff7441dd59186adf0db6e
  - path: docs/design/harness2-fit/design/component.md
    lines: '40'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 8c5e92c142c8caf9d9b324a69a54a7e667d29b34a3091f8e97cc0231a5631401
  - path: docs/design/harness2-fit/design/container.md
    lines: '35'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 271f3b6166c4d43ad6a95b4916350b6155fbe74c965c4cfaf9a5b9425623b3b4
  - path: docs/design/harness2-fit/design/considerations.md
    lines: '13'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 0b1a35941b749cb9ada7541283b40d794428d24138054dd40c7fd4222e7608a6
- id: A-90
  kind: flow
  statement: considerations.md says that after orqlet upgrade approved artifacts written against the old
    digest are reported stale, that a search of src found no refresh or re-bind step, and that the plan
    must state how a person refreshes a stale artifact; its rollback note says approvals refer to files
    in Git but their headers' bound values go stale after an upgrade.
  evidence:
  - path: docs/design/harness2-fit/design/considerations.md
    lines: 19-20
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 78bf4ea14fda487924dcbe8cda52d9ae0cce9a1d592bbf60837e5fd2d4067172
  - path: docs/design/harness2-fit/design/considerations.md
    lines: '28'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: f93fbc4cfa0dab74305308722611c83302563f1cffae7466e92bbf00991be3c4
- id: A-91
  kind: structure
  statement: The CLI registers the groups and commands init, upgrade, rollback, sync, doctor, explain,
    release, profile, standards, validate, gate, evidence, knowledge and review; no `approve`, `ci`, `hook`
    or guard command or group is registered.
  evidence:
  - path: src/orqlet/interface/cli/app.py
    lines: 34-47
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 822b147c030944d99e6f7c6059f01a5830430dfc601693cecc3875c0e76ae131
- id: A-92
  kind: flow
  statement: gate status reads .orqlet/generated.lock.yaml, .orqlet/standards.lock.yaml (as a contract
    and as raw bytes), .orqlet/project-profile.yaml and .orqlet/workflow.lock through read_file and load_contract,
    plus vcs.head_commit(); a missing file is ORQ-E390 and an unreadable one is ORQ-E391.
  evidence:
  - path: src/orqlet/application/usecases/gate_status.py
    lines: 80-93
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 9d2392cd716a86172c78430ca97f313bb86a04c24e6394f24683b608e3d13024
  - path: src/orqlet/application/usecases/gate_status.py
    lines: 126-142
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 0a0644d788df5573aad244dd3ff9feec7ded842eaf9b2ed53089ea755e708168
- id: A-93
  kind: flow
  statement: protected_set_digest is the digest of the sorted [path, rendered_sha256] pairs of every manifest
    entry whose file_class is FileClass.PROTECTED and whose rendered_sha256 is not None; here 'protected'
    means Orqlet-owned protected files, not a protected branch.
  evidence:
  - path: src/orqlet/application/usecases/gate_status.py
    lines: 70-77
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 02c727f331b6b5599015b32067b509ec3a82bc6986cbe4ce5a0b176b5b9b703a
- id: A-94
  kind: flow
  statement: With a task, gate_status always ends by adding info ORQ-I393 ('approval of the design and
    of the plan is evidence on the protected baseline; an offline run has none, so it is not checked')
    and skip('approval needs host evidence, which an offline run does not have'), so a PASS verdict is
    not reachable with a task.
  evidence:
  - path: src/orqlet/application/usecases/gate_status.py
    lines: 113-123
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: c15a3947e284e3fd1f180ae440b8acf60e2abf83bcd5e77305afb7b081851eed
- id: A-95
  kind: flow
  statement: '_stale_components compares the artifact header''s workflow_version, protected_set_digest,
    bound.standards_lock_hash, bound.applicable_rules_hash and bound.profile_version with the current
    values; _assess adds ORQ-W390 (''<name> is stale: ...'') as a warning and a skip when any differ.'
  evidence:
  - path: src/orqlet/application/usecases/gate_status.py
    lines: 169-201
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: eda86bb2344a76e2c3f6e62ed2f8a17925f3303d14e75bfc881128435a5a7519
- id: A-96
  kind: flow
  statement: '_base_moved applies when header.bound.base_revision differs from HEAD: it asks changed_in_scope
    whether a file in the artifact''s scope differs between the two revisions (scope is scope.paths for
    as-is and design, and the file_operations paths for a plan); a change makes ''base_revision'' stale,
    no change gives info ORQ-I392, and an unknown revision gives a skip.'
  evidence:
  - path: src/orqlet/application/usecases/gate_status.py
    lines: 188-229
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: bd3ec8105ec13d97f9367de51768edf0b9c5a76b16c54b05eaf8a4c213897527
- id: A-97
  kind: operation
  statement: output_of puts data.verdict first, then the result data, and exits 0 only for PASS; FAIL
    and NOT_RUN both exit with ExitCode.CHECK_FAILED, whose value is 5.
  evidence:
  - path: src/orqlet/interface/cli/commands/validate.py
    lines: 37-46
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 9d61d95633dd5d6239fbbba3aaea56b656f0124e0b850dfe3de6c7f98fc9c9cc
- id: A-98
  kind: structure
  statement: The committed JSON schema lists the header status enum draft, approved, superseded and requires
    `status`.
  evidence:
  - path: src/orqlet/workflow/schemas/orqlet.artifact-header.v1.json
    lines: 121-128
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 53a8b6437d188299f0733782139cdf79abf435e3087c9d2ceea97309c23a02b1
  - path: src/orqlet/workflow/schemas/orqlet.artifact-header.v1.json
    lines: 141-149
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 672efa98cec71b0d4faeb7a0dfbaa21b07d5a39c18969cdaffe599559543b3a2
- id: A-99
  kind: flow
  statement: 'A search of src/orqlet at the base revision finds no line that reads `header.status`: the
    validators read `header.task` and `header.bound.base_revision`, gate status reads the bound values,
    and `status` (draft, approved or superseded) is checked for shape when read_artifact loads the contract
    and is otherwise unused.'
  evidence:
  - path: src/orqlet/application/usecases/validation.py
    lines: 147-153
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: fe47f8acc9b13109cd23ca85bd18287b66394419d7d7a2df70dbc48dccd03819
  - path: src/orqlet/application/contracts/artifact_header.py
    lines: 1-6
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 92b2809945755425c7834bbbbf7ea27ac9cf9161853f00e4f9cb9db4513a085a
- id: A-100
  kind: structure
  statement: 'IMPLEMENTED_COMMANDS lists 22 commands: init, upgrade, rollback, sync, doctor, explain,
    release, profile answer, profile approve, standards for, validate as-is, validate design, validate
    plan, validate ledger, gate status, evidence cite, evidence hash, knowledge impact, review prepare,
    validate review, validate test, validate knowledge.'
  evidence:
  - path: src/orqlet/application/usecases/capabilities.py
    lines: 14-38
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 378adaeeb2c106a28e1ed9c2c478272c4aa1dfc134470ebe4a87452b576a8f0f
- id: A-101
  kind: structure
  statement: PLANNED_COMMANDS is an empty frozenset with the comment 'Nothing is planned at the moment';
    the module has no list of commands that are documented elsewhere but not built.
  evidence:
  - path: src/orqlet/application/usecases/capabilities.py
    lines: 10-12
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 73a67283b56e5aa8c5c14a2ba7bc160a4f75e1d565fa646f4e5e4a408f0edc19
- id: A-102
  kind: structure
  statement: 'doctor (full mode) emits info ORQ-I200: ''Local Git hooks are not part of this release.
    Checks that run in CI are authoritative; none runs locally.'''
  evidence:
  - path: src/orqlet/application/usecases/diagnose.py
    lines: 123-133
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: b9627a875e913d017558b962c2eecae47acf09a693466c7365537c6cc3810f8c
- id: A-103
  kind: interface
  statement: '`orqlet profile approve --reviewer NAME [--yes] [--dry-run]` has a required free-text `reviewer`
    option (''Your name, recorded as the reviewer'') and calls approve_profile.'
  evidence:
  - path: src/orqlet/interface/cli/commands/profile.py
    lines: 55-73
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 98cf0d362a518590bcbdeb87ffda95d2e97b5373e181fcbce8e2e88c043c3f1a
- id: A-104
  kind: flow
  statement: profile answer on an approved profile resets ProfileMeta to status 'draft' with no reviewer
    and emits info ORQ-I070; the version number is copied unchanged.
  evidence:
  - path: src/orqlet/application/usecases/profile_edit.py
    lines: 73-83
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 793c07ce9615ff3ab7d8e079c2f6030303d10d3771274d8237ce952687b44922
  - path: src/orqlet/application/usecases/profile_edit.py
    lines: 122-125
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: a27423b6999510f3d803b131f30069d4a79bbe9e1d6c38be3eaa812560fe4925
- id: A-105
  kind: flow
  statement: 'The only reader of the profile''s `status` outside profile_edit is doctor''s _profile_findings,
    which emits warning ORQ-W180 ''The project profile is a draft: nobody has recorded approving it''
    when status is not ''approved''.'
  evidence:
  - path: src/orqlet/application/usecases/diagnose.py
    lines: 313-322
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 55d73dca3df98870ec6a145bb02d453007c94bdbb1b5d1a915041f6b258aef3b
- id: A-106
  kind: structure
  statement: 'ChangeControl has one field, `lowering_pin_or_floor_requires_approvals: int = 2`, and Versions
    has `change_control: ChangeControl = ChangeControl()`; the module docstring says ''accepted versions,
    read from the baseline''.'
  evidence:
  - path: src/orqlet/application/contracts/versions_file.py
    lines: '1'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: ab3b9d29ec7a1363befb08a2a44136f6c2206e2a879ecf20af4c0ec5622cd369
  - path: src/orqlet/application/contracts/versions_file.py
    lines: 26-35
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: b24fcc42e4d569f3dbb4c4c2b2cebe7381955fec33af35f50ab9f0734d9de059
- id: A-107
  kind: flow
  statement: A search of src/orqlet finds `change_control` and `lowering_pin_or_floor_requires_approvals`
    only in versions_file.py and the committed JSON schema; no use case reads the value, and the strings
    'two approvals' in upgrade.py (lines 204, 213), rollback.py (line 74) and lifecycle.py (line 69) are
    fixed text.
  evidence:
  - path: src/orqlet/application/contracts/versions_file.py
    lines: 26-27
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: f051c9f61e3bdabfc2fa9fe76f7bec15ba44d679ec910b7637ec53352ca4f7f6
  - path: src/orqlet/application/contracts/versions_file.py
    lines: '35'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 9d450b3350040f510223e5c491d9746a7a0782bad1cb0fee6478ad4e915b1ce5
  - path: src/orqlet/application/usecases/upgrade.py
    lines: 204-213
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 92435a8b826a70e329ed231887856caf24adaa6525cd75abf7742ee261c3911b
  - path: src/orqlet/application/usecases/rollback.py
    lines: 72-76
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 3128385a13009624df749d8d2986e3f74cc4e4ab9a9d9f5e5ee430ecbd6d4a78
  - path: src/orqlet/interface/cli/commands/lifecycle.py
    lines: '69'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: c354bda336c8b2e591a49ed8989c32c4d05e73a1f511680a0aa1ddda80d73ac1
- id: A-108
  kind: structure
  statement: src/orqlet contains no code that reads, lists or applies the files under .orqlet/proposals;
    PROPOSALS_DIR is referenced only to compute proposal paths.
  evidence:
  - path: src/orqlet/domain/changeplan.py
    lines: '30'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 05096fe89c7563bd99c6c9326ae59ff4e0dd184005c8f3a1668c90b77c26d76e
  - path: src/orqlet/domain/changeplan.py
    lines: '154'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 59ad85e923af879461b2e23d6023b56f899d0caf82c9a42679b42185db61b796
- id: A-109
  kind: structure
  statement: WorkflowPolicy is referenced only in the contract table; no path constant for a workflow-policy
    file exists, no use case loads or writes it, and the repository's .orqlet folder contains no workflow-policy
    file.
  evidence:
  - path: src/orqlet/application/contracts/__init__.py
    lines: '16'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 24b5d541535794aa65c0ff7bb4fdb26bc2f6695ca87138abc59494615d2ddaf2
  - path: src/orqlet/application/contracts/__init__.py
    lines: '39'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 81f2911f18fa190bc8c0452773414096daf1fb89e19cd065c3c6e471dd1084b5
- id: A-110
  kind: flow
  statement: The only approver identity the code records is the free-text profile reviewer name (ORQ-E163
    checks length and newlines only) with a clock timestamp; it is not compared with any Git identity,
    CODEOWNERS entry or other list.
  evidence:
  - path: src/orqlet/application/usecases/profile_edit.py
    lines: 86-113
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 0fa75f443bcc704b486538adf2ffcfc9be1844d5deb58d8172ee736260d67991
- id: A-111
  kind: structure
  statement: The Vcs port exposes state, head_commit, current_branch, tracked_files, read_committed, has_revision,
    read_at, read_many_at, tree_at, merge_bases, diff_tree, diff_patch, resolve, staged_tree, recent_commits,
    remote_names, has_staged_changes, ignored and init_repository; CommitSummary has commit_id and subject
    only; there is no author, committer, merge or review accessor.
  evidence:
  - path: src/orqlet/application/ports/vcs.py
    lines: 39-143
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 993b0bff2b4a2b3e3beda251f1f703288f92d9c2af4e83b0bb9f8a35c1c04c93
- id: A-112
  kind: flow
  statement: CODEOWNERS is consulted only by codeowners_mentions, which reads .github/CODEOWNERS, CODEOWNERS
    or docs/CODEOWNERS and checks that the prompts folder name occurs in the text; the result drives info
    ORQ-I030; owners are not parsed.
  evidence:
  - path: src/orqlet/application/usecases/render_all.py
    lines: '324'
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: 226e87c547428c73b0e5f94dcd9ac22be31e9b57c3023461dcde7ffe9a09c67d
  - path: src/orqlet/application/usecases/render_all.py
    lines: 366-387
    revision: 87dd1bdf5a66c6d17d6c2d5212c0c1d5bf8088ab
    sha256: d6878d5afda82335ef7f078329b04387d663bd29b68b13f46d06efe8487046b0
unknowns:
- what: Whether 'the v0.5 packet plan' / 'the v0.5 plan' named by harness2-fit ADR-002, plan.yaml, considerations.md
    and the design diagrams exists; no such file is in docs/design.
  material: true
  question_ref: Q-10
  merged_from:
  - open-items-approval-merge-protection/U-13
  id: U-1
- what: 'Whether an installation is meant to hold .orqlet/workflow-policy.yaml: the WorkflowPolicy contract
    and schema exist, but no path constant, writer or reader does, and the repository has no such file.'
  material: true
  question_ref: Q-10
  merged_from:
  - approval-trace/U-3
  id: U-2
- what: 'Who or what enforces change_control.lowering_pin_or_floor_requires_approvals at merge time: no
    code reads the value, the number of approvals in messages is fixed text, and the check that would
    count approvals (`ci check`) does not exist.'
  material: true
  question_ref: Q-10
  merged_from:
  - approval-trace/U-4
  id: U-3
- what: 'What sets header `status` to approved or superseded, and when: no code and no skill text does
    it, and no test exercises those values.'
  material: true
  question_ref: Q-10
  merged_from:
  - approval-trace/U-5
  id: U-4
- what: Whether ProfileMeta.version is meant to change when the profile changes (the bound profile_version
    in artifact headers is compared with it, but no code increments it).
  material: true
  question_ref: Q-10
  merged_from:
  - approval-trace/U-6
  id: U-5
- what: How many approving reviews the design requires for a design or plan pull request; the proposal
    states at least one non-author approving review (item 13), a security owner for D3 (Q-03 recommendation)
    and two approvals only for floor, pin and loosening changes as 'host configuration', and does not
    say which host feature expresses a per-path approval count.
  material: true
  question_ref: Q-5
  merged_from:
  - proposal-approval/U-4
  id: U-6
- what: Whether a one-developer repository can satisfy the rules that require an approving reviewer who
    is not the pull request author and 'approval of the most recent reviewable push by someone other than
    the pusher'; the proposal states a small-team scope (R-05) and a 10 to 15 developer fit and contains
    no statement about a one-developer repository or a single maintainer.
  material: true
  question_ref: Q-5
  merged_from:
  - proposal-approval/U-5
  id: U-7
- what: Whether commit 2c4308e (the commit that recorded the approval of v0.5) or any earlier commit on
    main was reviewed by a second person; the proposal's definition of approval needs an approving review
    by a code owner who is not the author, and the working tree shows no review record for it.
  material: true
  question_ref: Q-5
  merged_from:
  - proposal-approval/U-25
  id: U-8
- what: 'Who counts as an authorised approver and who is a code owner of docs/design/** (Q-03): no answer
    is recorded in any artifact of the area, and no CODEOWNERS file exists.'
  material: true
  question_ref: Q-5
  merged_from:
  - open-items-approval-merge-protection/U-5
  id: U-9
- what: 'Whether a second person with write access exists or can be added: GitHub lists one collaborator
    (tmishari, admin) and organisation-level settings, required reviewers and CODEOWNERS enforcement were
    not requested.'
  material: true
  question_ref: Q-5
  merged_from:
  - open-items-approval-merge-protection/U-6
  id: U-10
- what: The values of project-profile.yaml repository.pull_requests.reviewers and merge_strategy, which
    are unknown, and branch_naming and commit_convention, which are open questions; the profile status
    is draft.
  material: true
  question_ref: Q-5
  merged_from:
  - open-items-approval-merge-protection/U-16
  id: U-11
- what: 'Who counts as ''an authorised person'' for design and plan approval (orqlet-design skill line
    19) and how a person or role is to be identified: no code, contract or file defines it.'
  material: true
  question_ref: Q-5
  merged_from:
  - approval-trace/U-1
  id: U-12
- what: Which GitHub plan (Free, Pro, Team, Enterprise Cloud or Enterprise Server) the repository or organisation
    is on, and which of the controls the design requires (rulesets with an App as expected source, required
    code-owner review, dismiss stale approvals, approval of the most recent reviewable push, strict checks,
    bypass-actor removal, organisation required workflows, merge queue, environment restriction) each
    plan offers; the proposal states no GitHub plan matrix and its Q-01 does not name GitHub plans.
  material: true
  question_ref: Q-6
  merged_from:
  - proposal-approval/U-1
  id: U-13
- what: Whether the repository is public or private and what that changes for the design (the proposal
    says scheduled workflows are disabled after 60 days in a public repository, that fork pull requests
    are NOT_RUN, and that public repositories with fork contributions were not reviewed).
  material: true
  question_ref: Q-6
  merged_from:
  - proposal-approval/U-2
  id: U-14
- what: Whether branch protection or rulesets exist on the remote main and whether CODEOWNERS exists on
    the remote; no CODEOWNERS file was found in the working tree (searched **/CODEOWNERS and .github/**),
    while the proposal's approval definition depends on CODEOWNERS and the proposal says orqlet init proposes
    a CODEOWNERS block. The host's actual state is outside the proposal; docs/design/open-items/evidence/github-state.yaml
    exists and was not read by this area.
  material: true
  question_ref: Q-6
  merged_from:
  - proposal-approval/U-11
  id: U-15
- what: Which GitHub feature expresses 'two approvals for that path' (FM-U02, D-39, Section 20.8 'host
    configuration'), and whether CODEOWNERS teams need an App permission to read organisation members
    ([U] in the proposal).
  material: true
  question_ref: Q-6
  merged_from:
  - proposal-approval/U-16
  id: U-16
- what: 'Whether branch protection or rulesets can be enabled on this repository: the only statement is
    the 403 message about GitHub Pro or a public repository, and the account''s plan was not requested.'
  material: true
  question_ref: Q-6
  merged_from:
  - open-items-approval-merge-protection/U-7
  id: U-17
- what: Answers to Q-01 (code host, CI platform, merge queue in use), Q-03 (where approvals live, who
    is an authorised human, how many approvers), Q-04 (managed settings and plans) and Q-05 (local guard);
    the proposal records all four as open and records no answer.
  material: true
  question_ref: Q-7
  merged_from:
  - proposal-approval/U-3
  id: U-18
- what: Whether a dedicated GitHub App can be created and installed in the organisation; the proposal
    makes it an administrator step and docs/design/orqlet-implementation/as-is.md U-2 lists the question
    as unknown.
  material: true
  question_ref: Q-7
  merged_from:
  - proposal-approval/U-12
  id: U-19
- what: How a changing verdict is published and which of the three publication mechanisms a required check
    honours (spike S-28), whether an App-created check satisfies a ruleset and merge group (S-14), and
    what head_sha a review-triggered workflow_run carries; none was run.
  material: true
  question_ref: Q-7
  merged_from:
  - proposal-approval/U-13
  id: U-20
- what: The CI executor's interface, authentication, data handling, permissions, compatibility and budget;
    the proposal records them as pending and option M-A of the merge queue depends on them.
  material: true
  question_ref: Q-7
  merged_from:
  - proposal-approval/U-14
  id: U-21
- what: What the built gate status reports for approval when online (the proposal says it reads the code
    host) given that the proposal says host evidence is not built and the built use case is offline only;
    and which of the staleness events listed in Section 17.7 are implemented beyond the five header comparisons
    and base-revision movement.
  material: true
  question_ref: Q-7
  merged_from:
  - proposal-approval/U-15
  id: U-22
- what: 'How host evidence (merge on the protected baseline, code-owner approval, merge_evidence) will
    be obtained and represented: no code, port or contract for it exists; only the policy literal ''baseline-with-merge-evidence'',
    the ORQ-I393 text and design documents mention it.'
  material: true
  question_ref: Q-7
  merged_from:
  - approval-trace/U-2
  id: U-23
- what: 'Which checks ORQ-I200 (''Checks that run in CI are authoritative'') refers to: no CI command
    is implemented and this repository''s own CI workflow runs no orqlet command.'
  material: true
  question_ref: Q-7
  merged_from:
  - approval-trace/U-7
  id: U-24
- what: How a gate decision is meant to read design, plan, role-bindings and versions from the protected
    baseline instead of the tree under review; offline all of them are read from the working tree, staged
    tree or a chosen commit.
  material: true
  question_ref: Q-7
  merged_from:
  - approval-trace/U-8
  id: U-25
- what: Whether v0.4 was approved; the proposal says its state is not recorded and the person did not
    state it, while docs/design/orqlet-implementation/as-is.md U-1 says v0.4 is not approved.
  material: true
  question_ref: Q-8
  merged_from:
  - proposal-approval/U-7
  - open-items-approval-merge-protection/U-1
  id: U-26
- what: Whether the plans under docs/design/orqlet-implementation/ and docs/design/orqlet-m2-workflow/
    are re-based on v0.5; the proposal says this is not decided, and both plans cite v0.4.
  material: true
  question_ref: Q-8
  merged_from:
  - proposal-approval/U-8
  - open-items-approval-merge-protection/U-2
  id: U-27
- what: How the approval of the two implementation plans ('planned and approved separately', 'the approved
    Phase 3 text', 'the design you approved as written') was recorded and by what evidence; the proposal
    does not say, and its own W-1 requires an approved design and plan before implementation.
  material: true
  question_ref: Q-8
  merged_from:
  - proposal-approval/U-9
  id: U-28
- what: 'Whether the v0.4 file bytes (SHA-256 d9d5e675…b324d4, 5,960 lines) exist in any commit: the oldest
    commit is dated 2026-10-24, the file at the path is now v0.5 (6,444 lines), and no git or sha256 command
    could be run in this read.'
  material: true
  question_ref: Q-8
  merged_from:
  - open-items-approval-merge-protection/U-3
  id: U-29
- what: Whether each section citation of the v0.4-based documents (for example §6.14.1, §14.9.2, §17.13,
    §17.13.3) still points to the same text in the v0.5 file; no citation was compared, and design.md
    of m2 says line numbers refer to v0.4 although this read found no proposal line number cited in it.
  material: true
  question_ref: Q-8
  merged_from:
  - open-items-approval-merge-protection/U-4
  id: U-30
- what: 'Who approved the orqlet-implementation design decisions D-1 to D-8 and the M1 plan, and in what
    words: only ''approved as recommended (2026-10-21)'' and ''the approved Phase 3 text'' are recorded;
    the AS-IS status still says ''awaiting your acceptance''.'
  material: true
  question_ref: Q-8
  merged_from:
  - open-items-approval-merge-protection/U-11
  id: U-31
- what: 'Who approved M2 Plan A and in what words: the design says ''Approved by the user on 2026-10-22'',
    the plan has no status line and no approval record.'
  material: true
  question_ref: Q-8
  merged_from:
  - open-items-approval-merge-protection/U-12
  id: U-32
- what: Whether the person's conversational 'I approve all' (header, Q-07, Q-08) is accepted by the design
    as approval of the proposal file itself; the proposal says no gate has evidence of it and defines
    approval only for design and plan artifacts under docs/design/<task>/, so what recorded form would
    count as approval of docs/design/orqlet-architecture-proposal.md is not stated.
  material: true
  question_ref: Q-9
  merged_from:
  - proposal-approval/U-6
  id: U-33
- what: Whether any design or plan in this repository is approved under the proposal's own definition
    (merged through a pull request with an approving review from the required code owners); the local
    reflog shows commits made on main by one author identity with no pull-request or merge records, and
    whether those commits reached the remote main by pull request or direct push cannot be observed from
    the working tree.
  material: true
  question_ref: Q-9
  merged_from:
  - proposal-approval/U-10
  id: U-34
- what: Whether the 'design pull request' that plan.yaml says 'merged elsewhere' exists in another repository
    or host; the repository has no pull request in any state.
  material: true
  question_ref: Q-9
  merged_from:
  - open-items-approval-merge-protection/U-8
  id: U-35
- what: 'Where the person''s conversation approvals (''I approve all designs and plans'', ''I approve
    all'') are stored: the repository holds only the quotations written into artifacts and commit subjects,
    not the conversation.'
  material: true
  question_ref: Q-9
  merged_from:
  - open-items-approval-merge-protection/U-9
  id: U-36
- what: The time of day of the 2026-10-25 conversation approvals, and so whether they came before the
    P-1 to P-6 implementation commits (10:20 to 10:30) or after; the artifacts give only the date.
  material: true
  question_ref: Q-9
  merged_from:
  - open-items-approval-merge-protection/U-10
  id: U-37
- what: Whether a decision to apply the .orqlet/proposals versions proposal is recorded anywhere besides
    the commit subject e65734a9150c, and whether change_control (which names only lowering a pin or floor)
    covers a raise.
  material: true
  question_ref: Q-9
  merged_from:
  - open-items-approval-merge-protection/U-15
  id: U-38
- what: Whether the document's statement 'no commit, no remote and no CI run' (dated 2026-10-22) still
    holds at the target commit; the working tree at 4aefcce contains .github/workflows/ci.yml and .git/config
    (local, not committed content) contains a remote origin at github.com/tmishari/orqlet.git, and the
    local reflog shows its first commit on 2026-10-24 (epoch 1792822002), the commit message 'Fix proposal
    wording from the P-5 reviews and record the approval of v0.5' (2c4308e) on 2026-10-25 and 4aefcce
    on 2026-10-26; whether any CI run has occurred on the remote is not observable here.
  material: false
  merged_from:
  - proposal-approval/U-17
  id: U-39
- what: Whether the host's stale-approval dismissal emits a review event (the proposal says not stated)
    and whether a base-branch change raises pull_request edited (the proposal says not verified).
  material: false
  merged_from:
  - proposal-approval/U-18
  id: U-40
- what: Whether a ruleset's expected source applies to a commit status (the proposal says reported by
    a reviewer, to be confirmed in S-28) and the effect of GitHub's one-month or seven-day rules on the
    first required check (bootstrap, documented but not run).
  material: false
  merged_from:
  - proposal-approval/U-19
  id: U-41
- what: Whether the working-tree file docs/design/orqlet-architecture-proposal.md equals the blob at commit
    4aefcce3fce1ab379377addc961d7cb8c1b84b7f; HEAD and the branch ref were read from .git files, and git
    status and git diff were not run because the session is read-only.
  material: false
  merged_from:
  - proposal-approval/U-20
  id: U-42
- what: Whether any line numbers in the proposal were affected by long table rows wrapped in tool output;
    line numbers in this fragment were counted from the tool's 10-line markers and verified against grep
    line numbers where available.
  material: false
  merged_from:
  - proposal-approval/U-21
  id: U-43
- what: What the proposal intends by the diagnostic style of ORQ-W390; the proposal does not define or
    mention it (only the built code does, gate_status.py:183), so no proposal statement maps its staleness
    events to codes.
  material: false
  merged_from:
  - proposal-approval/U-22
  id: U-44
- what: Whether 'approval-required spaces' for Jira and Confluence (formerly Q-02, now a pending input)
    affect any approval of Orqlet artifacts; the proposal says it affects only milestone M6 and decision
    D-12.
  material: false
  merged_from:
  - proposal-approval/U-23
  id: U-45
- what: Whether the required status checks beyond Orqlet's own (the project's build, test and lint jobs
    named in the baseline required_checks) exist on the remote; the proposal says branch protection requires
    them as separate checks and the baseline names them, and the working tree's ci.yml defines jobs lint,
    types, architecture, tests and build.
  material: false
  merged_from:
  - proposal-approval/U-24
  id: U-46
- what: Whether orqlet gate status currently reports the harness2-fit AS-IS, design and plan as stale,
    and whether the as_is_ref, design_ref and artifact hashes still match; no command was run in this
    read.
  material: false
  merged_from:
  - open-items-approval-merge-protection/U-14
  id: U-47
- what: 'What the three AI-reviewer review records of harness2-fit count as in place of a human reviewer:
    no artifact states who the ''human reviewer of the design pull request'' is.'
  material: false
  merged_from:
  - open-items-approval-merge-protection/U-17
  id: U-48
- what: 'Whether the GitHub run list is complete: the capture shows two runs and states no total count.'
  material: false
  merged_from:
  - open-items-approval-merge-protection/U-18
  id: U-49
- what: Whether a merge queue is used (Q-01 asks); GitHub is the host according to the capture, but no
    ledger answer records Q-01.
  material: false
  merged_from:
  - open-items-approval-merge-protection/U-19
  id: U-50
- what: Whether the tree of merge commit e8ef7a8832e9 equals the tree of the rebuilt tip 034007cb6726,
    and whether the original-line commits (a18faca to 0bfc2fa) were ever pushed.
  material: false
  merged_from:
  - open-items-approval-merge-protection/U-20
  id: U-51
- what: Why git remote -v prints an ssh:// URL while the repository-local config holds an https:// URL;
    the global git configuration was not read.
  material: false
  merged_from:
  - open-items-approval-merge-protection/U-21
  id: U-52
- what: What produced the empty .orqlet/proposals/.orqlet__role-bindings.yaml.diff.
  material: false
  merged_from:
  - open-items-approval-merge-protection/U-22
  id: U-53
- what: Whether the GitHub login tmishari and the commit author name Timur Misharin are the same person;
    no artifact states it.
  material: false
  merged_from:
  - open-items-approval-merge-protection/U-23
  id: U-54
- what: Why the GitHub run for head 2c4308ecdbed concluded failure and the run for e8ef7a8832e9 was cancelled;
    the causes were not requested (red CI jobs are outside the person's chosen item).
  material: false
  merged_from:
  - open-items-approval-merge-protection/U-24
  id: U-55
- what: Whether the empty file .orqlet/proposals/.orqlet__role-bindings.yaml.diff is expected (a Read
    returned '(omitted)' and a search for any character found none).
  material: false
  merged_from:
  - approval-trace/U-9
  id: U-56
- what: Whether `--phase` without a task is meant to be ignored (gate_status returns before reading it).
  material: false
  merged_from:
  - approval-trace/U-10
  id: U-57
- what: 'Whether any test covers upgrade''s own approval prompt without --yes (needs-input, ORQ-E115):
    none was found.'
  material: false
  merged_from:
  - approval-trace/U-11
  id: U-58
- what: 'Whether skill steps that tell the agent to run `orqlet gate status` and copy `bound` are meant
    to use --json: the skill text does not say, and the human output does not print `bound`.'
  material: false
  merged_from:
  - approval-trace/U-12
  id: U-59
- what: 'The relation between `assurance: advisory` in ReviewResult, the word ''attested'' in the review_result
    and validate_records docstrings, and the approval concept: not defined in code.'
  material: false
  merged_from:
  - approval-trace/U-13
  id: U-60
- what: 'How the Orqlet-Task and Orqlet-Phase trailers and the pull-request template fields are meant
    to be read by a future check: no code reads them at this commit.'
  material: false
  merged_from:
  - approval-trace/U-14
  id: U-61
- what: 'The intended use of ArtifactHeader.bound.upstream and ArtifactHeader.specialists: both are defined
    and validated for shape, and no use case reads them.'
  material: false
  merged_from:
  - approval-trace/U-15
  id: U-62
contradictions:
- sources:
  - docs/design/orqlet-architecture-proposal.md:5
  - docs/design/orqlet-architecture-proposal.md:3037
  - docs/design/orqlet-architecture-proposal.md:5147
  note: The header Status row says 'approved by the person on 2026-10-25, in conversation', while Section
    17.7 and D-22 define approval as presence on the protected baseline with a merged pull request and
    an approving review from the required code owners; the same Status row says the conversational approval
    is 'not a merged pull request, so no gate has evidence of it'. The document acknowledges the gap in
    the same row.
  merged_from:
  - proposal-approval/C-1
  id: C-1
- sources:
  - docs/design/orqlet-architecture-proposal.md:5095
  - docs/design/orqlet-architecture-proposal.md:5
  - docs/design/orqlet-architecture-proposal.md:130
  note: The Q-08 'Why it is material' cell says 'The status line says awaiting approval', while the header
    Status row now says v0.5 is approved and Section 0.3 says its 'awaiting human approval' status is
    superseded by Section 0.6.
  merged_from:
  - proposal-approval/C-2
  id: C-2
- sources:
  - docs/design/orqlet-architecture-proposal.md:5721
  - docs/design/orqlet-architecture-proposal.md:5645
  - docs/design/orqlet-architecture-proposal.md:4503
  - docs/design/orqlet-architecture-proposal.md:5084
  - docs/design/orqlet-architecture-proposal.md:5085
  note: Section 26.12.4 lists Q-07 and Q-08 under 'Unresolved', traceability row 7.7 says whether the
    Code Reviewer is a gate 'is Q-07', and the M0 row lists answering Q-07, while Section 25.1 and Section
    0.6.3 record both as answered on 2026-10-25.
  merged_from:
  - proposal-approval/C-3
  id: C-3
- sources:
  - docs/design/orqlet-architecture-proposal.md:4503
  - docs/design/orqlet-architecture-proposal.md:5179
  note: The M0 row lists Q-01, Q-03, Q-04, Q-05, Q-06 and Q-07 among the questions to answer, while Section
    25.3 says M0 is meant to begin when Q-01, Q-03, Q-04 and Q-05 are answered and that Q-06 gates only
    the Miro work.
  merged_from:
  - proposal-approval/C-4
  id: C-4
- sources:
  - docs/design/orqlet-architecture-proposal.md:5147
  - docs/design/orqlet-architecture-proposal.md:5090
  - docs/design/orqlet-architecture-proposal.md:5721
  note: The approval channel is recorded as a default in D-22 (approval is presence on the protected baseline
    with merge evidence, 'You are not asked to approve them') and as an unanswered question in Q-03, Section
    17.4 step 4 ('This is open question Q-03') and Section 26.12.4 ('Unresolved').
  merged_from:
  - proposal-approval/C-5
  id: C-5
- sources:
  - docs/design/orqlet-architecture-proposal.md:3037
  - docs/design/orqlet-architecture-proposal.md:3090
  - docs/design/orqlet-architecture-proposal.md:3162
  note: Section 17.7 says presence on the baseline alone is not approval and merge evidence is required,
    while Section 17.7 (revalidation on resume) says 'approval presence on the baseline' and Section 17.11
    says 'Approval is decided by presence on the baseline, not by status'; Section 26 (line 5382) claims
    'merge evidence' wording throughout.
  merged_from:
  - proposal-approval/C-6
  id: C-6
- sources:
  - docs/design/orqlet-architecture-proposal.md:426
  - docs/design/orqlet-architecture-proposal.md:3037
  - docs/design/orqlet-architecture-proposal.md:3771
  note: The protected baseline is defined as the tip of the protected target branch (glossary), as the
    branch for which branch protection requires pull-request review and code-owner approval (Section 17.7),
    and as the tip of the target branch or a pinned ref in a separate repository the organisation controls
    (Section 19.8.2 item 1); the three definitions differ in whether branch protection is part of the
    definition and whether a separate repository can be the baseline.
  merged_from:
  - proposal-approval/C-7
  id: C-7
- sources:
  - docs/design/orqlet-architecture-proposal.md:3853
  - docs/design/orqlet-architecture-proposal.md:3856
  - docs/design/orqlet-architecture-proposal.md:3884
  - docs/design/orqlet-architecture-proposal.md:3740
  - docs/design/orqlet-architecture-proposal.md:1266
  note: '''Dismiss stale approvals'' is listed as a required ruleset setting (checklist item 4), as part
    of trustworthy merge enforcement (Section 19.7) and as the T7 mitigation, while checklist item 7 says
    the design does not depend on it and the approval-counting rule and FM-E03 operate with it off.'
  merged_from:
  - proposal-approval/C-8
  id: C-8
- sources:
  - docs/design/orqlet-architecture-proposal.md:3744
  - docs/design/orqlet-architecture-proposal.md:2884
  - docs/design/orqlet-architecture-proposal.md:3817
  - docs/design/orqlet-architecture-proposal.md:3007
  - docs/design/orqlet-architecture-proposal.md:4563
  note: Sections 19.8 and 17.2 say that where no host is supported the merge gates are 'unavailable',
    reported as reduced capability, and onboarding does not fail, while Section 19.8.4 says approval evidence
    is required and not a project option and yields NOT_RUN if it cannot be obtained, and the Phase 4
    precondition stops unless the design and plan are approved on the baseline; the document does not
    state what gate status and the /orqlet-implement precondition do on an unsupported host.
  merged_from:
  - proposal-approval/C-9
  id: C-9
- sources:
  - docs/design/orqlet-architecture-proposal.md:4480
  - .github/workflows/ci.yml:3-6
  - docs/design/orqlet-implementation/plan.md:11
  note: Section 22.0 (dated 2026-10-22) says 'there is no commit, no remote and no CI run', while the
    working tree at 4aefcce contains a GitHub Actions workflow triggered on push to main and pull_request,
    and the implementation plan's decision D-8 mentions a 'Git repository plus remote for Orqlet'; the
    local reflog and .git/config (not committed content) show commits dated 2026-10-24 to 2026-10-26 and
    a remote origin.
  merged_from:
  - proposal-approval/C-11
  id: C-10
- sources:
  - docs/design/orqlet-implementation/as-is.md:85
  - docs/design/orqlet-architecture-proposal.md:5
  - docs/design/orqlet-architecture-proposal.md:5095
  - docs/design/orqlet-architecture-proposal.md:6052
  note: as-is.md U-1 states 'v0.4 is not approved', while the proposal states that the approval state
    of v0.4 is not recorded in the repository and that the person did not state it.
  merged_from:
  - proposal-approval/C-12
  id: C-11
- sources:
  - docs/design/orqlet-architecture-proposal.md:4480
  - docs/design/orqlet-architecture-proposal.md:3365
  - docs/design/orqlet-architecture-proposal.md:5095
  note: Section 22.0 says the implementation was 'planned and approved separately' from plans that cite
    v0.4 and was built before Q-01, Q-03, Q-04 and Q-05 were answered, W-1 says implementation starts
    only after the design and plan are approved, and Q-08 says the repository holds no record of approving
    v0.4.
  merged_from:
  - proposal-approval/C-13
  id: C-12
- sources:
  - docs/design/orqlet-implementation/design.md:6-6
  - docs/design/orqlet-implementation/design.md:10-10
  - docs/design/orqlet-implementation/plan.md:3-5
  - docs/design/orqlet-m2-workflow/design.md:7-7
  - docs/design/orqlet-architecture-proposal.md:4480-4480
  note: design.md says nothing in the folder is approved and no code may be written until it is, and also
    that decisions D-1 to D-8 were approved on 2026-10-21; plan.md calls itself the approved Phase 3 text;
    the m2 design calls the implementation design 'approved'; the proposal says the plans were 'planned
    and approved separately'. design.md line 6 and line 10 are in the same table.
  merged_from:
  - open-items-approval-merge-protection/C-1
  id: C-13
- sources:
  - docs/design/orqlet-implementation/adr-002-deterministic-data-and-hashing.md:3-3
  - docs/design/orqlet-implementation/design.md:10-10
  - docs/design/orqlet-implementation/plan.md:3-3
  note: ADR-001 to ADR-005 carry 'proposed (needs approval with design.md)' (ADR-002 names decision D-2),
    while design.md says D-1 to D-8 (D-2 included) are approved and plan.md says the plan built from them
    is executed and approved.
  merged_from:
  - open-items-approval-merge-protection/C-2
  id: C-14
- sources:
  - docs/design/orqlet-implementation/as-is.md:85-85
  - docs/design/orqlet-implementation/design.md:7-10
  - docs/design/orqlet-m2-workflow/design.md:7-9
  note: as-is.md records that v0.4 is not approved (U-1, material); design.md and the m2 design take v0.4
    as input and record their own approvals; the approval of v0.4 itself is recorded nowhere (proposal
    line 5, line 5095).
  merged_from:
  - open-items-approval-merge-protection/C-3
  id: C-15
- sources:
  - docs/design/harness2-fit/plan.yaml:226-226
  - docs/design/harness2-fit/plan.yaml:231-231
  - docs/design/open-items/evidence/github-state.yaml:35-37
  note: plan.yaml records with result pass that the design pull request 'merged elsewhere' and, in the
    next approval entry, that approval 'is not a merge on the protected baseline'; GitHub reports 0 pull
    requests in any state.
  merged_from:
  - open-items-approval-merge-protection/C-4
  id: C-16
- sources:
  - docs/design/harness2-fit/design/manifest.yaml:159-159
  - docs/design/harness2-fit/plan.yaml:231-231
  - docs/design/orqlet-architecture-proposal.md:3037-3037
  note: Both self_check entries are marked result pass while stating that a gate run has no approval evidence;
    the proposal says that without merge evidence on the protected baseline the result is NOT_RUN.
  merged_from:
  - open-items-approval-merge-protection/C-5
  id: C-17
- sources:
  - docs/design/harness2-fit/plan.yaml:226-226
  - docs/design/open-items/evidence/git-history.txt:5-26
  - docs/design/open-items/evidence/git-history.txt:35-36
  note: plan.yaml says the repository has no commit or remote; the history lists 22 commits (the plan
    itself is committed at 3b1d1cc) and an origin remote.
  merged_from:
  - open-items-approval-merge-protection/C-6
  - proposal-approval/C-10
  id: C-18
- sources:
  - docs/design/orqlet-implementation/plan.md:137-148
  - docs/design/orqlet-m2-workflow/design.md:26-26
  - docs/design/orqlet-m2-workflow/plan.md:169-169
  - docs/design/orqlet-architecture-proposal.md:4480-4480
  - docs/design/open-items/evidence/git-history.txt:5-26
  - docs/design/open-items/evidence/github-state.yaml:43-48
  note: These documents (dated 2026-10-21 to 2026-10-22) say there is no commit, no remote and no CI run;
    the captures of 2026-10-26 show 22 commits, an origin remote and two CI runs. None of the documents
    carries a later correction.
  merged_from:
  - open-items-approval-merge-protection/C-7
  id: C-19
- sources:
  - docs/design/orqlet-implementation/plan.md:43-43
  - docs/design/orqlet-implementation/design.md:62-62
  - docs/design/open-items/evidence/github-state.yaml:35-37
  - docs/design/open-items/evidence/git-history.txt:5-26
  note: plan.md says each phase is one pull request and design.md says Orqlet's own pull requests are
    reviewed by humans; GitHub reports 0 pull requests and the history holds direct commits and one local
    merge commit.
  merged_from:
  - open-items-approval-merge-protection/C-8
  id: C-20
- sources:
  - docs/design/orqlet-architecture-proposal.md:3037-3037
  - docs/design/orqlet-m2-workflow/design.md:40-40
  - docs/design/open-items/evidence/github-state.yaml:23-31
  - docs/design/open-items/evidence/github-state.yaml:38-42
  note: The proposal and the m2 design define approval as a merged pull request on a protected baseline
    with approval by a non-author code owner; GitHub reports main not protected, protection and rulesets
    unavailable (403), no CODEOWNERS file in the repository, and one collaborator.
  merged_from:
  - open-items-approval-merge-protection/C-9
  id: C-21
- sources:
  - .orqlet/versions.yaml:13-14
  - docs/design/open-items/evidence/github-state.yaml:38-42
  note: versions.yaml requires 2 approvals to lower a pin or floor; GitHub lists one collaborator, the
    repository's admin.
  merged_from:
  - open-items-approval-merge-protection/C-10
  id: C-22
- sources:
  - docs/design/harness2-fit/as-is.md:7-8
  - docs/design/harness2-fit/design/manifest.yaml:6-7
  - docs/design/harness2-fit/plan.yaml:6-7
  - .orqlet/versions.yaml:9-10
  note: 'The three artifacts of one task carry different bound values: the AS-IS header says workflow
    0.3.0 and digest 49ef4cd5..., the manifest and plan say 0.3.1 and be772328..., and versions.yaml says
    0.3.1; manifest and plan record a refresh of ''this header'' and the AS-IS records none, while its
    header status is approved.'
  merged_from:
  - open-items-approval-merge-protection/C-11
  id: C-23
- sources:
  - docs/design/harness2-fit/plan.yaml:231-231
  - docs/design/open-items/evidence/git-history.txt:26-26
  - docs/design/open-items/evidence/git-history.txt:10-19
  note: plan.yaml dates the approval to choose the design set and plan 2026-10-25; the original line commits
    harness2-fit P-1 to P-6 on 2026-10-24, and in the rebuilt line the P-1 to P-6 commits (10:20 to 10:30)
    precede the commit recording the approval (14:14) on 2026-10-25.
  merged_from:
  - open-items-approval-merge-protection/C-12
  id: C-24
- sources:
  - docs/design/orqlet-implementation/as-is.md:85-85
  - docs/design/orqlet-m2-workflow/design.md:45-45
  - docs/design/harness2-fit/as-is.md:259-259
  - docs/design/go-migration-feasibility/questions.yaml:159-159
  - docs/design/orqlet-architecture-proposal.md:5095-5095
  note: 'The identifiers U-1 and Q-08 are reused with different meanings: U-1 is v0.4 approval status
    (orqlet-implementation AS-IS, the one the proposal cites), Cursor skill listing (m2 design) and ''what
    a solution for us means'' (harness2-fit AS-IS); Q-8 is the byte-identical output reach (go-migration)
    while the proposal''s Q-08 is the approved proposal version.'
  merged_from:
  - open-items-approval-merge-protection/C-13
  id: C-25
- sources:
  - docs/design/open-items/evidence/git-history.txt:35-36
  - docs/design/open-items/evidence/git-history.txt:39-39
  - .git/config:9-9
  note: git remote -v prints ssh://github.com/tmishari/orqlet.git; the config key remote.origin.url and
    the repository config file hold https://github.com/tmishari/orqlet.git.
  merged_from:
  - open-items-approval-merge-protection/C-14
  id: C-26
- sources:
  - src/orqlet/application/usecases/gate_status.py:6-7
  - src/orqlet/interface/cli/commands/gate.py:34
  - src/orqlet/application/usecases/validation.py:73-80
  - src/orqlet/application/usecases/gate_status.py:258-269
  note: The docstrings say that with a task the verdict is always NOT_RUN; Collector.result returns FAIL
    when any error finding exists, and gate_status can add errors (ORQ-E390, ORQ-E391, read_artifact errors,
    ORQ-E450, ORQ-E451, ORQ-E453). Both verdicts exit 5. No test asserts a FAIL verdict with a task.
  merged_from:
  - approval-trace/C-1
  id: C-27
- sources:
  - src/orqlet/workflow/skills/orqlet-research/references/as-is-format.md:44
  - src/orqlet/workflow/skills/orqlet-research/skill.md:13
  - src/orqlet/interface/cli/render_human.py:170-203
  note: The skill texts say `orqlet gate status` prints the `bound` values to copy; the human renderer
    has no handling for the `bound` key and prints only the verdict line (and findings), so the values
    appear only in the --json envelope; the skill text does not mention --json and no test runs gate status
    without it.
  merged_from:
  - approval-trace/C-2
  id: C-28
- sources:
  - src/orqlet/application/contracts/versions_file.py:1
  - src/orqlet/application/usecases/installation.py:80
  - src/orqlet/application/usecases/upgrade.py:187-190
  note: The contract docstring describes .orqlet/versions.yaml as 'read from the baseline'; load_installation
    reads it from the working tree, and the floor that upgrade, rollback and doctor enforce comes from
    that working-tree copy, which is written as a SEEDED (team-owned) file.
  merged_from:
  - approval-trace/C-3
  id: C-29
- sources:
  - src/orqlet/application/contracts/versions_file.py:26-27
  - src/orqlet/application/usecases/upgrade.py:202-213
  - src/orqlet/application/usecases/rollback.py:72-76
  note: The number of approvals needed to lower the pin or floor is a configurable field with default
    2, while the upgrade and rollback messages state 'two approvals' as fixed text and never read the
    field.
  merged_from:
  - approval-trace/C-4
  id: C-30
self_check:
  schema: orqlet.self-check/v1
  checked_against:
    role: researcher
    phase: research
  checks:
  - what: the person's answers are in the ledger
    how: orqlet validate ledger docs/design/open-items/questions.yaml
    result: pass
  - what: bound values copied
    how: orqlet gate status --json at the base revision
    result: pass
  - what: GitHub and git state read without a write
    how: gh api GET requests and git log, captured in docs/design/open-items/evidence/
    result: pass
  - what: absence claims
    how: searched src/orqlet and the proposal with rg for header status reads, change_control reads, readers
      of .orqlet/proposals, WorkflowPolicy users, approve, ci and hook commands, and GitHub plan names;
      the results are the facts that say 'a search'
    result: pass
  - what: references resolve
    how: orqlet validate as-is docs/design/open-items/as-is.md --fragments docs/design/open-items/fragments
    result: pass
  unverified:
  - The three researchers were read-only and ran no command, so the main agent cited every line range
    with `orqlet evidence cite` and captured the GitHub and git state itself.
  - The researchers' statements were not each re-read against the cited lines; the contradictions' `sources`
    line numbers were not each checked.
  - The red CI jobs, the open items of harness2-fit and of the proposal other than approval, and go-migration-feasibility
    were not examined (ledger Q-1).
---

# AS-IS: approval and merge evidence, branch protection, plan re-basing

Facts: 112. Unknowns: 62 (38 material). Contradictions: 30. The raw reports of the three researchers are in `docs/design/open-items/fragments/`; the captured GitHub and git state is in `docs/design/open-items/evidence/`.
