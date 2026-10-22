import React from 'react';
import { interpolate, spring, useVideoConfig } from 'remotion';
import { ContentCard } from './types';

// ============================================================
// 内容卡图解层
// 一个论点可以有多种结构表达：流程 / 分解 / 集成 / 对比 / 映射 / 关系 / 层次。
// 这里把每种结构做成独立渲染器，由 card.kind 分发。
// ============================================================

const FONT = '"Microsoft YaHei", "PingFang SC", "Noto Sans SC", "Source Han Sans SC", sans-serif';
const HI = 'rgba(255,255,255,0.94)';
const MID = 'rgba(255,255,255,0.72)';
const DIM = 'rgba(255,255,255,0.52)';
const PANEL = 'rgba(255,255,255,0.055)';
const PANEL_STRONG = 'rgba(255,255,255,0.085)';
const BORDER = '1px solid rgba(255,255,255,0.10)';
const LINE = 'rgba(255,255,255,0.30)';

// —— 纯函数动画（可在 map 循环里安全调用，不涉及 hooks）——
const rise = (local: number, fps: number, delay = 0, distance = 18) => {
  const p = spring({ frame: local - delay, fps, config: { damping: 200, mass: 0.6 } });
  return {
    opacity: p,
    transform: `translateY(${interpolate(p, [0, 1], [distance, 0])}px)`,
  } as React.CSSProperties;
};

const fade = (local: number, delay = 0, dur = 12) =>
  interpolate(local, [delay, delay + dur], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

/** 画线进度 0→1，用于 strokeDashoffset */
const draw = (local: number, delay = 0, dur = 16) =>
  interpolate(local, [delay, delay + dur], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

const Box: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({
  children,
  style,
}) => (
  <div
    style={{
      background: PANEL,
      border: BORDER,
      borderRadius: 12,
      padding: '14px 18px',
      fontFamily: FONT,
      fontSize: 21,
      fontWeight: 600,
      color: HI,
      lineHeight: 1.42,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      textAlign: 'center',
      ...style,
    }}
  >
    {children}
  </div>
);

const Note: React.FC<{ text?: string; accent: string; local: number }> = ({
  text,
  accent,
  local,
}) => {
  if (!text) return null;
  return (
    <div
      style={{
        marginTop: 22,
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        opacity: fade(local, 30, 14),
      }}
    >
      <div style={{ width: 26, height: 2, background: accent, flexShrink: 0 }} />
      <div style={{ fontFamily: FONT, fontSize: 20, color: MID, letterSpacing: 1 }}>{text}</div>
    </div>
  );
};

// ============================================================
// 1. flow —— 流程链：A → B → C → D
// ============================================================

const FlowArrow: React.FC<{ local: number; delay: number; accent: string }> = ({
  local,
  delay,
  accent,
}) => (
  <div
    style={{
      width: 48,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      opacity: fade(local, delay, 9),
      transform: `translateX(${interpolate(local, [delay, delay + 9], [-8, 0], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      })}px)`,
      flexShrink: 0,
    }}
  >
    <svg width="20" height="20" viewBox="0 0 20 20">
      <path
        d="M2 10h12M9.5 5l5 5-5 5"
        stroke={accent}
        strokeWidth="2"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  </div>
);

const FlowBody: React.FC<{ card: ContentCard; accent: string; local: number }> = ({
  card,
  accent,
  local,
}) => {
  const { fps } = useVideoConfig();
  const items = card.items || [];
  const last = items.length - 1;
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'stretch', width: '100%' }}>
        {items.map((t, i) => (
          <React.Fragment key={i}>
            {/* 末节点是结论，用强调色单独标出来 */}
            <Box
              style={{
                flex: 1,
                minHeight: 118,
                ...(i === last
                  ? { background: `${accent}14`, border: `1px solid ${accent}`, fontWeight: 700 }
                  : {}),
                ...rise(local, fps, i * 7),
              }}
            >
              {t}
            </Box>
            {i < items.length - 1 ? (
              <FlowArrow local={local} delay={i * 7 + 5} accent={accent} />
            ) : null}
          </React.Fragment>
        ))}
      </div>
      <Note text={card.note} accent={accent} local={local} />
    </div>
  );
};

