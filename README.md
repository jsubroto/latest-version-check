# latest-version-check

A tiny, dependency-free CLI that shows:
- latest versions
- release dates
- end-of-life dates (where available)

It is meant for a quick local sanity check before you say "we should upgrade X to Y."

## Latest versions

Auto-updated daily by GitHub Actions. Commits land only when a version actually changes.

<!-- VERSIONS:START -->
```
tool    latest   releaseDate  eolDate   
======  =======  ===========  ==========
nodejs  24.18.0  2025-05-06   2028-04-30
python  3.14.6   2025-10-07   2030-10-31
nextjs  16.2.9   2025-10-22             
react   19.2.7   2024-12-05
```
<!-- VERSIONS:END -->

## What it checks

- Uses the endoflife.date v1 API for: nodejs (prefers LTS), python, nextjs, react

## Requirements

- Python 3.10+

## Quick start

    python latest_version_check.py

Only check specific tools:

    python latest_version_check.py --tools react,nextjs

JSON output:

    python latest_version_check.py --json

List supported tools:

    python latest_version_check.py --list-tools

## Example output

    tool    latest  releaseDate  eolDate
    ======  ======  ===========  =======
    react   19.2.4  2024-12-05
    python  3.13.7  2024-10-01  2029-10-01

## Notes

- `--tools` only accepts the built-in supported tool names.
- The CLI prints warnings to stderr and exits non-zero if any requested tool fails to load.
- `--json` includes an `error` field for failed tools.
- Data comes from the `endoflife.date` API, so output depends on that upstream dataset.

## Cache

Default cache path:

    .cache/latest_version_check.json

Add this to .gitignore:

    .cache/
    __pycache__/
    *.pyc

The cache stores lightweight JSON responses from the endoflife API.

## License

MIT
