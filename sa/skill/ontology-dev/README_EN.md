# ontology-driven-dev

> A reusable agent **skill for building ontology-driven business systems** through a three-stage pipeline: **Requirement Exploration → Ontology Modeling → App Construction**.
> Built on a seven-model ontology YAML set (M1/M2/M3/M5/M6/M7/MU) and a bundled `code-paas` tech base, with mandatory human-confirmation gates at every requirement stage, producing a **runnable browser front-end + back-end (BS) system** that is strictly aligned with the requirement doc, the ontology models, and the code.

[中文版 → README.md](./README.md)

---

## 1. What this skill does

Turn a business requirement (a sentence or a paragraph) into a **runnable management system**, while guaranteeing:

- **Traceable requirements**: every feature maps back to an item in the requirement spec;
- **Model as single source of truth**: DB tables, APIs, menus, permissions, flows, and rules are all generated from the seven-model YAML — no "model says one thing, code does another";
- **Non-skippable human gates**: the 8 stages of requirement exploration each **pause for explicit user confirmation** before proceeding;
- **Ready-to-extend tech base**: a bundled `code-paas` (Flask + SQLite + React/TS monolith with admin, flow engine, workbench, and ontology registry) that you copy and extend;
- **Mandatory AI chat panel**: the generated app ships with a right-side AI chat (ontology-registry injection + tool calls + SSE streaming + read-only SQL safety boundary).

---

## 2. What's included

```
ontology-driven-dev/
├── SKILL.md                      # Core skill instructions (methodology + 3-stage pipeline + discipline)
├── references/                   # 5 methodology docs (mandatory specs)
│   ├── AI需求探索与确认提示词V9.0.md      # incl. full "Software Requirement Spec V9.0"
│   ├── ontology_modeling_framework_v9.md  # seven-model meta-spec + YAML templates
│   ├── 本体模型业务功能开发指导书.md        # model→implementation mapping, 10-step pipeline
│   ├── AI原生应用技术架构设计文档.md        # stack / semantic registry / AI orchestration / SSE
│   └── UI-UE界面设计规范.md               # color tokens / layouts / full CSS library
├── reference-example/            # Golden example (sales-contract execution, fully run)
│   ├── 合同管理需求规格说明书-V9.md
│   ├── m1-object-model.yaml … m7-report-model.yaml + mu-ui-model.yaml
│   └── manifest.json
└── techbase/                     # clean code-paas source (copy to code-app, then extend)
    ├── backend/                  # Flask + SQLite (flow engine / ontology registry / services)
    ├── frontend/                 # React + TypeScript (Vite)
    ├── models/                   # sample seven-model YAML (replace with your own)
    ├── requirements.txt
    └── README.md                 # tech-base run instructions
```

---

## 3. Installation (mainstream tools)

> This skill has **zero dependency on any WorkBuddy-specific mechanism** and runs fully on Claude Code, Codex, Cursor, etc.
> The only adaptation point: relative paths resolve against "the folder containing this SKILL.md", which each tool resolves automatically.

### 3.1 WorkBuddy

```bash
# user-level (available in all projects)
cp -r ontology-driven-dev ~/.workbuddy/skills/ontology-driven-dev

# or project-level (current project only)
cp -r ontology-driven-dev <your-project>/.workbuddy/skills/ontology-driven-dev
```

Then just say a trigger phrase in a WorkBuddy chat (see Section 5).

### 3.2 Claude Code

Claude Code's Skills format is identical to this skill's frontmatter (`name` / `description`), so it is essentially a **direct copy**:

```bash
# user-level
cp -r ontology-driven-dev ~/.claude/skills/ontology-driven-dev

# or project-level
cp -r ontology-driven-dev .claude/skills/ontology-driven-dev
```

Claude Code auto-discovers `.claude/skills/<name>/SKILL.md` and follows its pipeline.

### 3.3 Codex

Codex has no native skill registry, but it can load in-repo instruction files and run bash in a sandbox:

