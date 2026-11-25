# Clippy: configuration lookup and disallowed types and methods

URL: https://github.com/rust-lang/rust-clippy/blob/main/book/src/configuration.md
Retrieved: 2026-11-25T12:07:00Z
Tool: Context7 query-docs (/rust-lang/rust-clippy)
Processed: unknown
Data class: public

1. Lookup order (verbatim) - "1. The directory specified by the `CLIPPY_CONF_DIR` environment variable, or 2. The directory specified by the CARGO_MANIFEST_DIR environment variable, or 3. The current directory."
2. Walk up (verbatim) - "If the chosen directory does not contain a configuration file, Clippy will walk up the directory tree"
3. disallowed-types (verbatim, from lint_configuration.md) - "The list of disallowed types, written as fully qualified paths."
4. disallowed-methods (verbatim, from lint_configuration.md) - "The list of disallowed methods, written as fully qualified paths."
