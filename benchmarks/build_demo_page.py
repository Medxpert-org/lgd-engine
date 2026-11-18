"""Build the static judge dossier page from the engine itself.

The point of this file is credibility, not decoration: every verdict shown on the
page is the literal output of `GateEngine` on a case file that ships in the repo.
`--check` fails if the committed page differs from what the engine produces now,
so the page cannot quietly drift away from the code.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks"))

from lgd_engine.gate import GateEngine                      # noqa: E402
from lgd_engine.judges.judge_510k import Judge510kChange     # noqa: E402
from lgd_engine.judges.judge_postmarket import JudgePostmarket  # noqa: E402
from lgd_engine.judges.judge_pccp import JudgePccpScope      # noqa: E402
from lgd_engine.judges.judge_mdr import JudgeMdrSignificance  # noqa: E402
from lgd_engine.judges.judge_nmpa import JudgeNmpaChangeRegistration  # noqa: E402
from lgd_engine.judges.basis import CLAUSE_BASIS, is_law, shipped_rules  # noqa: E402

OUT = ROOT / "demo" / "judge-dossier.html"

# (case directory, domain key, judge class, human label, jurisdiction line)
SUITES = [
    ("demo1/cases", "510k", Judge510kChange, "510(k) 变更分类", "FDA / NMPA"),
    ("demo1/cases_jurisdiction", "510k", Judge510kChange, "510(k) 变更分类", "FDA / NMPA"),
    ("demo1/cases_postmarket", "postmarket", JudgePostmarket, "上市后监测处置", "FDA / NMPA"),
    ("demo1/cases_pccp", "pccp", JudgePccpScope, "PCCP 变更范围", "FDA"),
    ("demo1/cases_mdr", "mdr", JudgeMdrSignificance, "EU MDR 重大变更", "EU"),
    ("demo1/cases_nmpa", "nmpa", JudgeNmpaChangeRegistration, "NMPA 变更注册", "中国"),
]

EXIT_CODE = {"go": 0, "hold": 1, "reject": 2}


def _load_cases() -> list:
    out = []
    for rel, domain, judge_cls, label, juris in SUITES:
        d = ROOT / rel
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.json")):
            ctx = json.loads(f.read_text(encoding="utf-8"))
            report = GateEngine([judge_cls()]).evaluate(ctx).to_dict()
            # Some fixtures declare per-jurisdiction expectations instead of one
            # global "expected_verdict" (same material, different regulator). Read
            # the one that belongs to the domain being run, and keep the split
            # visible on the page rather than silently dropping it.
            if ctx.get("expected_verdict"):
                expected = ctx["expected_verdict"]
            elif domain == "510k":
                expected = ctx.get("expected_fda_verdict") or ctx.get("expected_nmpa_verdict") or ""
            else:
                expected = ctx.get("expected_nmpa_verdict") or ctx.get("expected_fda_verdict") or ""
            split = {k: v for k, v in ctx.items()
                     if k in {"expected_fda_verdict", "expected_nmpa_verdict"}}
            out.append({
                "domain": domain,
                "domain_label": label,
                "jurisdiction": juris,
                "file": f"{rel}/{f.name}",
                "case_id": ctx.get("case_id") or f.stem,
                "note": ctx.get("_desensitized_from") or "",
                "description": ctx.get("device_description") or "",
                "expected": expected,
                "split_expectations": split,
                "verdict": report["verdict"],
                "matches": (report["verdict"] == expected) if expected else None,
                "exit_code": EXIT_CODE.get(report["verdict"], 3),
                "reasons": report["reasons"],
                "evidence": report["evidence"],
                "law_enforcements": report["law_enforcements"],
                "errors": report["errors"],
                "ctx": {k: v for k, v in ctx.items()
                        if k not in {"expected_verdict", "_desensitized_from",
                                     "expected_fda_verdict", "expected_nmpa_verdict"}},
            })
    return out


def _baseline() -> dict:
    """Run the naive-comparison benchmark and keep its own words."""
    try:
        p = subprocess.run([sys.executable, str(ROOT / "benchmarks" / "adversarial_baseline.py")],
                           capture_output=True, text=True, timeout=120, cwd=ROOT)
        lines = [ln.strip() for ln in (p.stdout or "").splitlines() if ln.strip()]
        picked = [ln for ln in lines if ln.startswith(("gate", "naive", "delta"))]
        return {"ok": p.returncode == 0, "lines": picked}
    except Exception as exc:  # pragma: no cover
        return {"ok": False, "lines": [f"baseline unavailable: {exc}"]}


def _clause_rows() -> list:
    """Every shipped rule with the provision behind it — the page's audit table."""
    rules = shipped_rules()
    rows = []
    for rid, judge in sorted(rules.items(), key=lambda kv: (kv[1], kv[0])):
        basis = CLAUSE_BASIS.get(rid, "")
        rows.append({"rule": rid, "judge": judge, "basis": basis,
                     "kind": "LAW" if is_law(basis) else "DOCTRINE"})
    return rows


