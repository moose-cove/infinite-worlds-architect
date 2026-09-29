"""Read-only Infinite Worlds community catalogue client.

The site uses Anvil's private WebSocket RPC protocol. This module deliberately
keeps that protocol behind one client so changes to the site fail clearly.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx
import keyring
from websockets.sync.client import ClientConnection, connect

ORIGIN = "https://infiniteworlds.app"
KEYRING_SERVICE = "infinite-worlds-architect"
KEYRING_USER = "community-worlds"
_TOKEN_RE = re.compile(r'window\.anvilSessionToken\s*=\s*("(?:\\.|[^"\\])*")')
_FIELDS = (
    "uuid",
    "reference_code",
    "title",
    "author_name",
    "description",
    "tag_display",
    "content_warnings",
    "mature",
    "nsfw",
    "turns_played",
    "trending_score",
    "created_at",
    "last_updated_at",
    "version",
)
_SORTS = {
    "most_played": ("turns_played", False),
    "trending": ("trending_score", False),
    "newest": ("created_at", False),
    "alphabetical": ("title", True),
}


class CommunityError(RuntimeError):
    """A user-facing catalogue or authentication failure."""


@dataclass
class AuthState:
    email: str
    password: str
    cookies: list[dict[str, str]]

    @classmethod
    def load(cls) -> AuthState | None:
        raw = keyring.get_password(KEYRING_SERVICE, KEYRING_USER)
        if not raw:
            return None
        data = json.loads(raw)
        return cls(data.get("email", ""), data.get("password", ""), data.get("cookies", []))

    def save(self) -> None:
        keyring.set_password(
            KEYRING_SERVICE,
            KEYRING_USER,
            json.dumps({"email": self.email, "password": self.password, "cookies": self.cookies}),
        )

    @staticmethod
    def delete() -> None:
        try:
            keyring.delete_password(KEYRING_SERVICE, KEYRING_USER)
        except keyring.errors.PasswordDeleteError:
            pass


def _cookie_records(client: httpx.Client) -> list[dict[str, str]]:
    return [
        {"name": c.name, "value": c.value, "domain": c.domain, "path": c.path}
        for c in client.cookies.jar
        if c.domain.lstrip(".") == "infiniteworlds.app"
    ]


def _cookie_header(cookies: list[dict[str, str]]) -> str:
    return "; ".join(f"{c['name']}={c['value']}" for c in cookies)


def _restore_cookies(client: httpx.Client, cookies: list[dict[str, str]]) -> None:
    for c in cookies:
        client.cookies.set(c["name"], c["value"], domain=c["domain"], path=c["path"])


def _bootstrap(client: httpx.Client) -> str:
    response = client.get(ORIGIN + "/")
    response.raise_for_status()
    match = _TOKEN_RE.search(response.text)
    if not match:
        raise CommunityError("Infinite Worlds did not provide an Anvil session token")
    token = json.loads(match.group(1))
    return "wss://infiniteworlds.app/_/ws/?_anvil_session=" + quote(token, safe="")


def _rpc(
    ws: ClientConnection,
    command: str,
    args: list[Any],
    objects: list[dict] | None = None,
    kwargs: dict[str, Any] | None = None,
) -> dict:
    request_id = "iw-community-1"
    ws.send(
        json.dumps(
            {
                "type": "CALL",
                "id": request_id,
                "command": command,
                "args": args,
                "kwargs": kwargs or {},
                "objects": objects or [],
            }
        )
    )
    while True:
        reply = json.loads(ws.recv(timeout=30))
        if reply.get("id") != request_id:
            continue
        error = reply.get("error")
        if error:
            kind = error.get("type", "unknown error")
            message = error.get("message", "")
            raise CommunityError(f"Infinite Worlds returned {kind}: {message}")
        return reply


class CommunityClient:
    """One authenticated direct connection to the Infinite Worlds server."""

    def __init__(self, state: AuthState):
        self.state = state
        self.http = httpx.Client(timeout=20, follow_redirects=True)
        _restore_cookies(self.http, state.cookies)
        self.ws: ClientConnection | None = None

    def __enter__(self) -> CommunityClient:
        try:
            self._open_socket()
            try:
                self._ensure_login()
            except CommunityError as exc:
                if "SessionExpiredError" not in str(exc) or not self.state.password:
                    raise
                self.ws.close()
                self.http.cookies.clear()
                self._open_socket()
                self._ensure_login()
            self.state.cookies = _cookie_records(self.http)
            self.state.save()
            return self
        except Exception:
            self.__exit__()
            raise

    def _open_socket(self) -> None:
        url = _bootstrap(self.http)
        cookies = _cookie_records(self.http)
        self.ws = connect(
            url,
            additional_headers={"Cookie": _cookie_header(cookies)},
            open_timeout=20,
            close_timeout=3,
            max_size=32 * 1024 * 1024,
        )

    def __exit__(self, *_: object) -> None:
        if self.ws:
            self.ws.close()
        self.http.close()

    def call(
        self,
        command: str,
        args: list[Any],
        objects: list[dict] | None = None,
        kwargs: dict[str, Any] | None = None,
    ) -> dict:
        if not self.ws:
            raise CommunityError("Community connection is not open")
        return _rpc(self.ws, command, args, objects, kwargs)

    def _ensure_login(self) -> None:
        current = self.call(
            "anvil.private.users.get_current_user",
            [],
            kwargs={"allow_remembered": True, "fetch": None},
        )
        if current.get("response") is not None:
            return
        if not self.state.email or not self.state.password:
            raise CommunityError(
                "Community session expired. Run `iw-community-auth login` to renew it."
            )
        self.call(
            "anvil.private.users.login_with_email",
            [self.state.email, self.state.password],
            kwargs={"remember": True, "mfa": None, "fetch": None},
        )
        current = self.call(
            "anvil.private.users.get_current_user",
            [],
            kwargs={"allow_remembered": True, "fetch": None},
        )
        if current.get("response") is None:
            raise CommunityError("Infinite Worlds did not accept the login")

    def _view_capability(self) -> dict:
        reply = self.call("initialise_views", [["CommunityWorld"], 1])
        for obj in reply.get("objects", []):
            if obj.get("type") == ["Capability"] and obj.get("path") == [
                "response",
                "CommunityWorld",
                "view",
                0,
            ]:
                return {**obj, "path": ["args", 0]}
        raise CommunityError("Community view capability was missing")

    def search(
        self,
        *,
        text: str = "",
        include_tags: list[str] | None = None,
        exclude_tags: list[str] | None = None,
        match_all_tags: bool = True,
        mature: bool | None = None,
        nsfw: bool | None = None,
        sort: str = "most_played",
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        if sort not in _SORTS:
            raise ValueError(f"sort must be one of {', '.join(_SORTS)}")
        if page < 1 or not 1 <= page_size <= 100:
            raise ValueError("page must be positive and page_size must be 1-100")
        query, query_objects = _make_query(
            text, include_tags or [], exclude_tags or [], match_all_tags, mature, nsfw
        )
        column, ascending = _SORTS[sort]
        search_args: list[Any] = [
            None,
            [{"rows": page_size}, {"column_name": column, "ascending": ascending}],
            {},
        ]
        objects = [
            self._view_capability(),
            _value_type(["args", 1, 0], "anvil.tables.query.page_size"),
            _value_type(["args", 1, 1], "anvil.tables.order_by"),
        ]
        if query is not None:
            search_args[1].append(query)
            objects.extend(query_objects)
        reply = self.call("anvil.private.tables.v2.table.search", search_args, objects)
        total_cap = _find_cap(reply, ["response", 1], ["args", 0])
        total_reply = self.call("anvil.private.tables.v2.search.get_length", [None], [total_cap])
        total = total_reply["response"]
        for index in range(page - 1):
            cap_index = 2 if index == 0 else 1
            next_cap = _find_cap(
                reply, ["response", cap_index], ["args", 0], required=False
            )
            if next_cap is None:
                return {"total": total, "page": page, "page_size": page_size, "worlds": []}
            reply = self.call("anvil.private.tables.v2.search.next_page", [None], [next_cap])
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "worlds": _decode_search_rows(reply),
        }

    def world_details(self, world_id: str) -> dict:
        return self._find_world(world_id)

    def world_json(self, world_id: str) -> dict:
        record = self._find_world(world_id)
        reply = self.call("fetch_world_by_uuid", ["CommunityWorld", record["uuid"]])
        data = reply.get("vt_global", [None, {}])[1]
        for table in data.values():
            columns = [col["name"] for col in table.get("spec", {}).get("cols", [])]
            if "adventure" not in columns:
                continue
            index = columns.index("adventure")
            for row in table.get("rows", {}).values():
                adventure = row[index]
                if isinstance(adventure, dict):
                    return adventure
        raise CommunityError("The world's JSON was not available to this account")

    def _find_world(self, world_id: str) -> dict:
        world_id = world_id.strip()
        if not world_id:
            raise ValueError("world_id is required")
        if world_id.startswith(ORIGIN + "/shared/"):
            world_id = world_id.split("/shared/", 1)[1].split("?", 1)[0].strip("/")
        cap = self._view_capability()
        column = "uuid" if re.fullmatch(r"[0-9a-f]{32}", world_id, re.I) else "reference_code"
        args = [None, [{"rows": 2}], {column: world_id}]
        reply = self.call(
            "anvil.private.tables.v2.table.search",
            args,
            [cap, _value_type(["args", 1, 0], "anvil.tables.query.page_size")],
        )
        rows = _decode_search_rows(reply)
        if not rows:
            raise CommunityError(f"Community world {world_id!r} was not found")
        return rows[0]


def _value_type(path: list[Any], name: str) -> dict:
    return {"path": path, "type": ["ValueType"], "typeName": name}


def _find_cap(
    reply: dict, source_path: list[Any], target_path: list[Any], required: bool = True
) -> dict | None:
    for obj in reply.get("objects", []):
        if obj.get("type") == ["Capability"] and obj.get("path") == source_path:
            return {**obj, "path": target_path}
    if required:
        raise CommunityError("Infinite Worlds did not provide a pagination capability")
    return None


def _normalise_tag(tag: str) -> str:
    return re.sub(r"\s+", "-", tag.strip().lower().replace("_", "-"))


def _make_query(
    text: str,
    include_tags: list[str],
    exclude_tags: list[str],
    match_all_tags: bool,
    mature: bool | None,
    nsfw: bool | None,
) -> tuple[dict | None, list[dict]]:
    """Build Anvil query values and postordered ValueType descriptors."""
    clauses: list[tuple[str, dict]] = []
    if text.strip():
        pattern = f"%{text.strip()}%"
        clauses.append(
            (
                "any_of",
                {
                    "args": [],
                    "kwargs": {
                        field: ("ilike", {"pattern": pattern})
                        for field in ("title", "description", "author_name")
                    },
                },
            )
        )
    tag_clauses = []
    for tag in include_tags:
        slug = _normalise_tag(tag)
        if slug:
            tag_clauses.append(
                (
                    "all_of",
                    {
                        "args": [],
                        "kwargs": {"tag_search_text": ("ilike", {"pattern": f"% {slug} %"})},
                    },
                )
            )
    if match_all_tags or len(tag_clauses) < 2:
        clauses.extend(tag_clauses)
    else:
        clauses.append(("any_of", {"args": tag_clauses, "kwargs": {}}))
    for tag in exclude_tags:
        slug = _normalise_tag(tag)
        if slug:
            child = (
                "all_of",
                {"args": [], "kwargs": {"tag_search_text": ("ilike", {"pattern": f"% {slug} %"})}},
            )
            clauses.append(("none_of", {"args": [child], "kwargs": {}}))
    filters = {}
    if mature is not None:
        filters["mature"] = mature
    if nsfw is not None:
        filters["nsfw"] = nsfw
    if filters:
        clauses.append(("all_of", {"args": [], "kwargs": filters}))
    if not clauses:
        return None, []
    root = clauses[0] if len(clauses) == 1 else ("all_of", {"args": clauses, "kwargs": {}})
    descriptors: list[dict] = []

    def encode(node: Any, path: list[Any]) -> Any:
        if not isinstance(node, tuple):
            return node
        kind, value = node
        if kind == "ilike":
            descriptors.append(_value_type(path, "anvil.tables.query.ilike"))
            return value
        encoded = {
            "args": [encode(child, [*path, "args", i]) for i, child in enumerate(value["args"])],
            "kwargs": {
                key: encode(child, [*path, "kwargs", key]) for key, child in value["kwargs"].items()
            },
        }
        descriptors.append(_value_type(path, f"anvil.tables.query.{kind}"))
        return encoded

    return encode(root, ["args", 1, 2]), descriptors


def _decode_search_rows(reply: dict) -> list[dict]:
    response = reply.get("response")
    if not isinstance(response, list) or len(response) not in (3, 4):
        raise CommunityError("Infinite Worlds returned an unexpected search response")
    row_ids, table_data = response[0], response[-1]
    table = next(
        (
            value
            for value in table_data.values()
            if "uuid" in [c["name"] for c in value.get("spec", {}).get("cols", [])]
        ),
        None,
    )
    if table is None:
        return []
    columns = [c["name"] for c in table["spec"]["cols"]]
    cache = table["spec"].get("cache", [1] * len(columns))
    cached_columns = [name for name, cached in zip(columns, cache, strict=True) if cached]
    worlds = []
    for row_id in row_ids:
        row = table["rows"].get(str(row_id))
        if row is None:
            continue
        raw = dict(zip(cached_columns, row, strict=False))
        worlds.append({field: raw.get(field) for field in _FIELDS})
    return worlds


def search_community_worlds(
    text: str = "",
    include_tags: list[str] | None = None,
    exclude_tags: list[str] | None = None,
    match_all_tags: bool = True,
    mature: bool | None = None,
    nsfw: bool | None = None,
    sort: str = "most_played",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Search Community Worlds by text and tags, with independent include/exclude filters.

    `text` searches title, description, and author. Tags may be names or slugs.
    `match_all_tags=False` matches any included tag; the default requires all.
    `mature` and `nsfw` are tri-state filters: None includes both values.
    Sort: most_played, trending, newest, alphabetical. Pages start at 1.
    """
    state = AuthState.load()
    if state is None:
        raise CommunityError("Run `uv run python -m iw_architect.community_auth login` first")
    with CommunityClient(state) as client:
        return client.search(
            text=text,
            include_tags=include_tags,
            exclude_tags=exclude_tags,
            match_all_tags=match_all_tags,
            mature=mature,
            nsfw=nsfw,
            sort=sort,
            page=page,
            page_size=page_size,
        )


def get_community_world_details(world_id: str) -> dict:
    """Get one Community World's description and catalog metadata by code or UUID."""
    state = AuthState.load()
    if state is None:
        raise CommunityError("Run `uv run python -m iw_architect.community_auth login` first")
    with CommunityClient(state) as client:
        return client.world_details(world_id)


def get_community_world_json(world_id: str) -> dict:
    """Read the original world JSON by community code or UUID, without copying it."""
    state = AuthState.load()
    if state is None:
        raise CommunityError("Run `uv run python -m iw_architect.community_auth login` first")
    with CommunityClient(state) as client:
        return client.world_json(world_id)
