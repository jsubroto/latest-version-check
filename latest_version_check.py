import argparse
import json
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen

EOL_API = "https://endoflife.date/api/v1/products"


@dataclass(frozen=True)
class Tool:
    name: str
    prefer_lts: bool = False


TOOLS = (
    Tool("nodejs", prefer_lts=True),
    Tool("python"),
    Tool("nextjs"),
    Tool("react"),
)
TOOL_NAMES = tuple(tool.name for tool in TOOLS)


def parse_date(value: object) -> str:
    if not isinstance(value, str):
        return ""
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return ""


def fetch_json(url: str, timeout: float) -> object:
    req = Request(url, headers={"User-Agent": "latest-version-check"})
    with urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def cached_get(url: str, timeout: float, cache: dict | None, ttl: int) -> object:
    now = int(time.time())
    if cache is not None:
        entry = cache.get(url)
        if isinstance(entry, dict) and now - entry.get("t", 0) <= ttl:
            return entry.get("p")

    payload = fetch_json(url, timeout)
    if cache is not None:
        cache[url] = {"t": now, "p": payload}
    return payload


def get_releases(
    tool_name: str, timeout: float, cache: dict | None, ttl: int
) -> list[dict]:
    payload = cached_get(f"{EOL_API}/{tool_name}/", timeout, cache, ttl)
    try:
        releases = payload["result"]["releases"]
    except (TypeError, KeyError):
        raise ValueError(f"invalid response for {tool_name}") from None

    if not isinstance(releases, list) or not all(isinstance(r, dict) for r in releases):
        raise ValueError(f"invalid releases for {tool_name}")
    return releases


def pick_release(releases: list[dict], prefer_lts: bool) -> dict:
    pool = [r for r in releases if r.get("isEol") is not True]
    if prefer_lts:
        pool = [r for r in pool if r.get("isLts")] or pool
    pool = pool or releases
    if not pool:
        return {}
    return max(pool, key=lambda r: int(str(r.get("name", "0")).split(".", 1)[0]))


def build_row(
    tool: Tool, timeout: float, cache: dict | None, ttl: int
) -> dict[str, str]:
    chosen = pick_release(get_releases(tool.name, timeout, cache, ttl), tool.prefer_lts)
    latest = chosen.get("latest")
    return {
        "tool": tool.name,
        "latest": latest.get("name", "") if isinstance(latest, dict) else "",
        "releaseDate": parse_date(chosen.get("releaseDate")),
        "eolDate": parse_date(chosen.get("eolFrom")),
    }


def load_cache(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_cache(path: Path, cache: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f"{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as tmp:
        tmp.write(json.dumps(cache, separators=(",", ":"), ensure_ascii=True))
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def parse_wanted_tools(raw: str) -> list[str]:
    return list(dict.fromkeys(part.strip() for part in raw.split(",") if part.strip()))


def print_table(rows: list[dict[str, str]]) -> None:
    headers = ("tool", "latest", "releaseDate", "eolDate")
    widths = {h: max(len(h), *(len(row.get(h, "")) for row in rows)) for h in headers}

    def render(row: dict[str, str]) -> str:
        return "  ".join(row.get(h, "").ljust(widths[h]) for h in headers)

    print("  ".join(h.ljust(widths[h]) for h in headers))
    print("  ".join("=" * widths[h] for h in headers))
    for row in rows:
        print(render(row))


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="latest-version-check",
        description="Lifecycle report for common runtimes and frontend frameworks.",
    )
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument(
        "--cache", type=Path, default=Path(".cache/latest_version_check.json")
    )
    parser.add_argument("--cache-ttl", type=int, default=24 * 60 * 60)
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--tools", default="")
    parser.add_argument("--list-tools", action="store_true")
    args = parser.parse_args()

    if args.list_tools:
        print("\n".join(TOOL_NAMES))
        return 0

    wanted = parse_wanted_tools(args.tools)
    unknown = [name for name in wanted if name not in TOOL_NAMES]
    if unknown:
        parser.error(
            f"unknown tool(s): {', '.join(unknown)}. Supported tools: {', '.join(TOOL_NAMES)}"
        )

    cache = None if args.no_cache else load_cache(args.cache)
    rows = []
    errors = []
    for tool in TOOLS:
        if wanted and tool.name not in wanted:
            continue
        try:
            rows.append(build_row(tool, args.timeout, cache, args.cache_ttl))
        except Exception as exc:
            errors.append(f"{tool.name}: {exc}")
            rows.append(
                {
                    "tool": tool.name,
                    "latest": "",
                    "releaseDate": "",
                    "eolDate": "",
                    "error": str(exc),
                }
            )

    if cache is not None:
        save_cache(args.cache, cache)

    if args.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
    else:
        print_table(rows)
        for error in errors:
            print(f"warning: {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
