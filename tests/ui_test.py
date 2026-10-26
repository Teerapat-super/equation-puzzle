"""ทดสอบ UI ด้วย Playwright: เล่นจริงบนจอคอม (ลากวาง) และจอมือถือ (แตะ)
รัน:  python3 tests/ui_test.py
"""
import sys, pathlib, csv, io
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent
URL = (ROOT.parent / 'index.html').as_uri()
SHOT = ROOT / 'screenshots'; SHOT.mkdir(exist_ok=True)
results = []
def check(c, m): results.append((bool(c), m)); print(('PASS ' if c else 'FAIL ') + m)

# หา "ชิ้นที่ถูก" ของสถานะปัจจุบัน (ใช้ engine ตัวเดียวกับเกม)
JS_FIND = """()=>{
  const c=G.cur;
  if(c.phase==='operate'){ if(parenOf(c.state)&&Math.random()<0.5){const p=G.pieces.find(p=>p.kind==='simp'&&validateSimplify(c.state,p.cand).ok); if(p) return {kind:'simp',id:p.id};}
    const k=opKey(bestOp(c.state)); return {kind:'op',id:G.pieces.find(p=>p.kind==='op'&&opKey(p.op)===k).id}; }
  if(c.phase==='simplify') return {kind:'simp',id:G.pieces.find(p=>p.kind==='simp'&&validateSimplify(c.state,p.cand).ok).id};
  return {kind:'ans',id:G.pieces.find(p=>p.kind==='ans'&&validateAnswer(c.problem.orig,p.v).ok).id};
}"""

def drag(page, pid, zone):
    pc = page.locator(f'.piece[data-id="{pid}"]'); z = page.locator(f'[data-zone="{zone}"]')
    pc.scroll_into_view_if_needed(); z.scroll_into_view_if_needed(); pc.scroll_into_view_if_needed()
    a = pc.bounding_box(); b = z.bounding_box()
    ax, ay = a['x'] + a['width'] / 2, a['y'] + a['height'] / 2
    bx, by = b['x'] + b['width'] / 2, b['y'] + b['height'] / 2
    page.mouse.move(ax, ay); page.mouse.down()
    for i in range(1, 11): page.mouse.move(ax + (bx - ax) * i / 10, ay + (by - ay) * i / 10)
    page.mouse.up()

def tap(page, pid, zone):
    page.locator(f'.piece[data-id="{pid}"]').tap(); page.locator(f'[data-zone="{zone}"]').tap()

def play_question(page, place):
    for _ in range(20):
        if page.locator('#modal').is_visible(): return True
        f = page.evaluate(JS_FIND)
        if f['kind'] == 'op': place(page, f['id'], 'opL'); place(page, f['id'], 'opR')
        else: place(page, f['id'], 'simp' if f['kind'] == 'simp' else 'ans')
        page.click('#btn-check'); page.wait_for_timeout(750)
        if 'bad' in page.get_attribute('#feedback', 'class'):
            print('   unexpected:', page.inner_text('#feedback')); return False
    return page.locator('#modal').is_visible()

def play_round(page, place, name, extra=None):
    ok = True
    for q in range(5):
        if extra and q == 0: extra()
        ok = play_question(page, place) and ok
        page.click('#modal-next'); page.wait_for_timeout(150)
    return ok

