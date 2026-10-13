#!/usr/bin/env python3
"""Statický generátor webu SK Vodní slalom České Budějovice.

Vstupy (výchozí cesty relativně k ../):
  web-src/wwcb/md/*.md   články a stránky stažené z ww-cb.cz (+ web-src/wwcb/img/)
  web-src/photos/        vybrané fotky z Galerie (+ index.json)
  web/content/*.md       vlastní stránky (klub, areal, kontakt, uspechy, historie-src)
  web/templates, web/static
  partneri/, logo/       loga
Výstup: --out (výchozí ../../jakubbican/pages/ww-cb)

Spuštění:  python3 build.py [--out DIR] [--budget SEC] [--no-images]
Zpracování obrázků je idempotentní; při vyčerpání --budget skončí a vypíše, kolik zbývá.
"""
import argparse, json, os, re, shutil, sys, time, html
from datetime import datetime, date
from pathlib import Path

import yaml, markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
ROOT = HERE  # kořen repa ww-cb
ap = argparse.ArgumentParser()
ap.add_argument('--out', default=str(ROOT / 'dist'))
ap.add_argument('--base', default='/ww-cb/', help='absolutní základ URL pro 404 stránku (GitHub Pages: /<repo>/)')
ap.add_argument('--budget', type=float, default=140.0, help='časový limit pro zpracování obrázků (s)')
ap.add_argument('--no-images', action='store_true')
args = ap.parse_args()

POSTS_DIR = ROOT / 'content' / 'posts'
EVENTS_DIR = ROOT / 'content' / 'events'
IMG_DIR = ROOT / 'img'
PHOTOS = ROOT / 'photos'
CONTENT = ROOT / 'content' / 'pages'
DESIGN = ROOT / 'design'
OUT = Path(args.out)
T0 = time.time()
MAX_W, THUMB_W, Q = 1600, 640, 82

env = Environment(loader=FileSystemLoader(str(HERE / 'templates')), autoescape=select_autoescape(['html']))
MONTHS = ['ledna','února','března','dubna','května','června','července','srpna','září','října','listopadu','prosince']

def cz_date(d):
    return f'{d.day}. {d.month}. {d.year}' if d else ''

def parse_dt(s):
    if not s: return None
    try:
        return datetime.fromisoformat(str(s).replace('Z', '+00:00'))
    except Exception:
        return None

def read_md(path):
    txt = path.read_text(encoding='utf-8')
    fm, body = {}, txt
    if txt.startswith('---'):
        parts = txt.split('\n---', 1)
        if len(parts) == 2:
            fm = yaml.safe_load(parts[0][3:]) or {}
            body = parts[1].lstrip('\n')
    return fm, body

def strip_markers(s):
    s = re.sub(r'\s*\*{0,2}\[ověřit[^\]]*\]\*{0,2}', '', s)
    s = re.sub(r'\(\s*\)', '', s)
    return s

# ---------- obrázky ----------
pending = 0
def img_out(rel):
    """rel = 'img/<slug>/NN.jpg' → (web path full, web path thumb). Vytvoří zmenšené verze."""
    global pending
    src = IMG_DIR / Path(rel).relative_to('img')
    if not src.exists():
        return None, None
    stem = src.stem
    dst = OUT / 'img' / src.parent.name / (stem + '.jpg')
    thumb = OUT / 'img' / src.parent.name / (stem + '_t.jpg')
    web_full = f'img/{src.parent.name}/{stem}.jpg'
    web_thumb = f'img/{src.parent.name}/{stem}_t.jpg'
    if dst.exists() and thumb.exists():
        return web_full, web_thumb
    if args.no_images or time.time() - T0 > args.budget:
        pending += 1
        return web_full, web_thumb
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        im = Image.open(src)
        im = ImageOps.exif_transpose(im)
        if im.mode not in ('RGB',):
            bg = Image.new('RGB', im.size, (255, 255, 255))
            if im.mode in ('RGBA', 'LA', 'P'):
                im = im.convert('RGBA'); bg.paste(im, mask=im.split()[-1]); im = bg
            else:
                im = im.convert('RGB')
        for target, width in ((dst, MAX_W), (thumb, THUMB_W)):
            if target.exists(): continue
            w, h = im.size
            t = im.copy()
            if max(w, h) > width:
                t.thumbnail((width, width), Image.LANCZOS)
            t.save(target, 'JPEG', quality=Q, optimize=True, progressive=True)
    except Exception as e:
        print('IMG ERR', src, e)
        return None, None
    return web_full, web_thumb

