# The /llms.txt file, v2 - llms-txt
URL: https://llmstxt.org/
Retrieved: 2026-10-26T16:04Z (workstation clock, UTC) through the WebFetch tool. The excerpts below are verbatim; the label of each says where it sits on the page.

## Excerpt 1: Proposal
We propose adding a `/llms.txt` markdown file to websites to provide LLM-friendly content. The file can be placed at the site root, or at any path within it, covering the pages under that path. This file offers brief background information, guidance, and links to detailed markdown files.

## Excerpt 2: How agents use it
Agents are expected to view or search `llms.txt` to find the information they need, then follow the relevant links. The links in an llms.txt file should therefore point to LLM-friendly content, such as the markdown versions of pages described above. The file itself stays small enough to fit in context. The detail lives behind the links, and is fetched only when needed.

## Excerpt 3: Format
- An H1 with the name of the project or site. This is the only required section
- A blockquote with a short summary of the project, containing key information necessary for understanding the rest of the file
- Zero or more markdown sections delimited by H2 headers, containing “file lists” of URLs where further detail is available 

- Each “file list” is a markdown list, containing a required markdown hyperlink `[name](url)`, then optionally a `:` and notes about the file.
