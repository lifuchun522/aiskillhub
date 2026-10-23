#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dtyl 生成器：把「动态原理拆解」规格 JSON 渲染成自包含动画 HTML。

用法：
    python gen_dpv.py <spec.json> [out.html]

不依赖任何第三方库，纯标准库。输出的 HTML 内联 CSS/JS，可直接双击打开。
"""
import json
import html
import sys
import os


def esc(s):
    return html.escape(str(s), quote=True)


def build_component_cards(components):
    cards = []
    for c in components:
        cards.append(
            '<div class="comp" id="comp-{id}">'
            '<div class="comp-label">{label}</div>'
            '<div class="comp-role">{role}</div>'
            '<div class="comp-state" id="state-{id}"><span class="chip none">—</span></div>'
            "</div>".format(id=esc(c["id"]), label=esc(c["label"]), role=esc(c.get("role", "")))
        )
    return "\n".join(cards)


def build_steps_js(steps):
    # 仅把每步的 state 与 caption 暴露给前端；state 支持「继承上一步未提及的组件」
    prev = {}
    out = []
    for i, st in enumerate(steps):
        merged = dict(prev)
        for cid, sv in (st.get("state") or {}).items():
            merged[cid] = sv
        prev = merged
        out.append({
            "cap": st.get("cap", ""),
            "actors": st.get("actors", []),
            "state": merged,
        })
    return json.dumps(out, ensure_ascii=False)


def build_quiz(quiz):
    items = []
    for idx, q in enumerate(quiz):
        change = q.get("change", "")
        change_html = '<div class="q-change">改变条件：{}</div>'.format(esc(change)) if change else ""
        items.append(
            '<div class="quiz">'
            '<div class="q-no">Q{no}</div>'
            '<div class="q-body">'
            '<div class="q-text">{q}</div>'
            '{change}'
            '<details><summary>看答案</summary><div class="q-ans">{a}</div></details>'
            "</div></div>".format(
                no=idx + 1, q=esc(q.get("q", "")), change=change_html, a=esc(q.get("a", ""))
            )
        )
    return "\n".join(items)


def build_list(items, cls):
    if not items:
        return '<p class="empty">（无）</p>'
    lis = "\n".join("<li>{}</li>".format(esc(x)) for x in items)
    return '<ul class="{cls}">{lis}</ul>'.format(cls=cls, lis=lis)


def render(spec):
    title = esc(spec.get("title", "动态原理拆解"))
    subtitle = esc(spec.get("subtitle", ""))
    disclaimer = esc(spec.get("disclaimer", "原理演示，非压测 / 非生产基准"))
    components = spec.get("components", [])
    steps = spec.get("steps", [])
    steps_js = build_steps_js(steps)
    comp_cards = build_component_cards(components)
    quiz_html = build_quiz(spec.get("quiz", []))
    scenarios = build_list(spec.get("scenarios", []), "scenarios")
    limits = build_list(spec.get("limits", []), "limits")
    conclusion = esc(spec.get("conclusion", ""))
    rigorous = esc(spec.get("rigorous", "")).replace("\n", "<br>")
    plain = esc(spec.get("plain", "")).replace("\n", "<br>")

    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ --bg:#0f1419; --panel:#1a2230; --ink:#e6edf3; --muted:#9aa7b5; --line:#2a3342;
          --green:#2ea043; --red:#e5534b; --amber:#d29922; --blue:#388bfd; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
         font-family:-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; line-height:1.6; }}
  .wrap {{ max-width:960px; margin:0 auto; padding:24px 18px 64px; }}
  .banner {{ background:#3b1d1d; border:1px solid var(--red); color:#ffb4ae;
            padding:10px 14px; border-radius:10px; font-size:14px; margin-bottom:18px; }}
  h1 {{ font-size:26px; margin:0 0 4px; }}
  .sub {{ color:var(--muted); margin:0 0 20px; }}
  .panel {{ background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:18px; margin:16px 0; }}
  .panel h2 {{ font-size:18px; margin:0 0 12px; border-left:3px solid var(--blue); padding-left:10px; }}
  .comps {{ display:flex; flex-wrap:wrap; gap:12px; }}
  .comp {{ flex:1 1 180px; background:#11171f; border:1px solid var(--line); border-radius:10px; padding:12px; }}
  .comp-label {{ font-weight:600; }}
  .comp-role {{ color:var(--muted); font-size:12px; margin:2px 0 8px; }}
  .comp-state .chip {{ display:inline-block; padding:3px 10px; border-radius:999px; font-size:13px; font-weight:600; }}
  .chip.none {{ background:#222c39; color:var(--muted); }}
  .chip.hit {{ background:rgba(46,160,67,.18); color:#56d364; }}
  .chip.miss {{ background:rgba(229,83,75,.18); color:#ff7b72; }}
  .chip.locked {{ background:rgba(210,153,34,.18); color:#e3b341; }}
  .chip.db {{ background:rgba(229,83,75,.30); color:#ff9a91; }}
  .chip.warn {{ background:rgba(210,153,34,.18); color:#e3b341; }}
  .stage {{ min-height:96px; }}
  .step-meta {{ display:flex; align-items:center; gap:10px; color:var(--muted); font-size:13px; margin-bottom:8px; }}
  .cap {{ font-size:16px; min-height:48px; }}
  .actors {{ color:var(--blue); font-size:13px; margin-top:8px; }}
  .ctrls {{ display:flex; gap:8px; margin-top:14px; flex-wrap:wrap; }}
  button {{ background:#212b38; color:var(--ink); border:1px solid var(--line); border-radius:8px;
           padding:7px 14px; cursor:pointer; font-size:14px; }}
  button:hover {{ border-color:var(--blue); }}
  .progress {{ height:6px; background:#222c39; border-radius:999px; overflow:hidden; margin-top:12px; }}
  .progress > i {{ display:block; height:100%; width:0; background:var(--blue); transition:width .25s; }}
  pre {{ background:#11171f; border:1px solid var(--line); border-radius:10px; padding:14px; overflow:auto;
        font-family:"SFMono-Regular",Consolas,monospace; font-size:13px; white-space:pre-wrap; }}
  .quiz {{ display:flex; gap:12px; background:#11171f; border:1px solid var(--line); border-radius:10px; padding:12px; margin:10px 0; }}
  .q-no {{ font-weight:700; color:var(--blue); }}
  .q-body {{ flex:1; }}
  .q-change {{ color:var(--amber); font-size:13px; margin:6px 0; }}
  details summary {{ cursor:pointer; color:var(--green); }}
  ul.scenarios li, ul.limits li {{ margin:6px 0; }}
  ul.limits li {{ border-left:3px solid var(--amber); padding-left:10px; }}
  .empty {{ color:var(--muted); }}
  footer {{ color:var(--muted); font-size:12px; margin-top:24px; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="banner">⚠ {disclaimer}</div>
  <h1>{title}</h1>
  <p class="sub">{sub}</p>

  <div class="panel">
    <h2>结构拆解</h2>
    <div class="comps">{comps}</div>
  </div>

  <div class="panel">
    <h2>动态过程</h2>
    <div class="stage">
      <div class="step-meta"><span id="step-no">第 0 / {nsteps} 步</span></div>
      <div class="cap" id="cap"></div>
      <div class="actors" id="actors"></div>
    </div>
    <div class="ctrls">
      <button id="prev">上一步</button>
      <button id="play">▶ 播放</button>
      <button id="next">下一步</button>
      <button id="reset">重置</button>
    </div>
    <div class="progress"><i id="bar"></i></div>
  </div>

  <div class="panel">
    <h2>严谨版</h2>
    <pre>{rigorous}</pre>
  </div>

  <div class="panel">
    <h2>白话版</h2>
    <p>{plain}</p>
  </div>

  <div class="panel">
    <h2>自测题（含改变条件）</h2>
    {quiz}
  </div>

  <div class="panel">
    <h2>适用场景</h2>
    {scenarios}
  </div>

  <div class="panel">
    <h2>限制</h2>
    {limits}
  </div>

  <div class="panel">
    <h2>实践结论</h2>
    <p>{conclusion}</p>
  </div>

  <footer>由 dtyl（动态原理拆解）技能生成 · 原理演示，非压测。</footer>
</div>

<script>
const STEPS = {steps_js};
const ids = {comp_ids};
let cur = -1, timer = null;

function applyState(state) {{
  ids.forEach(id => {{
    const el = document.getElementById('state-' + id);
    const s = state[id] || {{text:'—', cls:'none'}};
    el.innerHTML = '<span class="chip ' + (s.cls||'none') + '">' + s.text + '</span>';
  }});
}}

function show(i) {{
  if (i < 0) i = 0;
  if (i >= STEPS.length) i = STEPS.length - 1;
  cur = i;
  const st = STEPS[i];
  document.getElementById('step-no').textContent = '第 ' + (i+1) + ' / ' + STEPS.length + ' 步';
  document.getElementById('cap').textContent = st.cap;
  document.getElementById('actors').textContent = st.actors && st.actors.length ? ('调用链：' + st.actors.join('  →  ')) : '';
  applyState(st.state);
  document.getElementById('bar').style.width = ((i+1)/STEPS.length*100) + '%';
}}

function next() {{ if (cur < STEPS.length-1) show(cur+1); else stop(); }}
function prev() {{ if (cur > 0) show(cur-1); }}
function reset() {{ stop(); show(0); }}
function play() {{
  if (timer) {{ stop(); return; }}
  if (cur >= STEPS.length-1) show(0);
  document.getElementById('play').textContent = '⏸ 暂停';
  timer = setInterval(() => {{ if (cur >= STEPS.length-1) stop(); else next(); }}, 1600);
}}
function stop() {{ if (timer) {{ clearInterval(timer); timer = null; }} document.getElementById('play').textContent = '▶ 播放'; }}

document.getElementById('next').onclick = next;
document.getElementById('prev').onclick = prev;
document.getElementById('reset').onclick = reset;
document.getElementById('play').onclick = play;
show(0);
</script>
</body>
</html>
""".format(
        title=title, sub=subtitle, disclaimer=disclaimer,
        comps=comp_cards, nsteps=len(steps), steps_js=steps_js,
        comp_ids=json.dumps([esc(c["id"]) for c in components], ensure_ascii=False),
        rigorous=rigorous, plain=plain, quiz=quiz_html,
        scenarios=scenarios, limits=limits, conclusion=conclusion,
    )


def main():
    if len(sys.argv) < 2:
        sys.stderr.write("usage: gen_dpv.py <spec.json> [out.html]\n")
        return 2
    spec_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else None
    with open(spec_path, "r", encoding="utf-8") as f:
        spec = json.load(f)
    out = render(spec)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(out)
        sys.stderr.write("written: {}\n".format(out_path))
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
