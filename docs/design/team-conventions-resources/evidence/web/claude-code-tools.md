# Tools reference - Claude Code Docs
URL: https://code.claude.com/docs/en/tools-reference
Retrieved: 2026-10-26T16:04Z (workstation clock, UTC) through the WebFetch tool. The excerpts below are verbatim; the label of each says where it sits on the page.

## Excerpt 1: WebFetch and WebSearch in the tool list
| `WebFetch` | Fetches content from a specified URL. See WebFetch tool behavior | Yes |
| `WebSearch` | Performs web searches. See WebSearch tool behavior | Yes |

## Excerpt 2: WebFetch tool behavior
## WebFetch tool behavior

WebFetch takes a URL and a prompt describing what to extract. It fetches the page and converts the response to Markdown when the server returns HTML. For most fetches, it then runs the prompt against the content in a separate model call, and Claude receives the result of that call rather than the raw page. The conversion step is not configurable.

This makes WebFetch lossy by design. The extraction prompt determines what reaches Claude, so a result that says a page doesn't mention something may only mean the prompt didn't ask about it. Ask Claude to fetch again with a more specific prompt, or use `curl` via Bash for the unprocessed page.

## Excerpt 3: WebFetch limits
- WebFetch refuses `localhost` and any other hostname without a dot, such as a bare intranet name, before making a request. The error it returns tells Claude to reach local servers with `curl` through Bash instead.
- HTTP URLs are automatically upgraded to HTTPS.
- WebFetch reads up to 100,000 characters of a page's content per call. On Claude Code v2.1.290 or later, the result for a longer page tells Claude how much went unread, so Claude can fetch the next part.
- WebFetch caches each response for 15 minutes by default, so repeated fetches of the same URL return quickly. On Claude Code v2.1.233 or later, set `CLAUDE_CODE_WEBFETCH_CACHE_TTL_MS` to change how long WebFetch keeps each response.
