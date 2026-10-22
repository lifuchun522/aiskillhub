import React from 'react';
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import { NarrowCard, NW } from './NarrowCard';
import { ContentCard, SlidePage } from './types';

// ============================================================
// 分屏版式：左「结构化逻辑图」+ 右「PPT 原页」
//
// 为什么单独做一套而不是复用 CardView：
// CardView 是整幅 1320 宽的中置卡，塞进 780 窄栏后字号会被压到 15px 以下，
// 在 1080p 里基本读不了。所以左栏用 NarrowCard（按 780 重标定、结构图改竖排）。
// ============================================================

const FONT = '"Microsoft YaHei", "PingFang SC", "Noto Sans SC", "Source Han Sans SC", sans-serif';
const TEXT = '#FFFFFF';
const TEXT_DIM = 'rgba(255,255,255,0.60)';

export const LEFT_X = 48;
export const LEFT_W = NW + 72; // 内宽 728 + 左右 padding 36
export const RIGHT_X = 920;
export const RIGHT_W = 940;
const RIGHT_H = (RIGHT_W * 9) / 16; // 528.75
const STAGE_TOP = 128;
const STAGE_BOTTOM = 934;
const STAGE_H = STAGE_BOTTOM - STAGE_TOP; // 806
const PPT_TOP = STAGE_TOP + (STAGE_H - RIGHT_H) / 2 - 22; // 上方留出页码条空间后轻微上移

const findActive = (starts: number[], t: number): number => {
  let lo = 0;
  let hi = starts.length - 1;
  let ans = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (starts[mid] <= t) {
      ans = mid;
      lo = mid + 1;
    } else {
      hi = mid - 1;
    }
  }
  return ans;
};

const fadeOut = (local: number, dur: number, len = 14) =>
  interpolate(local, [Math.max(0, dur - len), dur], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

// ============================================================
// 右栏：PPT 页（带交叉淡化、页码徽标、页进度点）
// ============================================================

const PptFrame: React.FC<{
  src: string;
  opacity: number;
  offsetY: number;
}> = ({ src, opacity, offsetY }) => (
  <div
    style={{
      position: 'absolute',
      left: 0,
      top: 0,
      width: RIGHT_W,
      height: RIGHT_H,
      opacity,
      transform: `translateY(${offsetY}px)`,
      borderRadius: 14,
      overflow: 'hidden',
      boxShadow: '0 34px 90px rgba(0,0,0,0.62), 0 0 0 1px rgba(255,255,255,0.16)',
      background: '#FFFFFF',
    }}
  >
    <Img
      src={staticFile(src)}
      style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
    />
    {/* 极轻的压暗，避免纯白页在深色场景里刺眼 */}
    <div
      style={{
        position: 'absolute',
        inset: 0,
        background: 'linear-gradient(180deg, rgba(0,0,0,0.05) 0%, rgba(0,0,0,0.00) 40%)',
        pointerEvents: 'none',
      }}
    />
  </div>
);

const PptIndexBar: React.FC<{
  index: number;
  total: number;
  accent: string;
  light: number;
}> = ({ index, total, accent, light }) => (
  <div
    style={{
      position: 'absolute',
      left: 0,
      top: RIGHT_H + 20,
      width: RIGHT_W,
      display: 'flex',
      alignItems: 'center',
      gap: 16,
      opacity: light,
    }}
  >
    <div
      style={{
        display: 'flex',
        alignItems: 'baseline',
        gap: 6,
        fontFamily: FONT,
        letterSpacing: 1,
      }}
    >
      <div style={{ fontSize: 26, fontWeight: 800, color: accent }}>
        {String(index).padStart(2, '0')}
      </div>
      <div style={{ fontSize: 17, fontWeight: 600, color: TEXT_DIM }}>/ {String(total).padStart(2, '0')}</div>
    </div>
    <div style={{ flex: 1, height: 2, background: 'rgba(255,255,255,0.16)' }} />
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      {Array.from({ length: total }).map((_, i) => {
        const active = i + 1 === index;
        const passed = i + 1 < index;
        return (
          <div
            key={i}
            style={{
              width: active ? 22 : 7,
              height: 7,
              borderRadius: 4,
              background: active ? accent : passed ? 'rgba(255,255,255,0.34)' : 'rgba(255,255,255,0.13)',
              transition: 'none',
            }}
          />
        );
      })}
    </div>
  </div>
);

export const PptStage: React.FC<{
  slides: SlidePage[];
  accent: string;
  fps: number;
}> = ({ slides, accent, fps }) => {
  const frame = useCurrentFrame();
  if (!slides.length) return null;
  const t = frame / fps;
  const idx = findActive(
    slides.map((s) => s.start),
    t,
  );
  if (idx < 0) return null;

  const cur = slides[idx];
  const prev = idx > 0 ? slides[idx - 1] : null;
  const local = frame - Math.round(cur.start * fps);
  const durFrames = Math.max(1, Math.round((cur.end - cur.start) * fps));
  const fadeLen = Math.min(16, Math.max(6, Math.round(durFrames * 0.06)));
  const k = interpolate(local, [0, fadeLen], [0, 1], { extrapolateRight: 'clamp' });

  return (
    <div
      style={{
        position: 'absolute',
        left: RIGHT_X,
        top: PPT_TOP,
        width: RIGHT_W,
        height: RIGHT_H + 60,
      }}
    >
      {prev ? <PptFrame src={prev.src} opacity={1 - k} offsetY={-8 * k} /> : null}
      <PptFrame src={cur.src} opacity={k} offsetY={14 * (1 - k)} />
      <PptIndexBar
        index={cur.index}
        total={slides.length}
        accent={accent}
        light={interpolate(local, [0, 12], [0.55, 1], { extrapolateRight: 'clamp' })}
      />
    </div>
  );
};

// ============================================================
// 左栏：结构化逻辑图
// ============================================================

// 左栏做成一块「逻辑板」：右侧 PPT 是一块实体白板，左侧若只是浮在网格上，
// 画面会左轻右重。给左栏一块实心面板，两侧就形成「逻辑板 / 内容板」的对偶。
// 高度不写死：按内容自适应并在舞台内垂直居中，否则 4 宫格这类内容少的卡
// 会在固定 806 高的板里留下大片死白。
const LeftPanel: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div
    style={{
      position: 'absolute',
      left: LEFT_X,
      // 与右侧 PPT 同高偏移：PPT 为了让出页码条上移了 22px，左板跟着上移才同轴
      top: STAGE_TOP - 22,
      width: LEFT_W,
      height: STAGE_H,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    }}
  >
    <div
      style={{
        width: LEFT_W,
        maxHeight: STAGE_H,
        borderRadius: 18,
        background: 'linear-gradient(168deg, #16202C 0%, #111A24 62%, #0E1620 100%)',
        border: '1px solid rgba(255,255,255,0.10)',
        boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.09), 0 26px 70px rgba(0,0,0,0.45)',
        padding: '38px 36px',
        overflow: 'hidden',
      }}
    >
      {children}
    </div>
  </div>
);

