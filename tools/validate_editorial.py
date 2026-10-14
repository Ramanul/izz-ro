#!/usr/bin/env python3
"""Validate documentary context without collecting news or writing source state."""
import argparse
import copy
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from generator import config, editorial, moderation, render, state  # noqa: E402


def prepared_articles(path):
    articles = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(articles, list) or any(not isinstance(a, dict) for a in articles):
        raise editorial.EditorialError("articles: array of objects required")
    articles = copy.deepcopy(articles)
    # Keep the CLI's structured stdout separate from existing pipeline diagnostics.
    with redirect_stdout(sys.stderr):
        state._impune_published_utc(articles)
        articles = state._resync_pinned(articles)
        articles = moderation.apply(articles, moderation.load())
        articles = [a for a in render._dedup(articles) if render._quality_gate(a)]
    render.assign_slugs(articles)
    return articles


def load_validated(articles_path, annotations_path):
    articles = prepared_articles(articles_path)
    annotations = editorial.load_annotations(annotations_path)
    errors = editorial.validate_annotations(annotations, articles)
    if errors:
        raise editorial.EditorialError("\n".join(errors))
    return annotations, articles


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--articles", type=Path, default=Path(config.ROOT) / "data/articles.json")
    parser.add_argument("--annotations", type=Path, default=Path(config.ROOT) / "content/editorial/annotations.json")
    args = parser.parse_args()
    try:
        index, articles = load_validated(args.articles, args.annotations)
    except (editorial.EditorialError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps({"valid": True, "catalog_records": len(index),
                      "eligible_articles": len(articles)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
