"""Responsive layout audit using headless Chromium. Tests visible overflow, not only syntax."""
from pathlib import Path
import json
import sys
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / 'Python_ペンテスト10作品_全行構文分解_20261111.html'
SIZES = {'small': [320,360,390,600], 'large':[768,1024,1366,1920]}
if len(sys.argv)!=2 or sys.argv[1] not in SIZES:
    raise SystemExit('Usage: python3 verification/layout_checks.py small|large')
checks=[]
def check(label, ok, observation=None):
    checks.append({'check':label,'pass':bool(ok),'observation':observation})

with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox','--disable-dev-shm-usage'])
    for width in SIZES[sys.argv[1]]:
        page=browser.new_page(viewport={'width':width,'height':820}, device_scale_factor=1)
        errors=[]
        page.on('pageerror', lambda err:errors.append(str(err)))
        page.set_content(HTML.read_text(encoding='utf8'), wait_until='domcontentloaded')
        page.wait_for_timeout(80)
        stats=page.evaluate('''() => ({vp:innerWidth,body:document.scrollingElement.scrollWidth,main:document.querySelector('main').getBoundingClientRect().right,head:document.querySelector('header').getBoundingClientRect().height})''')
        check(f'{width}: cover fits without page overflow',stats['body']<=width+1,stats)
        check(f'{width}: main fits screen',stats['main']<=width+1,stats['main'])
        check(f'{width}: header is compact',stats['head'] <= (160 if width<=600 else 140),stats['head'])
        check(f'{width}: cover cards are not narrower than 100px', page.evaluate("Math.min(...[...document.querySelectorAll('.stats > div')].map(x=>x.getBoundingClientRect().width))")>=100)
        for target in ('p01','p09','appendix-a'):
            page.evaluate('(t)=>location.hash="#"+t',target)
            page.wait_for_timeout(45)
            r=page.evaluate('''()=>({scroll:document.scrollingElement.scrollWidth,active:document.querySelector('.chapter.active')?.id})''')
            check(f'{width}: {target} section navigation',r['active']==target,r)
            check(f'{width}: {target} no body overflow',r['scroll']<=width+1,r)
        page.evaluate('location.hash="#p01-step1"');page.wait_for_timeout(50)
        is_scroll=page.locator('#p01-step1 pre.numbered').evaluate('(e)=>e.scrollWidth>=e.clientWidth')
        check(f'{width}: code content remains reachable',is_scroll)
        # Stress visual scaling at 140% using DOM click to avoid stale button layout during rapid growth.
        page.locator('#larger').evaluate('(e)=>{for(let i=0;i<8;i++)e.click()}')
        for target in ('cover','p01','p09','appendix-a'):
            page.evaluate('(t)=>location.hash="#"+t',target);page.wait_for_timeout(45)
            scroll=page.evaluate('document.scrollingElement.scrollWidth')
            check(f'{width}: {target} no page overflow at 140%',scroll<=width+1,scroll)
        check(f'{width}: no script errors',not errors,errors)
        if width<=900:
            page.locator('#menu').click()
            check(f'{width}: mobile TOC accessible',page.locator('#toc').evaluate("e=>e.classList.contains('open')"))
            page.locator('nav a[href="#p02"]').click()
            page.wait_for_timeout(60)
            check(f'{width}: mobile TOC closes after choice',not page.locator('#toc').evaluate("e=>e.classList.contains('open')"))
        else:
            check(f'{width}: desktop nav visible',page.locator('#toc').is_visible())
        if width==390:
            page.evaluate('location.hash="#cover"');page.wait_for_timeout(60)
            page.screenshot(path=str(ROOT/'verification'/'mobile_layout.png'))
            page.evaluate('location.hash="#p01-step1"');page.wait_for_timeout(80)
            page.locator('#p01-step1 pre.numbered').scroll_into_view_if_needed()
            page.screenshot(path=str(ROOT/'verification'/'mobile_code_layout.png'))
        if width==1366:
            page.evaluate('location.hash="#cover"');page.wait_for_timeout(60)
            page.screenshot(path=str(ROOT/'verification'/'desktop_layout.png'))
        page.close()
    browser.close()

result={'environment':'Chromium headless set_content, viewport 820px high; code/table inner horizontal scroll permitted',
        'group':sys.argv[1],'checks':checks,'passed':sum(x['pass'] for x in checks),'total':len(checks),
        'failed':[x for x in checks if not x['pass']],
        'limitations':'Set_content checks layout, not file:// localStorage persistence or a physical mobile OS.'}
out=ROOT/'verification'/f'layout_{sys.argv[1]}.json'
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(f'LAYOUT_{sys.argv[1].upper()}: {result["passed"]}/{result["total"]} PASS')
if result['failed']:
    for item in result['failed'][:15]:print('FAIL',item)
    raise SystemExit(1)
