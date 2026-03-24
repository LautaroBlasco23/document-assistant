from infrastructure.ingest.normalizer import _clean_whitespace, _strip_repeated_lines, normalize


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