// ============================================================
// 2. quad —— 四宫格分解
// ============================================================

const QuadBody: React.FC<{ card: ContentCard; accent: string; local: number }> = ({
  card,
  accent,
  local,
}) => {
  const { fps } = useVideoConfig();
  const items = card.items || [];
  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>
        {items.map((t, i) => (
          <div
            key={i}
            style={{
              background: PANEL,
              border: BORDER,
              borderRadius: 12,
              padding: '20px 22px',
              display: 'flex',
              gap: 16,
              alignItems: 'center',
              minHeight: 124,
              ...rise(local, fps, i * 7),
            }}
          >
            <div
              style={{
                fontFamily: FONT,
                fontSize: 34,
                fontWeight: 800,
                color: accent,
                lineHeight: 1,
                letterSpacing: -1,
                flexShrink: 0,
              }}
            >
              {String(i + 1).padStart(2, '0')}
            </div>
            <div
              style={{
                fontFamily: FONT,
                fontSize: 21,
                fontWeight: 600,
                color: HI,
                lineHeight: 1.45,
              }}
            >
              {t}
            </div>
          </div>
        ))}
      </div>
      <Note text={card.note} accent={accent} local={local} />
    </div>
  );
};

// ============================================================
// 3. map —— 映射：左列 → 右列，逐行连线
// ============================================================

const MAP_W = 1120;
const MAP_LEFT_W = 420;
const MAP_RIGHT_W = 400;
const MAP_X1 = MAP_LEFT_W;
const MAP_X2 = MAP_W - MAP_RIGHT_W;
const MAP_ROW = 88;
const MAP_HEAD = 42;

const MapBody: React.FC<{ card: ContentCard; accent: string; local: number }> = ({
  card,
  accent,
  local,
}) => {
  const { fps } = useVideoConfig();
  const left = card.left || [];
  const right = card.right || [];
  const rows = Math.max(left.length, right.length);
  const height = MAP_HEAD + rows * MAP_ROW;
  const lineLen = MAP_X2 - MAP_X1;

  return (
    <div>
      <div style={{ position: 'relative', width: MAP_W, height, margin: '0 auto' }}>
        {/* 列标题 */}
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 6,
            width: MAP_LEFT_W,
            fontFamily: FONT,
            fontSize: 18,
            fontWeight: 700,
            color: DIM,
            letterSpacing: 3,
            opacity: fade(local, 0, 12),
          }}
        >
          {card.leftTitle}
        </div>
        <div
          style={{
            position: 'absolute',
            left: MAP_X2,
            top: 6,
            width: MAP_RIGHT_W,
            fontFamily: FONT,
            fontSize: 18,
            fontWeight: 700,
            color: accent,
            letterSpacing: 3,
            opacity: fade(local, 4, 12),
          }}
        >
          {card.rightTitle}
        </div>

        {/* 连接线 */}
        <svg
          width={MAP_W}
          height={height}
          style={{ position: 'absolute', left: 0, top: 0, overflow: 'visible' }}
        >
          {Array.from({ length: rows }).map((_, i) => {
            const y = MAP_HEAD + i * MAP_ROW + 32;
            const d = draw(local, 14 + i * 6, 14);
            return (
              <g key={i}>
                <line
                  x1={MAP_X1}
                  y1={y}
                  x2={MAP_X2 - 12}
                  y2={y}
                  stroke={LINE}
                  strokeWidth="2"
                  strokeDasharray={lineLen}
                  strokeDashoffset={lineLen * d}
                />
                <path
                  d={`M${MAP_X2 - 14} ${y - 6} L${MAP_X2 - 4} ${y} L${MAP_X2 - 14} ${y + 6}`}
                  stroke={accent}
                  strokeWidth="2"
                  fill="none"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  opacity={1 - d}
                />
              </g>
            );
          })}
        </svg>

        {/* 左列 */}
        {left.map((t, i) => (
          <Box
            key={i}
            style={{
              position: 'absolute',
              left: 0,
              top: MAP_HEAD + i * MAP_ROW,
              width: MAP_LEFT_W,
              height: 64,
              padding: '0 20px',
              fontSize: 20,
              ...rise(local, fps, i * 5),
            }}
          >
            {t}
          </Box>
        ))}

        {/* 右列 */}
        {right.map((t, i) => (
          <Box
            key={i}
            style={{
              position: 'absolute',
              left: MAP_X2,
              top: MAP_HEAD + i * MAP_ROW,
              width: MAP_RIGHT_W,
              height: 64,
              padding: '0 20px',
              fontSize: 20,
              background: `${accent}14`,
              border: `1px solid ${accent}`,
              color: '#FFFFFF',
              ...rise(local, fps, 22 + i * 6),
            }}
          >
            {t}
          </Box>
        ))}
      </div>
      <Note text={card.note} accent={accent} local={local} />
    </div>
  );
};

