/**
 * Client TypeScript de l'API publique LegalOne (https://api.legalone.fr).
 *
 * Licence MIT : copiez, modifiez et redistribuez ce fichier librement.
 *
 * ATTRIBUTION OBLIGATOIRE : les données servies par l'API ne sont réutilisables
 * qu'avec la mention prévue par les conditions d'utilisation, affichée près des
 * données (champ `meta.attribution` de chaque réponse) :
 *   « Données : LegalOne — sources INSEE Sirene, INPI RNE, DILA BODACC,
 *     mise à jour le {date} »
 * Voir https://www.legalone.fr/developers/conditions.
 *
 * CLÉ D'API OBLIGATOIRE : toute requête (sauf `health()`) exige une clé gratuite.
 * Créez un compte développeur sur https://www.legalone.fr/developers#compte, puis
 * générez la clé dans l'espace développeur (https://api.legalone.fr/compte).
 * Ne mettez jamais la clé dans un code exécuté chez vos utilisateurs.
 *
 * Zéro dépendance : `fetch` natif (Node 18+, navigateurs, Deno, Bun).
 *
 * ```ts
 * const api = new LegalOne({ apiKey: process.env.LEGALONE_API_KEY! });
 * const company = await api.getCompany("552032534"); // null si introuvable
 * console.log(company?.data.name, company?.meta.attribution);
 * ```
 *
 * Pré-remplir et enrichir l'onboarding de vos clients professionnels : à partir
 * du SIREN saisi, proposez un formulaire déjà rempli que le client confirme.
 *
 * ```ts
 * async function prefillOnboarding(api: LegalOne, siren: string) {
 *   const company = await api.getCompany(siren);
 *   if (!company) return null; // SIREN inconnu ou non diffusable : saisie manuelle
 *   const { data, meta } = company;
 *   const office = data.headOffice?.address;
 *   return {
 *     name: data.name,
 *     legalFormCode: data.legalFormCode,
 *     activityCode: data.activityCode,
 *     // adresse normalisée (Base Adresse Nationale) quand elle est connue
 *     address: office?.normalized?.label ?? [office?.line, office?.postalCode, office?.city].filter(Boolean).join(" "),
 *     capital: data.capital?.amount ?? null,
 *     officers: data.officers.map(({ name, role }) => ({ name, role })),
 *     attribution: meta.attribution, // à afficher près des données
 *   };
 * }
 * ```
 *
 * Ces données servent à pré-remplir et enrichir ; elles ne remplacent pas la
 * vérification réglementaire (article L.561-5 du code monétaire et financier) :
 * vérifiez sur un extrait Kbis ou RNE.
 */

export const DEFAULT_BASE_URL = "https://api.legalone.fr";
export const DEFAULT_TIMEOUT_MS = 10_000;

export type SourceDescriptor = {
  name: string;
  licence: string;
  url: string;
  updatedAt: string | null;
};

export type Meta = {
  requestId: string;
  updatedAt: string | null;
  sources: SourceDescriptor[];
  coverage?: Record<string, string>;
  warnings: string[];
  /** Mention à afficher près des données (obligatoire). */
  attribution: string;
  /** Lien vers la politique de confidentialité de l'API. */
  privacy: string;
  page?: number;
  perPage?: number;
  hasMore?: boolean;
};

export type Links = {
  self: string;
  documentation: string;
  next?: string;
  [name: string]: string | undefined;
};

/** Enveloppe commune à toutes les réponses de données. */
export type Envelope<T> = { data: T; meta: Meta; links: Links };

/** Adresse Sirene rapprochée de la Base Adresse Nationale (normalisée, géolocalisée). */
export type NormalizedAddress = {
  id: string;
  label: string;
  kind: "housenumber" | "street" | "locality" | "municipality";
  houseNumber: string | null;
  street: string | null;
  postalCode: string | null;
  city: string | null;
  cityCode: string | null;
  latitude: number;
  longitude: number;
  score: number;
  geocodedAt: string;
};

