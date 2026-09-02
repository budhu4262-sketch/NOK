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

        # Google ne specifically gemini-3.6-flash recommend kiya hai
        self.preferred_model = model or "gemini-3.6-flash"
        self.active_model = None
        self._initialize_model_pool()

    def _initialize_model_pool(self):
        """Discovers all working models on this API key to avoid 404 errors."""
        self.candidate_models = [self.preferred_model, "gemini-3.6-flash", "gemini-2.5-pro", "gemini-2.0-flash", "gemini-1.5-flash-latest"]
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                discovered = [
                    m["name"].replace("models/", "")
                    for m in data.get("models", [])
                    if "generateContent" in m.get("supportedGenerationMethods", [])
                ]
                # Add discovered models to pool
                for m in discovered:
                    if m not in self.candidate_models:
                        self.candidate_models.append(m)
                print(f"[AI Client] Discovered active models: {self.candidate_models[:5]}")
        except Exception as e:
            print(f"[AI Client] Warning during model discovery: {e}")

    def generate(self, prompt: str, system_prompt: str = "", temperature: float = 0.7, max_tokens: int = 4096) -> str:
        # Agar working model already mil chuka hai, pehle use try karo
        pool = [self.active_model] if self.active_model else []
        pool.extend([m for m in self.candidate_models if m != self.active_model])

        last_error = None
        for model_name in pool:
            if not model_name:
                continue
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
            
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens
                }
            }
            if system_prompt:
                payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

            try:
                with urllib.request.urlopen(req, timeout=90) as response:
                    res_json = json.loads(response.read().decode("utf-8"))
                    candidates = res_json.get("candidates", [])
                    if not candidates:
                        continue
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if not parts:
                        continue
                    
                    # Agar success hua, toh is model ko lock kar lo
                    self.active_model = model_name
                    return parts[0].get("text", "")
            except urllib.error.HTTPError as err:
                err_msg = err.read().decode("utf-8", errors="ignore")
                last_error = f"Model {model_name} failed ({err.code}): {err_msg}"
                print(f"[AI Client] {model_name} rejected. Trying next candidate...")
                continue
            except Exception as ex:
                last_error = str(ex)
                continue

        raise RuntimeError(f"All Gemini models in pool failed. Last error: {last_error}")

    def generate_json(self, prompt: str, system_prompt: str = "", temperature: float = 0.7, max_tokens: int = 4096) -> dict:
        augmented_prompt = prompt + "\n\nCRITICAL: Output ONLY raw, parseable JSON. Do not include markdown codeblocks (```json), commentary, or preambles."
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
