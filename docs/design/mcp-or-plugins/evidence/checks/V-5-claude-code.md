# V-5 for Claude Code: where a sign-in is stored and whether it follows a changed address

Verdict: PARTLY RUN. What was observed confirms the design. Only macOS and a canary sign-in were run.

- Check: V-5 of `docs/design/mcp-or-plugins/design/adr-004-verify-client-behaviour-with-test-accounts.md`, for Claude Code only (the halves for Codex and Cursor wait for the release that enables them)
- Unknowns it answers: U-32, U-46, U-47, U-59, U-65
- Date: 2026-10-29
- Client name and version: Claude Code 2.1.303, on macOS
- Kind of test account: none with a real service. A local OAuth server on the loopback interface, run by the tester, issued canary tokens that grant nothing. The client used an isolated configuration directory, so its keychain item was separate from the tester's own login. This record inspects file modes and key names and never values.
- Vendor statement beside the observations: `docs/design/mcp-or-plugins/evidence/web/claude-code-authentication.md` (read 2026-10-26)

## Question

Where does Claude Code store an OAuth sign-in (keychain or file)? With what file mode, keyed by what, and per operating-system user? After the address of the entry changes, does the client reuse the stored token for the new address?

## Steps as run

1. The local server answered a request with the metadata that sends a client to its authorization server. The client signed in through `claude mcp login`, with a stand-in for the browser command that followed the redirect on the same machine.
2. The configuration directory was listed, and the keychain was searched for the items of the client by service name. The stored blob of the new item was read into a script that printed key names and value types only.
3. The address of the entry was changed in the stored configuration, which keeps the stored sign-in, to: another path of the same server, another port (a second local server), the same address with a trailing slash, and the host written as `localhost`. `claude mcp list` ran after each change, and the server logged whether an Authorization header arrived. The original address was restored at the end.
4. The client signed out and removed the entry. The blob was read again for key names. The keychain item that the check had created was deleted and both local servers were stopped.

## Observed result

- Storage: the sign-in was in an item of the login keychain of the operating-system user. The service name of the item carried a suffix derived from the configuration directory, so a client with another configuration directory reads another item. The configuration file of the client (mode 0600) held no token, and no credentials file was created.
- Keyed by: the blob held a map named `mcpOAuth` whose keys were the server name and a hash, and each entry held the server name, the server address, an access token, a refresh token, the client id, the issuer, the redirect address, an expiry and the scope.
- Reuse: with the original address the server saw a valid token. After each change (path, port, trailing slash, host spelling) the first request carried no Authorization header, so the stored token was not reused. Two of the four changes (the other path and the `localhost` spelling) also made the client refuse the server, because the resource metadata of the server named another address. For the change of port and for the trailing slash there was no refusal and the client still sent no header, so the missing header is not only an effect of that refusal.
- After sign-out and removal: the blob kept entries with the server name and address and an empty access token, several of them (the client had checked several addresses), and no refresh token. A different address gave a different entry.
- Not run: Linux and Windows (a credentials file, per the vendor), another operating-system user, a world-readable fallback, and a sign-in to a real service.

## Verdict

Confirms the design (A-69): sign-ins are stored per address, and a changed address needs a new sign-in. Because a stored sign-in does not follow a changed address, a pull request that points `orqlet-*` at another server makes the user sign in again at that server; the README says so and does not call it a protection.

Plan amendment: none requested.

## If the result differs

A world-readable fallback, or a reuse of the token for a changed address, is written as a risk to the user's own credential. For Codex and Cursor it also gates their OAuth entries (ADR-004 decision 2). Neither was observed.

## Before you commit this record

- [x] The record holds no credential value, no account name, no raw client log, no address of a private server and no tenant host.
- [x] The canary tokens grant nothing, the client signed out, and the keychain item that the check created was deleted. The tester's own login item was not touched.
