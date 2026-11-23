"""Offline coverage for provider routing, redaction, and Gemini-free retrieval."""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from pydantic import BaseModel

from app.agents import llm
from app.services import knowledge_base


class Output(BaseModel):
    advice: str


def generate(**kwargs):
    return llm.generate_structured_with_model(
        system="Advise cautiously", payload={"question": "Paddy irrigation"},
        schema=Output, **kwargs,
    )


def response(url, *, status=200, text='{"advice":"Check the soil"}'):
    return httpx.Response(status, request=httpx.Request("POST", url),
                          json={"choices": [{"message": {"content": text}}]})


def run():
    with (
        patch.object(llm, "settings", SimpleNamespace(
            XAI_API_KEY="test-xai", XAI_MODEL="grok-test", XAI_VISION_MODEL="",
            META_API_KEY="test-meta", META_MODEL="llama-test", META_VISION_MODEL="llama-vision",
        )),
        patch.object(llm, "get_gemini_client", return_value=None),
        patch.object(llm.httpx, "post") as post,
    ):
        post.side_effect = [response("https://api.x.ai", status=429), response("https://api.llama.com")]
        output, model = generate()
        assert output == {"advice": "Check the soil"}
        assert model == "meta:llama-test" and llm.model_provider(model) == "meta"
        assert post.call_args_list[0].args[0] == "https://api.x.ai/v1/chat/completions"
        assert post.call_args_list[1].args[0] == "https://api.llama.com/compat/v1/chat/completions"
        assert post.call_args.kwargs["headers"]["Authorization"] == "Bearer test-meta"
        assert "test-meta" not in str(post.call_args.kwargs["json"])

        post.reset_mock()
        post.side_effect = None
        post.return_value = response("https://api.llama.com")
        _, model = generate(images=[(b"img", "image/png")])
        assert model == "meta:llama-vision" and post.call_count == 1
        assert post.call_args.kwargs["json"]["messages"][1]["content"][1]["image_url"]["url"].endswith("aW1n")

        post.reset_mock()
        post.side_effect = [response("https://api.x.ai", text="invalid"), response("https://api.llama.com", status=401)]
        try:
            generate()
        except llm.LLMError as exc:
            assert "HTTP 401" in str(exc) and "test-meta" not in str(exc)
        else:
            raise AssertionError("Invalid provider output must fail schema validation")

    approved_chunk = {"title": "Paddy guidance", "authority": "DOA", "authority_tier": 1,
                      "content": "Irrigate paddy with field checks.", "page_start": 2, "chunk_id": "c1"}
    with (
        patch.object(knowledge_base, "supabase_configured", return_value=True),
        patch.object(knowledge_base, "embeddings_configured", return_value=False),
        patch.object(knowledge_base, "_keyword_rows", return_value=[approved_chunk]),
    ):
        result = knowledge_base.search_knowledge("paddy irrigation", crop="Paddy")
        assert result["retrieval"] == "published_keyword"
        assert result["results"][0]["citation_label"] == "DOA — Paddy guidance — p. 2"
        assert result["evidence_quality"]["requires_expert_verification"]
        assert "embedding_model" not in result


if __name__ == "__main__":
    run()
    print("Provider routing, schema validation, safe fallback and keyword citation: PASS")
