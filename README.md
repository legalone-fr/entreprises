# LegalOne Entreprises

[Français](README.fr.md)

A free, read-only REST API and a keyless MCP server for public data on French companies, plus helper tools for French legal notices (annonces légales).

- **Companies**: identity, head office, establishments, share capital, current officers (name and role), from INSEE Sirene and INPI RNE.
- **BODACC notices**: latest notices of a company (creation, changes, sale of a business, insolvency proceedings, removal) and deeds and accounts filings listed at the INPI.
- **Addresses**: autocomplete, normalisation and reverse geocoding with the Base Adresse Nationale.
- **Legal notices**: which notices a corporate event requires, their legal basis and regulated rate, next steps, and a draft that the user reviews and publishes on legalone.fr.

The MCP server is listed as **LegalOne Entreprises** (a different, unrelated product is named "LegalOne" in the MCP registry).

This repository holds the public client material only: an [agent skill](SKILL.md), two single-file SDKs ([TypeScript](sdk/typescript/legalone.ts), [Python](sdk/python/legalone.py)) and the [MCP registry manifest](server.json).

## MCP server

| | |
|---|---|
| URL | `https://mcp.legalone.fr/mcp` |
| Transport | Streamable HTTP |
| Authentication | none |
| Quota | 60 requests/min and 1,000/day per IP |

Tools: `search_companies`, `get_company`, `get_establishment`, `list_bodacc_notices`, `get_bodacc_notice`, `list_company_documents`, `search_addresses`, `get_legal_notice_price`, `which_legal_notice`, `get_next_steps`, `prepare_legal_notice`. All are read-only except `prepare_legal_notice`, which saves a draft on legalone.fr. Nothing is paid in the chat.

**Claude (claude.ai and Claude Desktop)**: Settings > Connectors > Add custom connector, name `LegalOne Entreprises`, URL `https://mcp.legalone.fr/mcp`, no authentication. Connectors added on claude.ai are also available in Claude Desktop.

**Claude Code**:

```bash
claude mcp add --transport http legalone-entreprises https://mcp.legalone.fr/mcp
```

**ChatGPT**: Settings > Apps & Connectors > Advanced settings, turn on developer mode, then create a connector with the URL `https://mcp.legalone.fr/mcp` and no authentication. Availability depends on your ChatGPT plan; menu names may change.

**Other clients** that accept a remote server:

```json
{
  "mcpServers": {
    "legalone-entreprises": { "url": "https://mcp.legalone.fr/mcp" }
  }
}
```

Clients that only speak stdio can go through a bridge such as `npx -y mcp-remote https://mcp.legalone.fr/mcp`.

## REST API

| | |
|---|---|
| Base URL | `https://api.legalone.fr/v1` |
| Key | required on every `/v1` route: `Authorization: Bearer lo_…` (or `X-API-Key`). Free: create a developer account at <https://legalone.fr/developers>, then a key in the developer space |
| Contract | <https://api.legalone.fr/v1/openapi.json> (no key) |
| Quota per key | 60 requests/min, 5,000/day, 100,000/month; company search 20/min. A higher quota can be requested from the developer space |

Keep the key server-side; never ship it in client code.

```bash
# Company profile by SIREN
curl -s https://api.legalone.fr/v1/entreprises/552032534 \
  -H "Authorization: Bearer $LEGALONE_API_KEY"

# Search by start of name, or exact SIREN/SIRET
curl -s --get https://api.legalone.fr/v1/entreprises \
  --data-urlencode "q=exemple" -H "Authorization: Bearer $LEGALONE_API_KEY"

# Latest BODACC notices
curl -s "https://api.legalone.fr/v1/entreprises/552032534/bodacc?limit=5" \
  -H "Authorization: Bearer $LEGALONE_API_KEY"

# Normalise an address
curl -s --get https://api.legalone.fr/v1/adresses/normaliser \
  --data-urlencode "q=8 boulevard du Port 80000 Amiens" \
  -H "Authorization: Bearer $LEGALONE_API_KEY"
```

Every response is `{ data, meta, links }`; `meta` carries `updatedAt`, `sources`, `warnings` and `attribution`. Errors use RFC 9457 (`application/problem+json`): 400 bad parameter, 401 missing or invalid key, 404 unknown or not publicly available (treat as "not found", do not retry), 429 quota exceeded (wait for `Retry-After`), 503 retry later. The full list of routes is in the OpenAPI contract and in [SKILL.md](SKILL.md).

## SDKs

Each SDK is one file with no dependency: copy it into your project.

```ts
// sdk/typescript/legalone.ts — native fetch (Node 18+, browsers, Deno, Bun)
import { LegalOne } from "./legalone.ts";

const api = new LegalOne({ apiKey: process.env.LEGALONE_API_KEY! });
const company = await api.getCompany("552032534"); // null if not found
console.log(company?.data.name, company?.meta.attribution);
```

```python
# sdk/python/legalone.py — standard library only, Python 3.9+
from legalone import LegalOne

api = LegalOne(api_key="lo_...")
company = api.get_company("552032534")  # None if not found
if company:
    print(company["data"]["name"], company["meta"]["attribution"])
```

Methods: `getCompany` / `get_company`, `getEstablishment`, `searchCompanies`, `listBodaccNotices`, `getBodaccNotice`, `listCompanyDocuments`, `health`. Errors raise `LegalOneError` (status, title, detail, request id, retry delay on 429). Code comments and error messages are in French.

Python tests (local loopback server, no network): `cd sdk/python && python3 -m unittest -v`.

## Agent skill

[SKILL.md](SKILL.md) tells an agent when and how to use the API or the MCP server. Claude Code: copy it to `.claude/skills/legalone/SKILL.md`. Other agents: point them to <https://api.legalone.fr/skill.md>.

## Data sources and licences

| Source | Licence |
|---|---|
| INSEE Sirene | Licence Ouverte 2.0 |
| INPI RNE | INPI licence for reuse of the RNE (2024) |
| DILA BODACC | Licence Ouverte 2.0 |
| Base Adresse Nationale | Licence Ouverte 2.0 |
| Légifrance (legal-notice rules) | Licence Ouverte 2.0 |

Each response lists the sources actually used, with their update date, in `meta.sources`.

## Attribution (required)

Display `meta.attribution` next to the data, as is. For company data it reads:

> Données : LegalOne — sources INSEE Sirene, INPI RNE, DILA BODACC, mise à jour le {date}

`{date}` is `meta.updatedAt` as DD/MM/YYYY; "LegalOne" links to the company page (`data.links.legalone`) or to <https://legalone.fr>. Address routes read `Adresses : Base Adresse Nationale (BAN), Licence Ouverte 2.0 — via LegalOne`. Do not present the data as certified by INPI or INSEE.

## Limits

- The data is for pre-filling and enrichment. It is **not** a regulatory identity (KYC) source and not legal proof: verify on an official Kbis or RNE extract.
- Personal data is limited to an officer's name and role. No contact details, no people search, no financial statements, no beneficial owners.
- Companies whose data is not publicly distributed, and companies or people who objected to publication on LegalOne, are not served.
- Legal-notice rules and steps are indicative; ask a legal professional when a situation is unusual.

## Terms, privacy, support

- Terms of use: <https://legalone.fr/developers/conditions>
- Privacy: <https://legalone.fr/developers/conditions#confidentialite>
- Objection (GDPR) or correction request: <https://legalone.fr/developers/opposition>
- Support: api@legalone.fr

## Licence

The code and documentation in this repository are under the [MIT licence](LICENSE). Data returned by the API remains under the source licences above and the LegalOne terms of use.
