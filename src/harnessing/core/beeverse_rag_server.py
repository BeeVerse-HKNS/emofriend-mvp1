import logging

import requests
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from .beeverse_rag_retriever import BeeVerseRAGRetriever
from .beeverse_skill_gap_analyzer import BeeVerseSkillGapAnalyzer
from .formula_brainstormer import FormulaBrainstormer
from .prompt_understanding_skill import PromptUnderstandingSkill

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("beeverse-rag")

app = FastAPI(title="BeeVerse RAG Server")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def destination_domain_header_middleware(request: Request, call_next):
    dest = request.headers.get("destination-domain")
    if dest and "localhost" in dest.lower():
        rewritten = dest.lower().replace("localhost", "127.0.0.1")
        logger.info(
            "Rewriting destination-domain header: '%s' -> '%s'",
            dest,
            rewritten,
        )
        mutable_headers = dict(request.headers)
        mutable_headers["destination-domain"] = rewritten
        request._headers = mutable_headers
        request.scope["headers"] = [
            (k.encode(), v.encode()) for k, v in mutable_headers.items()
        ]
    response = await call_next(request)
    return response


retriever = BeeVerseRAGRetriever()
brainstormer = FormulaBrainstormer()
prompt_skill = PromptUnderstandingSkill()
gap_analyzer = BeeVerseSkillGapAnalyzer()
OLLAMA_BASE = "http://127.0.0.1:11434"
CONTEXT_HEADER = "[RELEVANT CONTEXT]"
CONTEXT_FOOTER = "[/RELEVANT CONTEXT]"
MODEL_ALIASES = {"beeverse": "beeverse:latest", "qwen3": "qwen3:8b"}
THINKING_MODELS = {"beeverse:latest", "qwen3:8b", "qwen3:4b", "qwen3"}
NO_THINK_PREFIX = "/no_think\n"


def _resolve_model_name(model: str) -> str:
    if model in MODEL_ALIASES:
        return MODEL_ALIASES[model]
    return model


def _needs_no_think(model: str) -> bool:
    return model in THINKING_MODELS or any(model.startswith(p) for p in THINKING_MODELS)


def _inject_no_think(body: dict) -> dict:
    model = body.get("model", "")
    if not _needs_no_think(model):
        return body
    messages = body.get("messages", [])
    has_no_think = False
    for msg in messages:
        c = msg.get("content", "")
        if isinstance(c, str) and c.strip().startswith("/no_think"):
            has_no_think = True
            break
    if not has_no_think:
        for i, msg in enumerate(messages):
            if msg.get("role") == "user":
                c = msg.get("content", "")
                if isinstance(c, str):
                    messages[i] = {**msg, "content": NO_THINK_PREFIX + c}
                elif isinstance(c, list):
                    new_parts = [{"type": "text", "text": NO_THINK_PREFIX}]
                    messages[i] = {**msg, "content": new_parts + c}
                break
    if body.get("max_tokens", 0) < 256:
        body["max_tokens"] = 4096
    return body


def _inject_context(messages: list, context: str) -> list:
    if not context.strip():
        return messages
    context_block = f"{CONTEXT_HEADER}\n{context}\n{CONTEXT_FOOTER}"
    has_system = False
    new_messages = []
    for msg in messages:
        if msg.get("role") == "system":
            has_system = True
            new_messages.append({
                "role": "system",
                "content": f"{context_block}\n\n{msg['content']}",
            })
        else:
            new_messages.append(msg)
    if not has_system:
        new_messages.insert(0, {"role": "system", "content": context_block})
    return new_messages


def _extract_user_message(messages: list) -> str:
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, list):
                parts = []
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        parts.append(part.get("text", ""))
                    elif isinstance(part, str):
                        parts.append(part)
                return "\n".join(parts)
            return str(content)
    return ""


