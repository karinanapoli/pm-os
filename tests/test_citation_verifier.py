from pm_os.citation_verifier import extract_source_ids, verify_citations


def test_extract_source_ids_uses_only_source_boundaries():
    context = """
<<<SOURCE id="SRC-A1B2C3D4" name="research.md" type="md">>>
Text mentions [SRC-FAKE000] but does not declare it.
<<<END SOURCE id="SRC-A1B2C3D4">>>
"""
    assert extract_source_ids(context) == {"SRC-A1B2C3D4"}


def test_verify_citations_accepts_only_supplied_ids():
    report = verify_citations(
        "Supported [SRC-A1B2C3D4]. Invented [SRC-DEADBEEF].",
        {"SRC-A1B2C3D4", "SRC-EEEEEEEE"},
    )
    assert report.status == "needs_review"
    assert report.valid_ids == ["SRC-A1B2C3D4"]
    assert report.invalid_ids == ["SRC-DEADBEEF"]
    assert report.missing_citations is False


def test_verify_citations_flags_missing_citations_when_sources_exist():
    report = verify_citations("A factual answer without evidence.", {"SRC-A1B2C3D4"})
    assert report.status == "needs_review"
    assert report.missing_citations is True


def test_verify_citations_marks_valid_output_as_verified():
    report = verify_citations(
        "Supported [src-a1b2c3d4] and repeated [SRC-A1B2C3D4].",
        {"SRC-A1B2C3D4"},
    )
    assert report.status == "verified"
    assert report.valid_ids == ["SRC-A1B2C3D4"]
    assert report.cited_ids == ["SRC-A1B2C3D4"]


def test_verify_citations_is_not_applicable_without_sources():
    report = verify_citations("Recommendation without context.", set())
    assert report.status == "not_applicable"
