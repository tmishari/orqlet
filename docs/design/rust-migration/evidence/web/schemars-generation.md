# Schemars: generating JSON Schema from Rust types

URL: https://github.com/gresau/schemars/blob/master/README.md
Retrieved: 2026-11-25T12:05:30Z
Tool: Context7 query-docs (/gresau/schemars)
Processed: unknown
Data class: public

1. Serde compatibility (verbatim) - "Shows how Schemars respects Serde attributes like rename_all, deny_unknown_fields, rename, default, and untagged when generating a JSON schema."
2. Closed objects (verbatim) - the generated schema for a type with deny_unknown_fields holds "\"additionalProperties\": false".
3. Macro (verbatim) - "let schema = schema_for!(MyStruct);"
4. Draft (verbatim, from docs/3-generating.md) - "This will create a schema that conforms to JSON Schema 2020-12, but this is liable to change in a future version of Schemars"
