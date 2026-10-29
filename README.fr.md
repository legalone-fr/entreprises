# LegalOne Entreprises

[English](README.md)

Une API REST gratuite en lecture seule et un serveur MCP sans clé pour les données publiques des entreprises françaises, avec des outils d'aide aux annonces légales.

- **Entreprises** : identité, siège, établissements, capital, dirigeants en fonction (nom et qualité), d'après INSEE Sirene et l'INPI RNE.
- **Avis BODACC** : derniers avis d'une société (création, modifications, vente de fonds, procédures collectives, radiation) et liste des actes et comptes déposés à l'INPI.
- **Adresses** : autocomplétion, normalisation et géocodage inverse avec la Base Adresse Nationale.
- **Annonces légales** : annonces qu'impose une décision, base légale et tarif réglementé, démarches suivantes, et brouillon que l'utilisateur relit et publie sur legalone.fr.

Le serveur MCP est référencé sous le nom **LegalOne Entreprises** (un autre produit, sans rapport, s'appelle « LegalOne » dans le registre MCP).

Ce dépôt ne contient que le matériel public côté client : un [skill pour agents](SKILL.md), deux SDK en un seul fichier ([TypeScript](sdk/typescript/legalone.ts), [Python](sdk/python/legalone.py)) et le [manifeste du registre MCP](server.json).

## Serveur MCP

| | |
|---|---|
| Adresse | `https://mcp.legalone.fr/mcp` |
| Transport | Streamable HTTP |
| Authentification | aucune |
| Quota | 60 requêtes/min et 1 000/jour par adresse IP |

Outils : `search_companies`, `get_company`, `get_establishment`, `list_bodacc_notices`, `get_bodacc_notice`, `list_company_documents`, `search_addresses`, `get_legal_notice_price`, `which_legal_notice`, `get_next_steps`, `prepare_legal_notice`. Tous en lecture seule, sauf `prepare_legal_notice` qui enregistre un brouillon sur legalone.fr. Rien n'est payé dans la conversation.

**Claude (claude.ai et Claude Desktop)** : Paramètres > Connecteurs > Ajouter un connecteur personnalisé, nom `LegalOne Entreprises`, URL `https://mcp.legalone.fr/mcp`, sans authentification. Un connecteur ajouté sur claude.ai est aussi disponible dans Claude Desktop.

**Claude Code** :

```bash
claude mcp add --transport http legalone-entreprises https://mcp.legalone.fr/mcp
```

**ChatGPT** : Paramètres > Applications et connecteurs > Paramètres avancés, activer le mode développeur, puis créer un connecteur avec l'URL `https://mcp.legalone.fr/mcp`, sans authentification. Disponible selon l'offre ChatGPT ; les menus peuvent changer.

**Autres clients** acceptant un serveur distant :

```json
{
  "mcpServers": {
    "legalone-entreprises": { "url": "https://mcp.legalone.fr/mcp" }
  }
}
```

Un client limité à stdio peut passer par une passerelle comme `npx -y mcp-remote https://mcp.legalone.fr/mcp`.

## API REST

| | |
|---|---|
| Base | `https://api.legalone.fr/v1` |
| Clé | obligatoire sur toutes les routes `/v1` : `Authorization: Bearer lo_…` (ou `X-API-Key`). Gratuite : créez un compte développeur sur <https://legalone.fr/developers>, puis une clé dans l'espace développeur |
| Contrat | <https://api.legalone.fr/v1/openapi.json> (sans clé) |
| Quota par clé | 60 requêtes/min, 5 000/jour, 100 000/mois ; recherche d'entreprises 20/min. Un quota supérieur se demande depuis l'espace développeur |

Gardez la clé côté serveur, jamais dans un code livré à vos utilisateurs.

```bash
# Fiche d'une entreprise par SIREN
curl -s https://api.legalone.fr/v1/entreprises/552032534 \
  -H "Authorization: Bearer $LEGALONE_API_KEY"

# Recherche par début de nom, ou SIREN/SIRET exact
curl -s --get https://api.legalone.fr/v1/entreprises \
  --data-urlencode "q=exemple" -H "Authorization: Bearer $LEGALONE_API_KEY"

# Derniers avis BODACC
curl -s "https://api.legalone.fr/v1/entreprises/552032534/bodacc?limit=5" \
  -H "Authorization: Bearer $LEGALONE_API_KEY"

# Normaliser une adresse
curl -s --get https://api.legalone.fr/v1/adresses/normaliser \
  --data-urlencode "q=8 boulevard du Port 80000 Amiens" \
  -H "Authorization: Bearer $LEGALONE_API_KEY"
```

Chaque réponse vaut `{ data, meta, links }` ; `meta` porte `updatedAt`, `sources`, `warnings` et `attribution`. Les erreurs suivent la RFC 9457 (`application/problem+json`) : 400 paramètre invalide, 401 clé absente ou invalide, 404 inconnu ou non diffusable (à traiter comme « introuvable », sans réessayer), 429 quota atteint (attendre `Retry-After`), 503 réessayer plus tard. La liste complète des routes est dans le contrat OpenAPI et dans [SKILL.md](SKILL.md).

## SDK

Chaque SDK tient en un fichier sans dépendance : copiez-le dans votre projet.

```ts
// sdk/typescript/legalone.ts — fetch natif (Node 18+, navigateurs, Deno, Bun)
import { LegalOne } from "./legalone.ts";

const api = new LegalOne({ apiKey: process.env.LEGALONE_API_KEY! });
const societe = await api.getCompany("552032534"); // null si introuvable
console.log(societe?.data.name, societe?.meta.attribution);
```

```python
# sdk/python/legalone.py — bibliothèque standard, Python 3.9+
from legalone import LegalOne

api = LegalOne(api_key="lo_...")
societe = api.get_company("552032534")  # None si introuvable
if societe:
    print(societe["data"]["name"], societe["meta"]["attribution"])
```

Méthodes : `getCompany` / `get_company`, `getEstablishment`, `searchCompanies`, `listBodaccNotices`, `getBodaccNotice`, `listCompanyDocuments`, `health`. Les erreurs lèvent `LegalOneError` (statut, titre, détail, identifiant de requête, délai conseillé sur 429).

Tests Python (serveur local, sans réseau) : `cd sdk/python && python3 -m unittest -v`.

## Skill pour agents

[SKILL.md](SKILL.md) indique à un agent quand et comment utiliser l'API ou le serveur MCP. Claude Code : le copier dans `.claude/skills/legalone/SKILL.md`. Autres agents : leur donner <https://api.legalone.fr/skill.md>.

## Sources et licences

| Source | Licence |
|---|---|
| INSEE Sirene | Licence Ouverte 2.0 |
| INPI RNE | Licence INPI de réutilisation du RNE (2024) |
| DILA BODACC | Licence Ouverte 2.0 |
| Base Adresse Nationale | Licence Ouverte 2.0 |
| Légifrance (règles des annonces) | Licence Ouverte 2.0 |

Chaque réponse cite dans `meta.sources` les sources réellement utilisées et leur date de mise à jour.

## Attribution (obligatoire)

Affichez `meta.attribution` près des données, tel quel. Pour les données d'entreprises :

> Données : LegalOne — sources INSEE Sirene, INPI RNE, DILA BODACC, mise à jour le {date}

`{date}` est `meta.updatedAt` au format JJ/MM/AAAA ; « LegalOne » renvoie vers la fiche de l'entreprise (`data.links.legalone`) ou vers <https://legalone.fr>. Les routes d'adresses portent `Adresses : Base Adresse Nationale (BAN), Licence Ouverte 2.0 — via LegalOne`. N'écrivez jamais « données certifiées INPI/INSEE ».

## Limites

- Les données servent à pré-remplir et enrichir. Elles ne sont **pas** une source de vérification d'identité réglementaire (KYC) ni une preuve : vérifiez sur un extrait Kbis ou RNE.
- Données personnelles limitées au nom et à la qualité des dirigeants. Pas de coordonnées, pas de recherche de personnes, pas de comptes annuels, pas de bénéficiaires effectifs.
- Les entreprises non diffusables, et les entreprises ou personnes qui se sont opposées à leur publication sur LegalOne, ne sont pas servies.
- Les règles et démarches des annonces légales sont indicatives ; en cas de situation inhabituelle, demandez conseil à un professionnel du droit.

## Conditions, confidentialité, support

- Conditions d'utilisation : <https://legalone.fr/developers/conditions>
- Confidentialité : <https://legalone.fr/developers/conditions#confidentialite>
- Opposition (RGPD) ou demande de correction : <https://legalone.fr/developers/opposition>
- Support : api@legalone.fr

## Licence

Le code et la documentation de ce dépôt sont sous [licence MIT](LICENSE). Les données renvoyées par l'API restent soumises aux licences des sources ci-dessus et aux conditions d'utilisation de LegalOne.
