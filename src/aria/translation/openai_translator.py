"""OpenAI-compatible translator using the official openai package."""


from ..logger import debug, info


class OpenAITranslator:
    """
    Translate via any OpenAI-compatible HTTP endpoint.
    Works with local llama-server, vLLM, ollama, DeepSeek, OpenAI, etc.
    """

    def __init__(
        self,
        endpoint: str = "http://127.0.0.1:1234/v1",
        api_key: str | None = None,
        model_name: str = "",
        target_language: str = "中文",
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ):
        from openai import OpenAI

        self.client = OpenAI(
            base_url=endpoint,
            api_key=api_key or "dummy",
        )
        self.model_name = model_name
        self.target_language = target_language
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt or (
            "请将文本翻译成{target_language}。请注意，您只需输出翻译后的结果，不要添加任何额外的解释"
            "文风："
            "- 不应该有翻译腔"
            "- 尽量使用短句，而不是复杂长句"
        )
        info(f"OpenAITranslator initialized: endpoint={endpoint}, model={model_name or 'default'}, target={target_language}")

    def translate(self, text: str) -> str:
        if not text.strip():
            return ""

        prompt = self.system_prompt.replace("{target_language}", self.target_language)

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content.strip()

    def set_target_language(self, language: str) -> None:
        self.target_language = language
        debug(f"OpenAITranslator target language set to: {language}")
