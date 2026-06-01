#!/usr/bin/env python3
"""
graph_view.py — 위키를 읽어 브라우저용 그래프 뷰어(graph.html)를 생성.
Obsidian 불필요. 인터넷·의존성 불필요. 출력 HTML 더블클릭하면 끝.

사용법:  python3 graph_view.py
동작:    wiki/**/*.md 파싱 → 노드(파일)·엣지([[링크]]) 추출 → graph.html 생성
"""
import re, json
from pathlib import Path

BASE = Path(__file__).resolve().parent
WIKI = BASE / "wiki"
OUT = BASE / "graph.html"

LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
FM_TYPE_RE = re.compile(r"^type:\s*(\w+)", re.MULTILINE)

TYPE_COLOR = {
    "stock": "#e8b14a", "sector": "#5aa9e6", "analyst": "#e06c75",
    "theme": "#56b69a", "raw_report": "#888", "_missing": "#444",
}

def parse():
    nodes, edges, seen = {}, [], set()
    for md in WIKI.rglob("*.md"):
        name = md.stem
        text = md.read_text(encoding="utf-8")
        m = FM_TYPE_RE.search(text)
        ntype = m.group(1) if m else "unknown"
        nodes[name] = {"id": name, "type": ntype}
        for tgt in LINK_RE.findall(text):
            tgt = tgt.strip()
            if (name, tgt) not in seen and tgt != name:
                seen.add((name, tgt)); edges.append({"s": name, "t": tgt})
    # 링크됐지만 페이지 없는 노드(고아 후보) 표시
    for e in edges:
        if e["t"] not in nodes:
            nodes[e["t"]] = {"id": e["t"], "type": "_missing"}
    return list(nodes.values()), edges

def build_html(nodes, edges):
    data = json.dumps({"nodes": nodes, "edges": edges, "colors": TYPE_COLOR},
                      ensure_ascii=False)
    return r"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>리서치 위키 그래프</title>
<style>
  :root{--bg:#0e1014;--panel:#15181f;--ink:#d7dae0;--dim:#7a8190;--line:#2a2f3a;}
  *{box-sizing:border-box;margin:0;padding:0}
  html,body{height:100%;background:var(--bg);color:var(--ink);
    font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace;overflow:hidden}
  #wrap{display:flex;height:100%}
  svg{flex:1;display:block;cursor:grab}
  svg:active{cursor:grabbing}
  .edge{stroke:var(--line);stroke-width:1.2}
  .edge.hl{stroke:#e8b14a;stroke-width:2}
  .node circle{cursor:pointer;transition:stroke .15s}
  .node text{fill:var(--ink);font-size:11px;pointer-events:none;
    paint-order:stroke;stroke:var(--bg);stroke-width:3px}
  .node.dim{opacity:.18}.edge.dim{opacity:.08}
  #side{width:300px;background:var(--panel);border-left:1px solid var(--line);
    padding:20px;overflow-y:auto;font-size:13px;line-height:1.6}
  #side h1{font-size:13px;letter-spacing:.08em;color:var(--dim);
    text-transform:uppercase;margin-bottom:14px;font-weight:600}
  #side .sel{font-size:17px;color:#fff;margin-bottom:4px}
  #side .typ{font-size:11px;margin-bottom:16px}
  #side .grp{color:var(--dim);font-size:10px;text-transform:uppercase;
    letter-spacing:.06em;margin:14px 0 6px}
  #side a{display:block;color:var(--ink);text-decoration:none;padding:3px 0;
    cursor:pointer;border-bottom:1px solid transparent}
  #side a:hover{color:#e8b14a}
  #legend{position:absolute;left:16px;bottom:16px;font-size:11px;color:var(--dim)}
  #legend span{display:inline-flex;align-items:center;margin-right:12px}
  #legend i{width:9px;height:9px;border-radius:50%;display:inline-block;margin-right:5px}
  #hint{position:absolute;left:16px;top:14px;font-size:11px;color:var(--dim)}
