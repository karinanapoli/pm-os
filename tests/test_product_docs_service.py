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
