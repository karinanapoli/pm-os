from pm_os.web.product_docs_service import ProductDocsService


def test_personal_scopes_are_isolated(tmp_path):
    first = ProductDocsService(owner_email="first@example.com", root_dir=tmp_path)
    second = ProductDocsService(owner_email="second@example.com", root_dir=tmp_path)
    first.context_dir.mkdir(parents=True)
    (first.context_dir / "private.md").write_text("Private", encoding="utf-8")

    assert first.count_docs() == 1
    assert second.count_docs() == 0
    assert first.base_dir != second.base_dir


def test_squad_scope_is_shared_by_members(tmp_path):
    first_member = ProductDocsService(
        owner_email="first@example.com",
        squad_name="growth",
        root_dir=tmp_path,
    )
    second_member = ProductDocsService(
        owner_email="second@example.com",
        squad_name="growth",
        root_dir=tmp_path,
    )
    first_member.save_links([{"title": "Strategy", "url": "https://example.com"}])

    assert first_member.base_dir == second_member.base_dir
    assert second_member.load_links() == [
        {"title": "Strategy", "url": "https://example.com"}
    ]


def test_source_ids_include_scope(tmp_path):
    personal = ProductDocsService(owner_email="pm@example.com", root_dir=tmp_path)
    squad = ProductDocsService(squad_name="growth", root_dir=tmp_path)

    assert personal._source_id("document/brief.md") != squad._source_id("document/brief.md")


def test_migrates_legacy_single_user_library_without_deleting_original(tmp_path):
    legacy_context = tmp_path / "context"
    legacy_context.mkdir()
    (legacy_context / "guide.md").write_text("Legacy guide", encoding="utf-8")
    (tmp_path / "links.json").write_text(
        '[{"title": "Legacy", "url": "https://example.com"}]',
        encoding="utf-8",
    )
    scoped = ProductDocsService(owner_email="pm@example.com", root_dir=tmp_path)

    assert scoped.migrate_legacy_if_empty(tmp_path)
    assert (scoped.context_dir / "guide.md").read_text(encoding="utf-8") == "Legacy guide"
    assert scoped.load_links()[0]["title"] == "Legacy"
    assert (legacy_context / "guide.md").exists()


def test_document_operations_validate_name_extension_and_size(tmp_path):
    service = ProductDocsService(owner_email="pm@example.com", root_dir=tmp_path)

    assert service.save_document("brief.md", b"Product brief", max_bytes=100)
    assert not service.save_document("../escape.md", b"bad", max_bytes=100)
    assert not service.save_document("script.exe", b"bad", max_bytes=100)
    assert not service.save_document("large.md", b"x" * 101, max_bytes=100)
    assert service.list_doc_metadata() == [{"name": "brief.md", "size": "13 B"}]
    assert service.delete_document("brief.md")
    assert not service.delete_document("brief.md")


def test_link_operations_deduplicate_and_handle_corrupted_storage(tmp_path):
    service = ProductDocsService(owner_email="pm@example.com", root_dir=tmp_path)

    assert service.add_link("Strategy", "https://example.com/strategy")
    assert not service.add_link("Duplicate", "https://example.com/strategy")
    assert not service.add_link("", "")
    assert service.load_links() == [
        {"title": "Strategy", "url": "https://example.com/strategy"}
    ]
    assert service.delete_link("https://example.com/strategy")
    assert not service.delete_link("https://example.com/missing")

    (service.base_dir / "links.json").write_text("{broken", encoding="utf-8")
    assert service.load_links() == []
