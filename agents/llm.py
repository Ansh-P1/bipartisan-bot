import os

GROQ_MODEL_BY_ROLE = {
    "right": "openai/gpt-oss-20b",
    "left": "openai/gpt-oss-20b",
    "moderator": "openai/gpt-oss-120b",
    "guardrail": "openai/gpt-oss-20b",
}


def get_llm(role: str = "default"):
    """Return a chat model for the given node role.

    Defaults to Anthropic; falls back to OpenAI, then Groq. The role parameter
    lets different nodes use different models later (e.g. a cheaper model for
    research summarization, a stronger one for debate/moderation) without
    changing call sites.
    """
    if os.environ.get("ANTHROPIC_API_KEY"):
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model="claude-sonnet-5")

    if os.environ.get("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model="gpt-4o")

    if os.environ.get("GROQ_API_KEY"):
        from langchain_groq import ChatGroq

        # Groq's free tier caps each model at 8k tokens/min, so spread roles
        # across models (each has its own bucket) and keep reasoning short.
        model = GROQ_MODEL_BY_ROLE.get(role, "openai/gpt-oss-20b")
        return ChatGroq(model=model, reasoning_effort="low", max_retries=5, timeout=90)

    raise RuntimeError(
        "No LLM API key found. Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or GROQ_API_KEY."
    )


if __name__ == "__main__":
    llm = get_llm("right")
    print(type(llm))
    print(llm.invoke("Say hello in five words.").content)
