import re
import time
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from app.config import settings
from app.schemas import Citation
from app.services.settings_service import get_active_gemini_model


class GeminiFileSearchService:
    def __init__(self) -> None:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        self.client = genai.Client(api_key=settings.gemini_api_key)

    def create_store(self, display_name: str) -> str:
        store = self.client.file_search_stores.create(
            config={"display_name": display_name}
        )
        return _get_value(store, "name") or ""

    def upload_and_wait(self, store_name: str, file_path: str, mime_type: str | None) -> str:
        operation = self.client.file_search_stores.upload_to_file_search_store(
            file=str(Path(file_path)),
            file_search_store_name=store_name,
            config={
                "display_name": Path(file_path).name,
            },
        )

        operation = self._wait_operation(operation)
        response = _get_value(operation, "response") or operation
        document = (
            _get_value(response, "file_search_store_document")
            or _get_value(response, "document")
            or response
        )
        document_name = _get_value(document, "name")
        if not document_name:
            document_name = _get_value(operation, "name") or ""
        return document_name

    def answer_with_sources(self, store_name: str, prompt: str) -> tuple[str, list[Citation]]:
        response = self.client.models.generate_content(
            model=get_active_gemini_model(),
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=[store_name]
                        )
                    )
                ]
            ),
        )
        text = getattr(response, "text", None) or ""
        return text.strip(), _extract_citations(response)

    def _wait_operation(self, operation: Any, timeout_seconds: int = 600) -> Any:
        start = time.monotonic()
        while not bool(_get_value(operation, "done")):
            if time.monotonic() - start > timeout_seconds:
                raise TimeoutError("Gemini File Search indexing timed out")
            time.sleep(5)
            op_name = _get_value(operation, "name")
            if not op_name:
                break
            try:
                operation = self.client.operations.get(operation)
            except TypeError:
                operation = self.client.operations.get(operation=op_name)

        error = _get_value(operation, "error")
        if error:
            raise RuntimeError(str(error))
        return operation


def _get_value(obj: Any, key: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _extract_citations(response: Any) -> list[Citation]:
    citations: list[Citation] = []
    seen: set[tuple[str, int | None, str | None]] = set()

    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        grounding = _get_value(candidate, "grounding_metadata")
        supports = _get_value(grounding, "grounding_supports") or []
        chunks = _get_value(grounding, "grounding_chunks") or []
        for support in supports:
            segment = _get_value(support, "segment")
            snippet = _get_value(segment, "text")
            chunk_indices = _get_value(support, "grounding_chunk_indices") or []
            for idx in chunk_indices:
                source = _source_from_chunk(chunks, idx)
                if source:
                    citation = Citation(
                        source=source,
                        page=_page_from_text(source),
                        snippet=snippet,
                    )
                    key = (citation.source, citation.page, citation.snippet)
                    if key not in seen:
                        seen.add(key)
                        citations.append(citation)

    return citations


def _source_from_chunk(chunks: Any, index: int) -> str | None:
    try:
        chunk = chunks[index]
    except (IndexError, TypeError):
        return None

    retrieved_context = _get_value(chunk, "retrieved_context")
    file_data = _get_value(chunk, "file_data")
    for obj in (retrieved_context, file_data, chunk):
        if not obj:
            continue
        title = _get_value(obj, "title") or _get_value(obj, "file_name") or _get_value(obj, "uri")
        if title:
            return str(title)
    return None


def _page_from_text(text: str) -> int | None:
    match = re.search(r"(?:page|pagina|p[áa]gina)\D+(\d+)", text, re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))
