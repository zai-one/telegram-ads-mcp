import inspect

import tg_ads_mcp.server as server_mod


def _tools():
    return server_mod.mcp._tool_manager.list_tools()


def test_tool_count_collapsed() -> None:
    names = sorted(t.name for t in _tools())
    assert "update_cookies" not in names
    assert "edit_ad_title" not in names
    assert "save_ads_columns" not in names
    assert "create_user_ad" not in names
    assert "reload_session" in names
    assert "launch_ad" in names
    assert "preview_ad" in names
    assert "get_account" in names
    assert "upload_media" in names
    assert 12 <= len(names) <= 28


def test_reload_session_has_no_cookie_args() -> None:
    assert list(inspect.signature(server_mod.reload_session).parameters) == []
    assert list(inspect.signature(server_mod.check_session).parameters) == []


def test_check_session_annotations_readonly() -> None:
    tools = {t.name: t for t in _tools()}
    anns = tools["check_session"].annotations
    assert anns is not None
    assert anns.read_only_hint is True
    dest = tools["delete_ad"].annotations
    assert dest is not None
    assert dest.destructive_hint is True
