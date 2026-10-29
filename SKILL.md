---
name: legalone
description: Look up French companies from public registers (INSEE Sirene, INPI RNE, DILA BODACC) with the free LegalOne API or MCP server, and handle French legal notices (annonces légales). Use when a task involves a SIREN or SIRET, pre-filling a business customer's onboarding form, a company's identity, head office, establishments, share capital or current officers (name and role), its BODACC notices (entreprise française, fiche société, avis BODACC), normalizing a French postal address (Base Adresse Nationale), or a legal notice to publish after a corporate event (transfert de siège, changement de gérant, dissolution…): which notices, regulated price, next steps, draft on legalone.fr. Not for KYC, people searches, contact details or financial statements.
---

# LegalOne API and MCP: French company data

Read-only, free, with quotas. Public registers only: INSEE Sirene, INPI RNE, DILA BODACC, and the Base Adresse Nationale for addresses.

## When to use it

- The user gives a company name, a SIREN (9 digits) or a SIRET (14 digits) and wants to identify the company or read its profile.
- Pre-filling a business customer's onboarding form from a SIREN: name, legal form code, NAF code, head-office address, share capital, officers.
- Checking a company's recent BODACC notices (creation, changes, sale of business, insolvency proceedings, removal).
- Checking, completing, normalizing or geolocating a French postal address.
- A French company must publish a legal notice (annonce légale) after a corporate event: which notices, how many, where, the regulated price, the next steps, and a draft prepared on legalone.fr.

Do not use it for: people searches, contact details (e-mail, phone), financial statements, beneficial owners, companies outside France, listing companies by sector or area, or as a regulatory identity check.

## Two ways in

| | MCP server | REST API |
|---|---|---|
| Address | `https://mcp.legalone.fr/mcp` (Streamable HTTP) | `https://api.legalone.fr` |
| Authentication | none | key required on every `/v1` route: `Authorization: Bearer lo_…` (or `X-API-Key`) |
| Quotas | 60 requests/min and 1,000/day per IP | free key: 60/min, 5,000/day, 100,000/month; search 20/min |
| Best for | an assistant answering a user | an application (onboarding, back office) |

Free key: create a developer account at https://www.legalone.fr/developers#compte, then create the key in the developer space (https://api.legalone.fr/compte). Keep the key server-side; never print it, commit it or put it in client code. A higher quota can be requested for free from the developer space.

## MCP tools

| Tool | Input | Use |
|---|---|---|
| `search_companies` | `query` (name, SIREN or SIRET), `page`, `limit` | find a company; name match is a prefix of the official name |
| `get_company` | `siren` | company profile: identity, head office, establishments, capital, officers (name and role) |
| `get_establishment` | `siret` | one establishment: address, activity, status |
| `list_bodacc_notices` | `siren`, `limit` | latest BODACC notices (20 max) |
| `get_bodacc_notice` | `id` | content of one notice |
| `list_company_documents` | `siren` | deeds and accounts filings at the INPI (metadata and link) |
| `search_addresses` | `address`, `postcode`, `limit` | best Base Adresse Nationale matches with coordinates and a reliability status |
| `get_legal_notice_price` | `formality`, `department`, `text` | regulated price of a legal notice, excl. and incl. VAT |
| `which_legal_notice` | `situations`, `legalForm`, `department`, `newDepartment`… | notices an event requires: count, department, deadline, legal basis, price |
| `get_next_steps` | `formality` | filing on the one-stop shop (INPI), BODACC, documents to prepare |
| `prepare_legal_notice` | `formality`, `siren`, facts of the decision | draft on legalone.fr: notice text, what is left to complete, link valid 7 days |

## REST endpoints