const IdleLeft: React.FC<{ title: string; accent: string; fps: number }> = ({
  title,
  accent,
  fps,
}) => {
  const frame = useCurrentFrame();
  const pulse = interpolate(Math.sin((frame / fps) * 0.7), [-1, 1], [0.06, 0.13]);
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'flex-start',
        gap: 26,
      }}
    >
      <div
        style={{
          fontFamily: FONT,
          fontSize: 50,
          fontWeight: 800,
          color: `rgba(255,255,255,${pulse})`,
          letterSpacing: 5,
          lineHeight: 1.35,
        }}
      >
        {title}
      </div>
      <div style={{ width: 150, height: 3, background: `${accent}55` }} />
    </div>
  );
};

export const LeftStage: React.FC<{
  cards: ContentCard[];
  title: string;
  accent: string;
  brand: string;
  fps: number;
}> = ({ cards, title, accent, brand, fps }) => {
  const frame = useCurrentFrame();
  const t = frame / fps;
  const idx = cards.length
    ? findActive(
        cards.map((c) => c.start),
        t,
      )
    : -1;

  const card = idx >= 0 && t <= cards[idx].end ? cards[idx] : null;

  if (!card) {
    return (
      <LeftPanel>
        <IdleLeft title={title} accent={accent} fps={fps} />
      </LeftPanel>
    );
  }

  const local = frame - Math.round(card.start * fps);
  const durFrames = Math.max(1, Math.round((card.end - card.start) * fps));
  const enterO = interpolate(local, [0, 12], [0, 1], { extrapolateRight: 'clamp' });
  const enterY = interpolate(local, [0, 12], [18, 0], { extrapolateRight: 'clamp' });
  const out = fadeOut(local, durFrames);

  return (
    <LeftPanel>
      <div style={{ opacity: enterO * out, transform: `translateY(${enterY}px)` }}>
        {card.title ? (
          <div
            style={{
              fontFamily: FONT,
              fontSize: 36,
              fontWeight: 800,
              color: TEXT,
              letterSpacing: 1.5,
              lineHeight: 1.32,
              marginBottom: 26,
              paddingLeft: 16,
              borderLeft: `4px solid ${accent}`,
            }}
          >
            {card.title}
          </div>
        ) : null}
        <NarrowCard card={card} accent={accent} brand={brand} local={local} />
      </div>
    </LeftPanel>
  );
};

// 左右分栏的分隔线，强化「一边逻辑 / 一边原页」的结构感
export const SplitDivider: React.FC<{ accent: string }> = ({ accent }) => (
  <AbsoluteFill style={{ pointerEvents: 'none' }}>
    <div
      style={{
        position: 'absolute',
        left: (LEFT_X + LEFT_W + RIGHT_X) / 2,
        top: STAGE_TOP - 10,
        width: 1,
        height: STAGE_H + 20,
        background: `linear-gradient(180deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.13) 22%, ${accent}55 50%, rgba(255,255,255,0.13) 78%, rgba(255,255,255,0) 100%)`,
      }}
    />
  </AbsoluteFill>
);