IMG_TOKEN = re.compile(r'^!\[([^\]]*)\]\(([^)]+)\)\s*$', re.M)

def md_to_html(body, rel_prefix, img_map=None):
    """markdown → html; obrázky z wwcb (img/..) přemapuje, po sobě jdoucí obrázky seskupí do galerie."""
    imgs = []
    def repl(m):
        alt, path = m.group(1), m.group(2)
        if img_map is not None and path.startswith('img/'):
            full, thumb = img_out(path)
            if not full: return ''
            imgs.append((full, thumb, alt))
            return f'\n\nIMGTOKEN{len(imgs)-1}\n\n'
        return m.group(0)
    body = IMG_TOKEN.sub(repl, body)
    # odrážky psané znakem ●
    body = re.sub(r'^\s*[●•]\s+', '- ', body, flags=re.M)
    # odrážka hned za odstavcem (bez prázdného řádku) + krátké řádky bez interpunkce jako mezititulky
    lines = body.split('\n'); out = []
    for i, ln in enumerate(lines):
        prev = out[-1] if out else ''
        if ln.startswith('- ') and prev.strip() and not prev.startswith('- ') and not prev.startswith('  '):
            out.append('')
        s = ln.strip()
        nxt = next((l for l in lines[i+1:] if l.strip()), '')
        if (img_map is not None and s and len(s) <= 70 and not s.startswith(('- ', '#', '!', '*', '[', '<', '>', 'IMGTOKEN', '|'))
                and s[-1] not in '.!?:,;…)' and '](' not in s and (not prev.strip()) and len(nxt) > 90):
            ln = '### ' + s
        out.append(ln)
    body = '\n'.join(out)
    h = markdown.markdown(body, extensions=['extra', 'sane_lists', 'attr_list'])
    # seskupení obrázků
    def grp(m):
        toks = [int(x) for x in re.findall(r'IMGTOKEN(\d+)', m.group(0))]
        if len(toks) == 1:
            full, thumb, alt = imgs[toks[0]]
            return f'<figure><a href="{rel_prefix}{full}" data-lb><img src="{rel_prefix}{full}" alt="{html.escape(alt)}" loading="lazy"></a></figure>'
        inner = ''.join(f'<a href="{rel_prefix}{imgs[t][0]}" data-lb><img src="{rel_prefix}{imgs[t][1]}" alt="" loading="lazy"></a>' for t in toks)
        return f'<div class="gallery">{inner}</div>'
    h = re.sub(r'(?:<p>IMGTOKEN\d+</p>\s*)+', grp, h)
    return h, imgs

def excerpt(fm, body, n=170):
    d = (fm.get('description') or '').strip()
    if not d:
        for para in body.split('\n\n'):
            p = para.strip()
            if p and not p.startswith('!') and not p.startswith('#') and not p.startswith('**Kdy') and not p.startswith('**Kde'):
                d = re.sub(r'[*_`\[\]]', '', p); break
    d = re.sub(r'\s+', ' ', d)
    return (d[:n].rsplit(' ', 1)[0] + '…') if len(d) > n else d

# ---------- načtení obsahu z ww-cb ----------
posts, events = [], []
for f in sorted(POSTS_DIR.glob('*.md')):
    fm, body = read_md(f)
    posts.append(dict(fm=fm, body=body, slug=f.stem, title=fm.get('title') or f.stem, dt=parse_dt(fm.get('date'))))
for f in sorted(EVENTS_DIR.glob('*.md')):
    fm, body = read_md(f)
    events.append(dict(fm=fm, body=body, slug=f.stem, title=fm.get('title') or f.stem, dt=parse_dt(fm.get('date'))))