- `GET /v1/entreprises?q=&page=&per_page=`: search by start of name, or exact SIREN/SIRET (20 per page, 5 pages max)
- `GET /v1/entreprises/{siren}`: company profile
- `GET /v1/etablissements/{siret}`: establishment
- `GET /v1/entreprises/{siren}/bodacc?limit=`: latest BODACC notices
- `GET /v1/bodacc/{id}`: one BODACC notice
- `GET /v1/entreprises/{siren}/documents`: deeds and accounts filings (metadata, INPI link)
- `GET /v1/adresses?q=`: address autocomplete
- `GET /v1/adresses/normaliser?q=`: best match for a full address, `status` = `matched`, `low_confidence` or `not_found`
- `GET /v1/adresses/inverse?lat=&lon=`: nearest addresses to a point
- `GET /v1/annonces/prix?formality=&department=`: regulated price of a legal notice (`POST` with `text` for a notice priced by the character)
- `GET /v1/annonces/quelle-annonce?situations=&department=`: notices an event requires
- `GET /v1/annonces/etapes?formality=`: next steps and documents
- `POST /v1/annonces/brouillons`: draft on legalone.fr, link to the pre-filled form
- `GET /v1/openapi.json` (full contract, no key) and `GET /v1/health` (no key)

Every response is `{ data, meta, links }`; `meta` carries `updatedAt`, `sources`, `warnings` and `attribution`. Errors follow RFC 9457 (`application/problem+json`): 400 bad parameter, 401 missing or invalid key, 404 unknown or not publicly available (opposition, partial INSEE distribution: treat it as "not found", do not retry), 429 quota (wait for `Retry-After`), 503 retry later.

## Examples

SIREN → pre-filled onboarding form (one call):

```bash
curl -s https://api.legalone.fr/v1/entreprises/552032534 \
  -H "Authorization: Bearer $LEGALONE_API_KEY"
```

Map `data.name`, `data.legalFormCode` (INSEE legal category code), `data.activityCode` (NAF), `data.headOffice.address` (prefer `address.normalized.label` when present), `data.capital.amount` and `data.officers[].name` / `role`. Show the form to the user to confirm or correct; on 404, fall back to manual entry.

BODACC notices of a company: MCP `list_bodacc_notices` with `{ "siren": "552032534", "limit": 5 }`, or:

```bash
curl -s "https://api.legalone.fr/v1/entreprises/552032534/bodacc?limit=5" \
  -H "Authorization: Bearer $LEGALONE_API_KEY"
```

Each notice has `family`, `noticeType`, `publicationDate`, `court` and `links.official` (bodacc.fr). Quote the official link when you report a notice.

Address: MCP `search_addresses` with `{ "address": "8 bd du Port Amiens" }`, or:

```bash
curl -s --get https://api.legalone.fr/v1/adresses/normaliser \
  --data-urlencode "q=8 boulevard du Port 80000 Amiens" \
  -H "Authorization: Bearer $LEGALONE_API_KEY"
```

Only use `data.address` when `data.status` is `matched`; otherwise offer the `alternatives` to the user.

## Legal notices (annonces légales)

1. `which_legal_notice` with the event(s) and the department of the registered office: it returns the notices, their legal basis and price, or a `question` to ask the user (for example whether a new office depends on the same commercial court). Ask it; do not guess.
2. `prepare_legal_notice` with the SIREN and the facts the user gave (decision body and date, new address, names of the officers): it returns the notice text (`preview`), what is left to complete (`missing`) and a link. Give the user the link and the text.
3. The user reviews, completes and pays on legalone.fr. Nothing is paid in the chat; never collect payment details. Do not send home addresses, birth dates or contact details: they are completed on the site.
4. `get_next_steps` for the filing on the one-stop shop and the documents.

The price is set by ministerial order and is the same in every authorised newspaper of the department. The rules and steps are indicative; say so and suggest a legal professional when the situation is unusual.

## Limits

- Not a regulatory KYC source. The data pre-fills and enriches; it does not replace the identity check required by article L.561-5 of the French monetary and financial code: verify on a Kbis or RNE extract.
- Personal data is limited to an officer's name and role. No contact details, no home address, no people search. Month and year of birth (`birth`, `YYYY-MM`) only with an extended-access key, granted after human review to verified accounts with a KYC, fraud, compliance or research purpose; never through MCP.
- When `commercialProspectingAllowed` is `false`, the terms forbid using that company for commercial prospecting.
- Not covered: financial statements, beneficial owners, annual accounts content.

## Attribution

Display `meta.attribution` next to the data, as is. For company data it reads:

> Données : LegalOne — sources INSEE Sirene, INPI RNE, DILA BODACC, mise à jour le {date}

where `{date}` is `meta.updatedAt` as DD/MM/YYYY. Terms: https://www.legalone.fr/developers/conditions. Full map: https://api.legalone.fr/llms.txt.
