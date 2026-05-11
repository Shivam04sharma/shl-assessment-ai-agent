import re
import os
import json
import asyncio
import google.generativeai as genai

JD_INDICATORS = [
    r"we are (looking|hiring|seeking)",
    r"job (description|requirements|responsibilities|title)",
    r"required (skills|qualifications|experience)",
    r"\d+\+?\s*years?\s*(of\s*)?(experience|exp)",
    r"responsibilities\s*(include|:)",
    r"(here is|here's|below is)\s*(the|a|our)?\s*j\.?d\.?",
    r"about the (role|position|job)",
    r"what you('ll| will) (do|be doing)",
]


def detect_jd(text: str) -> bool:
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in JD_INDICATORS)


def _extract_with_llm(jd_text: str) -> str:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))
    model = genai.GenerativeModel(
        model_name=os.getenv("LLM_MODEL", "gemini-1.5-flash"),
        generation_config={"temperature": 0.1},
    )

    prompt = f"""Extract key hiring requirements from this job description. Return JSON only:
{{
  "role": "exact job title",
  "seniority": "Junior|Mid|Senior|Manager|Executive",
  "skills": ["top 5 technical/soft skills"],
  "domain": "industry or domain if mentioned"
}}

JD:
{jd_text[:3000]}"""

    response = model.generate_content(prompt)
    text = response.text.strip()

    if "```" in text:
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]

    data = json.loads(text.strip())
    parts = [
        data.get("role", ""),
        data.get("seniority", ""),
        " ".join(data.get("skills", [])[:5]),
        data.get("domain", ""),
    ]
    return " ".join(filter(None, parts))


def _extract_simple(jd_text: str) -> str:
    role_match = re.search(
        r"(senior|junior|mid|lead|principal)?\s*([a-z]+\s*(?:developer|engineer|analyst|manager|designer|scientist))",
        jd_text.lower(),
    )
    role = role_match.group(0) if role_match else ""

    level_match = re.search(r"\b(junior|mid.level|senior|lead|principal|manager)\b", jd_text.lower())
    level = level_match.group(0) if level_match else ""

    skills = re.findall(
        r"\b(python|java|javascript|sql|react|node|aws|docker|kubernetes|"
        r"machine learning|data analysis|leadership|communication)\b",
        jd_text.lower(),
    )

    return " ".join(filter(None, [role, level] + list(set(skills))[:5]))


async def parse_jd_to_query(jd_text: str) -> str:
    try:
        return await asyncio.to_thread(_extract_with_llm, jd_text)
    except Exception:
        return _extract_simple(jd_text)
