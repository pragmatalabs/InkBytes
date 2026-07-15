/**
 * Country label → flag emoji for the entity map. Offline, zero-cost, no assets:
 * an ES+EN name table → ISO 3166-1 alpha-2 → regional-indicator flag emoji.
 * Covers the LATAM/Europe/global vertical + common variants. Returns null for
 * non-countries (cities, regions, orgs) so only countries get a flag.
 *
 * NB: flag emoji render natively on iOS/Android (the mobile-first audience) and
 * most browsers; Windows Chrome shows the two-letter code — acceptable fallback.
 */

// normalize: lowercase, strip accents/punctuation, collapse spaces
const norm = (s: string) =>
  s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/[.]/g, "").replace(/\s+/g, " ").trim();

// canonical name / variant → ISO alpha-2
const ISO: Record<string, string> = {};
const add = (iso: string, ...names: string[]) => names.forEach((n) => (ISO[norm(n)] = iso));

// LATAM
add("US", "estados unidos", "ee uu", "eeuu", "united states", "usa", "us", "america");
add("MX", "mexico");
add("AR", "argentina");
add("CO", "colombia");
add("PE", "peru");
add("CL", "chile");
add("EC", "ecuador");
add("VE", "venezuela");
add("PR", "puerto rico");
add("DO", "republica dominicana", "dominican republic");
add("BR", "brasil", "brazil");
add("UY", "uruguay");
add("PY", "paraguay");
add("BO", "bolivia");
add("GT", "guatemala");
add("HN", "honduras");
add("SV", "el salvador");
add("NI", "nicaragua");
add("CR", "costa rica");
add("PA", "panama");
add("CU", "cuba");
// Europe
add("ES", "espana", "spain");
add("FR", "francia", "france");
add("DE", "alemania", "germany");
add("GB", "reino unido", "united kingdom", "uk", "gran bretana", "britain", "great britain", "inglaterra", "england");
add("IT", "italia", "italy");
add("PT", "portugal");
add("NL", "paises bajos", "netherlands", "holanda", "holland");
add("BE", "belgica", "belgium");
add("CH", "suiza", "switzerland");
add("AT", "austria");
add("SE", "suecia", "sweden");
add("NO", "noruega", "norway");
add("DK", "dinamarca", "denmark");
add("FI", "finlandia", "finland");
add("IE", "irlanda", "ireland");
add("PL", "polonia", "poland");
add("GR", "grecia", "greece");
add("UA", "ucrania", "ukraine");
add("RU", "rusia", "russia");
add("TR", "turquia", "turkey", "turkiye");
add("HU", "hungria", "hungary");
add("CZ", "republica checa", "czech republic", "czechia");
add("RO", "rumania", "romania");
// Middle East / Africa
add("IL", "israel");
add("PS", "palestina", "palestine", "gaza");
add("IR", "iran");
add("IQ", "irak", "iraq");
add("SA", "arabia saudi", "arabia saudita", "saudi arabia");
add("AE", "emiratos arabes unidos", "united arab emirates", "uae");
add("QA", "qatar");
add("EG", "egipto", "egypt");
add("ZA", "sudafrica", "south africa");
add("NG", "nigeria");
add("KE", "kenia", "kenya");
add("MA", "marruecos", "morocco");
add("ET", "etiopia", "ethiopia");
add("SY", "siria", "syria");
add("LB", "libano", "lebanon");
// Asia-Pacific
add("CN", "china");
add("JP", "japon", "japan");
add("IN", "india");
add("KR", "corea del sur", "south korea", "corea");
add("KP", "corea del norte", "north korea");
add("TW", "taiwan");
add("HK", "hong kong");
add("SG", "singapur", "singapore");
add("ID", "indonesia");
add("PK", "pakistan");
add("AF", "afganistan", "afghanistan");
add("VN", "vietnam");
add("PH", "filipinas", "philippines");
add("TH", "tailandia", "thailand");
add("AU", "australia");
add("NZ", "nueva zelanda", "new zealand");
add("CA", "canada");

function isoToEmoji(iso: string): string {
  return iso.toUpperCase().replace(/./g, (c) =>
    String.fromCodePoint(0x1f1e6 + c.charCodeAt(0) - 65));
}

/** Flag emoji for a country label, or null if the label isn't a known country. */
export function countryFlag(label: string | null | undefined): string | null {
  if (!label) return null;
  const iso = ISO[norm(label)];
  return iso ? isoToEmoji(iso) : null;
}
