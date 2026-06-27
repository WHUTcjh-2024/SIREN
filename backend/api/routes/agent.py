from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from backend.api.deps import get_agent
from backend.schemas.agent import AskRequest, SuggestionRequest
from backend.services.agent import AgentUnavailableError, ExperimentAgent

router = APIRouter(tags=["agent"])


@router.post("/ask")
def ask(payload: AskRequest, agent: ExperimentAgent = Depends(get_agent)) -> dict:
    try:
        return agent.ask(payload)
    except AgentUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/ask/stream")
def ask_stream(payload: AskRequest, agent: ExperimentAgent = Depends(get_agent)) -> StreamingResponse:
    if not agent.available:
        raise HTTPException(status_code=503, detail="未配置 MIMO_API_KEY")
    return StreamingResponse(agent.stream(payload), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/ask/suggestions")
def suggestions(payload: SuggestionRequest) -> dict:
    # Deterministic fallback keeps this endpoint fast and available without an LLM.
    page = payload.page.lower()
    if "data-processing" in page or "module2" in page:
        items = ["误差如何传递到表面张力？", "拟合斜率的物理意义是什么？", "如何判断数据点是否异常？"]
    else:
        items = ["条纹间距由哪些因素决定？", "如何减小光路系统误差？", "为什么需要测量正负一级？"]
    return {"suggestions": items}


@router.get("/rag/status")
def rag_status(agent: ExperimentAgent = Depends(get_agent)) -> dict:
    context, sources = agent._context("激光衍射")
    return {"enabled": bool(context), "chunks": len(sources), "model": agent.settings.mimo_model}
