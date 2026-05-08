"""
ai/web_search.py — Recherche web via DuckDuckGo (sans clé API).

Utilise duckduckgo_search si installé, sinon l'API Instant Answer en fallback.
pip install duckduckgo_search
"""

import httpx
from utils.logger import print_system, print_error


class WebSearch:
    """Effectue des recherches web et retourne des résultats formatés pour l'IA."""

    INSTANT_URL = "https://api.duckduckgo.com/"

    def search(self, query: str, max_results: int = 4) -> str:
        """
        Cherche sur DuckDuckGo et retourne un texte structuré.

        Args:
            query:       Requête de recherche
            max_results: Nombre maximum de résultats à retourner

        Returns:
            str — Résultats formatés (titre + extrait + URL)
        """
        if not query.strip():
            return "Requête vide."

        print_system(f"Recherche web : {query!r}")

        try:
            return self._search_library(query, max_results)
        except ImportError:
            return self._search_instant(query)
        except Exception as e:
            print_error(f"WebSearch — erreur : {e}")
            # Fallback sur l'API instant
            try:
                return self._search_instant(query)
            except Exception:
                return f"Recherche impossible pour '{query}'."

    def _search_library(self, query: str, max_results: int) -> str:
        """Utilise la bibliothèque duckduckgo_search (résultats organiques)."""
        from duckduckgo_search import DDGS

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(r)

        if not results:
            return f"Aucun résultat trouvé pour '{query}'."

        lines = [f"Résultats web pour : {query}\n"]
        for i, r in enumerate(results, 1):
            title = r.get("title", "").strip()
            body  = r.get("body",  "").strip()[:250]
            url   = r.get("href",  "")
            lines.append(f"[{i}] {title}")
            if body:
                lines.append(f"    {body}")
            lines.append(f"    → {url}\n")

        return "\n".join(lines)

    def _search_instant(self, query: str) -> str:
        """
        Fallback : DuckDuckGo Instant Answer API.
        Fonctionne sans bibliothèque externe, mais ne retourne que des
        réponses directes (calculs, définitions, infos Wikipedia).
        """
        try:
            resp = httpx.get(
                self.INSTANT_URL,
                params={
                    "q":              query,
                    "format":         "json",
                    "no_html":        "1",
                    "skip_disambig":  "1",
                },
                timeout=5.0,
                headers={"User-Agent": "Boxy-Assistant/1.0"},
            )
            data = resp.json()

            # Réponse directe (calcul, conversion, etc.)
            answer = data.get("Answer", "")
            if answer:
                return f"Réponse directe pour '{query}' : {answer}"

            # Extrait Wikipedia / résumé
            abstract = data.get("AbstractText", "")
            src_url  = data.get("AbstractURL",  "")
            if abstract:
                return f"{abstract}\nSource : {src_url}"

            # Résultats liés
            related = data.get("RelatedTopics", [])[:3]
            if related:
                lines = [f"Résultats pour '{query}' :"]
                for item in related:
                    if isinstance(item, dict) and "Text" in item:
                        lines.append(f"• {item['Text'][:200]}")
                return "\n".join(lines)

            return (
                f"Aucun résultat instantané pour '{query}'.\n"
                "Installe duckduckgo_search pour de meilleurs résultats : "
                "pip install duckduckgo_search"
            )

        except Exception as e:
            return f"Erreur recherche instantanée : {e}"
