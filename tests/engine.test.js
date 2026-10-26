const fs=require('fs');
const html=fs.readFileSync('index.html','utf8');
const src=html.split('/* ==ENGINE START== */')[1].split('/* ==ENGINE END== */')[0];
const E=new Function(src+';return Engine;')();
const {Frac,L,N,linearOf,validateStep,validateSimplify,validateAnswer,solvedValue,genProblem,genOpPieces,genSimpCards,genAnswerCards,bestOp,levelScore}=E;
let pass=0,fail=0;
const ok=(c,m)=>{if(c)pass++;else{fail++;console.log('FAIL:',m);}};
const add=(a,b)=>({t:'add',term:L(a,b)}), mul=k=>({t:'mul',k:new Frac(k)}), div=(k,d=1)=>({t:'div',k:new Frac(k,d)});
function step(s,op){const r=validateStep(s,op,op); if(!r.ok) return {r}; const cand={L:linearOf(r.state.L),R:linearOf(r.state.R)}; const v=validateSimplify(r.state,cand); return {r,v,s:{L:N.linV(cand.L),R:N.linV(cand.R)}};}
function run(s,ops){for(const op of ops){const o=step(s,op); if(!o.r.ok||!o.v.ok) return {fail:o.r.msg}; s=o.s;} return {s};}

let p={L:N.lin(1,5),R:N.lin(0,12)};
let o=run(p,[add(0,-5)]); ok(o.s&&solvedValue(o.s).eq(7),'T1 x+5=12');
ok(validateAnswer(p,new Frac(7)).ok,'T1 answer 7');
o=run({L:N.lin(1,-6),R:N.lin(0,8)},[add(0,6)]); ok(o.s&&solvedValue(o.s).eq(14),'T1 x-6=8');
o=run({L:N.lin(3,0),R:N.lin(0,18)},[div(3)]); ok(o.s&&solvedValue(o.s).eq(6),'T2 3x=18');
o=run({L:N.lin(new Frac(1,4),0),R:N.lin(0,5)},[mul(4)]); ok(o.s&&solvedValue(o.s).eq(20),'T2 x/4=5');
o=run({L:N.lin(2,3),R:N.lin(0,13)},[add(0,-3),div(2)]); ok(o.s&&solvedValue(o.s).eq(5),'T2 2x+3=13 (-3, ÷2)');
o=run({L:N.lin(2,3),R:N.lin(0,13)},[div(2),add(0,new Frac(-3,2))]); ok(o.s&&solvedValue(o.s).eq(5),'T2 2x+3=13 (÷2 first)');
o=run({L:N.lin(3,5),R:N.lin(1,13)},[add(-1,0),add(0,-5),div(2)]); ok(o.s&&solvedValue(o.s).eq(4),'T3 via -x');
o=run({L:N.lin(3,5),R:N.lin(1,13)},[add(-3,0),add(0,-13),div(-2)]); ok(o.s&&solvedValue(o.s).eq(4),'T3 via -3x (4=x)');
o=run({L:N.lin(5,-4),R:N.lin(2,8)},[add(-2,0),add(0,4),div(3)]); ok(o.s&&solvedValue(o.s).eq(4),'T3 5x-4=2x+8');
let pp={L:N.paren(2,L(1,3)),R:N.lin(0,14)};
o=run(pp,[div(2),add(0,-3)]); ok(o.s&&solvedValue(o.s).eq(4),'T3 2(x+3)=14 via ÷2');
ok(validateSimplify(pp,{L:L(2,6),R:L(0,14)}).ok,'T3 distribute correct');
ok(!validateSimplify(pp,{L:L(2,3),R:L(0,14)}).ok,'T3 distribute 2x+3 rejected');
o=run({L:N.lin(2,6),R:N.lin(0,14)},[add(0,-6),div(2)]); ok(o.s&&solvedValue(o.s).eq(4),'T3 after distribute');
let r=validateStep(p,add(0,5),add(0,5)); ok(!r.ok&&r.code==='no-progress'&&r.msg.includes('ผกผัน'),'T4 +5 both rejected');
r=validateStep(p,null,add(0,5)); ok(!r.ok&&r.code==='one-side'&&r.msg.includes('ผกผัน'),'T4 +5 carried without sign change');
ok(!validateSimplify({L:N.sum(N.lin(1,5),L(0,-5)),R:N.sum(N.lin(0,12),L(0,-5))},{L:L(1,0),R:L(0,17)}).ok,'T4 simplify to 17 rejected');
r=validateStep(p,add(0,-5),null); ok(!r.ok&&r.code==='one-side','T5 one side');
r=validateStep(p,add(0,-5),add(0,5)); ok(!r.ok&&r.code==='mismatch','T5 mismatch');
r=validateStep({L:N.lin(3,0),R:N.lin(0,18)},div(0),div(0)); ok(!r.ok&&r.code==='div-zero','T6 ÷0');
r=validateStep({L:N.lin(3,0),R:N.lin(0,18)},mul(0),mul(0)); ok(!r.ok&&r.code==='mul-zero','T6 ×0');
ok(!validateAnswer(p,new Frac(17)).ok,'T7 x=17 rejected');
ok(!validateAnswer(pp,new Frac(10)).ok,'T7 paren wrong');
ok(validateAnswer(pp,new Frac(4)).ok,'T7 paren right');
ok(levelScore(0,0)===100&&levelScore(1,0)===80&&levelScore(0,3)===85&&levelScore(2,20)===50,'scoring');
r=validateStep(p,add(0,-5),add(0,-5)); ok(r.ok&&r.msg.includes('ลบ 5 ออกจากทั้งสองข้าง'),'feedback text');
ok(E.nodeHTML(r.state.L).includes('−'),'display x+5−5');

