#!/usr/bin/env python
"""build_graph.py — 위키 → 타입드 관계 그래프 산출물.

GRAPH_LAYER.md Phase 1. markdown이 source of truth, 그래프는 위키에서 파생되는
build artifact(단방향). 두 산출물을 만든다:

- graph.html  : 타입·관계종류·신뢰도로 채색/필터되는 독립 뷰어(의존성 없음, 더블클릭).
- graph.sqlite: nodes/edges 테이블 — graph_query.py / LLM·에이전트 질의용.

엣지 출처(둘 다 지원):
- prose `[[링크]]`  → rel을 페이지타입으로 추론(기본 MENTIONS), confidence=null.
- frontmatter `edges:` → rel/target/confidence/claim_type/source/date 그대로(Phase 3 backfill).
  (PyYAML이 있을 때만 파싱. 없거나 edges 없으면 prose 링크만 사용 — CI 안전.)

사용: python tools/build_graph.py
"""
import glob
import json
import os
import re
import sqlite3
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIKI = os.path.join(BASE, "wiki")
OUT_HTML = os.path.join(BASE, "graph.html")
OUT_DB = os.path.join(BASE, "graph.sqlite")

# 페이지 타입(노드로 취급). index.md·이슈.md 등 type 없는 nav 페이지는 제외.
ENTITY_TYPES = {"stock", "sector", "analyst", "theme", "macro", "issue"}

# 노드 타입 색
TYPE_COLOR = {
    "stock": "#e8b14a", "sector": "#5aa9e6", "analyst": "#e06c75",
    "theme": "#56b69a", "macro": "#c678dd", "issue": "#d19a66",
    "_missing": "#444",
}
# 관계종류 색(엣지)
REL_COLOR = {
    "MENTIONS": "#3a4150", "AFFECTS": "#c678dd", "SUPPLIES_TO": "#56b69a",
    "COMPETES_WITH": "#e06c75", "BELONGS_TO_THEME": "#5aa9e6", "HAS_RISK": "#e8b14a",
}
KNOWN_RELS = set(REL_COLOR)
DASHED_CLAIMS = {"추정", "루머"}  # 점선 처리

