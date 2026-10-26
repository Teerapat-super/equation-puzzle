import sys, pathlib
from playwright.sync_api import sync_playwright
URL=(pathlib.Path(__file__).resolve().parent.parent/'index.html').as_uri()
SHOT=str(pathlib.Path(__file__).resolve().parent/'screenshots')+'/'
pathlib.Path(SHOT).mkdir(exist_ok=True)
results=[]
def check(c,m): results.append((bool(c),m)); print(('PASS ' if c else 'FAIL ')+m)

JS_FIND = """(phase)=>{
  const c=G.cur;
  if(c.phase==='operate'){ if(parenOf(c.state)&&Math.random()<0.5){const p=G.pieces.find(p=>p.kind==='simp'&&validateSimplify(c.state,p.cand).ok); if(p) return {kind:'simp',id:p.id};}
    const k=opKey(bestOp(c.state)); return {kind:'op',id:G.pieces.find(p=>p.kind==='op'&&opKey(p.op)===k).id}; }
  if(c.phase==='simplify') return {kind:'simp',id:G.pieces.find(p=>p.kind==='simp'&&validateSimplify(c.state,p.cand).ok).id};
  return {kind:'ans',id:G.pieces.find(p=>p.kind==='ans'&&validateAnswer(c.problem.orig,p.v).ok).id};
}"""

def drag(page,pid,zone):
    pc=page.locator(f'.piece[data-id="{pid}"]'); pc.scroll_into_view_if_needed()
    a=pc.bounding_box(); z=page.locator(f'[data-zone="{zone}"]')
    z.scroll_into_view_if_needed(); a=pc.bounding_box(); b=z.bounding_box()
    page.mouse.move(a['x']+a['width']/2,a['y']+a['height']/2); page.mouse.down()
    for i in range(1,11):
        page.mouse.move(a['x']+a['width']/2+(b['x']+b['width']/2-a['x']-a['width']/2)*i/10, a['y']+a['height']/2+(b['y']+b['height']/2-a['y']-a['height']/2)*i/10)
    page.mouse.up()

def tap(page,pid,zone):
    page.locator(f'.piece[data-id="{pid}"]').tap()
    page.locator(f'[data-zone="{zone}"]').tap()

def play_level(page,place):
    for _ in range(20):
        if page.locator('#modal').is_visible(): return True
        f=page.evaluate(JS_FIND)
        if f['kind']=='op': place(page,f['id'],'opL'); place(page,f['id'],'opR')
        else: place(page,f['id'],'simp' if f['kind']=='simp' else 'ans')
        page.click('#btn-check'); page.wait_for_timeout(750)
        cls=page.get_attribute('#feedback','class')
        if 'bad' in cls: print('   unexpected bad:',page.inner_text('#feedback')); return False
    return page.locator('#modal').is_visible()

def run(mobile):
    name='mobile' if mobile else 'desktop'
    with sync_playwright() as p:
        b=p.chromium.launch()
        ctx=b.new_context(viewport={'width':375,'height':740},has_touch=True,is_mobile=True) if mobile else b.new_context(viewport={'width':1280,'height':900})
        page=ctx.new_page(); errs=[]
        page.on('pageerror',lambda e:errs.append(str(e))); page.on('console',lambda m: m.type=='error' and errs.append(m.text))
        page.goto(URL)
        page.screenshot(path=SHOT+f'{name}_start.png')
        page.click('#btn-howto'); check(page.locator('#screen-howto').is_visible(),f'{name}: how-to screen'); page.click('#btn-back')
        page.click('#btn-start'); check(page.locator('#screen-game').is_visible(),f'{name}: game screen')
        check('ด่าน 1/5' in page.inner_text('#lvl-badge'),f'{name}: progress shows level 1/5')
        check(page.locator('.piece.k-ans').count()==0,f'{name}: answer pieces hidden at start')
        place=tap if mobile else drag
        # wrong: one side only
        k=page.evaluate("()=>{const k=opKey(bestOp(G.cur.state));return G.pieces.find(p=>p.kind==='op'&&opKey(p.op)===k).id}")
        place(page,k,'opL'); page.click('#btn-check')
        check('bad' in page.get_attribute('#feedback','class') and page.evaluate('G.cur.wrong')==1,f'{name}: one-side op rejected, wrong counted')
        page.locator('[data-zone="opL"]').click(); check(page.evaluate('G.slots.opL')is None,f'{name}: tap slot removes piece')
        page.click('#btn-hint'); check(page.evaluate('G.cur.hints')==1 and 'hint' in page.get_attribute('#feedback','class'),f'{name}: hint works')
        page.screenshot(path=SHOT+f'{name}_game.png',full_page=True)
        page.click('#btn-restart'); check(page.evaluate('G.cur.log.length')==1,f'{name}: restart resets level')
        for lv in range(5):
            okk=play_level(page,place); check(okk,f'{name}: level {lv+1} passed via {"tap" if mobile else "drag"}')
            if lv==0: page.screenshot(path=SHOT+f'{name}_modal.png')
            page.click('#modal-next'); page.wait_for_timeout(200)
        check(page.locator('#screen-final').is_visible(),f'{name}: final screen')
        total=page.inner_text('#final-score'); rows=page.locator('#final-rows tr').count()
        check(rows==5 and int(total)==page.evaluate('G.results.reduce((a,r)=>a+r.score,0)'),f'{name}: total {total} = sum of 5 levels')
        check(page.evaluate('G.results[0].score')==75 and all(page.evaluate(f'G.results[{i}].score')==100 for i in range(1,5)),f'{name}: level1=75 (1 hint + 1 wrong), levels 2-5 = 100')
        page.screenshot(path=SHOT+f'{name}_final.png',full_page=True)
        old=page.evaluate("G.lastKey"); page.click('#btn-newround')
        check(page.locator('#screen-game').is_visible() and page.evaluate("G.lastKey")!=old and page.evaluate('G.total')==0,f'{name}: new round = new random problems')
        ow=page.evaluate('document.documentElement.scrollWidth>window.innerWidth')
        check(not ow,f'{name}: no horizontal scroll')
        check(not errs,f'{name}: no JS errors {errs[:2]}')
        b.close()
run(False); run(True)
print(f"\n{sum(r[0] for r in results)}/{len(results)} passed")
sys.exit(0 if all(r[0] for r in results) else 1)
