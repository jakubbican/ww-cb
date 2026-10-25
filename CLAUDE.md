# CLAUDE.md – web ww-cb

Statický web klubu SK Vodní slalom České Budějovice. Pracuj česky. Čtenáři webu jsou rodiče, junioři, partneři a návštěvníci areálu; správkyně obsahu jsou kolegyně z oddílu bez technického zázemí – obsah musí zůstat jednoduchý Markdown.

## Jak to funguje
- `python build.py` → `dist/`. Žádný JS framework, žádný CMS. Šablony Jinja2 v `templates/`, styl `static/style.css`.
- Obsah: `content/posts/` (zápisník – v menu a nadpisech „Zápisník“, URL zůstává `/kronika/`), `content/events/` (akce – soubory `YYYY-MM-<název>.md`, nový ročník = kopie loňského souboru se změnou roku v názvu i v `date`/`end_date`; hlavička viz README: subtitle, organizer, why, links), `content/pages/` (klub, areal, akce, partneri, kontakt, uspechy, wave, historie-src). Formát hlaviček viz README.
- Obrázky článků `img/<slug>/NN.jpg` (build zmenší na 1600 px a vyrobí náhledy `_t.jpg`), fotky archivu `photos/` + `photos/index.json` (skupiny hero/areal/historie/wave/akce).
- „Dnes teče voda“ na HP: `build.py` stáhne rozpis z itdev.cz (`fetch_voda`, 14 dní) a vloží ho do stránky jako JSON; JS vybere dnes/zítra (po 19:00). Workflow běží i denně ráno (cron), aby byl rozpis čerstvý. Při výpadku zdroje se řádek nezobrazí. `--no-voda` build bez stahování.
- Čísla na HP (pod partnery): blok `STATS` v `build.py`. Pod nimi blok Oddíl (text + `photos/klub/oddil.jpg`) a dvojice Závody a akce / Areál: seznam akcí (`hp_events` v `build.py`) ukazuje v sezoně nejbližší akce kalendáře, po sezoně poslední naše závody s odkazy na články.
- Stránka Akce = program areálu, ne archiv: příští akce, kalendář roku, ohlédnutí a text „Co pořádáme“ (`content/pages/akce.md`). Překlopení sezony řídí datum buildu (`WWCB_TODAY` pro test). Minulé ročníky se neukazují – odkazují se články v zápisníku.
- Stránka Partneři (`/partneri/`, není v menu – odkaz z pásu partnerů a patičky): vše v hlavičce `content/pages/partneri.md` (čísla, skupiny partnerů s logem/textem/odkazem, kontakt), úvod v těle. Loga přes `design/partneri/` (sync).
- Nasazení: GitHub Actions → GitHub Pages (`.github/workflows/pages.yml`). Odkazy jsou relativní, web funguje v podadresáři i na vlastní doméně; jen 404 stránka používá `--base`.

## Design – nesahat ručně
- Barvy, písma, loga jsou v `design/` **vendorované z repa skvscb-design**. Neměň je tady; změna patří do design repa a sem přijde přes `scripts/sync-design.sh` (zapíše `design/DESIGN_VERSION`).
- `static/style.css` smí používat jen proměnné z `design/tokens.css`. Nové barvy nezaváděj.
- Logo: nikdy nedeformovat, neořezávat; pravidla v design repu (`logo/README.md`).

## Pravidla obsahu
- Články převzaté ze starého webu (do 10/2026) jsou 1:1, včetně fotek – needitovat zpětně.
- Historie (`content/pages/historie-src.md`) vychází z diplomové práce Štumbauer (JU 2017) a dalších pramenů; značky `[ověřit]` build odstraní – při doplňování faktů uvádět zdroj v `## 4. Zdroje`.
- Fotky dětí: přednost závodům a areálu, vyhýbat se detailním portrétům z tréninků.
- Partneři: pořadí a rozdělení (Hlavní partneři / Podporují nás) v `templates/partners.html`.

## Než pushneš
- `python build.py` projde bez chyb a vypíše `OK:`.
- U nové stránky zkontrolovat odkazy v menu (`templates/base.html`) a `rel` hloubku (`../` podle zanoření).
- Commit message česky, stručně, prefix `ww-cb:` nepotřeba (jsme v repu webu).