// ============================================================
// 4. compare —— 对比：左右两栏
// ============================================================

const ComparePanel: React.FC<{
  title?: string;
  items: string[];
  accent: string;
  hero?: boolean;
  local: number;
  fps: number;
}> = ({ title, items, accent, hero, local, fps }) => (
  <div
    style={{
      flex: 1,
      background: hero ? `${accent}10` : PANEL,
      border: hero ? `1px solid ${accent}` : BORDER,
      borderRadius: 14,
      padding: '24px 26px',
      ...rise(local, fps, hero ? 10 : 0),
    }}
  >
    {title ? (
      <div
        style={{
          fontFamily: FONT,
          fontSize: 25,
          fontWeight: 800,
          color: hero ? accent : DIM,
          letterSpacing: 2,
          marginBottom: 20,
          textAlign: 'center',
        }}
      >
        {title}
      </div>
    ) : null}
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {items.map((t, i) => (
        <div
          key={i}
          style={{
            display: 'flex',
            gap: 12,
            alignItems: 'flex-start',
            opacity: hero ? fade(local, 18 + i * 5) : fade(local, 8 + i * 5),
            transform: `translateX(${interpolate(
              fade(local, (hero ? 18 : 8) + i * 5),
              [0, 1],
              [hero ? 14 : -14, 0],
            )}px)`,
          }}
        >
          <div
            style={{
              width: 9,
              height: 9,
              borderRadius: 2,
              marginTop: 9,
              flexShrink: 0,
              background: hero ? accent : 'rgba(255,255,255,0.34)',
            }}
          />
          <div
            style={{
              fontFamily: FONT,
              fontSize: 20,
              fontWeight: 500,
              color: hero ? HI : MID,
              lineHeight: 1.5,
            }}
          >
            {t}
          </div>
        </div>
      ))}
    </div>
  </div>
);