</style></head><body>
<div id="wrap">
  <svg id="g"></svg>
  <aside id="side">
    <h1>리서치 위키 그래프</h1>
    <div id="info"><div class="typ" style="color:var(--dim)">노드를 클릭하면 연결이 표시됩니다.</div></div>
  </aside>
</div>
<div id="hint">드래그로 이동 · 스크롤로 확대 · 노드 클릭</div>
<div id="legend"></div>
<script>
const DATA = """ + data + r""";
const svg=document.getElementById("g");
const W=()=>svg.clientWidth,H=()=>svg.clientHeight;
const NS="http://www.w3.org/2000/svg";
const colors=DATA.colors;
// legend
document.getElementById("legend").innerHTML=Object.entries({stock:"종목",sector:"섹터",analyst:"애널리스트",theme:"테마",_missing:"미생성"})
  .map(([k,v])=>`<span><i style="background:${colors[k]||'#888'}"></i>${v}</span>`).join("");

const nodes=DATA.nodes.map(n=>({...n,x:W()/2+(Math.random()-.5)*300,y:H()/2+(Math.random()-.5)*300,vx:0,vy:0}));
const idx=Object.fromEntries(nodes.map((n,i)=>[n.id,i]));
const edges=DATA.edges.filter(e=>e.s in idx&&e.t in idx).map(e=>({s:idx[e.s],t:idx[e.t]}));
const deg={};edges.forEach(e=>{deg[e.s]=(deg[e.s]||0)+1;deg[e.t]=(deg[e.t]||0)+1});

const gE=document.createElementNS(NS,"g"),gN=document.createElementNS(NS,"g");
svg.append(gE,gN);
const eEl=edges.map(()=>{const l=document.createElementNS(NS,"line");l.setAttribute("class","edge");gE.append(l);return l});
const nEl=nodes.map((n,i)=>{
  const g=document.createElementNS(NS,"g");g.setAttribute("class","node");
  const c=document.createElementNS(NS,"circle");
  const r=6+Math.min(8,(deg[i]||0)*1.6);
  c.setAttribute("r",r);c.setAttribute("fill",colors[n.type]||"#999");
  c.setAttribute("stroke","#0e1014");c.setAttribute("stroke-width",2);
  const t=document.createElementNS(NS,"text");t.setAttribute("x",r+4);
  t.setAttribute("y",4);t.textContent=n.id;
  g.append(c,t);gN.append(g);
  g.addEventListener("click",ev=>{ev.stopPropagation();select(i)});
  g.addEventListener("mousedown",ev=>drag(ev,i));
  return g;
});

let view={x:0,y:0,k:1};
function applyView(){gE.setAttribute("transform",`translate(${view.x},${view.y}) scale(${view.k})`);
  gN.setAttribute("transform",`translate(${view.x},${view.y}) scale(${view.k})`)}
svg.addEventListener("wheel",e=>{e.preventDefault();const s=e.deltaY<0?1.1:0.9;
  const mx=e.offsetX,my=e.offsetY;view.x=mx-(mx-view.x)*s;view.y=my-(my-view.y)*s;view.k*=s;applyView()},{passive:false});
let pan=null;
svg.addEventListener("mousedown",e=>{if(e.target===svg)pan={x:e.clientX-view.x,y:e.clientY-view.y}});
window.addEventListener("mousemove",e=>{if(pan){view.x=e.clientX-pan.x;view.y=e.clientY-pan.y;applyView()}});
window.addEventListener("mouseup",()=>pan=null);

let dragI=-1,dragOff=null;
function drag(ev,i){ev.stopPropagation();dragI=i;
  const p=toGraph(ev);dragOff={x:nodes[i].x-p.x,y:nodes[i].y-p.y}}
function toGraph(ev){return{x:(ev.offsetX-view.x)/view.k,y:(ev.offsetY-view.y)/view.k}}
svg.addEventListener("mousemove",ev=>{if(dragI<0)return;const p=toGraph(ev);
  nodes[dragI].x=p.x+dragOff.x;nodes[dragI].y=p.y+dragOff.y;nodes[dragI].vx=nodes[dragI].vy=0});