posts.sort(key=lambda p: p['dt'] or datetime.min.replace(tzinfo=None), reverse=True)
CAT_MAP = {'Závody': 'Závody', 'Oddíl': 'Oddíl', 'Areál': 'Areál', 'Akce': 'Akce'}
for i, p in enumerate(posts):
    p['date_cz'] = cz_date(p['dt'])
    p['year'] = p['dt'].year if p['dt'] else 0
    p['category'] = CAT_MAP.get(p['fm'].get('category'), 'Oddíl')
    p['excerpt'] = excerpt(p['fm'], p['body'])
    p['prev'] = posts[i-1] if i > 0 else None       # novější
    p['next'] = posts[i+1] if i+1 < len(posts) else None  # starší

# ---------- výstupní adresáře a assety ----------
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'assets').mkdir(exist_ok=True)
shutil.copy(HERE / 'static' / 'style.css', OUT / 'assets' / 'style.css')
shutil.copy(DESIGN / 'tokens.css', OUT / 'assets' / 'tokens.css')
for name in ('logo-navy.svg', 'logo-white.svg'):
    shutil.copy(DESIGN / 'logo' / name, OUT / 'assets' / name)
shutil.copy(DESIGN / 'logo' / 'logo-navy.svg', OUT / 'assets' / 'favicon.svg')
(OUT / 'assets' / 'partneri').mkdir(exist_ok=True)
for f in (DESIGN / 'partneri').iterdir():
    if f.suffix.lower() in ('.png', '.jpg', '.svg'):
        shutil.copy(f, OUT / 'assets' / 'partneri' / f.name)
# fotky z Galerie
if PHOTOS.exists():
    for src in PHOTOS.rglob('*'):
        if src.is_file() and src.suffix.lower() in ('.jpg', '.jpeg', '.png') and '_tmp' not in src.parts:
            dst = OUT / 'photos' / src.relative_to(PHOTOS)
            if not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(src, dst)
photo_index = json.loads((PHOTOS / 'index.json').read_text(encoding='utf-8')) if (PHOTOS / 'index.json').exists() else {}
photo_list = photo_index.get('photos') if isinstance(photo_index, dict) else photo_index
if not isinstance(photo_list, list): photo_list = []
def photos_in(group, event=None):
    out = []
    for ph in photo_list:
        if ph.get('group') != group: continue
        if event and ph.get('event_slug') != event: continue
        path = ph.get('path', '')
        path = path if path.startswith('photos/') else 'photos/' + path.lstrip('/')
        thumb = ph.get('thumb') or path.replace('.jpg', '_thumb.jpg')
        thumb = thumb if thumb.startswith('photos/') else 'photos/' + thumb.lstrip('/')
        out.append(dict(ph, path=path, thumb=thumb))
    return sorted(out, key=lambda x: x['path'])
def first_photo(group, event=None, fallback=''):
    ps = photos_in(group, event)
    return ps[0]['path'] if ps else fallback
def gallery_html(items, rel, cls='gallery'):
    if not items: return ''
    return f'<div class="{cls}">' + ''.join(f'<a href="{rel}{i["path"]}" data-lb><img src="{rel}{i["thumb"]}" alt="{html.escape(str(i.get("title") or ""))}" loading="lazy"></a>' for i in items) + '</div>'

def render(template, outpath, rel, **ctx):
    ctx.setdefault('rel', rel); ctx.setdefault('year', date.today().year)
    htmlout = env.get_template(template).render(**ctx)
    outpath.parent.mkdir(parents=True, exist_ok=True)
    outpath.write_text(htmlout, encoding='utf-8')

# ---------- příspěvky ----------
for p in posts:
    rel = '../../'
    body = p['body']
    cover_rel = p['fm']['images'][0] if p['fm'].get('images') else None
    # první obrázek = cover → vyndat z těla
    m = IMG_TOKEN.search(body)
    if m and cover_rel and m.group(2) == cover_rel:
        body = body[:m.start()] + body[m.end():]
    cover_full, cover_thumb = img_out(cover_rel) if cover_rel else (None, None)
    p['cover'] = cover_full; p['thumb'] = cover_thumb
    h, imgs = md_to_html(body, rel, img_map=True)
    p['html'] = h
    others = [o for o in posts if o is not p][:6]
    render('post.html', OUT / 'kronika' / p['slug'] / 'index.html', rel, title=p['title'], description=p['excerpt'],
           section='kronika', p=p, others=others, og_image=None)

