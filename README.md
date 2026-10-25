# ww-cb – web SK Vodní slalom České Budějovice

Statický web klubu (zápisník, historie, úspěchy, areál, akce, kontakt). Generuje ho `build.py` z Markdown souborů; nasazuje se automaticky na GitHub Pages při pushi do `main`.

- Web: https://jakubbican.github.io/ww-cb/ (cíl: ww-cb.cz)
- Design: https://github.com/jakubbican/skvscb-design (tokeny a loga vendorované v `design/`, verze v `design/DESIGN_VERSION`)

## Lokální build
```
pip install -r requirements.txt
python build.py            # → dist/
python -m http.server -d dist 8000
```

## Přidat článek do zápisníku
1. `content/posts/<slug>.md` – hlavička:
   ```
   ---
   title: "Název článku"
   date: "2026-10-12T18:00:00+02:00"
   category: "Závody"        # Závody | Oddíl | Areál
   kind: "post"
   images:
     - "img/<slug>/01.jpg"
   ---
   ![cover](img/<slug>/01.jpg)

   Text v Markdownu. Odrážky jako „- “. Další obrázky `![](img/<slug>/02.jpg)`;
   více obrázků za sebou se zobrazí jako galerie.
   ```
2. Fotky do `img/<slug>/` (ideálně do 1200 px na delší straně, build je zmenší).
3. Commit + push → za pár minut je článek na webu.

## Přidat akci
`content/events/YYYY-MM-<název>.md` (rok a měsíc začátku akce, např. `2026-09-nkz.md`; nový ročník = zkopírovat loňský soubor a změnit rok v názvu i v `date`/`end_date`) – hlavička:
```
---
title: "Jarní slalomy"
date: "2027-04-17T09:00:00+02:00"
end_date: "2027-04-18T18:00:00+02:00"
kind: "event"
location: "Areál Lídy Polesné"
subtitle: "Veřejný závod a nominace mládeže"        # co to je, pro koho – jedna řádka
organizer: "klub"                                   # klub | jiny
# org_name: "Rafting CB"                            # u cizích akcí jméno pořadatele (zobrazí se místo oválku)
# org_url: "https://raftingcb.cz/"
why: "Proč přijít – jedna až dvě věty. Zobrazí se jen u příští akce."
links:
  propozice: "https://..."                          # doplňovat průběžně: před akcí propozice/startovka,
  startovka: "https://..."                          #   po akci výsledky a článek v zápisníku
  live: "https://zive.results.cz/..."
  vysledky: "https://..."
  clanek: "kronika/<slug-clanku>/"                  # relativní odkaz na článek v zápisníku
---
```
Stránka Akce se skládá sama podle data: **Příští akce** (první budoucí), **Kalendář <rok>** (rok příští akce; bez budoucích akcí se měsíc po poslední akci překlopí na další rok), **Jak dopadl rok <předchozí>** (jen když je kalendář skoro prázdný) a text **Co pořádáme** z `content/pages/akce.md` (úvod, poznámka pro mezidobí a profily tradičních závodů – běžný Markdown, měsíc u nadpisu jako `### Název *měsíc*`).
Pro vyzkoušení stavu k jinému datu: `WWCB_TODAY=2027-01-10 python build.py`.

## Partneři
Stránka `/partneri/` se skládá z `content/pages/partneri.md`: v hlavičce `numbers` (čtyři čísla), `where` (odstavec), `groups` (skupiny: `title`, volitelně `sub`, `wide` = jeden řádek přes šířku, `cols: 3`, `noname: true` = bez názvu v textu (logo je slovní); v každé `partners` s `name`, `logo` (soubor z `design/partneri/`), `url`, `text`), `contact_heading`/`contact_text`; tělo = úvodní odstavce. Nové logo = přidat do repa skvscb-design a spustit `scripts/sync-design.sh`.

## Dnes teče voda
Homepage ukazuje dnešní (po 19:00 zítřejší) časy pouštění vody. Build je stahuje z http://itdev.cz/SlalomCourse/OpeningTimes.aspx; workflow proto běží každý den ráno. `python build.py --no-voda` build přeskočí stahování.

## Struktura
`content/pages/` stránky · `content/posts/` kronika · `content/events/` akce · `content/wix-pages/` archiv stránek ze starého Wixu (nepoužívá se) · `img/` obrázky článků · `photos/` vybrané fotky z archivu · `design/` tokeny a loga · `templates/`, `static/` · `scripts/sync-design.sh`

Originály fotek a dokumenty klubu jsou na OneDrive „Dokumenty nástěnky SK VS ČB“, do gitu nepatří.
