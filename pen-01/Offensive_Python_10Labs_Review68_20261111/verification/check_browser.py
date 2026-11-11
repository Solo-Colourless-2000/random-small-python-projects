"""Visual-state and interaction smoke tests for the local standalone HTML."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / 'Python_ペンテスト10作品_全行構文分解_20261111.html'
checks = []
errors = []


def check(name, predicate):
    ok = bool(predicate)
    checks.append({'check': name, 'result': 'PASS' if ok else 'FAIL'})
    if not ok:
        errors.append(name)


with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox', '--disable-dev-shm-usage'])
    for kind, viewport in [('desktop', {'width': 1365, 'height': 768}), ('mobile', {'width': 390, 'height': 780})]:
        page = browser.new_page(viewport=viewport)
        page.on('pageerror', lambda err: errors.append('JS page error: ' + str(err)))
        page.set_content(HTML.read_text(encoding='utf-8'), wait_until='domcontentloaded')
        page.wait_for_timeout(150)
        check(f'{kind}: cover visible', page.locator('.chapter.active').get_attribute('id') == 'cover')
        check(f'{kind}: 20 chapters present', page.locator('.chapter').count() == 20)
        check(f'{kind}: 40 lessons present', page.locator('article.step').count() == 40)
        if kind == 'mobile':
            page.locator('#menu').click()
            check('mobile: menu opens', 'open' in (page.locator('#toc').get_attribute('class') or ''))
        page.locator('nav a[href="#p02"]').click()
        page.wait_for_timeout(100)
        check(f'{kind}: navigation to project 02', page.locator('.chapter.active').get_attribute('id') == 'p02')
        page.locator('#search').fill('SameSite')
        check(f'{kind}: search finds content', page.locator('#matches a').count() >= 1)
        page.locator('#clear-search').click()
        check(f'{kind}: search clears', page.locator('#results').is_hidden())
        page.locator('#larger').click()
        check(f'{kind}: font scaling works', float(page.locator('html').evaluate("el => getComputedStyle(el).getPropertyValue('--scale')")) > 1)
        page.locator('#wrap').click()
        check(f'{kind}: wrapping toggle works', page.locator('body').evaluate("el => el.classList.contains('wrap')"))
        page.locator('#p02 [data-check]').check()
        check(f'{kind}: completion check works', '1 / 20' in page.locator('#progress').inner_text())
        page.close()
    browser.close()

report = {'environment': 'headless Chromium using set_content with local HTML source, two viewport widths; file:// navigation blocked by this environment',
          'checks': checks, 'passed': sum(c['result']=='PASS' for c in checks),
          'total': len(checks), 'errors': errors,
          'limit': 'Smoke checks only; platform-specific persistence/clipboard permissions are not guaranteed.'}
(ROOT/'verification/browser_checks.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
print('BROWSER_CHECKS=',report['total'],'PASSED=',report['passed'],'ERRORS=',len(errors))
if errors:
    print('\n'.join(errors))
    raise SystemExit(1)
