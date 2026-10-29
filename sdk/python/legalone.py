"""Client Python de l'API publique LegalOne (https://api.legalone.fr).

Licence MIT : copiez, modifiez et redistribuez ce fichier librement.

ATTRIBUTION OBLIGATOIRE : les données servies par l'API ne sont réutilisables
qu'avec la mention prévue par les conditions d'utilisation, affichée près des
données (champ ``meta["attribution"]`` de chaque réponse) :
« Données : LegalOne — sources INSEE Sirene, INPI RNE, DILA BODACC,
mise à jour le {date} ». Voir https://www.legalone.fr/developers/conditions.

CLÉ D'API OBLIGATOIRE : toute requête (sauf ``health()``) exige une clé gratuite.
Créez un compte développeur sur https://www.legalone.fr/developers#compte, puis
générez la clé dans l'espace développeur (https://api.legalone.fr/compte).

Bibliothèque standard uniquement (``urllib``, ``json``), Python 3.9 ou plus.

    from legalone import LegalOne

    api = LegalOne(api_key="lo_...")        # la clé est obligatoire
    societe = api.get_company("552032534")  # None si introuvable
    if societe:
        print(societe["data"]["name"], societe["meta"]["attribution"])

Pré-remplir et enrichir l'onboarding de vos clients professionnels : à partir du
SIREN saisi, proposez un formulaire déjà rempli que le client confirme.

    def pre_remplir(api, siren):
        societe = api.get_company(siren)
        if societe is None:  # SIREN inconnu ou non diffusable : saisie manuelle
            return None
        data = societe["data"]
        siege = (data["headOffice"] or {}).get("address") or {}
        normalisee = siege.get("normalized")  # Base Adresse Nationale, ou None
        return {
            "nom": data["name"],
            "forme_juridique": data["legalFormCode"],
            "code_activite": data["activityCode"],
            "adresse": normalisee["label"] if normalisee else " ".join(
                p for p in (siege.get("line"), siege.get("postalCode"), siege.get("city")) if p
            ),
            "capital": (data["capital"] or {}).get("amount"),
            "dirigeants": [{"nom": d["name"], "fonction": d["role"]} for d in data["officers"]],
            "attribution": societe["meta"]["attribution"],  # à afficher près des données
        }

Ces données servent à pré-remplir et enrichir ; elles ne remplacent pas la
vérification réglementaire (article L.561-5 du code monétaire et financier) :
vérifiez sur un extrait Kbis ou RNE.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

__all__ = ["LegalOne", "LegalOneError", "DEFAULT_BASE_URL"]

DEFAULT_BASE_URL = "https://api.legalone.fr"
DEFAULT_TIMEOUT = 10.0


class LegalOneError(Exception):
    """Erreur renvoyée par l'API (problème RFC 9457) ou échec réseau.

    Attributs :
        status: code HTTP (0 pour une erreur réseau ou un délai dépassé).
        type: URI du type de problème.
        title: titre court, en français.
        detail: explication destinée au développeur.
        request_id: identifiant de requête, à communiquer au support.
        retry_after_seconds: délai conseillé avant de réessayer (429, 503).
    """

    def __init__(
        self,
        status: int,
        title: str,
        detail: str,
        type: str = "about:blank",
        request_id: Optional[str] = None,
        retry_after_seconds: Optional[int] = None,
    ) -> None:
        super().__init__(f"{status} {title} : {detail}")
        self.status = status
        self.title = title
        self.detail = detail
        self.type = type
        self.request_id = request_id
        self.retry_after_seconds = retry_after_seconds


def _to_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    value = value.strip()
    return int(value) if value.isdigit() else None


def _read_rate_limit(headers: Any) -> Optional[Dict[str, int]]:
    limit = _to_int(headers.get("X-RateLimit-Limit"))
    remaining = _to_int(headers.get("X-RateLimit-Remaining"))
    reset = _to_int(headers.get("X-RateLimit-Reset"))
    if limit is None or remaining is None or reset is None:
        return None
    return {"limit": limit, "remaining": remaining, "reset_seconds": reset}


class LegalOne:
    """Client de lecture de l'API LegalOne.

    Les méthodes de lecture renvoient l'enveloppe JSON de l'API sous forme de
    ``dict`` : ``{"data": ..., "meta": {...}, "links": {...}}``. Les lectures
    unitaires renvoient ``None`` quand la ressource est introuvable ou non
    diffusable (404). Toute autre erreur lève :class:`LegalOneError`.

    Arguments :
        api_key: clé d'API (``lo_...``), obligatoire (``ValueError`` si elle
            est vide). Gratuite : https://www.legalone.fr/developers#compte
        base_url: racine de l'API (défaut : https://api.legalone.fr).
        timeout: délai maximal par requête, en secondes (défaut : 10).

    Après chaque appel, ``rate_limit`` contient la fenêtre de quota la plus
    contrainte (``limit``, ``remaining``, ``reset_seconds``), lue dans les
    en-têtes ``X-RateLimit-*``.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError(
                "api_key est obligatoire : créez un compte développeur gratuit sur "
                "https://www.legalone.fr/developers#compte, puis générez une clé "
                "dans l'espace développeur."
            )
        base_url = base_url.rstrip("/")
        # urllib accepte aussi file:// et ftp:// : on les refuse explicitement.
        if urllib.parse.urlsplit(base_url).scheme not in ("http", "https"):
            raise ValueError("base_url doit commencer par http:// ou https://")
        self.api_key = api_key.strip()
        self.base_url = base_url
        self.timeout = timeout
        self.rate_limit: Optional[Dict[str, int]] = None

    def get_company(self, siren: str) -> Optional[Dict[str, Any]]:
        """Fiche d'une entreprise à partir de son SIREN (9 chiffres).

        Renvoie ``None`` si l'entreprise est introuvable ou non diffusable.
        """
        return self._get("/v1/entreprises/" + _segment(siren), None, True)

    def get_establishment(self, siret: str) -> Optional[Dict[str, Any]]:
        """Un établissement à partir de son SIRET (14 chiffres).

        Renvoie ``None`` s'il est introuvable ou non diffusable.
        """
        return self._get("/v1/etablissements/" + _segment(siret), None, True)

    def search_companies(
        self,
        q: str,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Recherche par début de nom, ou par SIREN/SIRET exact.

        20 résultats par page au plus, 5 pages au maximum. Une recherche sans
        résultat renvoie une liste vide, jamais ``None``.
        """
        result = self._get(
            "/v1/entreprises", {"q": q, "page": page, "per_page": per_page}, False
        )
        assert result is not None
        return result

    def list_bodacc_notices(
        self, siren: str, limit: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Derniers avis BODACC d'une entreprise (résumés, plus récent d'abord).

        Renvoie ``None`` si l'entreprise est introuvable.
        """
        return self._get(
            "/v1/entreprises/" + _segment(siren) + "/bodacc", {"limit": limit}, True
        )

    def get_bodacc_notice(self, notice_id: str) -> Optional[Dict[str, Any]]:
        """Un avis BODACC filtré (ex. ``A202601950001``).

        Renvoie ``None`` s'il est introuvable.
        """
        return self._get("/v1/bodacc/" + _segment(notice_id), None, True)

    def list_company_documents(self, siren: str) -> Optional[Dict[str, Any]]:
        """Métadonnées des actes et dépôts de comptes (liens vers l'INPI).

        Renvoie ``None`` si l'entreprise est introuvable.
        """
        return self._get("/v1/entreprises/" + _segment(siren) + "/documents", None, True)

    def health(self) -> Dict[str, Any]:
        """État du service et fraîcheur des données."""
        result = self._get("/v1/health", None, False)
        assert result is not None
        return result

    def _get(
        self,
        path: str,
        query: Optional[Dict[str, Any]],
        none_on_404: bool,
    ) -> Optional[Dict[str, Any]]:
        url = self.base_url + path
        params = {k: v for k, v in (query or {}).items() if v is not None}
        if params:
            url += "?" + urllib.parse.urlencode(params)
        headers = {
            "Accept": "application/json",
            "User-Agent": "legalone-python",
            "Authorization": "Bearer " + self.api_key,
        }
        request = urllib.request.Request(url, headers=headers, method="GET")  # noqa: S310
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:  # noqa: S310
                self.rate_limit = _read_rate_limit(response.headers) or self.rate_limit
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            self.rate_limit = _read_rate_limit(error.headers) or self.rate_limit
            try:
                if error.code == 404 and none_on_404:
                    return None
                raise self._to_error(error) from None
            finally:
                error.close()
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            reason = getattr(error, "reason", error)
            raise LegalOneError(0, "Erreur réseau", str(reason)) from error

    def _to_error(self, error: urllib.error.HTTPError) -> LegalOneError:
        raw = error.read().decode("utf-8", errors="replace")
        body: Dict[str, Any] = {}
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                body = parsed
        except ValueError:
            pass  # corps non JSON (proxy, page d'erreur) : on garde le texte brut
        retry_after = _to_int(error.headers.get("Retry-After"))
        if retry_after is None and error.code == 429 and self.rate_limit:
            retry_after = self.rate_limit["reset_seconds"]
        return LegalOneError(
            status=body["status"] if isinstance(body.get("status"), int) else error.code,
            title=str(body.get("title") or error.reason or "Erreur"),
            detail=str(body["detail"]) if "detail" in body else raw[:200],
            type=str(body.get("type") or "about:blank"),
            request_id=body.get("requestId") or error.headers.get("X-Request-Id"),
            retry_after_seconds=retry_after,
        )


def _segment(value: str) -> str:
    """Encode un identifiant pour l'insérer dans un chemin d'URL."""
    return urllib.parse.quote(str(value), safe="")
