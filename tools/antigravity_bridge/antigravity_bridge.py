#!/usr/bin/env python3
"""Desktop bridge connecting Google Antigravity sessions to the Badgeware hardware badge."""

import argparse
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request


DEFAULT_CONFIG_PATH = Path.home() / ".gemini" / "antigravity_badge.json"
LOCAL_CONFIG_PATH = Path(".antigravity_badge.json")


def load_config(config_path=None):
    paths = [Path(config_path)] if config_path else [LOCAL_CONFIG_PATH, DEFAULT_CONFIG_PATH]
    for path in paths:
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f), path
            except Exception:
                pass
    return None, paths[0]


def save_config(data, config_path=None):
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return path


def post_badge(endpoint, body, config, timeout=3.0):
    host = config.get("host", "127.0.0.1")
    port = config.get("port", 80)
    token = config.get("token")
    url = f"http://{host}:{port}{endpoint}"

    data = body.encode("utf-8") if isinstance(body, str) else body
    req = urllib.request.Request(url, data=data, method="POST")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    if endpoint == "/pair":
        req.add_header("Content-Type", "text/plain")
    else:
        req.add_header("Content-Type", "application/octet-stream")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(content)
            except Exception:
                return resp.status, content
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="ignore")
        return e.code, err_msg
    except Exception as e:
        return 0, str(e)


def get_status(config, timeout=3.0):
    host = config.get("host", "127.0.0.1")
    port = config.get("port", 80)
    token = config.get("token")
    url = f"http://{host}:{port}/status"

    req = urllib.request.Request(url, method="GET")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return 0, str(e)


