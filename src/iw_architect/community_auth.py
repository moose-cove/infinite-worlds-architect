"""Local, interactive authentication for the community catalogue tools."""

from __future__ import annotations

import argparse
import getpass
import json
import sys

import httpx
from websockets.sync.client import connect

from iw_architect.community import ORIGIN, AuthState, CommunityClient, CommunityError


def _login() -> None:
    email = input("Infinite Worlds email: ").strip()
    password = getpass.getpass("Infinite Worlds password: ")
    if not email or not password:
        raise CommunityError("Email and password are required")
    state = AuthState(email=email, password=password, cookies=[])
    with CommunityClient(state):
        pass
    print("Signed in. Credentials and the session are stored in your system keychain.")


def _import_chrome(port: int) -> None:
    """Copy an existing login once, without controlling the browser UI."""
    base = f"http://127.0.0.1:{port}"
    with httpx.Client(timeout=5) as http:
        tabs = http.get(base + "/json/list").json()
    tab = next(
        (t for t in tabs if t.get("type") == "page" and t.get("url", "").startswith(ORIGIN + "/")),
        None,
    )
    if not tab:
        raise CommunityError("No Infinite Worlds tab is available at that Chrome debugging port")
    with connect(tab["webSocketDebuggerUrl"], open_timeout=5, close_timeout=3) as ws:
        ws.send(json.dumps({"id": 1, "method": "Network.getCookies", "params": {"urls": [ORIGIN]}}))
        while True:
            message = json.loads(ws.recv(timeout=5))
            if message.get("id") == 1:
                break
    cookies = [
        {"name": c["name"], "value": c["value"], "domain": c["domain"], "path": c["path"]}
        for c in message.get("result", {}).get("cookies", [])
        if c.get("domain", "").lstrip(".") == "infiniteworlds.app"
    ]
    state = AuthState(email="", password="", cookies=cookies)
    with CommunityClient(state):
        pass
    print("Imported the signed-in session into your system keychain.")
    print("For automatic renewal after it expires, run `iw-community-auth login`.")


def _status() -> None:
    state = AuthState.load()
    if state is None:
        print("No Infinite Worlds login is stored.")
        return
    with CommunityClient(state):
        pass
    print("Infinite Worlds login is active.")
    if not state.password:
        print("Automatic renewal is unavailable. Run `iw-community-auth login` to enable it.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sign in for Infinite Worlds community tools")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("login", help="Sign in with email and password, with automatic renewal")
    imported = commands.add_parser("import-chrome", help="Import the current Chrome session once")
    imported.add_argument("--port", type=int, default=9222)
    commands.add_parser("status", help="Check the stored login")
    commands.add_parser("logout", help="Remove local credentials and session")
    args = parser.parse_args()
    try:
        if args.command == "login":
            _login()
        elif args.command == "import-chrome":
            _import_chrome(args.port)
        elif args.command == "status":
            _status()
        elif args.command == "logout":
            AuthState.delete()
            print("Local Infinite Worlds login removed.")
    except (CommunityError, httpx.HTTPError, OSError, TimeoutError) as exc:
        print(f"Authentication failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