# kronika – seznam
by_year = {}
for p in posts: by_year.setdefault(p['year'], []).append(p)
render('kronika.html', OUT / 'kronika' / 'index.html', '../', title='Kronika', section='kronika',
       by_year=sorted(by_year.items(), reverse=True))

# ---------- akce ----------
for e in events:
    d1, d2 = e['dt'], parse_dt(e['fm'].get('end_date'))
    if d1 and d2 and d2.date() != d1.date():
        if d1.month == d2.month and d1.year == d2.year: e['date_range'] = f'{d1.day}.–{d2.day}. {d1.month}. {d1.year}'
        else: e['date_range'] = f'{cz_date(d1)} – {cz_date(d2)}'
    else: e['date_range'] = cz_date(d1)
    e['year'] = d1.year if d1 else 0
    e['location'] = e['fm'].get('location') or ''
    e['description'] = strip_markers(e['fm'].get('description') or '')
events.sort(key=lambda e: e['dt'] or datetime.min, reverse=True)
ev_by_year = {}
for e in events: ev_by_year.setdefault(e['year'], []).append(e)
render('akce.html', OUT / 'akce' / 'index.html', '../', title='Závody a akce', section='akce',
       by_year=sorted(ev_by_year.items(), reverse=True))

# ---------- vlastní stránky ----------
def content_page(name, section, extra_html='', aside=None, hero=None):
    fm, body = read_md(CONTENT / f'{name}.md')
    rel = '../'
    h, _ = md_to_html(strip_markers(body), rel)
    h += extra_html
    hero_img = fm.get('hero') or hero
    render('page.html', OUT / section / 'index.html', rel, title=fm.get('title'), heading=fm.get('heading'),
           eyebrow=fm.get('eyebrow'), lead=fm.get('lead'), hero_img=hero_img, section=section, html=h, aside=aside,
           description=fm.get('lead'))

content_page('klub', 'klub', extra_html='<h2>Z klubového života</h2>' + gallery_html(
    photos_in('akce', '2025-04-den-zeme') + photos_in('akce', '2022-10-brigada') + photos_in('akce', '2024-06-odm'), '../'),
    aside='<h3>Rychle</h3><ul><li><a href="#nabor">Nábor dětí od 8 let</a></li><li><a href="../kronika/">Kronika</a></li><li><a href="../akce/">Závody a akce</a></li><li><a href="../uspechy/">Úspěchy</a></li><li><a href="../kontakt/">Kontakt</a></li></ul>'
          '<h3 style="margin-top:18px">Bylo nebylo</h3><p>Film o lásce ke sportu, vodácích, závodech a síle, která nás pohání vpřed.</p><p><a class="more" href="https://www.youtube.com/watch?v=XQZUWNTBx80" target="_blank" rel="noopener">Přehrát na YouTube →</a></p>')
content_page('areal', 'areal', extra_html='<h2>Areál z výšky i z vody</h2>' + gallery_html(photos_in('areal') + photos_in('hero'), '../'),
    aside='<h3>Praktické</h3><ul><li>Tréninkové hodiny, kemp, ubytovna, půjčovna: <a href="https://raftingcb.cz/" target="_blank" rel="noopener">raftingcb.cz</a></li><li>Hospoda Na Kanále: otevřeno denně duben–září</li><li>Adresa: České Vrbné 1995, 370 11 České Budějovice</li><li><a href="../kontakt/">Jak k nám</a></li></ul>')