def _assertion_count() -> int:
    """Count the contract tests from source, so the page cannot lag the suite.

    Deliberately *not* `python -m unittest discover` here: at least one test runs
    this builder, so invoking the suite from inside the builder recursed (stack
    overflow locally, a dead job in CI). Counting `def test_` lines is cheap,
    deterministic, and still moves whenever a test is added — which is the drift
    this number exists to catch."""
    total = 0
    for path in sorted((ROOT / "tests").glob("test_*.py")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("def test_"):
                total += 1
    return total


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LGD Engine 判决档案</title>
<link rel="stylesheet" href="https://miaoda.feishu.cn/fonts/css2?family=Noto+Serif+SC:wght@400;600;900&family=Noto+Sans+SC:wght@300;400;500;700&family=JetBrains+Mono:wght@400;600&display=swap">
<style>
:root{
  --paper:#E9EBE6; --paper-2:#F3F4F0; --ink:#16181A; --ink-2:#4A4F52;
  --rule:#C3C8BF; --go:#1F6B4A; --hold:#8A5A00; --reject:#96302A;
  --mono:"JetBrains Mono","SFMono-Regular",ui-monospace,monospace;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{
  background:var(--paper); color:var(--ink);
  font-family:"Noto Sans SC","PingFang SC","Microsoft YaHei",sans-serif;
  font-size:15px; line-height:1.65; -webkit-font-smoothing:antialiased;
}
.wrap{max-width:1220px;margin:0 auto;padding:0 28px 96px}
header.top{border-bottom:2px solid var(--ink);padding:44px 0 26px;margin-bottom:0}
.eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:.16em;color:var(--ink-2);text-transform:uppercase}
h1{font-family:"Noto Serif SC","Songti SC",serif;font-weight:900;font-size:clamp(34px,5vw,60px);line-height:1.06;margin:14px 0 12px;letter-spacing:-.01em}
.lede{max-width:62ch;color:var(--ink-2);font-size:15.5px}
.lede b{color:var(--ink);font-weight:600}
.stamp{font-family:var(--mono);font-size:11.5px;color:var(--ink-2);margin-top:20px;line-height:1.9}
.stamp code{background:var(--paper-2);padding:2px 6px;border:1px solid var(--rule)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));border-bottom:1px solid var(--rule)}
.kpi{padding:22px 0 20px;border-right:1px solid var(--rule)}
.kpi:last-child{border-right:none}
.kpi .n{font-family:"Noto Serif SC",serif;font-weight:900;font-size:40px;line-height:1;font-variant-numeric:tabular-nums}
.kpi .l{font-family:var(--mono);font-size:11px;letter-spacing:.1em;color:var(--ink-2);margin-top:9px;text-transform:uppercase}
.kpi .s{font-size:12.5px;color:var(--ink-2);margin-top:3px}
.sect{margin-top:44px}
.sect-h{display:flex;align-items:baseline;gap:14px;border-bottom:1px solid var(--ink);padding-bottom:8px}
.sect-h h2{font-family:"Noto Serif SC",serif;font-weight:600;font-size:22px;margin:0}
.sect-h .cnt{font-family:var(--mono);font-size:11.5px;color:var(--ink-2)}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0 22px}
.chip{font-family:var(--mono);font-size:12px;letter-spacing:.02em;background:transparent;color:var(--ink-2);
  border:1px solid var(--rule);padding:6px 12px;cursor:pointer;transition:background .15s,color .15s,border-color .15s}
