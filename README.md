# ww-cb – web SK Vodní slalom České Budějovice

Statický web klubu (kronika, historie, úspěchy, areál, akce, kontakt). Generuje ho `build.py` z Markdown souborů; nasazuje se automaticky na GitHub Pages při pushi do `main`.

- Web: https://jakubbican.github.io/ww-cb/ (cíl: ww-cb.cz)
- Design: https://github.com/jakubbican/skvscb-design (tokeny a loga vendorované v `design/`, verze v `design/DESIGN_VERSION`)

## Lokální build
```
pip install -r requirements.txt
python build.py            # → dist/
python -m http.server -d dist 8000
```

## Přidat článek do kroniky
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
`content/events/<slug>.md` s `kind: "event"`, `date`, `end_date`, `location`, `description`.

## Dnes teče voda
Homepage ukazuje dnešní (po 19:00 zítřejší) časy pouštění vody. Build je stahuje z http://itdev.cz/SlalomCourse/OpeningTimes.aspx; workflow proto běží každý den ráno. `python build.py --no-voda` build přeskočí stahování.

## Struktura
`content/pages/` stránky · `content/posts/` kronika · `content/events/` akce · `content/wix-pages/` archiv stránek ze starého Wixu (nepoužívá se) · `img/` obrázky článků · `photos/` vybrané fotky z archivu · `design/` tokeny a loga · `templates/`, `static/` · `scripts/sync-design.sh`

Originály fotek a dokumenty klubu jsou na OneDrive „Dokumenty nástěnky SK VS ČB“, do gitu nepatří.