async def _handle_chat_completions(request: Request):
    body = await request.json()
    messages = body.get("messages", [])

    model = body.get("model", "")
    resolved = _resolve_model_name(model)
    if resolved != model:
        logger.info("Model alias: %s -> %s", model, resolved)
        body["model"] = resolved
    body = _inject_no_think(body)

    user_msg = _extract_user_message(messages)
    if user_msg:
        try:
            analysis = prompt_skill.analyze(user_msg)
            analysis_text = prompt_skill.format_analysis(analysis)
            logger.info(
                "Prompt analysis: %d requirements, %d intentions, completeness %.0f%%",
                len(analysis.requirements),
                len(analysis.real_intentions),
                analysis.completeness_check["completeness_score"] * 100,
            )
            context = retriever.retrieve_context(user_msg)
            brainstorm_kw = ["brainstorm", "invent", "新發明", "新想法", "創新", "formula think", "公式思維"]
            if any(kw in user_msg.lower() for kw in brainstorm_kw):
                try:
                    br = brainstormer.brainstorm(user_msg, max_formulas=10)
                    br_text = brainstormer.format_results(br)
                    context = f"{context}\n\n{br_text}" if context else br_text
                except Exception as e:
                    logger.warning("Brainstorm failed: %s", e)
            gap_kw = ["gap", "capability", "missing", "coverage", "improve", "install skill", "缺口", "能力", "覆蓋", "安裝"]
            if any(kw in user_msg.lower() for kw in gap_kw):
                try:
                    gap_report = gap_analyzer.analyze()
                    gap_context = f"\n[BeeVerse Gap Analysis] Coverage: {gap_report.overall_coverage:.1f}%, Missing: {gap_report.missing_count}, Critical: {len(gap_report.critical_gaps)}"
                    if context:
                        context = gap_context + "\n" + context
                    else:
                        context = gap_context
                except Exception as e:
                    logger.warning("Gap analysis failed: %s", e)
            if context:
                context = f"{analysis_text}\n\n{context}"
                logger.info("RAG context injected (%d chars) for query: %s",
                            len(context), user_msg[:80])
                body["messages"] = _inject_context(messages, context)
        except Exception as e:
            logger.warning("RAG retrieval failed: %s", e)

    is_stream = body.get("stream", False)
    ollama_url = f"{OLLAMA_BASE}/v1/chat/completions"

    if is_stream:
        def stream_generator():
            with requests.post(ollama_url, json=body, stream=True,
                               timeout=300) as resp:
                for chunk in resp.iter_content(chunk_size=None):
                    if chunk:
                        yield chunk
        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
        )

    try:
        resp = requests.post(ollama_url, json=body, timeout=300)
        return JSONResponse(content=resp.json(), status_code=resp.status_code)
    except requests.RequestException as e:
        logger.error("Ollama request failed: %s", e)
        return JSONResponse(
            content={"error": f"Ollama request failed: {e}"},
            status_code=502,
        )


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    return await _handle_chat_completions(request)


@app.get("/v1/models")
async def list_models():
    try:
        resp = requests.get(f"{OLLAMA_BASE}/v1/models", timeout=10)
        return JSONResponse(content=resp.json(), status_code=resp.status_code)
    except requests.RequestException as e:
        logger.error("Ollama models request failed: %s", e)
        return JSONResponse(
            content={"error": f"Ollama request failed: {e}"},
            status_code=502,
        )


@app.get("/api/tags")
async def list_tags():
    try:
        resp = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=10)
        return JSONResponse(content=resp.json(), status_code=resp.status_code)
    except requests.RequestException as e:
        logger.error("Ollama tags request failed: %s", e)
        return JSONResponse(
            content={"error": f"Ollama request failed: {e}"},
            status_code=502,
        )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "beeverse-rag"}


