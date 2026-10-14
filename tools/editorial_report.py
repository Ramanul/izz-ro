#!/usr/bin/env python3
"""Count actual pilot coverage; never equate coverage with truth or quality."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from generator import config, editorial, render  # noqa: E402
from tools.validate_editorial import load_validated  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--articles", type=Path, default=Path(config.ROOT) / "data/articles.json")
    parser.add_argument("--annotations", type=Path, default=Path(config.ROOT) / "content/editorial/annotations.json")
    args = parser.parse_args()
    try:
        index, articles = load_validated(args.articles, args.annotations)
        articles = render._fara_date_viitoare(sorted(articles, key=lambda a: a.get("published") or "", reverse=True))
        articles = articles[:render._articole_publicabile(len(articles))]
        report = editorial.catalog_report(index, articles)
    except (editorial.EditorialError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