export type Establishment = {
  siret: string;
  siren: string;
  name: string | null;
  status: "active" | "closed";
  isHeadOffice: boolean;
  address: {
    line: string | null;
    postalCode: string | null;
    city: string | null;
    countryCode: string | null;
    /** Adresse normalisée (Base Adresse Nationale), `null` si inconnue. */
    normalized: NormalizedAddress | null;
  };
  activityCode: string | null;
  creationDate: string | null;
  closureDate: string | null;
  links: { self: string; company: string; legalone: string };
};

export type Company = {
  siren: string;
  name: string;
  acronym: string | null;
  status: "active" | "ceased";
  legalFormCode: string | null;
  activityCode: string | null;
  creationDate: string | null;
  cessationDate: string | null;
  headOffice: Establishment | null;
  establishments: { total: number; open: number; items: Establishment[] };
  capital: {
    amount: number | null;
    currency: string | null;
    variable: boolean | null;
    minimum: number | null;
  } | null;
  officers: Array<{
    id: string;
    name: string;
    role: string;
    type: "person" | "company";
    /**
     * Mois et année de naissance (AAAA-MM), uniquement avec une clé d'accès étendu
     * (scope `officers:birth`, accordé par l'équipe à un compte vérifié).
     */
    birth?: string;
  }>;
  commercialProspectingAllowed: boolean;
  links: {
    self: string;
    legalone: string;
    bodacc: string;
    documents: string;
    inpi: string;
    officialDirectory: string;
  };
};

export type SearchHit = {
  siren: string;
  name: string;
  status: "active" | "ceased";
  legalFormCode: string | null;
  activityCode: string | null;
  postalCode: string | null;
  city: string | null;
  links: { self: string; legalone: string };
};

export type BodaccNoticeSummary = {
  id: string;
  publicationDate: string | null;
  companyName: string;
  sirens: string[];
  family: { code: string; label: string };
  noticeType: { code: string; label: string };
  department: { code: string; name: string };
  city: string;
  postalCode: string;
  court: string;
  bulletin: string;
  noticeNumber: number | null;
  publicationReference: string;
  links: { self: string; official: string; legalone: string };
};

export type BodaccNotice = BodaccNoticeSummary & {
  pdfUrl: string | null;
  sections: Array<{
    kind: string;
    title: string;
    fields: Array<{ key: string; label: string; value: string }>;
  }>;
};

export type CompanyDocument = {
  id: string;
  kind: "act" | "annual_accounts_filing";
  title: string;
  filingDate: string | null;
  closingDate: string | null;
  links: { inpi: string };
};

export type Health = {
  data: {
    status: "ok" | "degraded" | "starting";
    version: string;
    freshness: {
      catalogUpdatedAt: string | null;
      mainUpdatedAt: string | null;
      catalogSnapshotDate: string | null;
      lagSeconds: number | null;
      replicaReady: boolean;
    };
  };
};

/** Fenêtre de quota la plus contrainte, lue dans les en-têtes `X-RateLimit-*`. */
export type RateLimit = {
  limit: number;
  remaining: number;
  /** Secondes avant le renouvellement de la fenêtre. */
  resetSeconds: number;
};

export type FetchLike = (url: string, init?: RequestInit) => Promise<Response>;

export type LegalOneOptions = {
  /** Clé d'API (`lo_…`), obligatoire. Gratuite : https://www.legalone.fr/developers#compte */
  apiKey: string;
  /** Défaut : https://api.legalone.fr */
  baseUrl?: string;
  /** `fetch` à utiliser (tests, proxy, polyfill). Défaut : `fetch` global. */
  fetch?: FetchLike;
  /** Délai maximal par requête, en millisecondes (0 = illimité). Défaut : 10 000. */
  timeoutMs?: number;
};

