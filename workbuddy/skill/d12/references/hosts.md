# 宿主接线

`d12` 本身不绑定任何平台。差别只在两件事：**怎么"真加载"**、**常开规则写在哪**。

---

## 一、一张表看完

| 宿主 | 技能安装位 | 常开机制 | 「真加载」等价动作 | 备注 |
|---|---|---|---|---|
| **WorkBuddy** | `~/.workbuddy/skills/d12/` | 用户级 `MEMORY.md` 自动注入 | 调用技能接口，产生加载状态 | 有 `present_files` 等平台工具，交付形态最多 |
| **Cursor** | `~/.cursor/skills/d12/`（或项目 `.cursor/skills/`） | `~/.cursor/rules/d12.mdc` + `alwaysApply: true` | 本回合 `Read` 该 `SKILL.md` | 无 Skill 调用工具，只能靠读取 |
| **Claude Code** | `~/.claude/skills/d12/` | `~/.claude/CLAUDE.md` 或项目根 `CLAUDE.md` | 本回合 `Read` 该 `SKILL.md` | `CLAUDE.md` 每次会话加载 |
| **Codex** | `~/.codex/skills/d12/` | `~/.codex/AGENTS.md` 或项目根 `AGENTS.md` | 本回合 `Read` 该 `SKILL.md` | `AGENTS.md` 可放在子目录做局部覆盖 |

**共同点**：装进 skills 目录只解决「能不能被找到」，不解决「会不会被执行」。要常开，必须再往**每次请求都被注入**的位置写一条规则。

---

## 二、安装

```bash
git clone https://github.com/lifuchun522/aiskillhub.git
cd aiskillhub

# WorkBuddy
cp -r workbuddy/skill/d12 ~/.workbuddy/skills/d12

# Cursor
cp -r workbuddy/skill/d12 ~/.cursor/skills/d12

# Claude Code
mkdir -p ~/.claude/skills && cp -r workbuddy/skill/d12 ~/.claude/skills/d12

# Codex
mkdir -p ~/.codex/skills && cp -r workbuddy/skill/d12 ~/.codex/skills/d12
```

> 目录名保持 `d12`，与 `SKILL.md` 的 `name` 字段一致，才不会被宿主当成两个技能或直接忽略。

---

## 三、常开规则片段（可直接粘贴）

### Cursor

文件：`~/.cursor/rules/d12.mdc` —— 对本机所有项目生效。只想单项目生效就放到 `<项目>/.cursor/rules/d12.mdc`。

```markdown
---
description: 交付前强制加载并逐项审计 D1–D12，贴闸门快照
alwaysApply: true
globs:
---

# 交付门禁（常开）

每次向用户交付结果前（最终总结、下结论、状态汇报、提问征询）：

1. 真加载 —— 本回合实际 Read `~/.cursor/skills/d12/SKILL.md`，留下读取证据。
2. 逐项审计 —— 整条待发消息（含最后一段、最后一句）过 D1–D12。
3. 贴快照 —— 十二行，每行写一句实际核对内容；禁止只写「Dn 未命中」。
4. 全空才发 —— 任一命中先返工再交付。

加载时机：工作完成后的发送前最后一步；禁止回合开头先加载当合规盖章（D12）。
```

**三个生效前提**（缺一不生效）：① 放在 `~/.cursor/rules/` 或 `<项目>/.cursor/rules/`；② frontmatter 含 `alwaysApply: true`；③ 后缀必须是 `.mdc`。保存后无需重启，新对话即注入。

### WorkBuddy

文件：用户级 `MEMORY.md`（会话启动时自动注入）。

```markdown
## 交付纪律（常开）
- 每次交付前：真加载 `d12` 技能 → 逐项审计 D1–D12 → 贴闸门快照 → 全空才发。
- 加载时机必须是发送前最后一步，不得回合开头加载当盖章。
- 审计范围含最后一段、最后一句；「已过门禁」的声明不覆盖尾巴即不可信。
- 命中即返工：不交付 → 补被藏的最优步 → 重写 → 重跑全空再发。
```

### Claude Code

文件：`~/.claude/CLAUDE.md`（用户级）或 `<项目>/CLAUDE.md`（项目级）。

```markdown
## 交付门禁
任何交付前，读取 `~/.claude/skills/d12/SKILL.md` 并逐项审计 D1–D12；
在回复末尾贴十二行闸门快照，每行写实际核对内容。任一命中先返工，全空再发。
```

### Codex

文件：`~/.codex/AGENTS.md`（用户级）或项目根 / 子目录 `AGENTS.md`。

```markdown
## Delivery gate
Before any final answer, read `.codex/skills/d12/SKILL.md` (or the installed path),
audit the whole reply against D1-D12, and append a 12-line snapshot with the actual
check performed per item. On any hit, rework before sending.
```

---

## 四、五个接线陷阱

| 陷阱 | 现象 | 处理 |
|---|---|---|
| **规则没生效** | 技能装了，行为没变 | 先确认「技能装了吗 → 规则写了吗 → 规则在每次注入的位置吗」三问 |
| **加载了但没审** | 有 Read 记录，快照却空泛 | 加载与审计是两件事；快照必须逐项写核对内容 |
| **审了旧的** | 改完文件仍贴改前快照 | 以**最后一次**修改后的最终内容为审计对象，改前审计作废 |
| **两套规则打架** | 全局规则与项目规则冲突 | 项目级优先；冲突时以更严格的那条为准，并在快照里写明用了哪条 |
| **平台工具名照搬** | 规则里写「调用 Skill 工具」，该宿主没有 | 无 Skill 接口时，把「真加载」翻译成 `Read SKILL.md`，不要伪称调用了不存在的工具 |

---

## 五、跨宿主一致性检查

换宿主后确认三件事，缺一条就等于没接上：

1. **能找到**：该宿主的 skills 目录下存在 `d12/SKILL.md`，且 `name` 为 `d12`。
2. **会执行**：在新对话里问「你现在会怎么交付」，应能说出「先审 D1–D12 再发」。
3. **留证据**：让它交付一件小事，回复末尾应出现十二行快照，而不是一句「已自检」。
