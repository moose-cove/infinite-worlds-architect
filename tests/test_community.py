"""Protocol-focused tests for read-only Community Worlds access."""

from iw_architect.community import (
    AuthState,
    CommunityClient,
    _decode_search_rows,
    _make_query,
)


def _page(row_id: str, title: str, *, initial: bool) -> dict:
    table = {
        "spec": {
            "cols": [{"name": "uuid"}, {"name": "title"}, {"name": "description"}],
            "cache": [1, 1, 1],
        },
        "rows": {row_id: [f"uuid-{row_id}", title, "A description", None]},
    }
    response = [[row_id], None, None, {"view": table}] if initial else [
        [row_id], None, {"view": table}
    ]
    cap_paths = [["response", 1], ["response", 2]] if initial else [["response", 1]]
    return {
        "response": response,
        "objects": [
            {"path": path, "type": ["Capability"], "scope": ["t"], "mac": "test"}
            for path in cap_paths
        ],
    }


def test_query_serializes_nested_filters_in_postorder():
    query, descriptors = _make_query(
        "hero", ["modern_day", "romance"], ["mind control"], True, True, False
    )
    assert query is not None
    names = [item["typeName"] for item in descriptors]
    assert names.count("anvil.tables.query.ilike") == 6
    assert "anvil.tables.query.none_of" in names
    assert names[-1] == "anvil.tables.query.all_of"
    for index, descriptor in enumerate(descriptors):
        if descriptor["typeName"] == "anvil.tables.query.ilike":
            parent_path = descriptor["path"][:-2]
            assert any(
                later["path"] == parent_path for later in descriptors[index + 1 :]
            )
    assert "% modern-day %" in str(query)
    assert "% mind-control %" in str(query)


def test_include_tags_can_match_any():
    query, descriptors = _make_query("", ["romance", "superhero"], [], False, None, None)
    assert query["args"]
    assert descriptors[-1]["typeName"] == "anvil.tables.query.any_of"


def test_search_decodes_initial_and_next_page():
    client = CommunityClient(AuthState("", "", []))
    first = _page("1", "First", initial=True)
    second = _page("2", "Second", initial=False)
    third = _page("3", "Third", initial=False)
    calls = []
    replies = iter([first, {"response": 3}, second, third])
    client._view_capability = lambda: {"path": ["args", 0], "type": ["Capability"]}

    def fake_call(command, args, objects=None, kwargs=None):
        calls.append(command)
        return next(replies)

    client.call = fake_call
    result = client.search(text="hero", page=3, page_size=1)
    assert result["total"] == 3
    assert [world["title"] for world in result["worlds"]] == ["Third"]
    assert calls == [
        "anvil.private.tables.v2.table.search",
        "anvil.private.tables.v2.search.get_length",
        "anvil.private.tables.v2.search.next_page",
        "anvil.private.tables.v2.search.next_page",
    ]
    assert _decode_search_rows(first)[0]["description"] == "A description"


def test_expired_session_uses_stored_credentials():
    client = CommunityClient(AuthState("user@example.com", "secret", []))
    calls = []
    users = iter([None, ["user"]])

    def fake_call(command, args, objects=None, kwargs=None):
        calls.append((command, args))
        if command == "anvil.private.users.get_current_user":
            return {"response": next(users)}
        return {"response": ["user"]}

    client.call = fake_call
    client._ensure_login()
    assert [name for name, _ in calls] == [
        "anvil.private.users.get_current_user",
        "anvil.private.users.login_with_email",
        "anvil.private.users.get_current_user",
    ]
    assert calls[1][1] == ["user@example.com", "secret"]