@app.post("/v1/gap_analysis")
async def gap_analysis(request: Request):
    body = await request.json()
    detail_level = body.get("detail_level", "summary")
    report = gap_analyzer.analyze()
    if detail_level == "full":
        return JSONResponse(content={
            "overall_coverage": report.overall_coverage,
            "dimension_coverage": report.dimension_coverage,
            "total_capabilities": report.total_capabilities,
            "installed_count": report.installed_count,
            "partial_count": report.partial_count,
            "missing_count": report.missing_count,
            "critical_gaps": [{"name": g.name, "dimension": g.dimension.value, "description": g.description} for g in report.critical_gaps],
            "important_gaps": [{"name": g.name, "dimension": g.dimension.value} for g in report.important_gaps],
            "formula_suggestions": report.formula_suggestions,
        })
    return JSONResponse(content={
        "overall_coverage": report.overall_coverage,
        "missing_count": report.missing_count,
        "critical_gaps_count": len(report.critical_gaps),
    })


@app.post("/v1/brainstorm")
async def brainstorm(request: Request):
    body = await request.json()
    problem = body.get("problem", "")
    max_formulas = body.get("max_formulas", 10)
    if not problem:
        return JSONResponse(content={"error": "problem is required"}, status_code=400)
    try:
        result = brainstormer.brainstorm(problem, max_formulas=max_formulas)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/")
async def root():
    return {"status": "ok", "service": "beeverse-rag", "version": "1.0"}


@app.post("/v1/completions")
async def completions(request: Request):
    body = await request.json()
    model = body.get("model", "")
    resolved = _resolve_model_name(model)
    if resolved != model:
        body["model"] = resolved
    body = _inject_no_think(body)
    ollama_url = f"{OLLAMA_BASE}/v1/completions"
    try:
        resp = requests.post(ollama_url, json=body, timeout=300)
        return JSONResponse(content=resp.json(), status_code=resp.status_code)
    except requests.RequestException as e:
        return JSONResponse(content={"error": f"Ollama request failed: {e}"}, status_code=502)


@app.get("/v1/engines")
async def list_engines():
    try:
        resp = requests.get(f"{OLLAMA_BASE}/v1/models", timeout=10)
        models_data = resp.json()
        engines = []
        for model in models_data.get("data", []):
            engines.append({
                "id": model["id"],
                "object": "engine",
                "owner": "beeverse",
                "ready": True,
            })
        return JSONResponse(content={"object": "list", "data": engines})
    except requests.RequestException as e:
        return JSONResponse(content={"error": f"Ollama request failed: {e}"}, status_code=502)


@app.get("/models")
async def list_models_no_prefix():
    return await list_models()


@app.post("/chat/completions")
async def chat_completions_no_prefix(request: Request):
    return await _handle_chat_completions(request)


@app.post("/completions")
async def completions_no_prefix(request: Request):
    return await completions(request)


@app.get("/engines")
async def list_engines_no_prefix():
    return await list_engines()


@app.post("/v1/v1/chat/completions")
async def chat_completions_double_prefix(request: Request):
    return await _handle_chat_completions(request)


@app.get("/v1/v1/models")
async def list_models_double_prefix():
    return await list_models()


@app.post("/v1/v1/completions")
async def completions_double_prefix(request: Request):
    return await completions(request)


@app.get("/v1/v1/engines")
async def list_engines_double_prefix():
    return await list_engines()


@app.post("/v1/analyze_prompt")
async def analyze_prompt(request: Request):
    body = await request.json()
    prompt = body.get("prompt", "")
    if not prompt:
        return JSONResponse(content={"error": "prompt is required"}, status_code=400)
    try:
        analysis = prompt_skill.analyze(prompt)
        return JSONResponse(content={
            "word_count": analysis.word_count,
            "line_count": analysis.line_count,
            "requirements": [
                {
                    "original_text": r.original_text[:200],
                    "intent": r.intent,
                    "action_type": r.action_type,
                    "is_question": r.is_question,
                    "is_imperative": r.is_imperative,
                    "is_conditional": r.is_conditional,
                    "confidence": r.confidence,
                    "ambiguity": r.ambiguity,
                }
                for r in analysis.requirements
            ],
            "real_intentions": analysis.real_intentions,
            "ambiguities": [(p, d) for p, d in analysis.ambiguities],
            "questions_to_ask": analysis.questions_to_ask,
            "completeness_check": analysis.completeness_check,
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
