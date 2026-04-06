from infrastructure.ingest.normalizer import (
    _clean_whitespace,
    _dedupe_consecutive_paragraphs,
    _dehyphenate,
    _rebuild_paragraphs,
    _strip_repeated_lines,
    _strip_separator_lines,
    clean_text,
    normalize,
)


def test_clean_whitespace_collapses_spaces():
    result = _clean_whitespace("hello   world\t!")
    assert result == "hello world !"


def test_clean_whitespace_strips_trailing():
    result = _clean_whitespace("line   \nanother  ")
    assert "   " not in result


def test_normalize_empty():
    assert normalize([]) == []


def test_normalize_single_page():
    result = normalize(["hello   world"])
    assert result == ["hello world"]


def test_strip_repeated_header():
    # "HEADER" appears on every page -> should be stripped
    pages = [f"HEADER\nbody text {i}\nFOOTER" for i in range(10)]
    result = _strip_repeated_lines(pages)
    for page in result:
        assert "HEADER" not in page
        assert "FOOTER" not in page


def test_no_strip_below_threshold():
    # Line appears on only 2 of 20 pages -> below 30% threshold
    pages = [f"body text {i}" for i in range(20)]
    pages[0] = "RARE_LINE\n" + pages[0]
    pages[1] = "RARE_LINE\n" + pages[1]
    result = _strip_repeated_lines(pages)
    assert any("RARE_LINE" in p for p in result)


# --- clean_text() and helpers ---


def test_dehyphenate_simple():
    result = _dehyphenate("know-\nledge")
    assert result == "knowledge"


def test_dehyphenate_only_when_dehyphenate_true():
    # With dehyphenate=False the hyphen+newline should remain
    result = clean_text("know-\nledge", dehyphenate=False)
    # After _rebuild_paragraphs, the hyphen-newline is inside one block and
    # the newline collapses to a space: "know- ledge"
    assert "know-" in result


def test_strip_separator_lines_dashes():
    # 6 dashes -> removed; 3 dashes -> kept
    text = "intro\n------\nconclusion\n---\nend"
    result = _strip_separator_lines(text)
    assert "------" not in result
    assert "---" in result


def test_strip_separator_lines_em_dash():
    # 7 em-dashes -> removed
    text = "before\n\u2014\u2014\u2014\u2014\u2014\u2014\u2014\nafter"
    result = _strip_separator_lines(text)
    assert "\u2014\u2014\u2014\u2014\u2014\u2014\u2014" not in result
    assert "before" in result
    assert "after" in result


def test_strip_separator_lines_mixed_unaffected():
    # Mixed chars like --==-- do not match (chars differ) -> preserved
    text = "text\n--==--\nmore"
    result = _strip_separator_lines(text)
    assert "--==--" in result


def test_rebuild_paragraphs_joins_softwrapped():
    # Three layout lines forming one paragraph (no double newline)
    text = "This is\nthe first\nsentence."
    result = _rebuild_paragraphs(text)
    assert result == "This is the first sentence."


def test_rebuild_paragraphs_respects_double_newline():
    result = _rebuild_paragraphs("a\n\nb")
    assert result == "a\n\nb"


def test_rebuild_paragraphs_handles_blank_whitespace_lines():
    # A line with only spaces should act as a paragraph break
    result = _rebuild_paragraphs("a\n   \nb")
    assert result == "a\n\nb"


def test_dedupe_consecutive_paragraphs():
    result = _dedupe_consecutive_paragraphs("foo\n\nfoo\n\nbar")
    assert result == "foo\n\nbar"


def test_dedupe_keeps_non_adjacent_duplicates():
    # foo appears twice but not consecutively -> both kept
    result = _dedupe_consecutive_paragraphs("foo\n\nbar\n\nfoo")
    assert result == "foo\n\nbar\n\nfoo"


def test_clean_text_full_pipeline():
    # Input: hyphenated line break, separator line, soft-wrapped paragraph, duplicate
    text = (
        "know-\nledge is power.\n\n"
        "------\n\n"
        "This is a\nsoft-wrapped paragraph.\n\n"
        "This is a\nsoft-wrapped paragraph."
    )
    result = clean_text(text, dehyphenate=True)
    # Hyphen joined: "knowledge" appears in result
    assert "knowledge" in result
    # Separator removed
    assert "------" not in result
    # Duplicate paragraph removed (appears only once)
    assert result.count("soft-wrapped paragraph.") == 1