# 별칭/앵커 제거 후 링크 타깃. raw/ 인용은 엔티티 그래프에서 제외.
LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def parse_frontmatter(text):
    """(flat dict, edges list)를 반환. flat은 build_index와 동일한 naive 파서.
    edges는 PyYAML이 있을 때만(없으면 []). frontmatter는 첫 `---`~다음 `---`."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, []
    fm_lines = []
    for ln in lines[1:]:
        if ln.strip() == "---":
            break
        fm_lines.append(ln)
    flat = {}
    for ln in fm_lines:
        if ln.strip().startswith("-") or ln.startswith((" ", "\t")):
            continue  # 리스트/중첩 줄은 flat에서 무시(edges 등)
        if ":" in ln:
            k, v = ln.split(":", 1)
            flat[k.strip()] = v.strip()
    has_edges = any(ln.lstrip().startswith("edges:") for ln in fm_lines)
    edges = _parse_edges("\n".join(fm_lines)) if has_edges else []
    return flat, edges


def _parse_edges(fm_text):
    """frontmatter YAML에서 edges: 리스트만 추출(PyYAML 필요). 실패하면 []."""
    try:
        import yaml
    except Exception:
        return []
    try:
        data = yaml.safe_load(fm_text) or {}
    except Exception:
        return []
    raw = data.get("edges") or []
    out = []
    if isinstance(raw, list):
        for e in raw:
            if isinstance(e, dict) and e.get("rel") and e.get("target"):
                out.append({
                    "rel": str(e.get("rel")).strip(),
                    "target": _norm_target(str(e.get("target"))),
                    "confidence": e.get("confidence"),
                    "claim_type": (str(e["claim_type"]).strip() if e.get("claim_type") else None),
                    "source": (str(e["source"]).strip() if e.get("source") else None),
                    "date": (str(e["date"]).strip() if e.get("date") else None),
                })
    return out


def _clean(s):
    return (s or "").strip().strip("'\"").strip()


def _norm_target(raw):
    """'[[엔비디아|엔비디아(NVIDIA)]]' / '엔비디아#섹션' → '엔비디아'(stem 후보)."""
    t = raw.strip()
    t = t.replace("[[", "").replace("]]", "")
    t = t.split("|", 1)[0]   # 별칭 제거
    t = t.split("#", 1)[0]   # 앵커 제거
    return t.strip()


def extract_links(text):
    """prose [[링크]] 타깃 집합. raw/ 인용·자기 앵커는 제외."""
    out = []
    for m in LINK_RE.findall(text):
        tgt = _norm_target(m)
        if not tgt or tgt.startswith("raw/"):
            continue
        out.append(tgt)
    return out


def infer_rel(src_type, dst_type):
    """prose 링크의 rel 추론(Phase 1, 보수적)."""
    if dst_type == "theme":
        return "BELONGS_TO_THEME"
    if src_type == "macro" or dst_type == "macro":
        return "AFFECTS"
    return "MENTIONS"


def read_pages(wiki_dir):
    """엔티티 타입 페이지만 [{stem,type,name,ticker,updated,links,edges}]로."""
    pages = []
    for path in sorted(glob.glob(os.path.join(wiki_dir, "**", "*.md"), recursive=True)):
        text = open(path, encoding="utf-8").read()
        flat, edges = parse_frontmatter(text)
        ntype = _clean(flat.get("type"))
        if ntype not in ENTITY_TYPES:
            continue
        stem = os.path.splitext(os.path.basename(path))[0]
        pages.append({
            "stem": stem,
            "type": ntype,
            "name": _clean(flat.get("name")) or stem,
            "ticker": _clean(flat.get("ticker")) or None,
            "updated": _clean(flat.get("updated")) or _clean(flat.get("created")) or None,
            "links": extract_links(text),
            "edges": edges,
        })
    return pages


def build_graph(pages):
    """pages → (nodes: dict[id]->node, edges: list). 구조화 edges 우선, prose는 보강."""
    nodes = {}
    for p in pages:
        nodes[p["stem"]] = {
            "id": p["stem"], "type": p["type"], "name": p["name"],
            "ticker": p["ticker"], "updated": p["updated"],
        }
    type_of = lambda i: nodes[i]["type"] if i in nodes else "_missing"

    edges = []
    seen = set()
    for p in pages:
        src = p["stem"]
        # (1) 구조화 엣지(frontmatter edges:) — Phase 3 backfill 대비
        for e in p["edges"]:
            dst = e["target"]
            key = (src, e["rel"], dst)
            if dst == src or key in seen:
                continue
            seen.add(key)
            edges.append({
                "src": src, "rel": e["rel"], "dst": dst,
                "confidence": e["confidence"], "claim_type": e["claim_type"],
                "source": e["source"], "date": e["date"],
            })
        # (2) prose 링크 — rel 추론, confidence=null
        for dst in p["links"]:
            rel = infer_rel(p["type"], type_of(dst))
            key = (src, rel, dst)
            if dst == src or key in seen:
                continue
            seen.add(key)
            edges.append({
                "src": src, "rel": rel, "dst": dst,
                "confidence": None, "claim_type": None, "source": None, "date": None,
            })

    # 링크됐지만 페이지 없는 타깃 → _missing 노드(고아 후보)
    for e in edges:
        if e["dst"] not in nodes:
            nodes[e["dst"]] = {"id": e["dst"], "type": "_missing", "name": e["dst"],
                               "ticker": None, "updated": None}
    return nodes, edges


def write_sqlite(nodes, edges, path):
    if os.path.exists(path):
        os.remove(path)
    con = sqlite3.connect(path)
    try:
        con.executescript(
            "CREATE TABLE nodes (id TEXT PRIMARY KEY, type TEXT, name TEXT, ticker TEXT, updated TEXT);"
            "CREATE TABLE edges (src TEXT, rel TEXT, dst TEXT, confidence REAL,"
            " claim_type TEXT, source TEXT, date TEXT);"
            "CREATE INDEX idx_edges_src ON edges(src);"
            "CREATE INDEX idx_edges_dst ON edges(dst);"
        )
        con.executemany(
            "INSERT OR REPLACE INTO nodes VALUES (?,?,?,?,?)",
            [(n["id"], n["type"], n["name"], n["ticker"], n["updated"]) for n in nodes.values()],
        )
        con.executemany(
            "INSERT INTO edges VALUES (?,?,?,?,?,?,?)",
            [(e["src"], e["rel"], e["dst"], e["confidence"], e["claim_type"], e["source"], e["date"])
             for e in edges],
        )
        con.commit()
    finally:
        con.close()


def build_html(nodes, edges):
    data = json.dumps({
        "nodes": list(nodes.values()),
        "edges": [{"s": e["src"], "t": e["dst"], "rel": e["rel"],
                   "c": e["confidence"], "ct": e["claim_type"]} for e in edges],
        "typeColor": TYPE_COLOR, "relColor": REL_COLOR,
    }, ensure_ascii=False)
    return _HTML_HEAD + data + _HTML_TAIL


_HTML_HEAD = r"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>리서치 위키 관계 그래프</title>
<style>
  :root{--bg:#0e1014;--panel:#15181f;--ink:#d7dae0;--dim:#7a8190;--line:#2a2f3a;}
  *{box-sizing:border-box;margin:0;padding:0}
  html,body{height:100%;background:var(--bg);color:var(--ink);
    font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace;overflow:hidden}
  #wrap{display:flex;height:100%}
  svg{flex:1;display:block;cursor:grab}svg:active{cursor:grabbing}
  .edge{fill:none}
  .node circle{cursor:pointer}
  .node text{fill:var(--ink);font-size:11px;pointer-events:none;
    paint-order:stroke;stroke:var(--bg);stroke-width:3px}
  .node.dim{opacity:.12}.edge.dim{opacity:.05}.hidden{display:none}
  #side{width:310px;background:var(--panel);border-left:1px solid var(--line);
    padding:18px;overflow-y:auto;font-size:13px;line-height:1.55}
  #side h1{font-size:12px;letter-spacing:.08em;color:var(--dim);
    text-transform:uppercase;margin-bottom:12px;font-weight:600}
  #side .sel{font-size:17px;color:#fff;margin-bottom:2px}
  #side .typ{font-size:11px;margin-bottom:14px}
  #side .grp{color:var(--dim);font-size:10px;text-transform:uppercase;
    letter-spacing:.06em;margin:12px 0 5px}
  #side a{display:block;color:var(--ink);text-decoration:none;padding:2px 0;cursor:pointer}
  #side a:hover{color:#e8b14a}
  #side a small{color:var(--dim)}
  #filters{margin:6px 0 4px}
  #filters label{display:inline-flex;align-items:center;gap:5px;margin:2px 8px 2px 0;
    font-size:12px;cursor:pointer;user-select:none}
  #filters input{accent-color:#e8b14a}
  #filters i{width:9px;height:9px;border-radius:50%;display:inline-block}
  #legend{position:absolute;left:16px;bottom:14px;font-size:10px;color:var(--dim);max-width:60%}
  #legend span{display:inline-flex;align-items:center;margin:0 10px 4px 0}
  #legend b{width:16px;height:0;border-top:3px solid;display:inline-block;margin-right:5px}
  #hint{position:absolute;left:16px;top:12px;font-size:11px;color:var(--dim)}
</style></head><body>
<div id="wrap"><svg id="g"></svg>
  <aside id="side"><h1>관계 그래프</h1>
    <div class="grp">노드 타입 필터</div><div id="filters"></div>
    <div class="grp">시간 흐름 (updated ≤ <span id="tlabel">전체</span>)</div>
    <div id="timebox"><input id="tslider" type="range" min="0" max="0" value="0" step="1" style="width:100%;accent-color:#d19a66"></div>
    <div id="info"><div class="typ" style="color:var(--dim)">노드를 클릭하면 연결이 표시됩니다.</div></div>
  </aside></div>
<div id="hint">드래그 이동 · 스크롤 확대 · 노드 클릭 · 체크박스로 타입 필터</div>
<div id="legend"></div>
<script>
const DATA = """