window.addEventListener("mouseup",()=>dragI=-1);

// force sim
function tick(){
  for(let i=0;i<nodes.length;i++)for(let j=i+1;j<nodes.length;j++){
    const a=nodes[i],b=nodes[j];let dx=a.x-b.x,dy=a.y-b.y,d2=dx*dx+dy*dy||1;
    const f=2600/d2;const d=Math.sqrt(d2);dx/=d;dy/=d;
    a.vx+=dx*f;a.vy+=dy*f;b.vx-=dx*f;b.vy-=dy*f;}
  edges.forEach(e=>{const a=nodes[e.s],b=nodes[e.t];
    let dx=b.x-a.x,dy=b.y-a.y,d=Math.sqrt(dx*dx+dy*dy)||1;const f=(d-90)*0.012;dx/=d;dy/=d;
    a.vx+=dx*f;a.vy+=dy*f;b.vx-=dx*f;b.vy-=dy*f;});
  const cx=W()/2,cy=H()/2;
  nodes.forEach((n,i)=>{n.vx+=(cx-n.x)*0.0015;n.vy+=(cy-n.y)*0.0015;
    if(i!==dragI){n.x+=n.vx*=0.86;n.y+=n.vy*=0.86;}});
  edges.forEach((e,i)=>{const a=nodes[e.s],b=nodes[e.t];
    eEl[i].setAttribute("x1",a.x);eEl[i].setAttribute("y1",a.y);
    eEl[i].setAttribute("x2",b.x);eEl[i].setAttribute("y2",b.y);});
  nEl.forEach((g,i)=>g.setAttribute("transform",`translate(${nodes[i].x},${nodes[i].y})`));
  requestAnimationFrame(tick);
}
tick();

function neighbors(i){const s=new Set([i]);edges.forEach(e=>{
  if(e.s===i)s.add(e.t);if(e.t===i)s.add(e.s)});return s}
function select(i){
  const nb=neighbors(i);
  nEl.forEach((g,j)=>g.classList.toggle("dim",!nb.has(j)));
  eEl.forEach((l,k)=>{const e=edges[k],on=e.s===i||e.t===i;
    l.classList.toggle("hl",on);l.classList.toggle("dim",!on)});
  const n=nodes[i];
  const ins=edges.filter(e=>e.t===i).map(e=>nodes[e.s].id);
  const outs=edges.filter(e=>e.s===i).map(e=>nodes[e.t].id);
  const link=arr=>arr.length?arr.map(id=>`<a onclick="selById('${id}')">→ ${id}</a>`).join(""):'<span style="color:var(--dim)">없음</span>';
  document.getElementById("info").innerHTML=
    `<div class="sel">${n.id}</div>
     <div class="typ" style="color:${colors[n.type]||'#999'}">${n.type}</div>
     <div class="grp">이 노드가 링크하는 곳 (${outs.length})</div>${link(outs)}
     <div class="grp">이 노드를 링크하는 곳 (${ins.length})</div>${link(ins)}`;
}
function selById(id){if(id in idx)select(idx[id])}
window.selById=selById;
svg.addEventListener("click",()=>{nEl.forEach(g=>g.classList.remove("dim"));
  eEl.forEach(l=>l.classList.remove("hl","dim"));
  document.getElementById("info").innerHTML='<div class="typ" style="color:var(--dim)">노드를 클릭하면 연결이 표시됩니다.</div>'});
</script></body></html>"""

def main():
    nodes, edges = parse()
    OUT.write_text(build_html(nodes, edges), encoding="utf-8")
    print(f"생성: {OUT}")
    print(f"노드 {len(nodes)}개 / 엣지 {len(edges)}개")
    print("브라우저에서 graph.html 을 열면 됩니다 (인터넷 불필요).")

if __name__ == "__main__":
    main()
    aaa = 1.0
