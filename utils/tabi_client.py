import os
import json
import re
import urllib.request
import urllib.error
from utils.config import get_gemini_api_key

class TabiClient:
    def __init__(self, model: str = None):
        self.api_key = (get_gemini_api_key() or os.environ.get("GEMINI_API_KEY", "")).strip().strip('"').strip("'")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is missing.")

        self.model = self._resolve_active_model(model)
        print(f"[AI Client] Connected to Gemini via Official Native API -> Model: {self.model}")

    def _resolve_active_model(self, preferred: str = None) -> str:
        """Auto-discovers the exact working models available on this API key."""
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                available = [
                    m["name"].replace("models/", "")
                    for m in data.get("models", [])
                    if "generateContent" in m.get("supportedGenerationMethods", [])
                ]
                print(f"[AI Client] Models found on key: {available[:4]}")

                candidates = [preferred, "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash-latest", "gemini-1.5-flash", "gemini-pro"]
                for cand in candidates:
                    if cand and cand in available:
                        return cand
                if available:
                    return available[0]
        except Exception as e:
            print(f"[AI Client] Note: Model discovery fallback ({e})")

        return preferred or "gemini-2.0-flash"

    def generate(self, prompt: str, system_prompt: str = "", temperature: float = 0.7, max_tokens: int = 4096) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                res_json = json.loads(response.read().decode("utf-8"))
                candidates = res_json.get("candidates", [])
                if not candidates:
                    raise ValueError(f"Empty Gemini response: {res_json}")
                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    raise ValueError(f"No content parts in Gemini response: {res_json}")
                return parts[0].get("text", "")
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Gemini Native API Error {err.code}: {err_body}")

    def generate_json(self, prompt: str, system_prompt: str = "", temperature: float = 0.7, max_tokens: int = 4096) -> dict:
        augmented_prompt = prompt + "\n\nReturn ONLY a raw, valid JSON object. Do NOT wrap in markdown formatting or add extra text."
        raw_text = self.generate(augmented_prompt, system_prompt=system_prompt, temperature=temperature, max_tokens=max_tokens)

        cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            raise ValueError(f"Could not parse valid JSON from LLM: {raw_text[:200]}")
