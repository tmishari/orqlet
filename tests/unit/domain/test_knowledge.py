"""Pure rules of the knowledge-impact analysis: references, duplicates and copies."""

from __future__ import annotations

import pytest

from orqlet.domain.knowledge import (
    candidate,
    candidates_digest,
    longest_shared_run,
    markdown_references,
    near_duplicate,
)

pytestmark = pytest.mark.unit


def test_a_candidate_id_follows_from_what_it_is_about_and_nothing_else() -> None:
    first = candidate("reference", "src/a.py", "docs/a.md", "docs/a.md names src/a.py")
    again = candidate("reference", "src/a.py", "docs/a.md", "a different wording of the reason")
    other = candidate("reference", "src/b.py", "docs/a.md", "docs/a.md names src/b.py")

    assert first.id == again.id
    assert first.id != other.id
    assert first.id.startswith("cand-")


def test_the_digest_of_a_candidate_list_ignores_the_order() -> None:
    items = [candidate("public-symbol", name, None, "x") for name in ("a", "b", "c")]

    assert candidates_digest(items) == candidates_digest(list(reversed(items)))
    assert candidates_digest(items) != candidates_digest(items[:2])


def test_links_are_resolved_against_the_folder_of_the_document() -> None:
    text = "See [the service](../src/pkg/service.py#L10) and [guide](guide.md 'title')."

    refs = markdown_references("docs/knowledge/page.md", text)

    assert {"docs/src/pkg/service.py", "docs/knowledge/guide.md"} <= refs


def test_urls_anchors_absolute_paths_and_links_that_climb_out_are_not_references() -> None:
    text = (
        "[a](https://x.example/a) [b](#top) [c](/etc/passwd) "
        "[d](../../../outside.md) [e](mailto:x@y)"
    )

    assert markdown_references("docs/a.md", text) == frozenset()


def test_inline_code_and_orqlet_ref_blocks_name_paths_and_symbols_exactly() -> None:
    text = (
        "The code is in `src/pkg/service.py` and calls `pkg.service.create_order`.\n\n"
        "```orqlet-ref\nsrc/pkg/other.py\n\n  pkg.other.thing  \n```\n\n"
        "```python\nnot_a_reference()\n```\n"
    )

    refs = markdown_references("docs/a.md", text)

    assert refs == {
        "src/pkg/service.py",
        "pkg.service.create_order",
        "src/pkg/other.py",
        "pkg.other.thing",
    }


def test_a_prose_mention_is_not_found() -> None:
    assert (
        markdown_references("docs/a.md", "The file src/pkg/service.py does the work.")
        == frozenset()
    )


def test_near_duplicates_are_texts_that_share_most_of_their_word_five_grams() -> None:
    text = "the billing service computes the net price of an order from its lines and the tax rate"

    assert near_duplicate(text, text.upper() + ".")
    assert near_duplicate(text, text + " today")  # one extra word
    assert not near_duplicate(
        text, "a wholly different page about deployment and rollback steps today"
    )
    assert not near_duplicate("", text)


def test_a_short_text_compares_by_its_whole_word_list() -> None:
    assert near_duplicate("one two three", "One two three.")
    assert not near_duplicate("one two three", "one two four")


def test_the_longest_shared_run_counts_consecutive_non_empty_lines() -> None:
    draft = "intro\n\nline a\nline b\nline c\n\nlines that differ\n"
    source = "x\nline a\n\nline b\nline c\ny\n"

    assert longest_shared_run(draft, source) == 3  # blank lines and indentation do not count
    assert longest_shared_run("nothing in common", source) == 0
    assert longest_shared_run("  line a  \n    line b", source) == 2
