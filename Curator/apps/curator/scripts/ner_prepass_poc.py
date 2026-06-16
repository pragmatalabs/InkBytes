"""POC — ADR-0032 items 1+2 against real InkBytes articles.
Item 2: language-routed spaCy NER pre-pass (EN + ES) -> typed entity coverage.
Item 1: the salvaged 634->33 taxonomy + proposed widened themes.
Run with the DocTrainer venv (has spacy + es/en models).
"""
import json, spacy, collections

TAX = "/Volumes/Pragmata/Projects/InkBytes/Curator/apps/curator/data/taxonomy"
cats33 = json.load(open(f"{TAX}/categories_33.json"))["categories"]
bridge = json.load(open(f"{TAX}/source_category_bridge.json"))["mappings"]

# 33-category -> widened 15-theme rollup (ADR-0032 item 1)
CAT_TO_THEME = {
 "Politics":"politics","Global News":"world","Global News.MiddleEast":"world",
 "Headline News":"world","Headline News.North America":"world","Impact & Social Issues":"world",
 "Business & Economy":"business","Economy":"business","Automotive":"business",
 "Science & Technology":"technology","Health & Wellness":"health","Sports":"sports",
 "Arts & Culture":"culture","Culture & Experiences":"culture","Media & Journalism":"culture",
 "Entertainment":"entertainment","Entertainment.Tv":"entertainment","Entertainment.Movies":"entertainment",
 "Entertainment.Music":"entertainment","Weather & Environment":"environment","Crime & Justice":"crime",
 "Education":"education","Lifestyle":"lifestyle","Food & Drink":"lifestyle","Family & Parenting":"lifestyle",
 "Family & Parenting.Kids":"lifestyle","Human Interest":"lifestyle","Religion & Beliefs":"religion",
 "Disaster & Emergency":"disaster","Diversity & Identity":"world","Weird News":"world",
 "Positive News":"world","Miscellaneous":"world",
}

# spaCy label -> InkBytes entity type (EN=OntoNotes, ES=CoNLL differ)
def norm_type(lbl):
    return {"PERSON":"PERSON","PER":"PERSON","ORG":"ORG","GPE":"LOC","LOC":"LOC","FAC":"LOC",
            "EVENT":"EVENT"}.get(lbl, "OTHER")

print("Loading spaCy models (en_core_web_sm, es_core_news_sm)…")
nlp = {"en": spacy.load("en_core_web_sm"), "es": spacy.load("es_core_news_sm")}
MUST = ["PERSON","ORG","LOC","EVENT"]

for line in open("/tmp/ner_sample.psv"):
    parts = line.rstrip("\n").split("|", 3)
    if len(parts) < 4: continue
    aid, lang, theme, text = parts
    doc = nlp.get(lang, nlp["en"])(text)
    by_type = collections.defaultdict(set)
    for e in doc.ents:
        by_type[norm_type(e.label_)].add(e.text.strip())
    print("\n" + "="*78)
    print(f"[{lang}] {text[:64]}…")
    print(f"  current theme (8-set): {theme}")
    cov = [t for t in MUST if by_type.get(t)]
    print(f"  spaCy typed-entity coverage: {'/'.join(cov) if cov else '(none)'}  "
          f"({'✓ all core types' if len(cov)==4 else f'{len(cov)}/4 core types'})")
    for t in MUST + ["OTHER"]:
        if by_type.get(t):
            vals = sorted(by_type[t])[:6]
            print(f"    {t:7}: {', '.join(vals)}")

# Taxonomy demo: map real outlet/IPTC section labels through the salvaged bridge
print("\n" + "="*78)
print("ITEM 1 — taxonomy bridge in action (sample outlet/IPTC labels -> 33-cat -> widened theme):")
for raw in ["politics","economy, business and finance","sport","TECH","CULTURE & ARTS",
            "crime, law and justice","conflict, war and peace","health","SCIENCE"]:
    cat = bridge.get(raw, bridge.get(raw.lower(), "?"))
    theme = CAT_TO_THEME.get(cat, "?")
    print(f"    {raw:35} -> {cat:24} -> theme: {theme}")
print(f"\n  Widened themes (15): politics world business technology science health sports")
print(f"                       culture entertainment environment crime education lifestyle religion disaster")
print(f"  article_category granular layer: {len(cats33)} categories (Julian's ontology)")