_HTML_TAIL = r""";
const svg=document.getElementById("g"),NS="http://www.w3.org/2000/svg";
const W=()=>svg.clientWidth,H=()=>svg.clientHeight;
const TC=DATA.typeColor,RC=DATA.relColor;
const TYPE_LABEL={stock:"종목",sector:"섹터",analyst:"애널",theme:"테마",macro:"거시",issue:"이슈",_missing:"미생성"};
const DASHED=new Set(["추정","루머"]);

const nodes=DATA.nodes.map(n=>({...n,x:W()/2+(Math.random()-.5)*400,y:H()/2+(Math.random()-.5)*400,vx:0,vy:0}));
const idx=Object.fromEntries(nodes.map((n,i)=>[n.id,i]));
const edges=DATA.edges.filter(e=>e.s in idx&&e.t in idx).map(e=>({s:idx[e.s],t:idx[e.t],rel:e.rel,c:e.c,ct:e.ct}));
const deg={};edges.forEach(e=>{deg[e.s]=(deg[e.s]||0)+1;deg[e.t]=(deg[e.t]||0)+1});

// 타입 필터 상태
const present=[...new Set(nodes.map(n=>n.type))];
const active=new Set(present);
const fbox=document.getElementById("filters");
present.sort((a,b)=>(a==="_missing")-(b==="_missing"));
present.forEach(t=>{
  const l=document.createElement("label");
  l.innerHTML=`<input type="checkbox" checked data-t="${t}"><i style="background:${TC[t]||'#999'}"></i>${TYPE_LABEL[t]||t}`;
  l.querySelector("input").addEventListener("change",e=>{
    e.target.checked?active.add(t):active.delete(t);applyFilter();});
  fbox.append(l);
});
// 관계 범례
document.getElementById("legend").innerHTML=Object.keys(RC)
  .map(r=>`<span><b style="border-color:${RC[r]}"></b>${r}</span>`).join("")
  +`<span><b style="border-color:#7a8190;border-top-style:dashed"></b>추정/루머</span>`;

const gE=document.createElementNS(NS,"g"),gN=document.createElementNS(NS,"g");svg.append(gE,gN);
const eEl=edges.map(e=>{const l=document.createElementNS(NS,"line");l.setAttribute("class","edge");
  l.setAttribute("stroke",RC[e.rel]||"#3a4150");
  l.setAttribute("stroke-width",e.c==null?1.2:(1+e.c*2.8));
  if(e.c!=null)l.setAttribute("stroke-opacity",0.35+e.c*0.6);
  if(DASHED.has(e.ct))l.setAttribute("stroke-dasharray","4 3");
  gE.append(l);return l;});
const nEl=nodes.map((n,i)=>{
  const g=document.createElementNS(NS,"g");g.setAttribute("class","node");
  const c=document.createElementNS(NS,"circle"),r=6+Math.min(9,(deg[i]||0)*1.5);
  c.setAttribute("r",r);c.setAttribute("fill",TC[n.type]||"#999");
  c.setAttribute("stroke","#0e1014");c.setAttribute("stroke-width",2);
  const t=document.createElementNS(NS,"text");t.setAttribute("x",r+4);t.setAttribute("y",4);
  t.textContent=n.name||n.id;
  g.append(c,t);gN.append(g);
  g.addEventListener("click",ev=>{ev.stopPropagation();select(i)});
  g.addEventListener("mousedown",ev=>drag(ev,i));
  return g;});

function typeVisible(i){return active.has(nodes[i].type)}
let timeCut=null;  // 'YYYY-MM-DD' 이하만 표시. null=전체.
function timeVisible(i){const u=nodes[i].updated;return timeCut===null||!u||u<=timeCut;}
function visible(i){return typeVisible(i)&&timeVisible(i)}
function applyFilter(){
  nEl.forEach((g,i)=>g.classList.toggle("hidden",!visible(i)));
  eEl.forEach((l,k)=>l.classList.toggle("hidden",!(visible(edges[k].s)&&visible(edges[k].t))));
}
// 시간 슬라이더: updated 날짜를 정렬해 'updated ≤ 커서'만 표시 → 시간 흐름 가시화
const tdates=[...new Set(nodes.map(n=>n.updated).filter(Boolean))].sort();
const tslider=document.getElementById("tslider"),tlabel=document.getElementById("tlabel");
if(tdates.length>1){
  tslider.max=tdates.length-1;tslider.value=tdates.length-1;
  tslider.addEventListener("input",()=>{
    const v=+tslider.value;timeCut=(v>=tdates.length-1)?null:tdates[v];
    tlabel.textContent=timeCut||"전체";applyFilter();
  });
}else{document.getElementById("timebox").style.display="none";}

let view={x:0,y:0,k:1};
function applyView(){const tr=`translate(${view.x},${view.y}) scale(${view.k})`;
  gE.setAttribute("transform",tr);gN.setAttribute("transform",tr);}
svg.addEventListener("wheel",e=>{e.preventDefault();const s=e.deltaY<0?1.1:0.9;
  view.x=e.offsetX-(e.offsetX-view.x)*s;view.y=e.offsetY-(e.offsetY-view.y)*s;view.k*=s;applyView();},{passive:false});
let pan=null;
svg.addEventListener("mousedown",e=>{if(e.target===svg)pan={x:e.clientX-view.x,y:e.clientY-view.y}});
window.addEventListener("mousemove",e=>{if(pan){view.x=e.clientX-pan.x;view.y=e.clientY-pan.y;applyView()}});
window.addEventListener("mouseup",()=>pan=null);

let dragI=-1,dragOff=null;
function drag(ev,i){ev.stopPropagation();dragI=i;const p=toG(ev);dragOff={x:nodes[i].x-p.x,y:nodes[i].y-p.y}}
function toG(ev){return{x:(ev.offsetX-view.x)/view.k,y:(ev.offsetY-view.y)/view.k}}
svg.addEventListener("mousemove",ev=>{if(dragI<0)return;const p=toG(ev);
  nodes[dragI].x=p.x+dragOff.x;nodes[dragI].y=p.y+dragOff.y;nodes[dragI].vx=nodes[dragI].vy=0});
window.addEventListener("mouseup",()=>dragI=-1);

function tick(){
  for(let i=0;i<nodes.length;i++){if(!visible(i))continue;
    for(let j=i+1;j<nodes.length;j++){if(!visible(j))continue;
      const a=nodes[i],b=nodes[j];let dx=a.x-b.x,dy=a.y-b.y,d2=dx*dx+dy*dy||1;
      const f=2600/d2,d=Math.sqrt(d2);dx/=d;dy/=d;a.vx+=dx*f;a.vy+=dy*f;b.vx-=dx*f;b.vy-=dy*f;}}
  edges.forEach(e=>{if(!(visible(e.s)&&visible(e.t)))return;const a=nodes[e.s],b=nodes[e.t];
    let dx=b.x-a.x,dy=b.y-a.y,d=Math.sqrt(dx*dx+dy*dy)||1;const f=(d-90)*0.012;dx/=d;dy/=d;
    a.vx+=dx*f;a.vy+=dy*f;b.vx-=dx*f;b.vy-=dy*f;});
  const cx=W()/2,cy=H()/2;
  nodes.forEach((n,i)=>{if(!visible(i))return;n.vx+=(cx-n.x)*0.0015;n.vy+=(cy-n.y)*0.0015;
    if(i!==dragI){n.x+=n.vx*=0.86;n.y+=n.vy*=0.86;}});
  edges.forEach((e,i)=>{const a=nodes[e.s],b=nodes[e.t];
    eEl[i].setAttribute("x1",a.x);eEl[i].setAttribute("y1",a.y);
    eEl[i].setAttribute("x2",b.x);eEl[i].setAttribute("y2",b.y);});
  nEl.forEach((g,i)=>g.setAttribute("transform",`translate(${nodes[i].x},${nodes[i].y})`));
  requestAnimationFrame(tick);
}
tick();

function neighbors(i){const s=new Set([i]);edges.forEach(e=>{if(e.s===i)s.add(e.t);if(e.t===i)s.add(e.s)});return s}
function select(i){
  const nb=neighbors(i);
  nEl.forEach((g,j)=>g.classList.toggle("dim",visible(j)&&!nb.has(j)));
  eEl.forEach((l,k)=>{const e=edges[k],on=e.s===i||e.t===i;
    l.classList.toggle("dim",!on)});
  const n=nodes[i];
  const outs=edges.filter(e=>e.s===i).map(e=>({id:nodes[e.t].id,rel:e.rel,c:e.c}));
  const ins=edges.filter(e=>e.t===i).map(e=>({id:nodes[e.s].id,rel:e.rel,c:e.c}));
  const row=a=>a.length?a.map(o=>`<a onclick="selById('${o.id}')">→ ${o.id} <small>(${o.rel}${o.c!=null?' '+o.c:''})</small></a>`).join(""):'<span style="color:var(--dim)">없음</span>';
  document.getElementById("info").innerHTML=
    `<div class="sel">${n.name||n.id}</div>
     <div class="typ" style="color:${TC[n.type]||'#999'}">${n.type}${n.ticker?' · '+n.ticker:''}${n.updated?' · '+n.updated:''}</div>
     <div class="grp">나가는 관계 (${outs.length})</div>${row(outs)}
     <div class="grp">들어오는 관계 (${ins.length})</div>${row(ins)}`;
}
function selById(id){if(id in idx)select(idx[id])}
window.selById=selById;
svg.addEventListener("click",()=>{nEl.forEach(g=>g.classList.remove("dim"));
  eEl.forEach(l=>l.classList.remove("dim"));
  document.getElementById("info").innerHTML='<div class="typ" style="color:var(--dim)">노드를 클릭하면 연결이 표시됩니다.</div>'});
</script></body></html>"""


def main():
    pages = read_pages(WIKI)
    nodes, edges = build_graph(pages)
    write_sqlite(nodes, edges, OUT_DB)
    open(OUT_HTML, "w", encoding="utf-8", newline="\n").write(build_html(nodes, edges))
    structured = sum(1 for e in edges if e["confidence"] is not None)
    print(f"[OK] graph.html + graph.sqlite 생성 — 노드 {len(nodes)} · 엣지 {len(edges)}"
          f" (구조화 {structured} · prose {len(edges) - structured})")


if __name__ == "__main__":
    main()