def run(mobile):
    name = 'mobile' if mobile else 'desktop'
    place = tap if mobile else drag
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={'width': 375, 'height': 740}, has_touch=True, is_mobile=True, accept_downloads=True) if mobile \
            else b.new_context(viewport={'width': 1280, 'height': 900}, accept_downloads=True)
        page = ctx.new_page(); errs = []
        page.on('pageerror', lambda e: errs.append(str(e)))
        page.on('console', lambda m: m.type == 'error' and errs.append(m.text))
        page.on('dialog', lambda d: d.accept())
        page.goto(URL)
        check(page.locator('.topic-card').count() == 6, f'{name}: 6 topic cards on start screen')
        page.screenshot(path=str(SHOT / f'{name}_start.png'), full_page=True)
        # ต้องกรอกชื่อก่อน
        page.locator('[data-topic="1"]').click()
        check(page.locator('#screen-start').is_visible() and 'need' in page.get_attribute('#player-name', 'class'), f'{name}: name required before playing')
        page.fill('#player-name', 'ทดสอบ ม.1/1')
        page.click('#btn-howto'); check(page.locator('#screen-howto').is_visible(), f'{name}: how-to screen'); page.click('#btn-back')
        # ---------- ด้าน 1 รอบที่ 1 ----------
        page.locator('[data-topic="1"]').click()
        badge = page.inner_text('#lvl-badge')
        check('ด้าน 1' in badge and 'ข้อ 1/5' in badge, f'{name}: badge shows topic 1 · question 1/5')
        check(page.evaluate("G.round.every(p=>p.level===1)") and page.evaluate("new Set(G.round.map(p=>eqKey(p.orig))).size")==5, f'{name}: 5 distinct level-1 problems')
        check(page.locator('.piece.k-ans').count() == 0, f'{name}: answer pieces hidden at start')
        k = page.evaluate("()=>{const k=opKey(bestOp(G.cur.state));return G.pieces.find(p=>p.kind==='op'&&opKey(p.op)===k).id}")
        place(page, k, 'opL'); page.click('#btn-check')
        check('bad' in page.get_attribute('#feedback', 'class') and page.evaluate('G.cur.wrong') == 1, f'{name}: one-side op rejected')
        page.locator('[data-zone="opL"]').click(); check(page.evaluate('G.slots.opL') is None, f'{name}: tap slot removes piece')
        page.click('#btn-hint'); check(page.evaluate('G.cur.hints') == 1, f'{name}: hint works')
        page.wait_for_timeout(1600)
        tv = page.inner_text('#timer'); m_, s_ = tv.split(':')
        check(int(m_) * 60 + int(s_) >= 2 and abs(page.evaluate('Timer.sec()') - (int(m_) * 60 + int(s_))) <= 1, f'{name}: timer ticking in HUD ({tv})')
        page.screenshot(path=str(SHOT / f'{name}_game.png'), full_page=True)
        page.click('#btn-restart')
        check(page.evaluate('G.cur.log.length') == 1 and page.evaluate('Timer.sec()') >= 1, f'{name}: restart keeps timer running')
        ok = play_round(page, place, name)
        check(ok, f'{name}: topic 1 round 1 — 5 questions passed via {"tap" if mobile else "drag"}')
        check(page.locator('#screen-final').is_visible() and page.locator('#final-rows tr').count() == 5, f'{name}: final screen with 5 rows')
        r = page.evaluate('G.results')
        check(r[0]['sec'] >= 1 and all(x['sec'] >= 0 for x in r), f'{name}: per-question time recorded {[x["sec"] for x in r]}')
        check('ครั้งแรก' in page.inner_text('#final-compare'), f'{name}: first attempt message')
        check(page.evaluate("Store.sessions().length") == 1, f'{name}: session saved')
        page.screenshot(path=str(SHOT / f'{name}_final.png'), full_page=True)
        # ---------- ด้าน 1 รอบที่ 2 (เทียบกับครั้งก่อน) ----------
        page.click('#btn-again')
        check(page.evaluate("G.results.length") == 0 and page.evaluate("G.topic.id") == 1, f'{name}: play again resets round in same topic')
        play_round(page, place, name)
        check('เทียบกับครั้งก่อน' in page.inner_text('#final-compare'), f'{name}: compares with previous attempt')
        # ---------- ด้าน 6 แบบผสม ----------
        page.click('#btn-tohome'); page.wait_for_timeout(100)
        check('เล่นแล้ว 2 ครั้ง' in page.inner_text('[data-topic="1"]'), f'{name}: topic card shows play count')
        page.locator('[data-topic="6"]').click()
        check(page.evaluate("G.round.map(p=>p.level).join()") == '1,2,3,4,5', f'{name}: mixed topic = levels 1→5')
        check(play_round(page, place, name), f'{name}: mixed topic all 5 passed')
        # ---------- หน้าพัฒนาการ ----------
        page.click('#btn-final-stats')
        check(page.locator('#screen-stats').is_visible() and page.locator('#stats-body svg').count() == 2, f'{name}: stats screen with 2 charts (topic 6)')
        page.locator('[data-stopic="1"]').click(); page.wait_for_timeout(100)
        check(page.locator('#chart-time .ring').count() == 2 and page.locator('.hist tbody tr').count() == 2, f'{name}: topic 1 chart has 2 points + 2 history rows')
        check('เฉลี่ย' in page.inner_text('.trend'), f'{name}: trend summary text')
        page.locator('#chart-time .hit').scroll_into_view_if_needed()
        hb = page.locator('#chart-time .hit').bounding_box()
        if mobile: page.touchscreen.tap(hb['x'] + hb['width'] - 5, hb['y'] + hb['height'] / 2)
        else: page.mouse.move(hb['x'] + hb['width'] - 5, hb['y'] + hb['height'] / 2)
        check(page.locator('#chart-time .tip').is_visible() and 'ครั้งที่ 2' in page.inner_text('#chart-time .tip'), f'{name}: chart tooltip on hover/touch')
        page.screenshot(path=str(SHOT / f'{name}_stats.png'), full_page=True)
        check(not page.evaluate('document.documentElement.scrollWidth>window.innerWidth'), f'{name}: no horizontal scroll (stats)')
        # CSV
        with page.expect_download() as dl: page.click('#btn-export')
        txt = pathlib.Path(dl.value.path()).read_text(encoding='utf-8-sig')
        rows = list(csv.reader(io.StringIO(txt)))
        check(rows[0][0] == 'ผู้เล่น' and len(rows) == 1 + 15 and rows[1][0] == 'ทดสอบ ม.1/1', f'{name}: CSV export header + 15 question rows')
        # บันทึกคงอยู่หลังรีโหลด
        page.reload(); page.wait_for_timeout(200)
        check(page.input_value('#player-name') == 'ทดสอบ ม.1/1' and page.evaluate("Store.sessions().length") == 3, f'{name}: history + name persist after reload')
        page.click('#btn-stats'); page.click('#btn-clear'); page.wait_for_timeout(100)
        check(page.evaluate("Store.sessions().length") == 0 and 'ยังไม่มีประวัติ' in page.inner_text('#stats-body'), f'{name}: clear player history')
        check(not errs, f'{name}: no JS errors {errs[:2]}')
        b.close()

run(False); run(True)
print(f"\n{sum(r[0] for r in results)}/{len(results)} passed")
sys.exit(0 if all(r[0] for r in results) else 1)
