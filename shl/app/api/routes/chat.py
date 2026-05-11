from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Request
from app.models.schemas import ChatRequest, ChatResponse
from app.agent.agent import Agent
from app.api.middleware.auth import verify_token

router = APIRouter()


@router.post("/chat")
async def chat_endpoint(
    request: Request,
    body: ChatRequest,
    _token: Annotated[Optional[dict], Depends(verify_token)],
) -> ChatResponse:
    agent = Agent(request.app.state.retriever)
    return await agent.process(body.messages)
