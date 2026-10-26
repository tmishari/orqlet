# Configuration reference - Codex
URL: https://developers.openai.com/codex/config-reference
Retrieved: 2026-10-26T16:04Z (workstation clock, UTC) through the WebFetch tool. The excerpts below are verbatim; the label of each says where it sits on the page.

## Excerpt 1: tools.web_search
| `tools.web_search` | `boolean | { context_size = "low|medium|high", allowed_domains = [string], location = { country, region, city, timezone } }` | Optional web search tool configuration. The object form can set search context size, allowed search domains, and approximate user location. These search-domain filters are separate from sandboxed-command network domain rules and do not restrict connectors or MCP servers. |

## Excerpt 2: web_search
| `web_search` | `disabled | cached | indexed | live` | Web search mode (default: `"cached"`; cached uses an OpenAI-maintained index without external web access; indexed permits external access only when gated by the search index; if you use `--yolo` or another full access sandbox setting, it defaults to `"live"`). Use `"live"` for unrestricted live retrieval, or `"disabled"` to remove the tool. |