const CompareBody: React.FC<{ card: ContentCard; accent: string; local: number }> = ({
  card,
  accent,
  local,
}) => {
  const { fps } = useVideoConfig();
  return (
    <div>
      <div style={{ position: 'relative', display: 'flex', gap: 56, alignItems: 'stretch' }}>
        <ComparePanel
          title={card.leftTitle}
          items={card.left || []}
          accent={accent}
          local={local}
          fps={fps}
        />
        <ComparePanel
          title={card.rightTitle}
          items={card.right || []}
          accent={accent}
          hero
          local={local}
          fps={fps}
        />
        <div
          style={{
            position: 'absolute',
            left: '50%',
            top: '50%',
            transform: 'translate(-50%, -50%)',
            width: 54,
            height: 54,
            borderRadius: '50%',
            background: '#0B0E14',
            border: `1px solid ${accent}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontFamily: FONT,
            fontSize: 17,
            fontWeight: 800,
            color: accent,
            letterSpacing: 1,
            opacity: fade(local, 22, 12),
          }}
        >
          VS
        </div>
      </div>
      <Note text={card.note} accent={accent} local={local} />
    </div>
  );
};

// ============================================================
// 5/6. split（分解）与 integrate（集成）
// 几何相同、方向相反，共用一个连接件渲染器
// ============================================================

const TREE_W = 1120;
const TREE_PARENT_W = 470;
const TREE_GAP = 34;
const TREE_DROP = 28;
const TREE_CHILD_H = 96;

const TreeConnector: React.FC<{
  n: number;
  /** SVG 局部坐标系：子节点顶边（同时作为 SVG 高度） */
  childTop: number;
  /** SVG 局部坐标系：总线位置 */
  busY: number;
  upward: boolean;
  accent: string;
  local: number;
}> = ({ n, childTop, busY, upward, accent, local }) => {
  const childW = (TREE_W - (n - 1) * 16) / n;
  const centers = Array.from({ length: n }, (_, i) => i * (childW + 16) + childW / 2);
  const cx = TREE_W / 2;
  const busLen = Math.max(1, centers[n - 1] - centers[0]);
  // 汇聚（integrate）时线往上走进结果框，箭头朝上；分解（split）时往下走，箭头朝下
  const headY = upward ? 8 : busY - 8;
  const headDir = upward ? -1 : 1;
  return (
    <svg width={TREE_W} height={childTop} style={{ display: 'block', overflow: 'visible' }}>
      {/* 中轴竖线：父节点下沿 ↔ 总线 */}
      <line
        x1={cx}
        y1={0}
        x2={cx}
        y2={busY}
        stroke={accent}
        strokeWidth="2"
        strokeDasharray={busY}
        strokeDashoffset={busY * draw(local, 6, 12)}
      />
      {/* 方向箭头 */}
      <path
        d={`M${cx - 6} ${headY - 6 * headDir} L${cx} ${headY} L${cx + 6} ${headY - 6 * headDir}`}
        stroke={accent}
        strokeWidth="2"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity={1 - draw(local, 14, 10)}
      />
      {/* 总线 */}
      <line
        x1={centers[0]}
        y1={busY}
        x2={centers[n - 1]}
        y2={busY}
        stroke={LINE}
        strokeWidth="2"
        strokeDasharray={busLen}
        strokeDashoffset={busLen * draw(local, 12, 14)}
      />
      {/* 各分支 */}
      {centers.map((x, i) => (
        <line
          key={i}
          x1={x}
          y1={busY}
          x2={x}
          y2={childTop}
          stroke={LINE}
          strokeWidth="2"
          strokeDasharray={TREE_DROP}
          strokeDashoffset={TREE_DROP * draw(local, 18 + i * 4, 12)}
        />
      ))}
    </svg>
  );
};

const SplitBody: React.FC<{ card: ContentCard; accent: string; local: number }> = ({
  card,
  accent,
  local,
}) => {
  const { fps } = useVideoConfig();
  const items = card.items || [];
  const n = Math.max(items.length, 1);
  const childW = (TREE_W - (n - 1) * 16) / n;
  const parentTop = 0;
  const busY = parentTop + 62 + TREE_GAP;
  const childTop = busY + TREE_DROP;

  return (
    <div>
      <div style={{ position: 'relative', width: TREE_W, margin: '0 auto' }}>
        {/* 父节点 */}
        <Box
          style={{
            position: 'absolute',
            left: (TREE_W - TREE_PARENT_W) / 2,
            top: parentTop,
            width: TREE_PARENT_W,
            height: 62,
            fontSize: 24,
            fontWeight: 800,
            background: PANEL_STRONG,
            borderLeft: `4px solid ${accent}`,
            ...rise(local, fps, 0),
          }}
        >
          {card.center}
        </Box>

        <div style={{ position: 'absolute', left: 0, top: 62 }}>
          <TreeConnector
            n={n}
            childTop={childTop - 62}
            busY={busY - 62}
            upward={false}
            accent={accent}
            local={local}
          />
        </div>

        {/* 子节点 */}
        {items.map((t, i) => (
          <Box
            key={i}
            style={{
              position: 'absolute',
              left: i * (childW + 16),
              top: childTop,
              width: childW,
              height: TREE_CHILD_H,
              fontSize: 19,
              padding: '0 14px',
              ...rise(local, fps, 26 + i * 4),
            }}
          >
            {t}
          </Box>
        ))}
        <div style={{ height: childTop + TREE_CHILD_H }} />
      </div>
      <Note text={card.note} accent={accent} local={local} />
    </div>
  );
};

const FitBody: React.FC<{ card: ContentCard; accent: string; local: number }> = ({
  card,
  accent,
  local,
}) => {
  const { fps } = useVideoConfig();
  const items = card.inputs || [];
  const n = Math.max(items.length, 1);
  const childW = (TREE_W - (n - 1) * 16) / n;
  const busY = 62 + TREE_GAP;
  const childTop = busY + TREE_DROP;

  return (
    <div>
      <div style={{ position: 'relative', width: TREE_W, margin: '0 auto' }}>
        <Box
          style={{
            position: 'absolute',
            left: (TREE_W - 620) / 2,
            top: 0,
            width: 620,
            height: 68,
            fontSize: 24,
            fontWeight: 800,
            background: `${accent}1A`,
            border: `1px solid ${accent}`,
            ...rise(local, fps, 26),
          }}
        >
          {card.output}
        </Box>

        <div style={{ position: 'absolute', left: 0, top: 68 }}>
          <TreeConnector
            n={n}
            childTop={childTop - 68}
            busY={busY - 68}
            upward
            accent={accent}
            local={local}
          />
        </div>

        {items.map((t, i) => (
          <Box
            key={i}
            style={{
              position: 'absolute',
              left: i * (childW + 16),
              top: childTop,
              width: childW,
              height: TREE_CHILD_H,
              fontSize: 19,
              padding: '0 14px',
              ...rise(local, fps, i * 5),
            }}
          >
            {t}
          </Box>
        ))}
        <div style={{ height: childTop + TREE_CHILD_H }} />
      </div>
      <Note text={card.note} accent={accent} local={local} />
    </div>
  );
};

// ============================================================
// 7. pyramid —— 层次：自下而上的能力层级
// ============================================================

const PY_W = 1120;
const PY_H = 86;
const PY_GAP = 8;

const PyramidBody: React.FC<{ card: ContentCard; accent: string; local: number }> = ({
  card,
  accent,
  local,
}) => {
  const { fps } = useVideoConfig();
  const items = card.items || [];
  const n = Math.max(items.length, 1);
  const widths = Array.from({ length: n + 1 }, (_, i) => PY_W * (1 - (0.16 * i) / 1));
  const total = n * PY_H + (n - 1) * PY_GAP;

  return (
    <div>
      <div style={{ position: 'relative', width: PY_W, height: total, margin: '0 auto' }}>
        {items.map((t, k) => {
          // k = 0 为最底层
          const topY = total - (k + 1) * PY_H - k * PY_GAP;
          const wb = widths[k];
          const wt = widths[k + 1];
          const top = items.length - 1 === k;
          return (
            <div
              key={k}
              style={{
                position: 'absolute',
                left: 0,
                top: topY,
                width: PY_W,
                height: PY_H,
                opacity: fade(local, k * 8, 12),
                transform: `scaleY(${interpolate(
                  fade(local, k * 8, 12),
                  [0, 1],
                  [0.6, 1],
                )})`,
                transformOrigin: 'bottom',
              }}
            >
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  background: top ? `${accent}22` : PANEL,
                  border: top ? `1px solid ${accent}` : BORDER,
                  clipPath: `polygon(${(PY_W - wb) / 2}px ${PY_H}px, ${
                    (PY_W + wb) / 2
                  }px ${PY_H}px, ${(PY_W + wt) / 2}px 0px, ${(PY_W - wt) / 2}px 0px)`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <div
                  style={{
                    fontFamily: FONT,
                    fontSize: top ? 25 : 23,
                    fontWeight: 700,
                    color: top ? accent : HI,
                    letterSpacing: 1,
                  }}
                >
                  {t}
                </div>
              </div>
            </div>
          );
        })}
      </div>
      <Note text={card.note} accent={accent} local={local} />
    </div>
  );
};

// ============================================================
// 8. relation —— 关系：中心节点 + 周边要素
// ============================================================

const REL_W = 1120;
const REL_H = 320;
const REL_CX = REL_W / 2;
const REL_CY = REL_H / 2;
const REL_CENTER_W = 380;
const REL_CENTER_H = 104;
const SAT_W = 248;
const SAT_H = 64;

const RelationBody: React.FC<{ card: ContentCard; accent: string; local: number }> = ({
  card,
  accent,
  local,
}) => {
  const { fps } = useVideoConfig();
  const items = card.items || [];
  const slots = [
    { left: 6, top: 26 },
    { left: REL_W - SAT_W - 6, top: 26 },
    { left: 6, top: REL_H - SAT_H - 26 },
    { left: REL_W - SAT_W - 6, top: REL_H - SAT_H - 26 },
  ];
  const centerBox = {
    left: (REL_W - REL_CENTER_W) / 2,
    top: (REL_CY - REL_CENTER_H / 2),
  };
  const anchors = slots.map((s) => ({
    x: s.left < REL_CX ? s.left + SAT_W : s.left,
    y: s.top + SAT_H / 2,
  }));
  const targets = slots.map((s) => ({
    x: s.left < REL_CX ? centerBox.left + 10 : centerBox.left + REL_CENTER_W - 10,
    y: s.top < REL_CY ? centerBox.top + 16 : centerBox.top + REL_CENTER_H - 16,
  }));

  return (
    <div>
      <div style={{ position: 'relative', width: REL_W, height: REL_H, margin: '0 auto' }}>
        <svg
          width={REL_W}
          height={REL_H}
          style={{ position: 'absolute', left: 0, top: 0, overflow: 'visible' }}
        >
          {anchors.map((a, i) => {
            const t = targets[i];
            const mx = (a.x + t.x) / 2;
            const my = (a.y + t.y) / 2 + (a.y < REL_CY ? 14 : -14);
            return (
              <path
                key={i}
                d={`M${a.x} ${a.y} Q${mx} ${my} ${t.x} ${t.y}`}
                stroke={LINE}
                strokeWidth="2"
                fill="none"
                pathLength={1}
                strokeDasharray={1}
                strokeDashoffset={draw(local, 12 + i * 5, 16)}
              />
            );
          })}
        </svg>

        {/* 中心节点 */}
        <Box
          style={{
            position: 'absolute',
            left: centerBox.left,
            top: centerBox.top,
            width: REL_CENTER_W,
            height: REL_CENTER_H,
            fontSize: 26,
            fontWeight: 800,
            background: `${accent}1A`,
            border: `1px solid ${accent}`,
            ...rise(local, fps, 0),
          }}
        >
          {card.center}
        </Box>

        {/* 周边要素 */}
        {items.slice(0, 4).map((t, i) => (
          <Box
            key={i}
            style={{
              position: 'absolute',
              left: slots[i].left,
              top: slots[i].top,
              width: SAT_W,
              height: SAT_H,
              fontSize: 19,
              padding: '0 14px',
              ...rise(local, fps, 24 + i * 5),
            }}
          >
            {t}
          </Box>
        ))}
      </div>
      <Note text={card.note} accent={accent} local={local} />
    </div>
  );
};

// ============================================================
// 文本型：bullets / stat / quote
// ============================================================

const BulletsBody: React.FC<{ card: ContentCard; accent: string; brand: string; local: number }> = ({
  card,
  accent,
  brand,
  local,
}) => {
  const { fps } = useVideoConfig();
  return (
    <div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 22 }}>
        {(card.items || []).map((it, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 18, ...rise(local, fps, 10 + i * 7) }}>
            <div
              style={{
                width: 12,
                height: 12,
                borderRadius: 3,
                background: i % 2 === 0 ? accent : brand,
                marginTop: 15,
                flexShrink: 0,
              }}
            />
            <div style={{ fontFamily: FONT, fontSize: 34, fontWeight: 500, color: HI, lineHeight: 1.5 }}>
              {it}
            </div>
          </div>
        ))}
      </div>
      <Note text={card.note} accent={accent} local={local} />
    </div>
  );
};

const StatBody: React.FC<{ card: ContentCard; accent: string; local: number }> = ({
  card,
  accent,
  local,
}) => (
  <div style={{ display: 'flex', alignItems: 'baseline', gap: 16, opacity: fade(local, 6, 14) }}>
    <div
      style={{
        fontFamily: FONT,
        fontSize: 130,
        fontWeight: 800,
        color: accent,
        lineHeight: 1,
        letterSpacing: -2,
      }}
    >
      {card.value}
    </div>
    {card.unit ? (
      <div style={{ fontFamily: FONT, fontSize: 34, color: DIM, fontWeight: 600 }}>{card.unit}</div>
    ) : null}
    {card.note ? (
      <div style={{ fontFamily: FONT, fontSize: 24, color: DIM, marginLeft: 18 }}>{card.note}</div>
    ) : null}
  </div>
);

const QuoteBody: React.FC<{ card: ContentCard; local: number }> = ({ card, local }) => (
  <div
    style={{
      fontFamily: FONT,
      fontSize: 40,
      fontWeight: 600,
      color: HI,
      lineHeight: 1.6,
      letterSpacing: 1,
      opacity: fade(local, 6, 14),
    }}
  >
    “{card.note}”
  </div>
);

// ============================================================
// 分发
// ============================================================

// 图解型统一给一个最小高度并垂直居中，避免不同结构的卡片高度忽高忽低
const DIAGRAM_MIN_H = 344;

export const CardBody: React.FC<{
  card: ContentCard;
  accent: string;
  brand: string;
  local: number;
}> = ({ card, accent, brand, local }) => {
  const inner = (() => {
    switch (card.kind) {
      case 'flow':
        return <FlowBody card={card} accent={accent} local={local} />;
      case 'quad':
        return <QuadBody card={card} accent={accent} local={local} />;
      case 'map':
        return <MapBody card={card} accent={accent} local={local} />;
      case 'compare':
        return <CompareBody card={card} accent={accent} local={local} />;
      case 'split':
        return <SplitBody card={card} accent={accent} local={local} />;
      case 'integrate':
        return <FitBody card={card} accent={accent} local={local} />;
      case 'pyramid':
        return <PyramidBody card={card} accent={accent} local={local} />;
      case 'relation':
        return <RelationBody card={card} accent={accent} local={local} />;
      case 'stat':
        return <StatBody card={card} accent={accent} local={local} />;
      case 'quote':
        return <QuoteBody card={card} local={local} />;
      case 'bullets':
      default:
        return <BulletsBody card={card} accent={accent} brand={brand} local={local} />;
    }
  })();

  const isDiagram =
    card.kind !== 'bullets' && card.kind !== 'stat' && card.kind !== 'quote';
  if (!isDiagram) return inner;

  return (
    <div
      style={{
        minHeight: DIAGRAM_MIN_H,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
      }}
    >
      {inner}
    </div>
  );
};