/** Problème RFC 9457 renvoyé par l'API (`application/problem+json`). */
export type ProblemDetails = {
  status: number;
  type: string;
  title: string;
  detail: string;
  requestId?: string;
};

export class LegalOneError extends Error implements ProblemDetails {
  readonly status: number;
  readonly type: string;
  readonly title: string;
  readonly detail: string;
  readonly requestId: string | undefined;
  /** Délai conseillé avant de réessayer (réponses 429 et 503). */
  readonly retryAfterSeconds: number | undefined;

  constructor(
    problem: ProblemDetails & { retryAfterSeconds?: number },
    options?: { cause?: unknown },
  ) {
    super(`${problem.status} ${problem.title} : ${problem.detail}`, options);
    this.name = "LegalOneError";
    this.status = problem.status;
    this.type = problem.type;
    this.title = problem.title;
    this.detail = problem.detail;
    this.requestId = problem.requestId;
    this.retryAfterSeconds = problem.retryAfterSeconds;
  }
}

function readInteger(value: string | null): number | undefined {
  if (value === null || !/^\d+$/.test(value.trim())) return undefined;
  return Number(value);
}

function readRateLimit(headers: Headers): RateLimit | null {
  const limit = readInteger(headers.get("X-RateLimit-Limit"));
  const remaining = readInteger(headers.get("X-RateLimit-Remaining"));
  const resetSeconds = readInteger(headers.get("X-RateLimit-Reset"));
  if (limit === undefined || remaining === undefined || resetSeconds === undefined) return null;
  return { limit, remaining, resetSeconds };
}

export class LegalOne {
  readonly baseUrl: string;
  readonly timeoutMs: number;
  /** Quota lu sur la dernière réponse reçue (succès ou erreur), `null` avant. */
  lastRateLimit: RateLimit | null = null;

  readonly #apiKey: string;
  readonly #fetch: FetchLike;

  constructor(options: LegalOneOptions) {
    const apiKey = typeof options?.apiKey === "string" ? options.apiKey.trim() : "";
    if (apiKey === "") {
      throw new Error(
        "LegalOne : apiKey est obligatoire. Créez un compte développeur gratuit sur https://www.legalone.fr/developers#compte, puis générez une clé dans l'espace développeur.",
      );
    }
    this.baseUrl = (options.baseUrl ?? DEFAULT_BASE_URL).replace(/\/+$/, "");
    this.timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    this.#apiKey = apiKey;
    this.#fetch = options.fetch ?? ((url, init) => fetch(url, init));
  }

  /** Fiche d'une entreprise (SIREN, 9 chiffres). `null` si introuvable ou non diffusable. */
  getCompany(siren: string): Promise<Envelope<Company> | null> {
    return this.#get(`/v1/entreprises/${encodeURIComponent(siren)}`, undefined, true);
  }

  /** Un établissement (SIRET, 14 chiffres). `null` si introuvable ou non diffusable. */
  getEstablishment(siret: string): Promise<Envelope<Establishment> | null> {
    return this.#get(`/v1/etablissements/${encodeURIComponent(siret)}`, undefined, true);
  }