content_page('kontakt', 'kontakt', hero=None)
content_page('uspechy', 'uspechy', extra_html='<h2>Kuba mistrem světa 2026</h2>' + gallery_html(photos_in('akce', '2026-07-kuba-mistr'), '../') +
    '<h2>ME juniorů a U23 2022 u nás</h2>' + gallery_html(photos_in('akce', '2026-07-eca-cup-cb')[:3], '../'),
    aside='<h3>Sleduj výsledky</h3><ul><li><a href="https://www.kanoe.cz" target="_blank" rel="noopener">kanoe.cz – Český svaz kanoistů</a></li><li><a href="https://zive.results.cz" target="_blank" rel="noopener">results.cz – živé výsledky</a></li><li><a href="https://www.canoeicf.com" target="_blank" rel="noopener">canoeicf.com</a></li></ul><h3 style="margin-top:18px">Z kroniky</h3><ul><li><a href="../kronika/jakub-krejci-na-mistrovstvi-sveta/">Jakub Krejčí na mistrovství světa</a></li><li><a href="../kronika/jakub-krejci-ovladl-anketu-sportovec-okresu-za-rok-2025/">Sportovec okresu 2025</a></li><li><a href="../kronika/ms-rafting-u23/">MS v raftingu U23</a></li><li><a href="../kronika/mlade-nadeje-skvscb-sbiraji-oceneni/">Mladé naděje sbírají ocenění</a></li></ul>')

# ---------- historie (z rešerše) ----------
hist_src = CONTENT / 'historie-src.md'
if hist_src.exists():
    txt = strip_markers(hist_src.read_text(encoding='utf-8'))
    def section(title):
        m = re.search(r'^## \d+\. ' + re.escape(title) + r'\s*$(.*?)(?=^## \d+\. |\Z)', txt, re.M | re.S)
        return m.group(1).strip() if m else ''
    story, lida, timeline = section('Příběh místa'), section('Lída Polesná'), section('Časová osa')
    timeline = re.sub(r'^### ', '#### ', timeline, flags=re.M)
    timeline = timeline.replace('- **2007–2008**', '- **2006** – První ročník Mezinárodního vodáckého festivalu Wave: mezinárodní slalom ICF (na startu Tony Estanguet, Štěpánka Hilgertová, Stanislav Ježek), mládežnické závody, kapely a večírky. Koná se do roku 2015.\n- **2007–2008**', 1)
    timeline = timeline.replace('- **2016**', '- **2015** – Poslední ročník festivalu Wave (Memoriál Zdenky Husákové) spolu s ECA Junior Cupem.\n- **2016**', 1)
    wave_md = (CONTENT / 'wave.md').read_text(encoding='utf-8') if (CONTENT / 'wave.md').exists() else ''
    body = (story + '\n\n## Lída Polesná\n\n' + lida + '\n\nWAVESECTION\n\n## Časová osa\n\n' + timeline +
            '\n\n## Prameny\n\n- Štumbauer, P. (2017): *Historie vodáckého areálu Lídy Polesné v Českém Vrbném.* Diplomová práce, Pedagogická fakulta JU v Českých Budějovicích. [dspace.jcu.cz](https://dspace.jcu.cz/handle/20.500.14390/33558)\n'
            '- Štumbauer, J. & Štumbauer, P. (2017): Historie českobudějovické kanoistiky od jejích počátků do poloviny 80. let 20. století. *Studia Kinanthropologica* 18(2). [PDF](https://sk.pf.jcu.cz/pdfs/stk/2017/02/08.pdf)\n'
            '- Polesná, L. (1979): *Hranaté medaile.* Jihočeské nakladatelství.\n'
            '- [Vodácký areál Lídy Polesné – Wikipedie](https://cs.wikipedia.org/wiki/Vod%C3%A1ck%C3%BD_are%C3%A1l_L%C3%ADdy_Polesn%C3%A9), [Ludmila Polesná – Wikipedie](https://cs.wikipedia.org/wiki/Ludmila_Polesn%C3%A1), dobový tisk a klubový archiv.\n')
    rel = '../'
    h, _ = md_to_html(body, rel)
    hist_photos = photos_in('historie')
    h = h.replace('<h2>Lída Polesná</h2>', '<h2>Ze starého alba</h2>' + gallery_html(hist_photos, rel) + '<h2>Lída Polesná</h2>', 1)
    def yt(vid, title):
        return f'<figure><div class="video"><iframe src="https://www.youtube-nocookie.com/embed/{vid}" title="{html.escape(title)}" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe></div><figcaption>{html.escape(title)}</figcaption></figure>'
    wave_html, _ = md_to_html(wave_md, rel)
    wave_html = wave_html.replace('<h2>Festival Wave (2006–2015)</h2>', '<h2 id="wave">Festival Wave (2006–2015)</h2>', 1)
    wave_html += gallery_html(photos_in('wave'), rel) + '<div class="video-grid">' + yt('idyDTOz1l1g', 'Festivalový film Wave 2014') + yt('LvP5XhDhKbw', 'Velký vodácký festival WAVE 2008') + '</div>'
    h = h.replace('<p>WAVESECTION</p>', wave_html, 1)
    intro = '<h2 id="filmy">Bylo nebylo</h2><p>Film o lásce ke sportu, vodácích, závodech a síle, která nás pohání vpřed.</p>' + yt('XQZUWNTBx80', 'Bylo nebylo – film o klubu a areálu')
    h = intro + h
    render('page.html', OUT / 'historie' / 'index.html', rel, title='Historie', heading='Příběh místa', eyebrow='Historie klubu a areálu',
           lead='Od propusti starého jezu, kde trénovala Lída Polesná, přes dráhu postavenou rukama členů oddílu až po kanál olympijských parametrů.',
           hero_img=first_photo('historie', fallback='photos/areal/01.jpg'), section='historie', html=h,
           aside='<h3>V kostce</h3><ul><li><b>1950</b> první slalom v jižních Čechách</li><li><b>1965</b> založen oddíl TJ Škoda</li><li><b>1978–1983</b> stavba umělé dráhy</li><li><b>2002</b> povodeň</li><li><b>2009–2012</b> přestavba kanálu</li><li><b>2019–2022</b> nové zázemí</li><li><b>2022</b> ME juniorů a U23</li></ul>',
           description='Historie SK Vodní slalom České Budějovice a Vodáckého areálu Lídy Polesné.')