.chip:hover{border-color:var(--ink);color:var(--ink)}
.chip[aria-pressed="true"]{background:var(--ink);color:var(--paper);border-color:var(--ink)}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:14px}
.card{background:var(--paper-2);border:1px solid var(--rule);padding:16px 18px 14px;cursor:pointer;
  display:flex;flex-direction:column;gap:10px;transition:border-color .15s,transform .15s}
.card:hover{border-color:var(--ink);transform:translateY(-1px)}
.card:focus-visible{outline:2px solid var(--ink);outline-offset:2px}
.card .cid{font-family:var(--mono);font-size:11px;color:var(--ink-2);letter-spacing:.04em;display:flex;justify-content:space-between;gap:10px}
.card .desc{font-size:13.5px;line-height:1.55;color:var(--ink)}
.v{font-family:var(--mono);font-weight:600;font-size:11.5px;letter-spacing:.08em;padding:4px 9px;border:1px solid currentColor;white-space:nowrap}
.v.go{color:var(--go)} .v.hold{color:var(--hold)} .v.reject{color:var(--reject)}
.card .foot{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:auto;padding-top:6px;border-top:1px solid var(--rule)}
.card .meta{font-family:var(--mono);font-size:10.5px;color:var(--ink-2)}
.miss{color:var(--reject);font-weight:600}
.panel{grid-column:1/-1;background:#fff;border:1px solid var(--ink);padding:22px 24px}
.panel h3{font-family:var(--mono);font-size:12px;letter-spacing:.1em;margin:0 0 4px;color:var(--ink-2);text-transform:uppercase}
.panel .headline{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:14px}
.panel .file{font-family:var(--mono);font-size:11.5px;color:var(--ink-2)}
.rules{list-style:none;margin:12px 0 0;padding:0;display:flex;flex-direction:column;gap:0}
.rules li{display:grid;grid-template-columns:96px 1fr;gap:14px;padding:9px 0;border-top:1px dashed var(--rule)}
.rules .lv{font-family:var(--mono);font-size:10.5px;letter-spacing:.06em;align-self:start;padding-top:2px}
.lv.critical{color:var(--reject)} .lv.major{color:var(--hold)} .lv.minor{color:var(--ink-2)}
.rules .rid{font-family:var(--mono);font-size:12.5px;font-weight:600;display:block}
.rules .det{font-size:13px;color:var(--ink-2);margin-top:2px}
.ev{font-family:var(--mono);font-size:11.5px;color:var(--ink-2);margin-top:12px}
.ev span{border-bottom:1px solid var(--rule);margin-right:12px}
.law{margin-top:12px;font-size:12.5px;color:var(--ink-2);border-left:2px solid var(--go);padding-left:10px}
.raw{margin-top:14px}
.raw summary{font-family:var(--mono);font-size:11px;letter-spacing:.06em;color:var(--ink-2);cursor:pointer}
.raw pre{font-family:var(--mono);font-size:11.5px;line-height:1.7;background:var(--paper);border:1px solid var(--rule);
  padding:14px;overflow:auto;max-height:320px;margin:10px 0 0}
table.cmp{width:100%;border-collapse:collapse;margin-top:16px;font-size:13px}
table.cmp th,table.cmp td{text-align:left;padding:9px 12px;border-bottom:1px solid var(--rule);vertical-align:top}
table.cmp th{font-family:var(--mono);font-size:11px;letter-spacing:.06em;color:var(--ink-2);font-weight:400}
table.cmp td.mono{font-family:var(--mono);font-size:12px}
.note{margin-top:18px;font-size:13.5px;color:var(--ink-2);max-width:78ch}
.note b{color:var(--ink)}
footer{margin-top:56px;border-top:2px solid var(--ink);padding-top:18px;font-family:var(--mono);font-size:11px;color:var(--ink-2);line-height:2}
a{color:var(--ink);text-decoration:none;border-bottom:1px solid var(--ink-2)}
@media(max-width:640px){.wrap{padding:0 16px 64px}.card .desc{font-size:13px}.rules li{grid-template-columns:1fr;gap:4px}}
@media(prefers-reduced-motion:reduce){*{transition:none!important}}
</style>
</head>
<body>
<div class="wrap">
<header class="top">
  <div class="eyebrow">LGD Engine · 判决档案 · 由引擎自身生成</div>
  <h1>五个判定器，<br>__CASES__ 个案件，<br>__RULES__ 条规则逐条对条款。</h1>
  <p class="lede">这一页不是宣传材料。<b>每张卡上的判决，都是本仓库里的案件文件送进 <code style="font-family:var(--mono)">GateEngine</code> 跑出来的原始结果</b>——含命中的规则编号、等级、理由原文。你可以在本地用一条命令重跑，得到与页面逐字相同的结果。</p>
  <div class="stamp">
    生成时间（UTC）：__GENERATED__<br>
    重跑 <code>python benchmarks/build_demo_page.py</code> · 校验 <code>python benchmarks/build_demo_page.py --check</code>（不一致则 CI 失败）<br>
    判定器：510(k) 变更分类 / 上市后监测 / PCCP 范围 / EU MDR 重大变更 / NMPA 变更注册
  </div>
</header>

<div class="kpis">
  <div class="kpi"><div class="n">5</div><div class="l">judges shipped</div><div class="s">覆盖 FDA / EU / 中国三辖区</div></div>
  <div class="kpi"><div class="n" id="kpi-cases">—</div><div class="l">case files</div><div class="s">全部随包发布，可直接跑</div></div>
  <div class="kpi"><div class="n" id="kpi-match">—</div><div class="l">verdicts match</div><div class="s">判决 = 案件预期，逐条一致</div></div>
  <div class="kpi"><div class="n">__ASSERTIONS__</div><div class="l">contract assertions</div><div class="s">每次推送由 CI 执行</div></div>
  <div class="kpi"><div class="n">__LAWN__</div><div class="l">rules with a clause</div><div class="s">__RULES__ 条规则全部点名依据</div></div>
  <div class="kpi"><div class="n">0</div><div class="l">network / model calls</div><div class="s">确定性 __DET__ · 单次判决预算 ≤500 µs</div></div>
</div>

<section class="sect">
  <div class="sect-h"><h2>案件档案</h2><span class="cnt">点击任一案件展开完整理由链</span></div>
  <div class="chips" id="chips"></div>
  <div class="cards" id="cards"></div>
</section>

<section class="sect">
  <div class="sect-h"><h2>它和"看着像就行"的写法差多少</h2><span class="cnt">12 条对抗探针 · 同一批输入</span></div>
  <p class="note">对照物不是商用产品，是一个"最可能被写出来的偷懒实现"：JSON 里出现 <code>banned</code> 关键词就 reject、出现 <code>requires_submission</code> 就 hold、其余放行。下面是 <code>benchmarks/adversarial_baseline.py</code> 此刻的真实输出（逐字）。</p>
  <table class="cmp">
    <thead><tr><th>实现</th><th>与预期一致的探针</th><th>说明</th></tr></thead>
    <tbody id="cmp-body"></tbody>
  </table>
  <div class="law" id="cmp-verdict"></div>
  <p class="note">朴素法错在两个相反方向：<b>该拦的放行</b>（空证据、未知变更类型、字符串 <code>"yes"</code> 被当成等价声明）、<b>该放的拦住</b>（PCCP 绿色案件因为 JSON 里出现了键名 <code>affects_intended_use</code>（值为 false）而被误判 hold）。这正是"键名匹配"与"语义判定"的差别。</p>
</section>

<section class="sect">
  <div class="sect-h"><h2>条款矩阵</h2><span class="cnt">__RULES__ 条规则 · 每条点名它编码的条款</span></div>
  <p class="note">判定器给结论不点条款，就和"模型的意见"无法区分。下表把每条规则落到依据上，并分列两种来源：<b>LAW</b> 是我们读过原文的法条／法规／MDCG·CAMD 通知／FDA 指南；<b>DOCTRINE</b> 是本家规则（L2 证据门、单辖区声明），明示为家法，不许冒充法条。家法占比由测试硬性封顶，防止它悄悄长成多数。</p>
  <div class="chips" id="basis-chips"></div>
  <input id="basis-q" type="search" placeholder="搜规则号或条款（如 §515C、第七十九条、MDCG）" aria-label="搜索条款矩阵"
    style="width:100%;font-family:var(--mono);font-size:13px;padding:10px 12px;border:1px solid var(--rule);background:var(--paper-2);margin-bottom:14px;color:var(--ink)">
  <table class="cmp">
    <thead><tr><th style="width:150px">判定器</th><th style="width:300px">规则</th><th>条款依据</th><th style="width:96px">类型</th></tr></thead>
    <tbody id="basis-body"></tbody>
  </table>
  <div class="law" id="basis-foot"></div>
  <p class="note">复核方式：<code>python benchmarks/clause_matrix.py</code> 双向检查——有规则无依据会失败，有依据但对应规则不存在也会失败（死引用正是引用表烂掉的方式）。可读版见 <code>docs/methods/Clause_Matrix.md</code>。</p>
</section>

<footer>
  LGD Engine · MedXpert-org/lgd-engine · 纯标准库，零运行时依赖 · 判定逻辑为代码，规则改动必须过 CI<br>
  本页由 <code>benchmarks/build_demo_page.py</code> 生成；页面与代码不一致时 CI 报错，不允许手工编辑。
</footer>
</div>

<script id="data" type="application/json">__DATA__</script>
<script>
(function(){
  var DATA = JSON.parse(document.getElementById('data').textContent);
  var cases = DATA.cases, base = DATA.baseline;
  var LABEL = {go:'GO', hold:'HOLD', reject:'REJECT'};

  document.getElementById('kpi-cases').textContent = cases.length;
  var declared = cases.filter(function(c){return c.matches !== null;});
  document.getElementById('kpi-match').textContent =
    declared.filter(function(c){return c.matches;}).length + '/' + declared.length;

  // chips
  var domains = [];
  cases.forEach(function(c){ if(domains.indexOf(c.domain) < 0) domains.push(c.domain); });
  var chips = document.getElementById('chips');
  function mkChip(key, text){
    var b = document.createElement('button');
    b.className = 'chip'; b.type = 'button'; b.textContent = text;
    b.setAttribute('aria-pressed', key === state.filter ? 'true':'false');
    b.addEventListener('click', function(){ state.filter = key; state.open = null; render(); });
    return b;
  }
  var state = {filter:'all', open:null};

  function renderChips(){
    chips.innerHTML = '';
    chips.appendChild(mkChip('all', '全部 ' + cases.length));
    domains.forEach(function(d){
      var n = cases.filter(function(c){return c.domain===d;}).length;
      var lab = cases.filter(function(c){return c.domain===d;})[0].domain_label;
      chips.appendChild(mkChip(d, lab + ' ' + n));
    });
  }

  var cards = document.getElementById('cards');
  function esc(s){ return String(s==null?'':s).replace(/[&<>"]/g, function(m){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]; }); }

  function detail(c){
    var el = document.createElement('div');
    el.className = 'panel';
    var rs = (c.reasons||[]).map(function(r){
      return '<li><span class="lv ' + esc(r.level) + '">' + esc(r.level.toUpperCase()) + '</span>'
        + '<div><span class="rid">' + esc(r.rule) + '</span><span class="det">' + esc(r.detail) + '</span></div></li>';
    }).join('');
    var evs = (c.evidence||[]).map(function(e){ return '<span>(' + esc(e.kind) + ') ' + esc(e.ref) + '</span>'; }).join('') || '<span>（无证据引用）</span>';
    var law = (c.law_enforcements||[]).map(function(x){ return esc(x); }).join('<br>');
    el.innerHTML =
      '<div class="headline"><span class="v ' + esc(c.verdict) + '">' + LABEL[c.verdict] + '</span>'
      + '<span class="file">' + esc(c.case_id) + ' · ' + esc(c.file) + '</span>'
      + '<span class="meta">exit ' + c.exit_code + ' · 预期 ' + esc(c.expected||'未声明') + (c.matches === false ? ' ✗' : (c.matches ? ' ✓' : '')) + '</span></div>'
      + (c.description ? '<p class="note" style="margin:0 0 4px">' + esc(c.description) + '</p>' : '')
      + (Object.keys(c.split_expectations||{}).length
          ? '<div class="law">同一份材料按辖区分别声明预期：' + Object.keys(c.split_expectations).map(function(k){
              return esc(k.replace('expected_','').replace('_verdict','').toUpperCase()) + ' → ' + esc(c.split_expectations[k]);
            }).join(' · ') + '（本卡跑的是 ' + esc(c.jurisdiction) + '）</div>' : '')
      + '<h3>理由链</h3><ul class="rules">' + (rs || '<li><span class="lv minor">—</span><div>无规则命中</div></li>') + '</ul>'
      + '<div class="ev">证据：' + evs + '</div>'
      + (law ? '<div class="law">' + law + '</div>' : '')
      + ((c.errors||[]).length ? '<div class="law" style="border-color:#96302A">errors：' + c.errors.map(esc).join('；') + '</div>' : '')
      + '<details class="raw"><summary>看输入上下文（送进判定器的原始 JSON）</summary><pre>' + esc(JSON.stringify(c.ctx, null, 2)) + '</pre></details>';
    return el;
  }

  function render(){
    renderChips();
    cards.innerHTML = '';
    var list = cases.filter(function(c){ return state.filter==='all' || c.domain===state.filter; });
    list.forEach(function(c){
      var card = document.createElement('article');
      card.className = 'card'; card.tabIndex = 0;
      card.innerHTML = '<div class="cid"><span>' + esc(c.case_id) + '</span><span>' + esc(c.domain_label) + '</span></div>'
        + '<div class="desc">' + esc(c.description || c.note || c.file) + '</div>'
        + '<div class="foot"><span class="v ' + esc(c.verdict) + '">' + LABEL[c.verdict] + '</span>'
        + '<span class="meta">' + (c.matches === null ? '未声明预期' : (c.matches ? '预期一致' : '<span class="miss">与预期不一致</span>'))
        + ' · ' + c.reasons.length + ' 条理由</span></div>';
      card.addEventListener('click', function(){ state.open = (state.open===c.file ? null : c.file); render(); });
      card.addEventListener('keydown', function(e){ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); card.click(); } });
      cards.appendChild(card);
      if(state.open === c.file){ cards.appendChild(detail(c)); }
    });
  }

  var body = document.getElementById('cmp-body');
  var rows = [['确定性判定器（本仓库）', base.lines.filter(function(l){return l.indexOf('gate')===0;})[0] || '—', '规则逐条执行，命中即记理由'],
              ['朴素关键词分类器（对照）', base.lines.filter(function(l){return l.indexOf('naive')===0;})[0] || '—', '键名/关键词匹配，不看语义']];
  rows.forEach(function(r){
    var tr = document.createElement('tr');
    tr.innerHTML = '<td>' + esc(r[0]) + '</td><td class="mono">' + esc(r[1].replace(/^[a-z]+\s*:\s*/,'')) + '</td><td>' + esc(r[2]) + '</td>';
    body.appendChild(tr);
  });
  document.getElementById('cmp-verdict').textContent = (base.lines.filter(function(l){return l.indexOf('delta')===0;})[0] || '—')
    + (base.ok ? '' : '（基线脚本未成功执行）');

  // clause matrix
  var RULES = DATA.rules || [];
  var bstate = {kind:'all'};
  var bchips = document.getElementById('basis-chips');
  function bChip(key, text){
    var b = document.createElement('button');
    b.className='chip'; b.type='button'; b.textContent=text;
    b.setAttribute('aria-pressed', bstate.kind===key?'true':'false');
    b.addEventListener('click', function(){ bstate.kind=key; renderBasis(); });
    return b;
  }
  function renderBasis(){
    var q = (document.getElementById('basis-q').value || '').toLowerCase();
    var body = document.getElementById('basis-body');
    body.innerHTML='';
    var list = RULES.filter(function(r){
      if(bstate.kind!=='all' && r.kind!==bstate.kind) return false;
      if(!q) return true;
      return (r.rule+' '+r.basis+' '+r.judge).toLowerCase().indexOf(q) >= 0;
    });
    list.forEach(function(r){
      var tr=document.createElement('tr');
      tr.innerHTML='<td class="mono">'+esc(r.judge.replace('judge_',''))+'</td><td class="mono">'+esc(r.rule)+'</td><td>'+esc(r.basis)+'</td><td class="mono">'+esc(r.kind)+'</td>';
      body.appendChild(tr);
    });
    bchips.innerHTML='';
    bchips.appendChild(bChip('all','全部 '+RULES.length));
    bchips.appendChild(bChip('LAW','LAW '+RULES.filter(function(r){return r.kind==='LAW';}).length));
    bchips.appendChild(bChip('DOCTRINE','DOCTRINE '+RULES.filter(function(r){return r.kind==='DOCTRINE';}).length));
    document.getElementById('basis-foot').textContent =
      '显示 '+list.length+' / '+RULES.length+' 条 · ' + (DATA.rules_meta || '');
  }
  document.getElementById('basis-q').addEventListener('input', renderBasis);
  renderBasis();

  render();
})();
</script>
</body>
</html>
"""


def build() -> str:
    cases = _load_cases()
    rules = _clause_rows()
    law_n = sum(1 for r in rules if r["kind"] == "LAW")
    from verdict_cost import measure as _measure_cost
    cost = _measure_cost()
    payload = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "cases": cases,
        "baseline": _baseline(),
        "rules": rules,
        "rules_meta": f"{len(rules)} 规则 · LAW {law_n} · DOCTRINE {len(rules)-law_n} · 0 无依据",
    }
    data_json = json.dumps(payload, ensure_ascii=False, indent=None, sort_keys=False)
    data_json = data_json.replace("</", "<\\/")
    html = TEMPLATE.replace("__GENERATED__", payload["generated_utc"]).replace("__DATA__", data_json)
    # Only the *stable* facts go into the page: a measured microsecond figure
    # varies run to run, so publishing it here would make --check flap. The
    # number lives in `benchmarks/verdict_cost.py`; the page publishes the claim
    # that a test enforces (a ≤500 µs budget, determinism, no model call).
    html = (html.replace("__CASES__", str(len(cases)))
                .replace("__RULES__", str(len(rules)))
                .replace("__LAWN__", str(law_n))
                .replace("__ASSERTIONS__", str(_assertion_count()))
                .replace("__DET__", "YES" if cost["deterministic"] else "NO"))
    return html
    data_json = json.dumps(payload, ensure_ascii=False, indent=None, sort_keys=False)
    data_json = data_json.replace("</", "<\\/")
    html = TEMPLATE.replace("__GENERATED__", payload["generated_utc"]).replace("__DATA__", data_json)
    html = (html.replace("__CASES__", str(len(cases)))
                .replace("__RULES__", str(len(rules)))
                .replace("__LAWN__", str(law_n))
                .replace("__ASSERTIONS__", str(_assertion_count())))
    return html


def main() -> int:
    html = build()

    if "--check" in sys.argv:
        if not OUT.exists():
            print(f"FAIL: {OUT.relative_to(ROOT)} is missing — run build_demo_page.py")
            return 1
        committed = OUT.read_text(encoding="utf-8")
        # The build timestamp is the only intended difference between two builds.
        # Normalise each side against the timestamp *found in that side*: passing
        # an external clock in made the check fail whenever a build and a check
        # straddled a minute boundary, which is a false alarm, not drift.
        if _normalise(committed) != _normalise(html):
            print("FAIL: demo page is out of date with the engine. Run "
                  "`python benchmarks/build_demo_page.py` and commit the result.")
            return 1
        print("OK: demo page matches the engine output")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    cases = _load_cases()
    declared = [c for c in cases if c["matches"] is not None]
    ok = sum(1 for c in declared if c["matches"])
    print(f"wrote {OUT.relative_to(ROOT)} · {len(cases)} cases · {ok}/{len(declared)} declared expectations match")
    return 0


def _ts_of(html: str) -> str:
    marker = "生成时间（UTC）："
    i = html.find(marker)
    if i < 0:
        return ""
    return html[i + len(marker):i + len(marker) + 16].strip()


def _normalise(html: str) -> str:
    ts = _ts_of(html)
    return html.replace(ts, "<TS>") if ts else html


if __name__ == "__main__":
    raise SystemExit(main())