// ---- new 5-level specific tests ----
// L4: 3(x+2) = x + 14  → x = 4
let q4={L:N.paren(3,L(1,2)),R:N.lin(1,14)};
r=validateStep(q4,div(3),div(3)); ok(!r.ok&&r.code==='no-progress','L4 ÷3 rejected when x on other side');
ok(E.opKey(bestOp(q4))==='add:-1|0','L4 hint suggests −x');
ok(validateSimplify(q4,{L:L(3,6),R:L(1,14)}).ok,'L4 distribute ok');
ok(!validateSimplify(q4,{L:L(3,2),R:L(1,14)}).ok,'L4 bad distribute rejected');
o=run(q4,[add(-1,0),add(0,-6),div(2)]); ok(o.s&&solvedValue(o.s).eq(4),'L4 solve via −x directly on bracket form');
o=run({L:N.lin(3,6),R:N.lin(1,14)},[add(-1,0),add(0,-6),div(2)]); ok(o.s&&solvedValue(o.s).eq(4),'L4 solve after distribute');
// negative k: −2(x−3) = x − 3 → −2x+6 = x−3 → x = 3
let q4n={L:N.paren(-2,L(1,-3)),R:N.lin(1,-3)};
ok(E.nodeHTML(q4n.L).startsWith('−2('),'L4 shows −2(x − 3)');
ok(validateAnswer(q4n,new Frac(3)).ok,'L4 negative k answer');
// L5: 4(x−1) = 2(x+3) → 4x−4 = 2x+6 → x = 5
let q5={L:N.paren(4,L(1,-1)),R:N.paren(2,L(1,3))};
ok(validateSimplify(q5,{L:L(4,-4),R:L(2,6)}).ok,'L5 distribute both sides');
ok(!validateSimplify(q5,{L:L(4,-4),R:L(2,3)}).ok,'L5 half-distributed right rejected');
ok(genSimpCards(q5,null).filter(c=>validateSimplify(q5,c).ok).length===1,'L5 one correct distribute card');
o=run(q5,[add(-2,0),add(0,4),div(2)]); ok(o.s&&solvedValue(o.s).eq(5),'L5 solve without distributing first');
ok(validateAnswer(q5,new Frac(5)).ok&&!validateAnswer(q5,new Frac(-5)).ok,'L5 answer check');
// L2 negative coefficient: −3x + 7 = 19 → x = −4
o=run({L:N.lin(-3,7),R:N.lin(0,19)},[add(0,-7),div(-3)]); ok(o.s&&solvedValue(o.s).eq(-4),'L2 −3x+7=19 → −4');
// L1 x/3 − 2 = 4 → x = 18 (both orders)
o=run({L:N.lin(new Frac(1,3),-2),R:N.lin(0,4)},[add(0,2),mul(3)]); ok(o.s&&solvedValue(o.s).eq(18),'L1 x/3−2=4');
o=run({L:N.lin(new Frac(1,3),-2),R:N.lin(0,4)},[mul(3),add(0,6)]); ok(o.s&&solvedValue(o.s).eq(18),'L1 x/3−2=4 (×3 first)');