  /** Recherche par début de nom, ou par SIREN/SIRET exact. 20 résultats par page, 5 pages au plus. */
  async searchCompanies(
    q: string,
    options: { page?: number; perPage?: number } = {},
  ): Promise<Envelope<SearchHit[]>> {
    const result = await this.#get<SearchHit[]>(
      "/v1/entreprises",
      { q, page: options.page, per_page: options.perPage },
      false,
    );
    return result as Envelope<SearchHit[]>;
  }

  /** Derniers avis BODACC d'une entreprise. `null` si l'entreprise est introuvable. */
  listBodaccNotices(
    siren: string,
    options: { limit?: number } = {},
  ): Promise<Envelope<BodaccNoticeSummary[]> | null> {
    return this.#get(
      `/v1/entreprises/${encodeURIComponent(siren)}/bodacc`,
      { limit: options.limit },
      true,
    );
  }

  /** Un avis BODACC filtré (ex. `A202601950001`). `null` si introuvable. */
  getBodaccNotice(id: string): Promise<Envelope<BodaccNotice> | null> {
    return this.#get(`/v1/bodacc/${encodeURIComponent(id)}`, undefined, true);
  }

  /** Métadonnées des actes et dépôts de comptes (liens INPI). `null` si l'entreprise est introuvable. */
  listCompanyDocuments(siren: string): Promise<Envelope<CompanyDocument[]> | null> {
    return this.#get(`/v1/entreprises/${encodeURIComponent(siren)}/documents`, undefined, true);
  }

  /** État du service et fraîcheur des données. */
  async health(): Promise<Health> {
    const result = await this.#get<unknown>("/v1/health", undefined, false);
    return result as unknown as Health;
  }

  async #get<T>(
    path: string,
    query: Record<string, string | number | undefined> | undefined,
    nullOn404: true,
  ): Promise<Envelope<T> | null>;
  async #get<T>(
    path: string,
    query: Record<string, string | number | undefined> | undefined,
    nullOn404: false,
  ): Promise<Envelope<T>>;
  async #get<T>(
    path: string,
    query: Record<string, string | number | undefined> | undefined,
    nullOn404: boolean,
  ): Promise<Envelope<T> | null> {
    const url = new URL(this.baseUrl + path);
    for (const [name, value] of Object.entries(query ?? {})) {
      if (value !== undefined) url.searchParams.set(name, String(value));
    }
    const headers: Record<string, string> = {
      Accept: "application/json",
      Authorization: `Bearer ${this.#apiKey}`,
    };

    let response: Response;
    try {
      response = await this.#fetch(url.toString(), {
        method: "GET",
        headers,
        ...(this.timeoutMs > 0 ? { signal: AbortSignal.timeout(this.timeoutMs) } : {}),
      });
    } catch (cause) {
      const timedOut = cause instanceof Error && (cause.name === "TimeoutError" || cause.name === "AbortError");
      throw new LegalOneError(
        {
          status: 0,
          type: "about:blank",
          title: timedOut ? "Délai dépassé" : "Erreur réseau",
          detail: timedOut
            ? `Aucune réponse en ${this.timeoutMs} ms.`
            : cause instanceof Error ? cause.message : String(cause),
        },
        { cause },
      );
    }

    this.lastRateLimit = readRateLimit(response.headers) ?? this.lastRateLimit;
    if (response.status === 404 && nullOn404) {
      await response.body?.cancel();
      return null;
    }
    if (!response.ok) throw await this.#toError(response);
    return (await response.json()) as Envelope<T>;
  }

  async #toError(response: Response): Promise<LegalOneError> {
    const retryAfterSeconds =
      readInteger(response.headers.get("Retry-After")) ??
      (response.status === 429 ? readRateLimit(response.headers)?.resetSeconds : undefined);
    let body: Partial<ProblemDetails> = {};
    let text = "";
    try {
      text = await response.text();
      const parsed: unknown = JSON.parse(text);
      if (parsed && typeof parsed === "object") body = parsed as Partial<ProblemDetails>;
    } catch {
      // Corps absent ou non JSON (proxy, page d'erreur) : on garde le texte brut.
    }
    return new LegalOneError({
      status: typeof body.status === "number" ? body.status : response.status,
      type: typeof body.type === "string" ? body.type : "about:blank",
      title: typeof body.title === "string" ? body.title : response.statusText || "Erreur",
      detail: typeof body.detail === "string" ? body.detail : text.slice(0, 200),
      requestId: typeof body.requestId === "string" ? body.requestId : response.headers.get("X-Request-Id") ?? undefined,
      ...(retryAfterSeconds !== undefined ? { retryAfterSeconds } : {}),
    });
  }
}
