from typing import Any, Dict, List, Optional
import httpx
from app.core.config import settings
from app.core.exceptions import (
    OpenRouterConfigError,
    OpenRouterAuthError,
    OpenRouterRateLimitError,
    OpenRouterTimeoutError,
    OpenRouterModelUnavailableError,
    OpenRouterNetworkError,
)

class OpenRouterClient:
    """Dedicated HTTP client for communicating with OpenRouter API."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, timeout: Optional[int] = None):
        self.api_key = api_key if api_key is not None else settings.OPENROUTER_API_KEY
        self.model = model or settings.OPENROUTER_MODEL
        self.timeout = timeout or settings.OPENROUTER_TIMEOUT
        self.base_url = "https://openrouter.ai/api/v1"

    def _get_headers(self) -> Dict[str, str]:
        if not self.api_key or not self.api_key.strip():
            raise OpenRouterConfigError(
                "OpenRouter API key is missing. Set OPENROUTER_API_KEY in your .env file."
            )
        return {
            "Authorization": f"Bearer {self.api_key.strip()}",
            "HTTP-Referer": "http://localhost:5173",
            "X-Title": "AI Code Debugger",
            "Content-Type": "application/json",
        }

    async def verify_model_availability(self) -> Dict[str, Any]:
        """Check whether the configured model is available in OpenRouter catalog."""
        headers = self._get_headers()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/models", headers=headers)
                if response.status_code == 401:
                    raise OpenRouterAuthError()
                if response.status_code != 200:
                    return {
                        "verified": False,
                        "available": False,
                        "model": self.model,
                        "detail": f"Catalog check returned status {response.status_code}",
                    }
                data = response.json()
                models = [m.get("id") for m in data.get("data", [])]
                is_available = self.model in models
                return {
                    "verified": True,
                    "available": is_available,
                    "model": self.model,
                    "detail": "Model found in catalog" if is_available else "Model not found in catalog",
                }
        except httpx.TimeoutException:
            return {
                "verified": False,
                "available": False,
                "model": self.model,
                "detail": "Timeout checking model catalog",
            }
        except (httpx.ConnectError, httpx.RequestError) as exc:
            return {
                "verified": False,
                "available": False,
                "model": self.model,
                "detail": f"Network error checking catalog: {str(exc)}",
            }

    async def generate_chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        use_json_mode: bool = True,
    ) -> str:
        """Call OpenRouter chat completions endpoint and return the assistant message content.

        Notes:
        - temperature=0.0: Most deterministic output, confirmed supported by qwen-2.5-coder-32b-instruct.
        - response_format json_object: Confirmed supported by qwen-2.5-coder-32b-instruct via /models catalog.
          When use_json_mode=False (e.g. for the delimited-block retry), json mode is skipped.
        """
        headers = self._get_headers()
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": settings.OPENROUTER_MAX_TOKENS,
        }
        if settings.OPENROUTER_PROVIDER_ORDER:
            providers = [p.strip() for p in settings.OPENROUTER_PROVIDER_ORDER.split(",") if p.strip()]
            if providers:
                payload["provider"] = {
                    "order": providers,
                    "allow_fallbacks": False,
                }
        if use_json_mode:
            payload["response_format"] = {"type": "json_object"}


        try:
            async with httpx.AsyncClient(timeout=float(self.timeout)) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )

                if response.status_code == 401:
                    raise OpenRouterAuthError()
                elif response.status_code == 429:
                    raise OpenRouterRateLimitError()
                elif response.status_code == 404:
                    raise OpenRouterModelUnavailableError(
                        f"Model '{self.model}' not found on OpenRouter."
                    )
                elif response.status_code == 503:
                    raise OpenRouterModelUnavailableError()
                elif response.status_code >= 400:
                    error_detail = response.text
                    raise OpenRouterNetworkError(
                        f"OpenRouter returned error {response.status_code}: {error_detail}"
                    )

                data = response.json()
                choices = data.get("choices", [])
                if not choices:
                    raise OpenRouterNetworkError("OpenRouter response did not contain choices.")

                message = choices[0].get("message", {})
                content = message.get("content", "")
                if not content or not content.strip():
                    raise OpenRouterNetworkError("OpenRouter assistant message content was empty.")

                return content

        except httpx.TimeoutException as exc:
            raise OpenRouterTimeoutError() from exc
        except (httpx.ConnectError, httpx.RequestError) as exc:
            raise OpenRouterNetworkError(f"Connection failure: {str(exc)}") from exc
