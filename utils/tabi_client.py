import os
import json
import re
import sys
from openai import OpenAI
from config import settings

class TabiClient:
    def __init__(self, api_key=None, base_url=None, model=None):
        self.api_key = api_key or getattr(settings, 'TABI_API_KEY', os.getenv('TABI_API_KEY'))
        self.base_url = base_url or getattr(settings, 'TABI_BASE_URL', os.getenv('TABI_BASE_URL', 'https://tabitoken.com/v1'))
        self.model = model or getattr(settings, 'TABI_MODEL', os.getenv('TABI_MODEL', 'claude-opus-5'))
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            max_retries=1,
            timeout=300.0,
            default_headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
                "Accept": "text/event-stream, application/json"
            }
        )

    def generate(self, prompt: str, system_prompt: str = "", temperature: float = 0.7, max_tokens: int = 4096) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # stream=True ensures Cloudflare doesn't 524 timeout
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True
        )
        
        collected_text = []
        for chunk in response:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    collected_text.append(delta.content)
                    sys.stdout.write(".")
                    sys.stdout.flush()

        print("")
        return "".join(collected_text)

    def generate_json(self, prompt: str, system_prompt: str = "", temperature: float = 0.7, max_tokens: int = 2500) -> dict:
        augmented_prompt = (
            f"{prompt}\n\n"
            "CRITICAL: Respond ONLY with a valid JSON object. "
            "Do not include any markdown backticks, conversational preamble, or explanations."
        )
        content = self.generate(augmented_prompt, system_prompt=system_prompt, temperature=temperature, max_tokens=max_tokens)
        
        cleaned = re.sub(r"^```json\s*", "", content.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            raise ValueError(f"Failed to parse JSON from Claude response: {content}")