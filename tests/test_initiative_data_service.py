from pm_os.web.initiative_data_service import InitiativeDataService


def test_adds_csv_metadata_without_storing_cell_contents(tmp_path):
    service = InitiativeDataService()
    result = service.add_spreadsheet(
        tmp_path, "metricas.csv", b"week,conversion\n1,20\n2,24\n"
    )
    assert result["rows"] == 2
    assert result["columns"] == 2
    assert service.list_spreadsheets(tmp_path)[0]["name"] == "metricas.csv"
    assert "conversion" not in (tmp_path / "data-sources" / "spreadsheets.json").read_text()


def test_rejects_unsupported_spreadsheet(tmp_path):
    service = InitiativeDataService()
    try:
        service.add_spreadsheet(tmp_path, "metricas.xlsx", b"not-an-xlsx")
    except ValueError as error:
        assert str(error) == "unsupported_spreadsheet"
    else:
        raise AssertionError("unsupported file should be rejected")


def test_registers_external_automation(tmp_path):
    service = InitiativeDataService()
    result = service.register_automation(
        tmp_path, name="Coletar métricas", tool="VS Code", description="Diária"
    )
    assert result["status"] == "connected"
    assert service.list_automations(tmp_path)[0]["tool"] == "VS Code"
