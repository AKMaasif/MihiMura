import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.knowledge_base import chunk_pages, extract_pages, search_knowledge


def test_multilingual_chunking_preserves_unicode():
    pages = [
        {"page": 1, "text": "වී වගාව සඳහා ජල කළමනාකරණය වැදගත් වේ.\n\nநெல் சாகுபடியில் நீர் மேலாண்மை முக்கியம்."},
        {"page": 2, "text": "Paddy crop monitoring should use field observations and verified guidance."},
    ]
    chunks = chunk_pages(pages, max_chars=500, overlap_chars=60)
    joined = " ".join(x["content"] for x in chunks)
    assert "වී වගාව" in joined
    assert "நெல் சாகுபடி" in joined
    assert "Paddy" in joined
    assert chunks[0]["page_start"] == 1


def test_text_extraction():
    pages = extract_pages("Paddy guidance\n\nFertilizer timing".encode(), "guide.txt", "text/plain")
    assert pages[0]["text"].startswith("Paddy guidance")


def test_search_degrades_gracefully_without_runtime_configuration():
    # In source-only CI/local packaging there may be no Supabase/Gemini .env.
    result = search_knowledge("paddy fertilizer", crop="Paddy")
    assert "results" in result
    assert "evidence_quality" in result


def run() -> None:
    test_multilingual_chunking_preserves_unicode()
    test_text_extraction()
    test_search_degrades_gracefully_without_runtime_configuration()
    print("MihiMura RAG phase 2 test: PASS")


if __name__ == "__main__":
    run()
