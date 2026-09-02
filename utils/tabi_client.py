import os
import json
import re
from openai import OpenAI
from utils.config import get_gemini_api_key, get_tabi_api_key

class TabiClient:
    def __init__(self, model: str = "gemini-1.5-flash"):
        gemini_key = get_gemini_api_key() or os.environ.get("GEMINI_API_KEY", "")

        if gemini_key:
            # Google Gemini Official OpenAI-compatible Endpoint (Never blocked by Cloudflare)
            self.client = OpenAI(
                api_key=gemini_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )
            self.model = "gemini-1.5-flash"
            print(f"[AI Client] Connected to Google Gemini Official ({self.model})")
        else:
            # Fallback to Tabi if Gemini key is missing
            tabi_key = get_tabi_api_key() or os.environ.get("TABI_API_KEY", "")
            self.client = OpenAI(
                api_key=tabi_key,
                base_url="https://tabitoken.com/v1"
            )
            self.model = model or "claude-3-5-sonnet-20241022"
            print(f"[AI Client] Connected to Tabi proxy ({self.model})")

    def generate(self, prompt: str, system_prompt: str = "", temperature: float = 0.7, max_tokens: int = 4096) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content

    def generate_json(self, prompt: str, system_prompt: str = "", temperature: float = 0.7, max_tokens: int = 4096) -> dict:
        augmented_prompt = prompt + "\n\nReturn ONLY a valid JSON object. Do not include extra text or markdown format."
        raw_text = self.generate(augmented_prompt, system_prompt=system_prompt, temperature=temperature, max_tokens=max_tokens)

        cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            raise ValueError(f"Could not parse valid JSON from LLM response: {raw_text[:200]}")
