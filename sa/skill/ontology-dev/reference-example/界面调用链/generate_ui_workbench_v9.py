#!/usr/bin/env python3
"""Generate the V9 seven-model UI call-chain workbench.

This adapter keeps the parent reference directory read-only. It reuses the
existing parser and renderer in memory, then applies the positive V9 model
boundary before writing output exclusively to this directory by default.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


HERE = Path(__file__).resolve().parent
REFERENCE_DIR = HERE.parent
BASE_ENGINE = REFERENCE_DIR / "generate_ui_workbench.py"
DEFAULT_OUTPUT = HERE / "contract-management-ui-callchain_v9.html"


def load_base_engine():
    """Load the existing generator without importing it or creating bytecode."""
    if not BASE_ENGINE.exists():
        raise FileNotFoundError(f"找不到基础生成器：{BASE_ENGINE}")
    namespace = {
        "__name__": "v9_base_engine",
        "__file__": str(BASE_ENGINE),
    }
    source = BASE_ENGINE.read_text(encoding="utf-8")
    exec(compile(source, str(BASE_ENGINE), "exec"), namespace)
    return namespace


def validate_manifest(yaml_dir: Path, engine_files):
    manifest_path = yaml_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"找不到模型清单：{manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    declared = tuple(manifest.get("model_files") or [])
    supported = tuple(engine_files)
    if declared != supported:
        raise ValueError(
            "manifest.json 的 model_files 与 V9 七模型读取顺序不一致：\n"
            f"manifest={declared}\n生成器={supported}"
        )
    return manifest


def v9_template(base_template: str) -> str:
    """Replace legacy explanatory notices with positive seven-model wording."""
    aggregate_pattern = (
        r"(else if\(type==='aggregate'\)\{.*?body=)"
        r"'<div class=\"notice\">.*?</div>'\+"
    )
    aggregate_replacement = (
        r"\1'<div class=\"notice\">"
        r"对象详情严格展示 M1 已声明的聚合、属性、约束和对象关联。"
        r"</div>'+"
    )
    template, aggregate_count = re.subn(
        aggregate_pattern,
        aggregate_replacement,
        base_template,
        count=1,
        flags=re.S,
    )

    welcome_pattern = (
        r'<div class="notice" style="margin-top:25px">'
        r'本工作台严格采用 manifest.*?</div>'
    )
    welcome_replacement = (
        '<div class="notice" style="margin-top:25px">'
        '本工作台以 manifest 声明的七模型 YAML 为唯一业务事实源。'
        '</div>'
    )
    template, welcome_count = re.subn(
        welcome_pattern,
        welcome_replacement,
        template,
        count=1,
        flags=re.S,
    )

    if aggregate_count != 1 or welcome_count != 1:
        raise RuntimeError(
            "基础模板结构已变化，V9 提示区适配失败；请检查基础生成器后再生成。"
        )

    linked_reports = (
        "function linkedReports(owner){return DATA.reports.filter("
        "r=>arr(r.sourceObjects).some(x=>(x.objectRef||x)===owner))}"
    )
    linked_actions = (
        "function linkedActions(behaviorId){return DATA.screens.flatMap("
        "s=>arr(s.actions).filter(a=>a.behaviorRef===behaviorId)"
        ".map(a=>({screen:s,action:a}))) }"
    )
    if linked_reports not in template:
        raise RuntimeError("基础模板缺少报表反向索引函数。")
    template = template.replace(
        linked_reports,
        linked_reports + linked_actions,
        1,
    )

    behavior_prefix = (
        "else if(type==='behavior'){const reports=DATA.reports.filter("
        "r=>r.behaviorRef===o.id);const flows=DATA.flows.filter("
        "f=>arr(f.activities).some(a=>a.behaviorRef===o.id));body="
    )
    if behavior_prefix not in template:
        raise RuntimeError("基础模板的行为详情结构已变化。")
    template = template.replace(
        behavior_prefix,
        behavior_prefix[:-5] + "const actions=linkedActions(o.id);body=",
        1,
    )

    flow_card = "${card('参与流程',refs(flows.map(x=>x.id)))}"
    action_card = (
        "${card('界面入口',table(actions,[[\'界面\',x=>ref("
        "x.screen.screenId,x.screen.name)],[\'操作\',x=>`<button "
        "class=\"ref\" data-ref=\"${esc(key('action',x.action))}\">"
        "${esc(x.action.name)}</button>`]]))}"
    )
    if flow_card not in template:
        raise RuntimeError("基础模板缺少行为参与流程卡片。")
    template = template.replace(flow_card, flow_card + action_card, 1)

    role_branch = (
        "else if(type==='role'){body=`<div class=\"grid\">"
        "${card('角色权限',refs(o.permissions))}"
        "${card('关联参与者',refs(DATA.actors.filter("
        "a=>arr(a.roles).includes(o.roleId)).map(a=>a.actorId)))}</div>`}"
    )
    role_replacement = (
        "else if(type==='role'){const flows=DATA.flows.filter("
        "f=>arr(f.roleRefs).includes(o.roleId)||arr(f.activities).some("
        "a=>a.roleRef===o.roleId));body=`<div class=\"grid\">"
        "${card('角色权限',refs(o.permissions))}"
        "${card('关联参与者',refs(DATA.actors.filter("
        "a=>arr(a.roles).includes(o.roleId)).map(a=>a.actorId)))}"
        "${card('参与流程',refs(flows.map(f=>f.id)))}</div>`}"
    )
    if role_branch not in template:
        raise RuntimeError("基础模板的角色详情结构已变化。")
    template = template.replace(role_branch, role_replacement, 1)

    copy_helper = r"""
