# serde-saphyr: deserializer options and budget

URL: https://github.com/bourumir-wyngs/serde-saphyr/blob/master/_autodocs/configuration.md
Retrieved: 2026-11-25T12:05:00Z
Tool: Context7 query-docs (/bourumir-wyngs/serde-saphyr)
Processed: unknown
Data class: public

1. Entry points (verbatim) - "For YAML bytes in memory: serde_saphyr::from_slice" ... "Custom parsing behavior: the corresponding *_with_options function"
2. Feature split (verbatim) - "Include only serialize or deserialize feature, as needed"
3. Duplicate keys (verbatim) - "duplicate_keys | `DuplicateKeyPolicy` | `Error` | Duplicate key policy"
4. Merge keys (verbatim) - "`MergeKeyPolicy::Error` rejects merge keys."
5. Tags (verbatim) - "reject_unsupported_tags | `bool` | `false` | Reject unsupported explicit YAML tags (`Error::UnsupportedTag`)"
6. Booleans (verbatim) - "strict_booleans | `bool` | `false` | Only `true`/`false` accepted as booleans"
7. Aliases, anchors and documents (verbatim) - "aliases and anchors are rejected by zeroing their counters (max_aliases: 0, max_anchors: 0), and enforcing exactly one YAML document is done with max_documents: 1."
8. Depth and nodes (verbatim) - "max_depth | `usize` | `64` | Max structural nesting depth" and "max_nodes | `usize` | `250,000` | Max nodes"
