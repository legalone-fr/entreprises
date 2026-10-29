"""Tests du client Python : serveur HTTP local, réponses fixes."""

import json
import socketserver
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from legalone import LegalOne, LegalOneError

COMPANY = {
    "data": {
        "siren": "100000001",
        "name": "Exemple Un SAS",
        "legalFormCode": "5710",
        "activityCode": "62.01Z",
        "headOffice": {
            "address": {
                "line": "8 boulevard du Port",
                "postalCode": "80000",
                "city": "Amiens",
                "normalized": {"label": "8 Boulevard du Port 80000 Amiens"},
            }
        },
        "capital": {"amount": 10000},
        "officers": [
            {"id": "dirigeant-1", "name": "Exemple Holding", "role": "Président", "type": "company"},
            {"id": "dirigeant-2", "name": "Camille Exemple", "role": "Directeur général", "type": "person"},
        ],
    },
    "meta": {"attribution": "Données : LegalOne — sources INSEE Sirene"},
    "links": {},
}
RATE_HEADERS = {
    "X-RateLimit-Limit": "30",
    "X-RateLimit-Remaining": "29",
    "X-RateLimit-Reset": "42",
}


def problem(status, title, detail, **extra):
    return {
        "type": "https://api.legalone.fr/problems/x",
        "title": title,
        "status": status,
        "detail": detail,
        "requestId": "req-test-0001",
        **extra,
    }


# chemin -> (statut, en-têtes, corps JSON ou texte)
ROUTES = {
    "/v1/entreprises/100000001": (200, RATE_HEADERS, COMPANY),
    "/v1/entreprises/100000001/bodacc": (200, {}, {"data": [{"id": "A202601950001"}]}),
    "/v1/entreprises/100000001/documents": (200, {}, {"data": [{"id": "document-exemple-1"}]}),
    "/v1/entreprises": (200, {}, {"data": [{"siren": "100000001"}], "meta": {"page": 1}}),
    "/v1/etablissements/10000000100010": (200, {}, {"data": {"siret": "10000000100010"}}),
    "/v1/bodacc/A202601950001": (200, {}, {"data": {"id": "A202601950001"}}),
    "/v1/health": (200, {}, {"data": {"status": "ok"}}),
    "/v1/entreprises/123": (
        400, {}, problem(400, "Paramètre invalide", "Le SIREN doit contenir 9 chiffres.")
    ),
    "/v1/entreprises/200000002": (
        429,
        {"Retry-After": "12", **RATE_HEADERS, "X-RateLimit-Remaining": "0"},
        problem(429, "Quota dépassé", "Quota atteint."),
    ),
    "/v1/entreprises/300000003": (502, {}, "<h1>Bad gateway</h1>"),
}


class Handler(BaseHTTPRequestHandler):
    requests = []  # (chemin, requête, en-têtes) vus par le serveur

    def do_GET(self):  # noqa: N802 - nom imposé par http.server
        parts = urlsplit(self.path)
        Handler.requests.append((parts.path, parse_qs(parts.query), dict(self.headers)))
        status, headers, body = ROUTES.get(
            parts.path, (404, {}, problem(404, "Ressource introuvable", "introuvable ou non diffusable."))
        )
        payload = body if isinstance(body, str) else json.dumps(body)
        content_type = "text/html" if isinstance(body, str) else "application/json"
        data = payload.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        for name, value in headers.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):  # silence
        pass


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True

    def server_bind(self):
        # HTTPServer.server_bind appelle getfqdn(), qui peut bloquer ~35 s
        # sans DNS inverse : inutile pour un serveur de test en boucle locale.
        socketserver.TCPServer.server_bind(self)
        self.server_name = "127.0.0.1"
        self.server_port = self.server_address[1]


class LegalOneTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = LocalServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = "http://127.0.0.1:%d" % cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        Handler.requests.clear()
        self.api = LegalOne(api_key="lo_exemple", base_url=self.base_url, timeout=5)

    def test_get_company(self):
        result = self.api.get_company("100000001")
        self.assertEqual(result["data"]["name"], "Exemple Un SAS")
        self.assertIn("LegalOne", result["meta"]["attribution"])

    def test_get_establishment(self):
        self.assertEqual(self.api.get_establishment("10000000100010")["data"]["siret"], "10000000100010")

    def test_search_companies_sends_query(self):
        result = self.api.search_companies("exemple société", page=2, per_page=5)
        self.assertEqual(result["data"][0]["siren"], "100000001")
        _, query, _ = Handler.requests[-1]
        self.assertEqual(query, {"q": ["exemple société"], "page": ["2"], "per_page": ["5"]})

    def test_search_companies_without_options_sends_only_q(self):
        self.api.search_companies("exemple")
        _, query, _ = Handler.requests[-1]
        self.assertEqual(query, {"q": ["exemple"]})

    def test_list_bodacc_notices_passes_limit(self):
        result = self.api.list_bodacc_notices("100000001", limit=3)
        self.assertEqual(result["data"][0]["id"], "A202601950001")
        self.assertEqual(Handler.requests[-1][1], {"limit": ["3"]})

    def test_get_bodacc_notice(self):
        self.assertEqual(self.api.get_bodacc_notice("A202601950001")["data"]["id"], "A202601950001")

    def test_list_company_documents(self):
        self.assertEqual(self.api.list_company_documents("100000001")["data"][0]["id"], "document-exemple-1")

    def test_health(self):
        self.assertEqual(self.api.health()["data"]["status"], "ok")

    def test_404_returns_none_for_unit_reads(self):
        self.assertIsNone(self.api.get_company("999999999"))
        self.assertIsNone(self.api.get_establishment("99999999999999"))
        self.assertIsNone(self.api.get_bodacc_notice("A209999999999"))
        self.assertIsNone(self.api.list_bodacc_notices("999999999"))
        self.assertIsNone(self.api.list_company_documents("999999999"))

    def test_400_raises_with_problem_details(self):
        with self.assertRaises(LegalOneError) as caught:
            self.api.get_company("123")
        error = caught.exception
        self.assertEqual(error.status, 400)
        self.assertEqual(error.title, "Paramètre invalide")
        self.assertEqual(error.detail, "Le SIREN doit contenir 9 chiffres.")
        self.assertEqual(error.request_id, "req-test-0001")
        self.assertIsNone(error.retry_after_seconds)

    def test_429_carries_retry_after_and_rate_limit(self):
        with self.assertRaises(LegalOneError) as caught:
            self.api.get_company("200000002")
        self.assertEqual(caught.exception.status, 429)
        self.assertEqual(caught.exception.retry_after_seconds, 12)
        self.assertEqual(self.api.rate_limit, {"limit": 30, "remaining": 0, "reset_seconds": 42})

    def test_rate_limit_after_success(self):
        self.assertIsNone(self.api.rate_limit)
        self.api.get_company("100000001")
        self.assertEqual(self.api.rate_limit, {"limit": 30, "remaining": 29, "reset_seconds": 42})

    def test_non_json_error_body(self):
        with self.assertRaises(LegalOneError) as caught:
            self.api.get_company("300000003")
        self.assertEqual(caught.exception.status, 502)
        self.assertEqual(caught.exception.detail, "<h1>Bad gateway</h1>")

    def test_authorization_header_is_always_sent(self):
        LegalOne(api_key="lo_autre", base_url=self.base_url).get_company("100000001")
        self.assertEqual(Handler.requests[-1][2].get("Authorization"), "Bearer lo_autre")
        self.api.search_companies("exemple")
        self.assertEqual(Handler.requests[-1][2].get("Authorization"), "Bearer lo_exemple")

    def test_api_key_is_required(self):
        with self.assertRaises(TypeError):
            LegalOne()  # type: ignore[call-arg]
        for vide in ("", "   ", None):
            with self.assertRaises(ValueError) as caught:
                LegalOne(api_key=vide)  # type: ignore[arg-type]
            self.assertIn("api_key est obligatoire", str(caught.exception))
            self.assertIn("https://www.legalone.fr/developers#compte", str(caught.exception))

    def test_onboarding_prefill_from_a_company(self):
        # Même logique que l'exemple de la docstring de legalone.py.
        societe = self.api.get_company("100000001")
        data = societe["data"]
        siege = (data["headOffice"] or {}).get("address") or {}
        normalisee = siege.get("normalized")
        prefill = {
            "nom": data["name"],
            "forme_juridique": data["legalFormCode"],
            "code_activite": data["activityCode"],
            "adresse": normalisee["label"] if normalisee else " ".join(
                p for p in (siege.get("line"), siege.get("postalCode"), siege.get("city")) if p
            ),
            "capital": (data["capital"] or {}).get("amount"),
            "dirigeants": [{"nom": d["name"], "fonction": d["role"]} for d in data["officers"]],
            "attribution": societe["meta"]["attribution"],
        }
        self.assertEqual(prefill["nom"], "Exemple Un SAS")
        self.assertEqual(prefill["forme_juridique"], "5710")
        self.assertEqual(prefill["adresse"], "8 Boulevard du Port 80000 Amiens")
        self.assertEqual(prefill["capital"], 10000)
        self.assertEqual(prefill["dirigeants"][1], {"nom": "Camille Exemple", "fonction": "Directeur général"})
        self.assertIn("LegalOne", prefill["attribution"])

    def test_network_failure_raises(self):
        server = LocalServer(("127.0.0.1", 0), Handler)
        port = server.server_address[1]
        server.server_close()  # port désormais fermé
        with self.assertRaises(LegalOneError) as caught:
            LegalOne(api_key="lo_exemple", base_url="http://127.0.0.1:%d" % port, timeout=2).health()
        self.assertEqual(caught.exception.status, 0)

    def test_base_url_scheme_is_checked(self):
        with self.assertRaises(ValueError):
            LegalOne(api_key="lo_exemple", base_url="file:///etc/passwd")

    def test_default_base_url(self):
        self.assertEqual(LegalOne(api_key="lo_exemple").base_url, "https://api.legalone.fr")


if __name__ == "__main__":
    unittest.main()
