from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.services.knowledge_base import ingest_knowledge_document


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest an agricultural document into the MihiMura Supabase RAG index")
    parser.add_argument("file", help="Path to PDF/TXT/MD/CSV/TSV/JSON")
    parser.add_argument("--title", required=True)
    parser.add_argument("--authority", required=True)
    parser.add_argument("--authority-tier", type=int, default=2, choices=[1, 2, 3, 4])
    parser.add_argument("--document-type", default="guidance")
    parser.add_argument("--crop", default=None)
    parser.add_argument("--language", default="English")
    parser.add_argument("--region", default=None)
    parser.add_argument("--district", default=None)
    parser.add_argument("--source-url", default=None)
    parser.add_argument("--version-label", default=None)
    parser.add_argument("--published-at", default=None, help="YYYY-MM-DD")
    parser.add_argument("--status", default="published", choices=["draft", "published", "archived"])
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists() or not path.is_file():
        raise SystemExit(f"File not found: {path}")
    suffix = path.suffix.lower()
    mime = {
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".markdown": "text/markdown",
        ".csv": "text/csv",
        ".tsv": "text/tab-separated-values",
        ".json": "application/json",
    }.get(suffix, "application/octet-stream")

    result = ingest_knowledge_document(
        data=path.read_bytes(),
        filename=path.name,
        mime_type=mime,
        title=args.title,
        authority=args.authority,
        authority_tier=args.authority_tier,
        document_type=args.document_type,
        crop=args.crop,
        language=args.language,
        region=args.region,
        district=args.district,
        source_url=args.source_url,
        version_label=args.version_label,
        published_at=args.published_at,
        status=args.status,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
