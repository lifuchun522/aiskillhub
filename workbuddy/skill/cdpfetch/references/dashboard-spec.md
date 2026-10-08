# 单文件看板交付规范

抓取只是原料。cdpfetch 的默认交付物是一份**单文件 HTML 看板**——双击即看、可离线、
可归档、不依赖任何外部服务。以下是要点，逐条都是踩过的。

## 一、硬约束（缺一条即为不合格）

| 约束 | 校验方式 |
|---|---|
| 全部 CSS 内联（单一 `<style>`） | `verify_dashboard.py` 自动查 `externalRefs == 0` |
| 全部 JS 内联（单一 `<script>`，无 `src`） | 同上 |
| 图形全内联 SVG / Canvas，**不用外链图片** | `img[src]` 必须为 0 |
| 导航用**按钮 + `scrollIntoView`**，不用 `<a href="#id">` | `forbid_anchor_href: true` |
| 中英双语，**双侧编译**而非运行时翻译 | `--toggle-lang` 检查文案确实变化 |
| 顶部标注数据来源与抓取时间 | 人眼复核 + 抓取窗口取自 `_manifest.json` |

「导航用按钮不用锚点」的原因很实际：锚点跳转会在 URL 上留 `#hash`、会触发浏览器
默认滚动定位（和自定义滚动打架）、且在不同宿主预览器里行为不一致。按钮返回 `<button>`
（`type="button"`）+ 显式的 `data-scroll` 指向目标 id，行为完全可控。

## 二、中英切换：双侧编译

**不要**在运行时做「中译英」——翻译质量不可控，且切换时重新渲染会丢可视化状态。

正确做法：数据对象里每个文案字段都存 `{zh, en}`，切换只改一个全局 `LANG` 变量后重渲染：

```js
const PRODUCTS = [{
  id: 'vendorA',
  tagline: { zh: '一句话定位', en: 'One-line positioning' },
  // ...
}];
let LANG = 'zh';
function render() { /* 全部取 x[LANG] */ }
document.getElementById('lang-zh').addEventListener('click', () => { LANG = 'zh'; render(); });
```

同时切换 `document.documentElement.lang`——无障碍读屏与字体回退都依赖它，
验证脚本也靠它判断切换是否生效。

## 三、可视化选型

| 想表达 | 用什么 | 不用什么 |
|---|---|---|
| 单值强度对比 | 横向条形图（纯 CSS 宽度的 `div`，或内联 SVG） | 饼图 |
| 多维度综合能力 | 内联 SVG 雷达图 | 3D 图 |
| 逐字精确对照 | HTML `<table>`（`position: sticky` 表头） | Canvas 画的表格 |
| 数值看板 | 大字号数字 + 单位标签 | 仪表盘（gauge） |

**雷达图两条实战注意**：轴标签要根据标签点相对圆心的水平位置决定
`text-anchor`（`middle` / `start` / `end`），否则文字会压在图元上；
多边形要留 `fill-opacity`，否则 5 个产品叠在一起完全看不清。

## 四、自建评分必须公开规则

雷达图和条形图的数值若是**本看板自建口径**（不是厂商官方评分），必须：

1. 在页内写清评分函数与各维度分档，可回溯；
2. 明确标注「本看板自建指数，非厂商官方评分」；
3. 评分逻辑写成显式纯函数，不要散在渲染代码里。

否则读者会把自建指数误当成客观事实——这是看板类交付最容易造成的信息失真。

## 五、可直接拿来用的验证规格

```json
{
  "title_contains": "竞品对比",
  "zero_console_errors": true,
  "forbid_external_refs": true,
  "forbid_anchor_href": true,
  "selectors": {
    "#cards .card": 5,
    "#cmp tbody tr": 13,
    "#radar svg polygon": 5,
    "#evt tbody tr": 19
  }
}
```

选择器计数是**最便宜的回归测试**：改完样式跑一遍，卡片少一张、证据表少一行立刻暴露。
数量填成「当前实测值」——它的作用不是断言正确性，而是断言「没有意外减少」。
