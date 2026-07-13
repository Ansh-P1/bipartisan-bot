import os


def get_llm(role: str = "default"):
    """Return a chat model for the given node role.

    Defaults to Anthropic; falls back to OpenAI if only OPENAI_API_KEY is set.
    The role parameter lets different nodes use different models later
    (e.g. a cheaper model for research summarization, a stronger one for
    debate/moderation) without changing call sites.
    """
    if os.environ.get("ANTHROPIC_API_KEY"):
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model="claude-sonnet-5")

    if os.environ.get("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model="gpt-4o")

    raise RuntimeError(
        "No LLM API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY."
    )


if __name__ == "__main__":
    llm = get_llm("right")
    print(type(llm))
    print(llm.invoke("Say hello in five words.").content)
