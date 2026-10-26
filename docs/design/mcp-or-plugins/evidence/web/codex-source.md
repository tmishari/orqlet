# openai/codex source files (configuration types and OAuth storage)
URL: https://github.com/openai/codex/blob/main/codex-rs/config/src/mcp_types.rs
Retrieved: 2026-10-26T08:44Z (workstation clock, UTC) through the WebSearch tool. The excerpts below are verbatim; the label of each says where it sits on the page.
Also from: config_toml.rs https://github.com/openai/codex/blob/main/codex-rs/config/src/config_toml.rs
Also from: oauth.rs https://github.com/openai/codex/blob/main/codex-rs/rmcp-client/src/oauth.rs

## Excerpt 1: mcp_types.rs: OAuth settings
/// Client settings for MCP OAuth login or enterprise token exchange.
#[derive(Serialize, Deserialize, Debug, Clone, Default, PartialEq, Eq, JsonSchema)]
#[schemars(deny_unknown_fields)]
pub struct McpServerOAuthConfig {
 /// Explicit OAuth client identifier to present during authorization and token exchange.
 #[serde(default, skip_serializing_if = "Option::is_none")]
 pub client_id: Option,

 /// OAuth client secret used for token exchange with a pre-registered client.
 #[serde(default, skip_serializing_if = "Option::is_none")]
 pub client_secret: Option,

## Excerpt 2: mcp_types.rs: HTTP transport credentials
 /// Name of the environment variable to read for an HTTP bearer token.
 /// When set, requests will include the token via `Authorization: Bearer `.
 /// The actual secret value must be provided via the environment.
 #[serde(default, skip_serializing_if = "Option::is_none")]
 bearer_token_env_var: Option,
 /// Additional HTTP headers to include in requests to this server.
 #[serde(default, skip_serializing_if = "Option::is_none")]
 http_headers: Option<HashMap<String, String>>,
 /// HTTP headers where the value is sourced from an environment variable.
 #[serde(default, skip_serializing_if = "Option::is_none")]
 env_http_headers: Option<HashMap<String, String>>,
 /// Local-only shell command that prints a JSON object of dynamic HTTP headers.
 /// The command may be visible to local process inspection; do not embed credentials.
 #[serde(default, skip_serializing_if = "Option::is_none")]
 http_headers_helper: Option,
 },

## Excerpt 3: config_toml.rs: where MCP OAuth credentials are stored
 /// Preferred backend for storing MCP OAuth credentials.
 /// keyring: Use an OS-specific keyring service.
 /// https://github.com/openai/codex/blob/main/codex-rs/rmcp-client/src/oauth.rs#L2
 /// file: Use a file in the Codex home directory.
 /// auto (default): Use the OS-specific keyring service if available, otherwise use a file.
 #[serde(default)]

## Excerpt 4: rmcp-client/src/oauth.rs: storage of MCP OAuth credentials
//! This file handles all logic related to managing MCP OAuth credentials.
//! All credentials are stored using the keyring crate which uses os-specific keyring services.
//! https://crates.io/crates/keyring
//! macOS: macOS keychain.
//! Windows: Windows Credential Manager
//! Linux: DBus-based Secret Service, the kernel keyutils, and a combo of the two
//! FreeBSD, OpenBSD: DBus-based Secret Service
//!
//! For Linux, we use linux-native-async-persistent which uses both keyutils and async-secret-service (see below) for storage.
//! See the docs for the keyutils_persistent module for a full explanation of why both are used. Because this store uses the
//! async-secret-service, you must specify the additional features required by that store
//!
//! async-secret-service provides access to the DBus-based Secret Service storage on Linux, FreeBSD, and OpenBSD. This is an asynchronous
//! keystore that always encrypts secrets when they are transferred across the bus. If DBus isn't installed the keystore will fall back to the json
