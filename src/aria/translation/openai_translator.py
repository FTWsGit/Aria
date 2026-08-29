"""OpenAI-compatible translator using the official openai package."""

from typing import TYPE_CHECKING

from ..logger import debug, info
from .language_names import nllb_code_to_name

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletionMessageParam


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
        # Convert NLLB codes (e.g. "zho_Hans") to human-readable names
        self.target_language = nllb_code_to_name(target_language)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt or (
            "请将文本翻译成{target_language}。请注意，您只需输出翻译后的结果，不要添加任何额外的解释"
            "文风："
            "- 不应该有翻译腔"
            "- 尽量使用短句，而不是复杂长句"
        )
        info(
            f"OpenAITranslator initialized: endpoint={endpoint}, model={model_name or 'default'}, target={self.target_language}"
        )

    def translate(self, text: str, context: list[str] | None = None) -> str:
        """Translate one sentence.

        Args:
            text: Source sentence to translate.
            context: Previously committed source sentences, provided so the
                model keeps terminology/pronoun/style coherent. Context is
                reference-only and must never be translated or echoed.
        """
        if not text.strip():
            return ""

        prompt = self.system_prompt.replace("{target_language}", self.target_language)

        messages: list[ChatCompletionMessageParam] = [{"role": "system", "content": prompt}]
        if context:
            context_block = "\n".join(f"- {sentence}" for sentence in context)
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "以下是此前已提交句子的原文，仅供理解上下文（保持术语、代词与文风连贯），"
                        f"不要翻译或输出它们：\n{context_block}"
                    ),
                }
            )
        messages.append({"role": "user", "content": text})

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        content = response.choices[0].message.content
        return content.strip() if content else ""

    def set_target_language(self, language: str) -> None:
        self.target_language = nllb_code_to_name(language)
        debug(f"OpenAITranslator target language set to: {self.target_language}")
