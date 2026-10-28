# Authorization - Model Context Protocol (draft)
URL: https://modelcontextprotocol.io/specification/draft/basic/authorization
Retrieved: 2026-10-26T16:43Z (workstation clock, UTC) through the WebFetch tool. The excerpts below are verbatim; the label of each says where it sits on the page.

## Excerpt 1: Roles
A protected MCP server acts as an OAuth 2.1 resource server,
capable of accepting and responding to protected resource requests using access tokens.

An MCP client acts as an OAuth 2.1 client,
making protected resource requests on behalf of a resource owner.

## Excerpt 2: Token audience and passthrough
MCP servers MUST validate that access tokens were issued specifically for them as the intended audience,
according to RFC 8707 Section 2.
If validation fails, servers MUST respond according to
OAuth 2.1 Section 5.3
error handling requirements. Invalid or expired tokens MUST receive a HTTP 401
response.

MCP clients MUST NOT send tokens to the MCP server other than ones issued by the MCP server's authorization server.

MCP servers MUST only accept tokens that are valid for use with their
own resources.

MCP servers MUST NOT accept or transit any other tokens.