```bash
# drop the skill into the repo (any directory name)
mkdir -p .codex/skills && cp -r ontology-driven-dev .codex/skills/
```

Then add one line to your repo's `codex.md` (or `AGENTS.md`):

> When the user wants "ontology-driven dev / requirement exploration / ontology modeling / seven-model / code-paas / AI-native app", load `.codex/skills/ontology-driven-dev/SKILL.md` and strictly follow its "3-stage + human-confirmation gate" pipeline.

Codex maps each stage's human gate to an interactive prompt/approval. Note: the sandbox needs network access for `npm install` / `pip install`.

### 3.4 Cursor / Aider / Cline / other generic agents

Treat `SKILL.md` as a "methodology instruction file" and inject it into the project context:
- Cursor: put it in `.cursorrules` or project rules;
- Cline / Aider: paste the full `SKILL.md` at the start of a chat, or reference its path;
- Any agent supporting "system instructions / project memory": just load this `SKILL.md`.

---

## 4. Usage (detailed)

The skill runs as **three strongly-ordered stages**, each separated by mandatory human confirmation.

### Stage 1: Requirement Exploration → Software Requirement Spec
- **Basis**: `references/AI需求探索与确认提示词V9.0.md` (incl. full "Software Requirement Spec V9.0").
- **Flow**: 8 stages — overall understanding → business objects → functions & rules → cross-object linkage → end-to-end collaboration/approval flow → queries/reports → roles & permissions → UI prototype (optional).
- **Gate**: at the end of each stage, ask in the format "question + AI suggestion + rationale + other options + quick reply" and **hard-pause for confirmation**; enterprise-specific (Type-B) content must be proposed with an AI suggestion and cannot proceed until confirmed.
- **Output**: `<domain>-需求规格说明书-V9.md` (incl. Appendix C, the seven-model input baseline).

### Stage 2: Ontology Modeling → Seven-model YAML
- **Basis**: `references/ontology_modeling_framework_v9.md`.
- **Input**: Appendix C baseline from Stage 1 (a deterministic input — no further large-scale business splitting).
- **Output**: seven YAML files — M1 object / M2 behavior / M3 rule / M5 actor / M6 flow / M7 query-report / MU UI — plus `manifest.json`, written to `yaml/`.
- **Consistency gate**: traceability, M7↔M2 one-to-one, M6 references acyclic, etc.

### Stage 3: App Construction → Runnable BS System
- **Tech base**: copy `techbase/` into the project's `code-app/`:
  ```bash
  cp -r <skill-root>/techbase/. <your-project>/code-app/
  cd <your-project>/code-app/frontend && npm install
  cd <your-project>/code-app/backend  && pip install -r requirements.txt
  ```
- **Order** (10 steps from the guidebook): write seven-model YAML → generate DDL/tables → register data dictionary → behavior+rule services → role/permission seed → flow engine → menus/pages/routes → **mandatory right-side AI chat panel** → end-to-end integration → acceptance.
- **Run**:
  ```bash
  # backend
  cd code-app/backend && pip install -r requirements.txt && python app.py   # http://localhost:5000
  # frontend dev
  cd code-app/frontend && npm install && npm run dev                       # http://localhost:5173
  ```
- **Default account**: `admin / admin123` (see `techbase/README.md`).

---

## 5. Trigger phrases (just say to the agent)

| Intent | Example |
|---|---|
| Full build | "Help me build an XX management system", "Make this requirement ontology-driven" |
| Modeling only | "Based on this spec, do the ontology modeling" |
| Construction only | "Generate the system from these seven-model YAMLs" |
| Keywords | ontology-driven, requirement exploration, ontology modeling, seven-model, code-paas, AI-native app, business system dev |

---

## 6. Runtime requirements

- Python 3.10+ (Flask + SQLite backend)
- Node.js 18+ (React + Vite frontend)
- Network access on first run for `npm install` / `pip install`

---

## 7. License

Released under the **MIT License** — free to use, modify, and redistribute. See [LICENSE](./LICENSE).
(The `code-paas` tech base is also MIT-licensed.)