async function copyText(text){
 try{if(navigator.clipboard?.writeText){await navigator.clipboard.writeText(text);return true}}catch(_error){}
 const area=document.createElement('textarea');area.value=text;area.setAttribute('readonly','');area.style.position='fixed';area.style.opacity='0';document.body.appendChild(area);area.select();
 try{return document.execCommand('copy')}finally{area.remove()}
}
""".strip()
    bind_marker = "function bindDetail(){"
    clipboard_call = "navigator.clipboard?.writeText(c.dataset.copy)"
    if bind_marker not in template or clipboard_call not in template:
        raise RuntimeError("基础模板的复制 ID 逻辑已变化。")
    template = template.replace(bind_marker, copy_helper + bind_marker, 1)
    template = template.replace(clipboard_call, "copyText(c.dataset.copy)", 1)
    return template


def normalize_meta(data: dict, manifest: dict) -> dict:
    meta = data.get("meta") or {}
    data["meta"] = {
        "domain": meta.get("domain") or manifest.get("domain") or "本体模型",
        "application": meta.get("application") or manifest.get("project") or "本体调用链工作台",
        "modelFiles": list(manifest.get("model_files") or []),
        "missingFiles": list(meta.get("missingFiles") or []),
        "promptVersion": "V9",
    }
    return data


def generate(yaml_dir: Path, output_html: Path, pretty: bool = False):
    engine = load_base_engine()
    manifest = validate_manifest(yaml_dir, engine["MODEL_FILES"])
    data = normalize_meta(engine["normalize"](yaml_dir), manifest)
    if data["meta"]["missingFiles"]:
        raise FileNotFoundError(
            "模型文件不完整：" + ", ".join(data["meta"]["missingFiles"])
        )

    payload = json.dumps(
        data,
        ensure_ascii=False,
        indent=2 if pretty else None,
    ).replace("</", "<\\/")
    title = f'{data["meta"]["application"]} · V9'
    html = (
        v9_template(engine["HTML"])
        .replace("__TITLE__", title)
        .replace("__DATA__", payload)
    )

    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_html.write_text(html, encoding="utf-8")
    counts = {
        key: len(value)
        for key, value in data.items()
        if isinstance(value, list)
    }
    return counts


def main():
    parser = argparse.ArgumentParser(description="生成 V9 七模型 UI 调用链工作台")
    parser.add_argument("yaml_dir", nargs="?", type=Path, default=REFERENCE_DIR)
    parser.add_argument("output_html", nargs="?", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--pretty", action="store_true", help="内嵌格式化 JSON")
    args = parser.parse_args()

    yaml_dir = args.yaml_dir.resolve()
    output_html = args.output_html.resolve()
    if output_html.parent != HERE:
        raise ValueError(f"V9 产物只能写入目录：{HERE}")

    counts = generate(yaml_dir, output_html, args.pretty)
    print(f"Generated: {output_html}")
    print("Counts:", counts)


if __name__ == "__main__":
    main()
