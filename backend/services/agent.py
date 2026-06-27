import json
from collections.abc import Iterator

from openai import OpenAI

from backend.core.config import Settings
from backend.schemas.agent import AskRequest
from config import RAG_CONFIG, ZHIXING_LLM_CONFIG
from rag import get_retriever


class AgentUnavailableError(RuntimeError):
    pass


class ExperimentAgent:
    """RAG-backed experiment agent isolated from HTTP transport."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = (
            OpenAI(api_key=settings.mimo_api_key, base_url=settings.mimo_base_url)
            if settings.mimo_api_key
            else None
        )

    def _context(self, question: str) -> tuple[str, list[dict]]:
        if not RAG_CONFIG.get("enabled"):
            return "", []
        try:
            retriever = get_retriever(RAG_CONFIG.get("knowledge_base_dir", "knowledge_base"))
            hits = retriever.retrieve(question, top_k=RAG_CONFIG.get("top_k", 6))
        except Exception:
            return "", []
        sources = []
        blocks = []
        for hit in hits:
            score = float(hit.get("score", 0))
            if score < RAG_CONFIG.get("min_score", 0.04):
                continue
            blocks.append(hit.get("text", ""))
            sources.append({key: hit.get(key) for key in ("source", "score", "title") if key in hit})
        return "\n\n".join(blocks), sources

    @property
    def available(self) -> bool:
        return self._client is not None

    def _messages(self, request: AskRequest) -> tuple[list[dict], list[dict]]:
        context, sources = self._context(request.question)
        system = ZHIXING_LLM_CONFIG["system_prompt_kb" if context else "system_prompt_general"]
        if context:
            system += f"\n\n知识库检索片段：\n{context}"
        history = [message.model_dump() for message in request.history[-12:]]
        return [{"role": "system", "content": system}, *history,
                {"role": "user", "content": request.question}], sources

    def ask(self, request: AskRequest) -> dict:
        if self._client is None:
            raise AgentUnavailableError("未配置 MIMO_API_KEY")
        messages, sources = self._messages(request)
        response = self._client.chat.completions.create(
            model=self.settings.mimo_model,
            messages=messages,
            max_tokens=ZHIXING_LLM_CONFIG.get("max_tokens", 640),
            temperature=ZHIXING_LLM_CONFIG.get("temperature", 0.45),
            extra_body={"thinking": {"type": "disabled"}},
        )
        return {"answer": (response.choices[0].message.content or "").strip(), "sources": sources}

    def stream(self, request: AskRequest) -> Iterator[str]:
        if self._client is None:
            raise AgentUnavailableError("未配置 MIMO_API_KEY")
        messages, sources = self._messages(request)
        yield self._event("meta", sources=sources, rag=bool(sources))
        response = self._client.chat.completions.create(
            model=self.settings.mimo_model,
            messages=messages,
            max_tokens=ZHIXING_LLM_CONFIG.get("max_tokens", 640),
            temperature=ZHIXING_LLM_CONFIG.get("temperature", 0.45),
            stream=True,
            extra_body={"thinking": {"type": "disabled"}},
        )
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield self._event("delta", content=chunk.choices[0].delta.content)
        yield self._event("done")

    @staticmethod
    def _event(event_type: str, **payload) -> str:
        return f"data: {json.dumps({'type': event_type, **payload}, ensure_ascii=False)}\n\n"
