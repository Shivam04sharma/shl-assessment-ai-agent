import os
import json
import asyncio
from typing import List
from dotenv import load_dotenv

import google.generativeai as genai

from app.models.schemas import Message, ChatResponse, Recommendation
from app.catalog.retriever import Retriever
from app.agent.prompts import build_prompt
from app.agent.jd_parser import detect_jd, parse_jd_to_query
from app.utils.helpers import clean_json_response, get_last_user_message

load_dotenv()

MAX_TURNS = int(os.getenv("MAX_TURNS", "8"))
MAX_RECOMMENDATIONS = int(os.getenv("MAX_RECOMMENDATIONS", "10"))

FALLBACK_DECISION = {
    "action": "clarify",
    "reply": "Could you tell me more about the role you're hiring for?",
    "search_query": "",
    "end_of_conversation": False,
}


class Agent:
    def __init__(self, retriever: Retriever):
        self.retriever = retriever
        self._setup_genai()
        self.llm = genai.GenerativeModel(
            model_name=os.getenv("LLM_MODEL", "gemini-2.0-flash"),
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": 300,
            },
        )

    @staticmethod
    def _setup_genai() -> None:
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
        api_key = os.getenv("GEMINI_API_KEY", "")
        if api_key and not creds_path:
            genai.configure(api_key=api_key)

    def _call_llm(self, prompt: str) -> dict:
        try:
            response = self.llm.generate_content(prompt)
            text = clean_json_response(response.text)
            return json.loads(text)
        except (json.JSONDecodeError, Exception):
            return FALLBACK_DECISION.copy()

    async def process(self, messages: List[Message]) -> ChatResponse:
        # Hard turn limit
        if len(messages) >= MAX_TURNS:
            return ChatResponse(
                reply="We've reached the conversation limit. Please start a new chat.",
                recommendations=[],
                end_of_conversation=True,
            )

        last_user_msg = get_last_user_message(messages)

        # JD detected → extract search query, skip clarifying questions
        jd_search_query = ""
        if detect_jd(last_user_msg):
            jd_search_query = await parse_jd_to_query(last_user_msg)

        # LLM decides the action
        prompt = build_prompt(messages)
        decision = await asyncio.to_thread(self._call_llm, prompt)

        action = decision.get("action", "clarify")
        reply = decision.get("reply", FALLBACK_DECISION["reply"])
        search_query = jd_search_query or decision.get("search_query", "")

        # JD provided → force recommend
        if jd_search_query and action not in ("refuse",):
            action = "recommend"

        # Refine: if user is updating constraints on existing recommendations, force recommend
        has_prior_recommendations = any(
            msg.role == "assistant" and "assessment" in msg.content.lower()
            for msg in messages[:-1]
        )
        if has_prior_recommendations and action == "clarify" and search_query:
            action = "recommend"

        recommendations: List[Recommendation] = []

        if action == "recommend":
            if search_query:
                results = self.retriever.search(search_query, k=MAX_RECOMMENDATIONS)
                recommendations = [
                    Recommendation(
                        name=r["name"],
                        url=r["url"],
                        test_type=r.get("test_type", "K"),
                    )
                    for r in results
                ]

            # If catalog empty, fallback to clarify instead of returning empty recs
            if not recommendations:
                return ChatResponse(
                    reply="I wasn't able to find matching assessments right now. Could you provide more details about the role?",
                    recommendations=[],
                    end_of_conversation=False,
                )

            # Recommendations found → build reply, close conversation
            reply = f"Here are {len(recommendations)} SHL assessment(s) that match your requirements."
            return ChatResponse(
                reply=reply,
                recommendations=recommendations,
                end_of_conversation=True,
            )

        if action == "compare" and search_query:
            results = self.retriever.search(search_query, k=6)
            if results:
                catalog_context = "\n".join(
                    f"- {r['name']} (Type: {r.get('test_type','?')}): "
                    f"{r.get('description', 'No description available.')}"
                    for r in results
                )
                compare_prompt = build_prompt(messages, catalog_context)
                compare_decision = await asyncio.to_thread(self._call_llm, compare_prompt)
                reply = compare_decision.get("reply", reply)

        # clarify / compare / refuse → always end_of_conversation = false
        return ChatResponse(
            reply=reply,
            recommendations=[],
            end_of_conversation=False,
        )