// regression: right side 0 (e.g. 2x − 8 = 0) must still be solvable in any order
o=run({L:N.lin(2,-8),R:N.lin(0,0)},[add(0,8),div(2)]); ok(o.s&&solvedValue(o.s).eq(4),'reg 2x−8=0 (+8, ÷2)');
o=run({L:N.lin(2,-8),R:N.lin(0,0)},[div(2),add(0,4)]); ok(o.s&&solvedValue(o.s).eq(4),'reg 2x−8=0 (÷2, +4)');
r=validateStep({L:N.lin(1,5),R:N.lin(0,12)},add(0,5),add(0,5)); ok(!r.ok,'reg +5 on x+5=12 still rejected');
const key=c=>c.L.a+'|'+c.L.b+'='+c.R.a+'|'+c.R.b;
let fuzz=0, types={};
for(let lvl=1;lvl<=5;lvl++) for(let i=0;i<4000;i++){
  const prob=genProblem(lvl); types[lvl+':'+prob.type]=1; let s={L:prob.orig.L,R:prob.orig.R}; let steps=0;
  ok(Number.isInteger(prob.ans)&&prob.ans!==0&&validateAnswer(prob.orig,new Frac(prob.ans)).ok,'gen answer valid '+lvl);
  while(solvedValue(s)===null&&steps<8){
    steps++;
    const pieces=genOpPieces(s,lvl), best=bestOp(s);
    ok(pieces.some(q=>E.opKey(q)===E.opKey(best)),'best in pieces');
    ok(pieces.length>=3&&pieces.length<=7,'piece count '+pieces.length);
    if(E.parenOf(s)){const cs=genSimpCards(s,null); ok(cs.filter(c=>validateSimplify(s,c).ok).length===1,'one distribute card');}
    const valid=pieces.filter(q=>validateStep(s,q,q).ok);
    ok(valid.length>=1,'some piece valid');
    const q=valid[Math.floor(Math.random()*valid.length)];
    const rr=validateStep(s,q,q);
    const cards=genSimpCards(rr.state,rr.op);
    ok(cards.length===4,'4 simp cards');
    const good=cards.filter(c=>validateSimplify(rr.state,c).ok);
    ok(good.length===1,'one correct simp card');
    ok(new Set(cards.map(key)).size===cards.length,'cards distinct');
    s={L:N.linV(good[0].L),R:N.linV(good[0].R)};
  }
  const v=solvedValue(s);
  ok(v!==null&&v.eq(prob.ans),'solved lvl'+lvl+' '+prob.type);
  const ac=genAnswerCards(prob.orig,v);
  ok(ac.length===4&&ac.filter(x=>validateAnswer(prob.orig,x).ok).length===1,'one valid answer card');
  fuzz++;
}
console.log('types:',Object.keys(types).join(', '));
console.log(`fuzz problems: ${fuzz}`);
console.log(`PASS ${pass}  FAIL ${fail}`);
process.exit(fail?1:0);