# ---------- úvodní stránka ----------
directory = [
    dict(name='Rafting CB', text='Rafty, půjčovna, komerční jízdy, ubytování a kemp.', url='https://raftingcb.cz/', label='raftingcb.cz', external=True),
    dict(name='Hospoda Na Kanále', text='Jídlo, pití a terasa nad vodou. Otevřeno denně duben–září.', url='https://www.facebook.com/hospodanakanale/', label='Facebook', external=True),
    dict(name='BUDE Sport', text='Paddleboarding na klidné vodě nad jezem.', url='../areal/', label='Více v areálu', external=False),
    dict(name='River surf', text='Surfování na stojaté vlně na prvním stupni kanálu.', url='../areal/', label='Více v areálu', external=False),
    dict(name='CB Dragons', text='Dračí lodě — tréninky a firemní jízdy na klidné vodě.', url='../areal/', label='Více v areálu', external=False),
]
for d in directory:
    if not d['external']: d['url'] = d['url'].replace('../', '')
render('home.html', OUT / 'index.html', '', title=None, section='home', latest=posts[:3],
       hero=dict(path='photos/hero/13.jpg'),
       feat=dict(deti=first_photo('akce', '2025-05-cp-zaci-veltrusy', 'photos/akce/2024-06-odm/01.jpg'),
                 areal=(photos_in('areal')[1]['path'] if len(photos_in('areal')) > 1 else first_photo('areal')),
                 zavody=first_photo('akce', '2026-09-nkz-cb', first_photo('hero'))),
       directory=directory)

# 404 + .nojekyll
(OUT / '.nojekyll').write_text('')
render('page.html', OUT / '404.html', args.base, title='Stránka nenalezena', heading='Tady nic neteče', eyebrow='404',
       lead='Stránka, kterou hledáš, neexistuje. Zkus úvodní stránku nebo kroniku.', html=f'<p><a class="btn btn-primary" href="{args.base}">Na úvod</a></p>', section='')

print(f'OK: {len(posts)} příspěvků, {len(events)} akcí, {len(photo_list)} fotek; čas {time.time()-T0:.0f}s; nezpracované obrázky: {pending}')
if pending:
    print('→ spusť build znovu, dokončí zbývající obrázky.')
