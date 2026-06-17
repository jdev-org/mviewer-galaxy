#!/usr/bin/env python3
import os
import re
import sys
from pathlib import Path


VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def replace_var(match: re.Match[str]) -> str:
    name = match.group(1)
    default = match.group(2)
    value = os.environ.get(name)
    if value is not None and value != "":
        return value
    if default is not None:
        return default
    return ""


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: render_config.py <template> <output>", file=sys.stderr)
        return 1

    template_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    rendered = VAR_PATTERN.sub(replace_var, template_path.read_text())
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