def cmd_pair(args):
    url = f"http://{args.host}:{args.port}/pair"
    code = args.code.strip()
    print(f"Attempting to pair with badge at {args.host}:{args.port} using code {code}...")

    req = urllib.request.Request(url, data=code.encode("utf-8"), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            token = res.get("token")
            device_id = res.get("deviceId")
            if token and device_id:
                cfg = {
                    "host": args.host,
                    "port": args.port,
                    "deviceId": device_id,
                    "token": token
                }
                saved_to = save_config(cfg, args.config)
                print(f"SUCCESS: Paired with badge! Device ID: {device_id}")
                print(f"Configuration saved to {saved_to}")
                return 0
            print("Pairing response missing token or deviceId:", res)
            return 1
    except Exception as e:
        print(f"Pairing failed: {e}")
        return 1


def cmd_state(args, config):
    status, res = post_badge("/state", args.state + "\n", config)
    if status == 200:
        print(f"State set to '{args.state}'")
        return 0
    print(f"Failed to set state ({status}): {res}")
    return 1


def cmd_agents(args, config):
    packet = f"&{args.agents}\n"
    status, res = post_badge("/agents", packet, config)
    if status == 200:
        print(f"Agents set to '{args.agents}'")
        return 0
    print(f"Failed to set agents ({status}): {res}")
    return 1


def cmd_usage(args, config):
    packet = f"${args.usage}\n"
    status, res = post_badge("/usage", packet, config)
    if status == 200:
        print(f"Usage set to '{args.usage}'")
        return 0
    print(f"Failed to set usage ({status}): {res}")
    return 1


def cmd_hook(args, config, input_data=None):
    """Lifecycle hook handler receiving Antigravity JSON on stdin."""
    raw_input = input_data
    if raw_input is None and getattr(args, "read_stdin", False):
        try:
            raw_input = sys.stdin.read()
        except Exception:
            pass

    hook_type = args.hook_type
    target_state = "working"

    if hook_type == "pre_invocation":
        target_state = "working"
    elif hook_type == "pre_tool_use":
        target_state = "attention"
        if raw_input:
            try:
                data = json.loads(raw_input)
                tool_name = data.get("toolCall", {}).get("name", "tool")
                post_badge("/agents", f"&{tool_name[:12]}=a\n", config)
            except Exception:
                pass
    elif hook_type == "post_tool_use":
        target_state = "working"
    elif hook_type == "stop":
        target_state = "complete"

    post_badge("/state", target_state + "\n", config)
    # Hooks must return valid JSON on stdout
    print("{}")
    return 0


def cmd_watch(args, config):
    """Tail an active Antigravity transcript.jsonl and mirror state to the badge."""
    transcript_path = args.transcript
    if not transcript_path:
        # Search common Antigravity AppData transcript directories
        appdata = os.environ.get("LOCALAPPDATA") or str(Path.home())
        candidates = list(Path(appdata).glob("**/antigravity/**/transcript.jsonl"))
        if candidates:
            # Pick the most recently modified transcript
            candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            transcript_path = candidates[0]
            print(f"Auto-detected active transcript: {transcript_path}")
        else:
            print("No active transcript.jsonl found. Specify --transcript <path> manually.")
            return 1

    transcript_path = Path(transcript_path)
    print(f"Watching {transcript_path} for session events...")
    last_size = transcript_path.stat().st_size if transcript_path.exists() else 0

    while True:
        try:
            time.sleep(0.5)
            if not transcript_path.exists():
                continue
            curr_size = transcript_path.stat().st_size
            if curr_size > last_size:
                with open(transcript_path, "r", encoding="utf-8", errors="ignore") as f:
                    f.seek(last_size)
                    new_lines = f.readlines()
                    last_size = f.tell()
                for line in new_lines:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        step = json.loads(line)
                        step_type = step.get("type", "")
                        status = step.get("status", "")
                        if step_type == "USER_INPUT":
                            post_badge("/state", "working\n", config)
                        elif "tool_calls" in step and step["tool_calls"]:
                            post_badge("/state", "attention\n", config)
                        elif step_type == "PLANNER_RESPONSE" and status == "DONE":
                            post_badge("/state", "complete\n", config)
                    except Exception:
                        pass
        except KeyboardInterrupt:
            print("\nStopped watcher.")
            break
        except Exception as e:
            time.sleep(1.0)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, help="Path to pairing config JSON")

    subparsers = parser.add_subparsers(dest="command")

    # pair
    pair_parser = subparsers.add_parser("pair", help="Pair with a badge displaying an 8-digit code")
    pair_parser.add_argument("code", help="8-digit pairing code shown on badge")
    pair_parser.add_argument("--host", required=True, help="IP address of the badge")
    pair_parser.add_argument("--port", type=int, default=80, help="HTTP port (default 80)")

    # state
    state_parser = subparsers.add_parser("state", help="Set the badge state")
    state_parser.add_argument("state", choices=["idle", "working", "attention", "complete", "surprise"],
                              help="Mascot mood/state")

    # agents
    agents_parser = subparsers.add_parser("agents", help="Set active agent indicators")
    agents_parser.add_argument("agents", help="Agent string, e.g. 'antigravity=w,linter=a'")

    # usage
    usage_parser = subparsers.add_parser("usage", help="Set usage lines")
    usage_parser.add_argument("usage", help="Usage text, e.g. 'Tokens: 12k|Steps: 4'")

    # status
    subparsers.add_parser("status", help="Query badge status and connection")

    # hook
    hook_parser = subparsers.add_parser("hook", help="Antigravity lifecycle hook runner")
    hook_parser.add_argument("hook_type", choices=["pre_invocation", "pre_tool_use", "post_tool_use", "stop"],
                             help="Lifecycle hook event name")
    hook_parser.add_argument("--read-stdin", action="store_true", help="Read hook payload from stdin")

    # watch
    watch_parser = subparsers.add_parser("watch", help="Watch transcript.jsonl and stream events")
    watch_parser.add_argument("--transcript", type=Path, help="Path to transcript.jsonl")

    args = parser.parse_args()

    if args.command == "pair":
        return cmd_pair(args)

    config, _ = load_config(args.config)

    if args.command == "status":
        if not config:
            print("No badge pairing found. Run 'pair' first.")
            return 1
        st, res = get_status(config)
        print(f"Status ({st}): {res}")
        return 0 if st == 200 else 1

    if args.command == "state":
        if not config:
            print("No badge pairing found. Run 'pair' first.")
            return 1
        return cmd_state(args, config)

    if args.command == "agents":
        if not config:
            print("No badge pairing found. Run 'pair' first.")
            return 1
        return cmd_agents(args, config)

    if args.command == "usage":
        if not config:
            print("No badge pairing found. Run 'pair' first.")
            return 1
        return cmd_usage(args, config)

    if args.command == "hook":
        if not config:
            # Hooks must not crash or block agent if badge is offline
            print("{}")
            return 0
        return cmd_hook(args, config)

    if args.command == "watch":
        if not config:
            print("No badge pairing found. Run 'pair' first.")
            return 1
        return cmd_watch(args, config)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
