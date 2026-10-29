# V-10 for Claude Code: unattended surfaces, narrower scopes and personal tokens

Verdict: PARTLY RUN. The question about narrower scopes was observed against a local server only. The unattended surfaces and the administrator setting were not run.

- Check: V-10 of `docs/design/mcp-or-plugins/design/adr-004-verify-client-behaviour-with-test-accounts.md`, for Claude Code only (the halves for Codex and Cursor wait for the release that enables them)
- Unknowns it answers: U-23, U-70 to U-75
- Date: 2026-10-29
- Client name and version: Claude Code 2.1.303, on macOS
- Kind of test account: none. A local OAuth server on the loopback interface, run by the tester, advertised three scopes and issued canary tokens that grant nothing. No test tenant of a real service was used.
- Vendor statements beside the observations: `docs/design/mcp-or-plugins/evidence/web/claude-code-mcp-checks.md`, excerpts 4 and 6 (read 2026-10-29)

## Question

Can a cloud agent, a review context or CI use a committed entry with the account of the one user who started or owns the surface (Q-12)? Can the client request fewer Atlassian scopes than the consent offers (A-146)? In a separate test tenant, does an administrator's setting for API-token authentication allow personal tokens without service-account keys?

## Steps as run

1. The local server listed three scopes in its resource metadata. The client signed in with `claude mcp login`, with a stand-in for the browser command, for an entry that set nothing about scopes. The server logged the scope of the authorization request.
2. A second entry set `oauth.scopes` to one of the three scopes, and the client signed in again. The server logged the scope again.
3. Both entries were signed out and removed, and the keychain item that the check created was deleted.
4. The unattended surfaces and the test tenant were not run (no account and no surface was available to the tester).

## Observed result

- With nothing set, the authorization request asked for all three scopes that the local server listed in its resource metadata. The vendor text (excerpt 6) speaks of the metadata of the authorization server and says the full catalog is not requested from it; the two may not conflict, and the metadata of Atlassian was not read.
- With `oauth.scopes` set, the request asked for only the scope that was set.
- A `claude -p` run (see V-1) loads a project entry without a prompt. Which sign-in or account a cloud agent, a review context or CI holds when it uses the entry was not run.
- Not run: the account that each unattended surface uses, the consent screen of Atlassian and its scope names, and the administrator setting for API-token authentication in a test tenant.

## Verdict

Partly run. The client can ask for fewer scopes than a server advertises, through `oauth.scopes` on the entry. The entry that Orqlet generates does not set it, so it still carries the user's full permissions, as the README says. Whether the consent of Atlassian offers a smaller set of scopes, and what their names are, needs a test tenant and was not run.

Plan amendment: not requested. A person decides whether the generated entry should set `oauth.scopes`; that would change ADR-002 decision 10 and needs a design amendment after the scope names are checked in a test tenant.

## If the result differs

Where a surface cannot use the account of one user, Q-6 and Q-9 are not met there for any mode, and the README says so. If the scopes cannot be limited, the README says that the entry carries the user's full permissions (ADR-004 decision 3). Neither the surfaces nor the tenant were run, so the README keeps both statements as written.

## Before you commit this record

- [x] The record holds no credential value, no account name, no raw client log, no address of a private server and no tenant host.
- [x] No throwaway repository was created. The canary tokens grant nothing, the client signed out, and the keychain item that the check created was deleted.
