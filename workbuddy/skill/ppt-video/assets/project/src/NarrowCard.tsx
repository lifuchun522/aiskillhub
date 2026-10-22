import React from 'react';
import { interpolate, spring, useVideoConfig } from 'remotion';
import { ContentCard } from './types';

// ============================================================
// 窄栏内容卡（左栏专用，设计宽度 780）
// 与 CardBody 的区别：CardBody 按 1320 宽横幅设计，这里按 780 竖窄栏重新标定字号，
// 结构图一律改成「竖排」走向——窄栏里横向排 4 个方框会被压成一条线。
// ============================================================

const FONT = '"Microsoft YaHei", "PingFang SC", "Noto Sans SC", "Source Han Sans SC", sans-serif';
const HI = 'rgba(255,255,255,0.95)';
const MID = 'rgba(255,255,255,0.70)';
const DIM = 'rgba(255,255,255,0.48)';
const PANEL = 'rgba(255,255,255,0.055)';
const PANEL_STRONG = 'rgba(255,255,255,0.09)';
const BORDER = '1px solid rgba(255,255,255,0.11)';
const LINE = 'rgba(255,255,255,0.28)';

export const NW = 728; // 窄栏内容宽度（左面板 800 − 左右 padding 36）

const rise = (local: number, fps: number, delay = 0, distance = 16) => {
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
      borderRadius: 11,
      padding: '14px 18px',
      fontFamily: FONT,
      fontSize: 22,
      fontWeight: 600,
      color: HI,
      lineHeight: 1.38,
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

const Note: React.FC<{
  text?: string;
  accent: string;
  local: number;
  /** 居中构图（金字塔 / 关系图）的注释要跟着居中，不然会孤零零挂在左下角 */
  center?: boolean;
}> = ({ text, accent, local, center }) => {
  if (!text) return null;
  return (
    <div
      style={{
        marginTop: 24,
        display: 'flex',
        alignItems: 'center',
        justifyContent: center ? 'center' : 'flex-start',
        gap: 11,
        opacity: fade(local, 26, 14),
      }}
    >
      <div style={{ width: 22, height: 2, background: accent, flexShrink: 0 }} />
      <div style={{ fontFamily: FONT, fontSize: 19, color: MID, letterSpacing: 0.6 }}>{text}</div>
    </div>
  );
};

// 竖排箭头（窄栏里的方向指示）
const DownArrow: React.FC<{ local: number; delay: number; accent: string; h?: number }> = ({
  local,
  delay,
  accent,
  h = 26,
}) => (
  <div
    style={{
      height: h,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      opacity: fade(local, delay, 8),
      flexShrink: 0,
    }}
  >
    <svg width="18" height={h} viewBox={`0 0 18 ${h}`}>
      <path
        d={`M9 1 V${h - 8}`}
        stroke={accent}
        strokeWidth="2"
        fill="none"
        strokeLinecap="round"
        strokeDasharray={h}
        strokeDashoffset={h * draw(local, delay, 10)}
      />
      <path
        d={`M4 ${h - 12} L9 ${h - 5} L14 ${h - 12}`}
        stroke={accent}
        strokeWidth="2"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity={1 - draw(local, delay + 6, 8)}
      />
    </svg>
  </div>
);

// ============================================================
// flow —— 竖排步骤链
// ============================================================

const FlowNarrow: React.FC<{ card: ContentCard; accent: string; local: number }> = ({
  card,
  accent,
  local,
}) => {
  const { fps } = useVideoConfig();
  const items = card.items || [];
  const last = items.length - 1;
  return (
    <div>
      {items.map((t, i) => (
        <React.Fragment key={i}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 16,
              background: i === last ? `${accent}16` : PANEL,
              border: i === last ? `1px solid ${accent}` : BORDER,
              borderRadius: 11,
              padding: '18px 20px',
              minHeight: 78,
              ...rise(local, fps, i * 6),
            }}
          >
            <div
              style={{
                fontFamily: FONT,
                fontSize: 16,
                fontWeight: 800,
                color: i === last ? accent : DIM,
                letterSpacing: 1,
                flexShrink: 0,
                width: 26,
              }}
            >
              {String(i + 1).padStart(2, '0')}
            </div>
            <div
              style={{
                fontFamily: FONT,
                fontSize: 23,
                fontWeight: i === last ? 700 : 600,
                color: i === last ? '#FFFFFF' : HI,
                lineHeight: 1.4,
              }}
            >
              {t}
            </div>
          </div>
          {i < items.length - 1 ? (
            <DownArrow local={local} delay={i * 6 + 4} accent={`${accent}CC`} />
          ) : null}
        </React.Fragment>
      ))}
      <Note text={card.note} accent={accent} local={local} />
    </div>
  );
};

