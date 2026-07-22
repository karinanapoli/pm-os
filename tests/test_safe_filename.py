from pm_os.web.app import _safe_filename


def test_normal_filename():
    assert _safe_filename("readme.md") == "readme.md"
    assert _safe_filename("document.txt") == "document.txt"


def test_rejects_directory():
    assert _safe_filename("path/to/file.md") == ""
    assert _safe_filename("subdir/file.txt") == ""


def test_rejects_traversal():
    assert _safe_filename("..") == ""
    assert _safe_filename("../..") == ""
    assert _safe_filename("../../etc/passwd") == ""
    assert _safe_filename("../context/secret.md") == ""


def test_rejects_absolute_path():
    assert _safe_filename("/etc/passwd") == ""
    assert _safe_filename("/readme.md") == ""


def test_empty_string():
    assert _safe_filename("") == ""


def test_special_chars():
    assert _safe_filename("file with spaces.md") == "file with spaces.md"
    assert _safe_filename("document (1).txt") == "document (1).txt"
    assert _safe_filename("some_file-v2.md") == "some_file-v2.md"
