import os
import json
import logging
import hashlib
from typing import Optional, Dict, Any, Tuple, List
import httpx
import redis.asyncio as redis
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
try:
    redis_client = redis.from_url(redis_url, decode_responses=True)
except Exception as e:
    logger.warning(f"Could not connect to Redis: {e}")
    redis_client = None


class LLMClient:
    """
    Client d'inférence hybride et économe en ressources.
    - SLM Local (Qwen 2.5 3B via Ollama) : Utilisé pour 80%+ des flux, optimisé faible mémoire.
    - Teacher Distant (Groq) : Utilisé en escalade pour cas ambigus ou complexes.
    """

    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "ollama").lower()

        # Ollama config (local SLM)
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

        # Groq config (Teacher / Escalade)
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        self.groq_model = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")

        self.model = self.groq_model if self.provider == "groq" else self.ollama_model

    async def call_slm(self, system_prompt: str, user_text: str) -> Optional[Dict[str, Any]]:
        """
        Appel optimisé au SLM local (Qwen 2.5 3B).
        Applique un contexte borné (num_ctx=2048) et un keep_alive pour limiter la mémoire.
        """
        full_prompt = f"{system_prompt}\n\n{user_text}"
        
        # Vérification cache Redis
        if redis_client:
            prompt_hash = hashlib.md5(full_prompt.encode("utf-8")).hexdigest()
            cache_key = f"llm_cache:slm:{self.ollama_model}:{prompt_hash}"
            try:
                cached = await redis_client.get(cache_key)
                if cached:
                    logger.info("SLM cache hit!")
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Redis cache read error: {e}")

        payload = {
            "model": self.ollama_model,
            "prompt": full_prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.0,    # Déterministe
                "top_p": 0.9,
                "num_ctx": 2048,       # Économie majeure de RAM (~60% de gain)
                "num_predict": 512,    # Réponse compacte
            },
            "keep_alive": "15m"        # Garde le modèle en mémoire active sans pic CPU/disque
        }

        try:
            async with httpx.AsyncClient(timeout=35) as client:
                response = await client.post(f"{self.ollama_url}/api/generate", json=payload)
                response.raise_for_status()
                result = response.json()
                raw_json = result.get("response", "{}")
                parsed = json.loads(raw_json)

                if redis_client and parsed:
                    try:
                        await redis_client.setex(cache_key, 86400, json.dumps(parsed))
                    except Exception:
                        pass
                return parsed
        except Exception as e:
            logger.warning(f"SLM local indisponible ou en échec ({e}), fallback nécessaire.")
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=20))
    async def call_teacher_groq(self, system_prompt: str, user_text: str) -> Optional[Dict[str, Any]]:
        """Appel direct à Groq (Teacher) pour résolution d'ambiguïté."""
        if not self.groq_api_key:
            logger.warning("Clé GROQ_API_KEY non configurée pour l'escalade.")
            return None

        payload = {
            "model": self.groq_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            "temperature": 0.1,
            "top_p": 0.9,
            "response_format": {"type": "json_object"}
        }
        headers = {"Authorization": f"Bearer {self.groq_api_key}"}

        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            return json.loads(content)

    async def call_reflection_teacher(
        self, raw_text: str, slm_draft: Dict[str, Any], issues: List[str], base_prompt: str
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Appel Reflection-Tuning au Teacher (Groq) :
        Explique au Teacher ce que le SLM a produit et les anomalies physiques/structurelles détectées.
        Retourne : (correction_parfaite, explication_reflexion)
        """
        reflection_instruction = f"""Tu es un Senior Lighting Engineer et Teacher IA.
Un modèle léger (SLM) a tenté d'extraire les spécifications techniques du luminaire suivant, mais son extraction présente des anomalies :

TEXTE BRUT ORIGINAL :
\"\"\"{raw_text}\"\"\"

EXTRACTION INITIALE DU SLM :
{json.dumps(slm_draft, ensure_ascii=False, indent=2)}

ANOMALIES ET DOUTES DÉTECTÉS :
{json.dumps(issues, ensure_ascii=False, indent=2)}

MISSION :
1. Révise attentivement le texte brut original.
2. Corrige chaque erreur du SLM.
3. Produis le JSON final rigoureusement conforme au schéma d'extraction.
4. Ajoute une clé '_reflection_rationale' dans le JSON pour expliquer en 1 ou 2 phrases concises pourquoi l'extraction du SLM était inexacte et comment tu l'as corrigée.
"""
        try:
            corrected = await self.call_teacher_groq(base_prompt, reflection_instruction)
            if corrected:
                rationale = corrected.pop("_reflection_rationale", "Correction automatique par Teacher")
                return corrected, rationale
        except Exception as e:
            logger.error(f"Échec de l'appel Reflection Teacher: {e}")

        return None, ""

    async def extract_json_async(self, text: str, system_prompt: str) -> Any:
        """Méthode universelle avec aiguillage dynamique."""
        if self.provider == "groq":
            return await self.call_teacher_groq(system_prompt, text)
        res = await self.call_slm(system_prompt, text)
        if res:
            return res
        return await self.call_teacher_groq(system_prompt, text)


# Alias pour compatibilité
OllamaClient = LLMClient