// ============================================================
// quad —— 2×2 分解
// ============================================================

const QuadNarrow: React.FC<{ card: ContentCard; accent: string; local: number }> = ({
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
              borderRadius: 11,
              padding: '20px 18px',
              minHeight: 160,
              display: 'flex',
              flexDirection: 'column',
              gap: 10,
              ...rise(local, fps, i * 6),
            }}
          >
            <div
              style={{
                fontFamily: FONT,
                fontSize: 30,
                fontWeight: 800,
                color: `${accent}`,
                lineHeight: 1,
                letterSpacing: -1,
                opacity: 0.9,
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
// compare —— 上下两栏对照（窄栏竖排比左右并列更易读）
// ============================================================

const CompareNarrow: React.FC<{ card: ContentCard; accent: string; local: number }> = ({
  card,
  accent,
  local,
}) => {
  const { fps } = useVideoConfig();
  const panel = (
    title: string | undefined,
    items: string[],
    hero: boolean,
    delay: number,
  ) => (
    <div
      style={{
        flex: 1,
        background: hero ? `${accent}12` : PANEL,
        border: hero ? `1px solid ${accent}` : BORDER,
        borderRadius: 12,
        padding: '22px 22px',
        ...rise(local, fps, delay, 14),
      }}
    >
      {title ? (
        <div
          style={{
            fontFamily: FONT,
            fontSize: 24,
            fontWeight: 800,
            color: hero ? accent : MID,
            letterSpacing: 1.5,
            marginBottom: 12,
          }}
        >
          {title}
        </div>
      ) : null}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
        {items.map((t, i) => (
          <div
            key={i}
            style={{
              display: 'flex',
              gap: 11,
              alignItems: 'flex-start',
              opacity: fade(local, delay + 8 + i * 4),
            }}
          >
            <div
              style={{
                width: 8,
                height: 8,
                borderRadius: 2,
                marginTop: 9,
                flexShrink: 0,
                background: hero ? accent : 'rgba(255,255,255,0.32)',
              }}
            />
            <div
              style={{
                fontFamily: FONT,
                fontSize: 20,
                fontWeight: hero ? 600 : 500,
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

  return (
    <div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {panel(card.leftTitle, card.left || [], false, 0)}
        {panel(card.rightTitle, card.right || [], true, 14)}
      </div>
      <Note text={card.note} accent={accent} local={local} />
    </div>
  );
};

// ============================================================
// map —— 左项逐行映射到右项（窄栏两列 + 箭头）
// ============================================================

const MAP_NARROW_ROW = 68;
const MAP_NARROW_GAP = 8;

const MapNarrow: React.FC<{ card: ContentCard; accent: string; local: number }> = ({
  card,
  accent,
  local,
}) => {
  const { fps } = useVideoConfig();
  const left = card.left || [];
  const right = card.right || [];
  const rows = Math.max(left.length, right.length);
  const colW = (NW - 56) / 2;
  return (
    <div>
      <div style={{ display: 'flex', gap: 12, marginBottom: 8 }}>
        <div
          style={{
            width: colW,
            fontFamily: FONT,
            fontSize: 16,
            fontWeight: 700,
            color: DIM,
            letterSpacing: 2,
            opacity: fade(local, 0, 10),
          }}
        >
          {card.leftTitle}
        </div>
        <div style={{ width: 32 }} />
        <div
          style={{
            width: colW,
            fontFamily: FONT,
            fontSize: 16,
            fontWeight: 700,
            color: accent,
            letterSpacing: 2,
            opacity: fade(local, 4, 10),
          }}
        >
          {card.rightTitle}
        </div>
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 0,
            marginBottom: MAP_NARROW_GAP,
          }}
        >
          <Box
            style={{
              width: colW,
              height: MAP_NARROW_ROW,
              fontSize: 19,
              padding: '0 12px',
              ...rise(local, fps, i * 5, 12),
            }}
          >
            {left[i]}
          </Box>
          <div
            style={{
              width: 32,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              opacity: fade(local, 10 + i * 5, 9),
            }}
          >
            <svg width="20" height="20" viewBox="0 0 20 20">
              <path
                d="M2 10h13M10 5l5 5-5 5"
                stroke={accent}
                strokeWidth="2"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <Box
            style={{
              width: colW,
              height: MAP_NARROW_ROW,
              fontSize: 19,
              padding: '0 12px',
              background: `${accent}14`,
              border: `1px solid ${accent}`,
              color: '#FFFFFF',
              ...rise(local, fps, 14 + i * 5, 12),
            }}
          >
            {right[i]}
          </Box>
        </div>
      ))}
      <Note text={card.note} accent={accent} local={local} />
    </div>
  );
};

// ============================================================
// split / integrate —— 父节点 + 竖排子项（共用）
// ============================================================

const SplitNarrow: React.FC<{ card: ContentCard; accent: string; local: number }> = ({
  card,
  accent,
  local,
}) => {
  const { fps } = useVideoConfig();
  const items = card.items || [];
  return (
    <div>
      <Box
        style={{
          minHeight: 72,
          fontSize: 23,
          fontWeight: 800,
          background: PANEL_STRONG,
          borderLeft: `4px solid ${accent}`,
          justifyContent: 'flex-start',
          padding: '12px 18px',
          ...rise(local, fps, 0),
        }}
      >
        {card.center}
      </Box>
      <DownArrow local={local} delay={6} accent={accent} h={30} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {items.map((t, i) => (
          <Box
            key={i}
            style={{
              minHeight: 66,
              fontSize: 20,
              justifyContent: 'flex-start',
              padding: '12px 18px',
              ...rise(local, fps, 12 + i * 5, 12),
            }}
          >
            <span style={{ color: accent, fontWeight: 800, marginRight: 12, fontSize: 16 }}>
              {String(i + 1).padStart(2, '0')}
            </span>
            {t}
          </Box>
        ))}
      </div>
      <Note text={card.note} accent={accent} local={local} />
    </div>
  );
};

const IntegrateNarrow: React.FC<{ card: ContentCard; accent: string; local: number }> = ({
  card,
  accent,
  local,
}) => {
  const { fps } = useVideoConfig();
  const items = card.inputs || [];
  return (
    <div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {items.map((t, i) => (
          <Box
            key={i}
            style={{ minHeight: 62, fontSize: 20, ...rise(local, fps, i * 5, 12) }}
          >
            {t}
          </Box>
        ))}
      </div>
      <DownArrow local={local} delay={18} accent={accent} h={30} />
      <Box
        style={{
          minHeight: 78,
          fontSize: 24,
          fontWeight: 800,
          background: `${accent}1C`,
          border: `1px solid ${accent}`,
          ...rise(local, fps, 26),
        }}
      >
        {card.output}
      </Box>
      <Note text={card.note} accent={accent} local={local} />
    </div>
  );
};

// ============================================================
// pyramid —— 自下而上的层级（窄栏梯形）
// ============================================================

const PY_NARROW_H = 76;
const PY_NARROW_GAP = 7;

const PyramidNarrow: React.FC<{ card: ContentCard; accent: string; local: number }> = ({
  card,
  accent,
  local,
}) => {
  const { fps } = useVideoConfig();
  const items = card.items || [];
  const n = Math.max(items.length, 1);
  const total = n * PY_NARROW_H + (n - 1) * PY_NARROW_GAP;
  // k=0 是最底层 → 最宽；越往上越窄（原来按 0.46+0.54k/n 写，等于把梯形翻过来了）
  const wAt = (k: number) => NW * 0.96 * (1 - (0.54 * k) / Math.max(1, n));
  return (
    <div>
      <div style={{ position: 'relative', width: NW, height: total }}>
        {items.map((t, k) => {
          const topY = total - (k + 1) * PY_NARROW_H - k * PY_NARROW_GAP;
          const wb = wAt(k);
          const wt = wAt(k + 1);
          const isTop = n - 1 === k;
          return (
            <div
              key={k}
              style={{
                position: 'absolute',
                left: 0,
                top: topY,
                width: NW,
                height: PY_NARROW_H,
                opacity: fade(local, k * 7, 12),
                transform: `scaleY(${interpolate(fade(local, k * 7, 12), [0, 1], [0.7, 1])})`,
                transformOrigin: 'bottom',
              }}
            >
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  background: isTop ? `${accent}22` : PANEL,
                  border: isTop ? `1px solid ${accent}` : BORDER,
                  clipPath: `polygon(${(NW - wb) / 2}px ${PY_NARROW_H}px, ${
                    (NW + wb) / 2
                  }px ${PY_NARROW_H}px, ${(NW + wt) / 2}px 0px, ${(NW - wt) / 2}px 0px)`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <div
                  style={{
                    fontFamily: FONT,
                    fontSize: isTop ? 23 : 22,
                    fontWeight: 700,
                    color: isTop ? accent : HI,
                    letterSpacing: 0.8,
                  }}
                >
                  {t}
                </div>
              </div>
            </div>
          );
        })}
      </div>
      <Note text={card.note} accent={accent} local={local} center />
    </div>
  );
};

// ============================================================
// relation —— 中心节点 + 周边要素（窄栏：中心在上，周边 2×2）
// ============================================================

const RelationNarrow: React.FC<{ card: ContentCard; accent: string; local: number }> = ({
  card,
  accent,
  local,
}) => {
  const { fps } = useVideoConfig();
  const items = (card.items || []).slice(0, 4);
  const CENTER_W = 420;
  const SAT_W = (NW - 14) / 2;
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'center' }}>
        <Box
          style={{
            width: CENTER_W,
            minHeight: 86,
            fontSize: 25,
            fontWeight: 800,
            background: `${accent}1A`,
            border: `1px solid ${accent}`,
            ...rise(local, fps, 0),
          }}
        >
          {card.center}
        </Box>
      </div>
      <svg width={NW} height={34} style={{ display: 'block', overflow: 'visible' }}>
        <path
          d={`M${NW / 2} 0 V10`}
          stroke={LINE}
          strokeWidth="2"
          strokeDasharray={10}
          strokeDashoffset={10 * draw(local, 8, 8)}
        />
        <path
          d={`M${SAT_W / 2} 10 H${NW - SAT_W / 2}`}
          stroke={LINE}
          strokeWidth="2"
          strokeDasharray={NW - SAT_W}
          strokeDashoffset={(NW - SAT_W) * draw(local, 12, 12)}
        />
        {[0, 1].map((j) => (
          <path
            key={j}
            d={`M${SAT_W / 2 + j * SAT_W} 10 V30`}
            stroke={LINE}
            strokeWidth="2"
            strokeDasharray={20}
            strokeDashoffset={20 * draw(local, 18 + j * 3, 8)}
          />
        ))}
      </svg>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
        {items.map((t, i) => (
          <Box
            key={i}
            style={{
              minHeight: 76,
              fontSize: 20,
              padding: '12px 12px',
              ...rise(local, fps, 22 + i * 5, 12),
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

const BulletsNarrow: React.FC<{ card: ContentCard; accent: string; brand: string; local: number }> =
  ({ card, accent, brand, local }) => {
    const { fps } = useVideoConfig();
    return (
      <div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {(card.items || []).map((it, i) => (
            <div
              key={i}
              style={{ display: 'flex', alignItems: 'flex-start', gap: 18, ...rise(local, fps, 8 + i * 6) }}
            >
              <div
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: 3,
                  background: i % 2 === 0 ? accent : brand,
                  marginTop: 12,
                  flexShrink: 0,
                }}
              />
              <div style={{ fontFamily: FONT, fontSize: 27, fontWeight: 500, color: HI, lineHeight: 1.5 }}>
                {it}
              </div>
            </div>
          ))}
        </div>
        <Note text={card.note} accent={accent} local={local} />
      </div>
    );
  };

const StatNarrow: React.FC<{ card: ContentCard; accent: string; local: number }> = ({
  card,
  accent,
  local,
}) => (
  <div style={{ opacity: fade(local, 6, 14) }}>
    <div style={{ display: 'flex', alignItems: 'baseline', gap: 12 }}>
      <div
        style={{
          fontFamily: FONT,
          fontSize: 110,
          fontWeight: 800,
          color: accent,
          lineHeight: 1,
          letterSpacing: -2,
        }}
      >
        {card.value}
      </div>
      {card.unit ? (
        <div style={{ fontFamily: FONT, fontSize: 28, color: DIM, fontWeight: 600 }}>{card.unit}</div>
      ) : null}
    </div>
    {card.note ? (
      <div style={{ fontFamily: FONT, fontSize: 20, color: DIM, marginTop: 14, lineHeight: 1.5 }}>
        {card.note}
      </div>
    ) : null}
  </div>
);

const QuoteNarrow: React.FC<{ card: ContentCard; accent: string; local: number }> = ({
  card,
  accent,
  local,
}) => (
  <div style={{ opacity: fade(local, 6, 14), display: 'flex', gap: 20 }}>
    {/* 左侧引用条：让这块「金句板」有引用块的身份，而不是两行浮字 */}
    <div
      style={{
        width: 4,
        flexShrink: 0,
        background: `linear-gradient(180deg, ${accent} 0%, ${accent}55 100%)`,
        borderRadius: 2,
      }}
    />
    <div
      style={{
        fontFamily: FONT,
        fontSize: 40,
        fontWeight: 700,
        color: HI,
        lineHeight: 1.6,
        letterSpacing: 0.5,
        whiteSpace: 'pre-line',
      }}
    >
      {card.note}
    </div>
  </div>
);

// ============================================================
// 分发
// ============================================================

export const NarrowCard: React.FC<{
  card: ContentCard;
  accent: string;
  brand: string;
  local: number;
}> = ({ card, accent, brand, local }) => {
  switch (card.kind) {
    case 'flow':
      return <FlowNarrow card={card} accent={accent} local={local} />;
    case 'quad':
      return <QuadNarrow card={card} accent={accent} local={local} />;
    case 'map':
      return <MapNarrow card={card} accent={accent} local={local} />;
    case 'compare':
      return <CompareNarrow card={card} accent={accent} local={local} />;
    case 'split':
      return <SplitNarrow card={card} accent={accent} local={local} />;
    case 'integrate':
      return <IntegrateNarrow card={card} accent={accent} local={local} />;
    case 'pyramid':
      return <PyramidNarrow card={card} accent={accent} local={local} />;
    case 'relation':
      return <RelationNarrow card={card} accent={accent} local={local} />;
    case 'stat':
      return <StatNarrow card={card} accent={accent} local={local} />;
    case 'quote':
      return <QuoteNarrow card={card} accent={accent} local={local} />;
    case 'bullets':
    default:
      return <BulletsNarrow card={card} accent={accent} brand={brand} local={local} />;
  }
};
