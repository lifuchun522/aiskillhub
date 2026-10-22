import React from 'react';
import {
  AbsoluteFill,
  Audio,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import { CardBody } from './CardBody';
import { LeftStage, PptStage, SplitDivider } from './SplitLayout';
import { CaptionLine, ContentCard, KouboProps, SectionMark } from './types';

// 类型统一放在 types.ts，并在此转出，方便 Root.tsx 引用
export type { CaptionLine, ContentCard, KouboProps, SectionMark };

// ============================================================
// 基础样式常量
// ============================================================

const FONT = '"Microsoft YaHei", "PingFang SC", "Noto Sans SC", "Source Han Sans SC", sans-serif';
const BG_BASE = '#0B0E14';
const TEXT = '#FFFFFF';
const TEXT_DIM = 'rgba(255,255,255,0.62)';

// ============================================================
// 性能关键：只渲染「当前时刻命中」的那一项
// 一条 50 分钟的口播有 700+ 行字幕，若给每行都挂一个组件，
// 每帧都要协调整棵组件树，渲染会慢到不可用。
// ============================================================

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

const rise = (frame: number, fps: number, delay = 0, distance = 26) => {
  const p = spring({ frame: frame - delay, fps, config: { damping: 200, mass: 0.6 } });
  return {
    opacity: interpolate(p, [0, 1], [0, 1]),
    transform: `translateY(${interpolate(p, [0, 1], [distance, 0])}px)`,
  };
};

// ------------------------------------------------------------
// 大标题自适应字号
// 片头卡与空闲水印若把字号写死，长标题会折行并留下「孤字」：
// 「业务系统 + AI + 赋能的三个层次」会把「次」甩到第二行。
// 这里按字符宽度估算总宽，反推出能单行放下的字号。
// 1.15 是实测经验系数（纯按 1em 估算会偏小，Microsoft YaHei 粗体实际更宽）。
// ------------------------------------------------------------

const CHAR_W = (ch: string): number => {
  if (/[\u2E80-\u9FFF\uF900-\uFAFF\uFF00-\uFFEF]/.test(ch)) return 1.0;
  if (ch === ' ') return 0.32;
  if (/[A-Z0-9]/.test(ch)) return 0.68;
  if (/[a-z]/.test(ch)) return 0.58;
  if (/[+\-—·]/.test(ch)) return 0.62;
  return 0.5;
};

const fitFontSize = (
  text: string,
  maxWidth: number,
  maxSize: number,
  minSize: number,
  letterSpacing: number,
): number => {
  const chars = [...text];
  if (!chars.length) return maxSize;
  const units = chars.reduce((s, c) => s + CHAR_W(c), 0);
  const safety = 1.15;
  const usable = maxWidth - chars.length * letterSpacing * safety;
  const size = usable / (units * safety);
  return Math.max(minSize, Math.min(maxSize, Math.floor(size)));
};

// ============================================================
// 背景：深色 + 缓慢漂移的光斑，长时间观看不疲劳
// ============================================================

const Background: React.FC<{ accent: string; brand: string }> = ({ accent, brand }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const t = frame / Math.max(1, durationInFrames);

  return (
    <AbsoluteFill style={{ backgroundColor: BG_BASE }}>
      <AbsoluteFill
        style={{
          background: `linear-gradient(158deg, #0B0E14 0%, #101A26 46%, #0A1520 100%)`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          top: -260 + Math.sin(t * Math.PI * 2) * 40,
          right: -200 + Math.cos(t * Math.PI * 2) * 50,
          width: 900,
          height: 900,
          borderRadius: '50%',
          background: `radial-gradient(circle, ${brand}22 0%, transparent 68%)`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          bottom: -320 + Math.cos(t * Math.PI * 2) * 40,
          left: -240 + Math.sin(t * Math.PI * 2) * 50,
          width: 820,
          height: 820,
          borderRadius: '50%',
          background: `radial-gradient(circle, ${accent}18 0%, transparent 70%)`,
        }}
      />
      <AbsoluteFill
        style={{
          backgroundImage:
            'linear-gradient(rgba(255,255,255,0.030) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.030) 1px, transparent 1px)',
          backgroundSize: '88px 88px',
        }}
      />
    </AbsoluteFill>
  );
};

// ============================================================
// 顶部：品牌标 + 标题
// ============================================================

const HeaderBar: React.FC<{ title: string; subtitle?: string; brand: string }> = ({
  title,
  subtitle,
  brand,
}) => (
  <div
    style={{
      position: 'absolute',
      top: 56,
      left: 72,
      display: 'flex',
      alignItems: 'center',
      gap: 18,
    }}
  >
    <div style={{ width: 6, height: 44, background: brand, borderRadius: 3 }} />
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div
        style={{
          fontFamily: FONT,
          fontSize: 26,
          fontWeight: 700,
          color: 'rgba(255,255,255,0.86)',
          letterSpacing: 2,
        }}
      >
        {title}
      </div>
      {subtitle ? (
        <div style={{ fontFamily: FONT, fontSize: 17, color: TEXT_DIM, letterSpacing: 3 }}>
          {subtitle}
        </div>
      ) : null}
    </div>
  </div>
);

// ============================================================
// 章节角标：右上角，进入章节时出现，8 秒后淡出
// ============================================================

const SectionTicker: React.FC<{ sections: SectionMark[]; fps: number; accent: string }> = ({
  sections,
  fps,
  accent,
}) => {
  const frame = useCurrentFrame();
  if (!sections.length) return null;
  const idx = findActive(
    sections.map((s) => s.start),
    frame / fps,
  );
  if (idx < 0) return null;
  const local = frame - Math.round(sections[idx].start * fps);
  const opacity = interpolate(local, [0, 12, fps * 8, fps * 8 + 14], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return (
    <div
      style={{
        position: 'absolute',
        top: 60,
        right: 72,
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        opacity,
      }}
    >
      <div style={{ width: 30, height: 2, background: accent }} />
      <div
        style={{
          fontFamily: FONT,
          fontSize: 20,
          fontWeight: 700,
          color: accent,
          letterSpacing: 3,
        }}
      >
        {sections[idx].text}
      </div>
    </div>
  );
};

// ============================================================
// 中央舞台：命中内容卡就显示卡，否则显示低对比标题水印
// ============================================================

const CenterStage: React.FC<{
  cards: ContentCard[];
  title: string;
  fps: number;
  accent: string;
  brand: string;
}> = ({ cards, title, fps, accent, brand }) => {
  const frame = useCurrentFrame();
  if (!cards.length) return <IdleStage title={title} accent={accent} />;

  const t = frame / fps;
  const idx = findActive(
    cards.map((c) => c.start),
    t,
  );
  if (idx < 0 || t > cards[idx].end) return <IdleStage title={title} accent={accent} />;

  const card = cards[idx];
  const durFrames = Math.max(1, Math.round((card.end - card.start) * fps));
  const local = frame - Math.round(card.start * fps);
  return <CardView card={card} accent={accent} brand={brand} durFrames={durFrames} local={local} />;
};

const IdleStage: React.FC<{ title: string; accent: string }> = ({ title, accent }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pulse = interpolate(Math.sin((frame / fps) * 0.7), [-1, 1], [0.05, 0.1]);
  const size = fitFontSize(title, 1600, 104, 40, 10);
  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        gap: 28,
      }}
    >
      <div
        style={{
          fontFamily: FONT,
          fontSize: size,
          fontWeight: 800,
          color: `rgba(255,255,255,${pulse})`,
          letterSpacing: 10,
          textAlign: 'center',
          whiteSpace: 'nowrap',
          lineHeight: 1.25,
        }}
      >
        {title}
      </div>
      <div style={{ width: 220, height: 3, background: `${accent}55` }} />
    </div>
  );
};

const CardView: React.FC<{
  card: ContentCard;
  accent: string;
  brand: string;
  durFrames: number;
  local: number;
}> = ({ card, accent, brand, durFrames, local }) => {
  const { fps } = useVideoConfig();

  const enterO = interpolate(local, [0, 14], [0, 1], { extrapolateRight: 'clamp' });
  const enterY = interpolate(local, [0, 14], [26, 0], { extrapolateRight: 'clamp' });
  // 退场锚定卡片自身时长，而不是写死秒数
  const exitStart = Math.max(durFrames * 0.55, durFrames - 14);
  const out = interpolate(local, [exitStart, durFrames], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <div
      style={{
        position: 'absolute',
        left: '50%',
        top: 250,
        transform: `translateX(-50%) translateY(${enterY}px)`,
        width: 1320,
        opacity: enterO * out,
      }}
    >
      <div
        style={{
          background: 'rgba(255,255,255,0.045)',
          border: '1px solid rgba(255,255,255,0.10)',
          borderLeft: `5px solid ${accent}`,
          borderRadius: 18,
          padding: '48px 56px',
          boxShadow: '0 24px 80px rgba(0,0,0,0.45)',
        }}
      >
        {card.title ? (
          <div
            style={{
              fontFamily: FONT,
              fontSize: 44,
              fontWeight: 800,
              color: TEXT,
              letterSpacing: 3,
              marginBottom: card.kind === 'stat' ? 26 : 34,
            }}
          >
            {card.title}
          </div>
        ) : null}

        <CardBody card={card} accent={accent} brand={brand} local={local} />
      </div>
    </div>
  );
};

// ============================================================
// 片头标题卡
// ============================================================

const TitleCard: React.FC<{ title: string; subtitle?: string; accent: string; brand: string }> = ({
  title,
  subtitle,
  accent,
  brand,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const titleSize = fitFontSize(title, 1660, 92, 40, 8);
  const bar = interpolate(frame, [0, 20], [0, 340], { extrapolateRight: 'clamp' });
  const a = rise(frame, fps, 8, 30);
  const b = rise(frame, fps, 26, 22);
  const fade = interpolate(frame, [Math.max(0, fps * 4 - 16), fps * 4], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return (
    <AbsoluteFill
      style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        background: BG_BASE,
        opacity: fade,
      }}
    >
      <div style={{ width: bar, height: 5, background: brand, borderRadius: 3, marginBottom: 40 }} />
      <div
        style={{
          fontFamily: FONT,
          fontSize: titleSize,
          fontWeight: 800,
          color: TEXT,
          letterSpacing: 8,
          textAlign: 'center',
          whiteSpace: 'nowrap',
          lineHeight: 1.3,
          ...a,
        }}
      >
        {title}
      </div>
      {subtitle ? (
        <div
          style={{
            fontFamily: FONT,
            fontSize: 28,
            color: TEXT_DIM,
            letterSpacing: 6,
            marginTop: 34,
            ...b,
          }}
        >
          {subtitle}
        </div>
      ) : null}
      <div style={{ width: 160, height: 2, background: accent, marginTop: 48, opacity: 0.8 }} />
    </AbsoluteFill>
  );
};

// ============================================================
// 字幕轨：单行单显（同一时刻只显示当前正在讲的那一行）
// ============================================================

const CaptionTrack: React.FC<{
  lines: CaptionLine[];
  fps: number;
  fontSize: number;
  bottom: number;
}> = ({ lines, fps, fontSize, bottom }) => {
  const frame = useCurrentFrame();
  if (!lines.length) return null;
  const t = frame / fps;
  const idx = findActive(
    lines.map((l) => l.start),
    t,
  );
  if (idx < 0 || t > lines[idx].end) return null;
  const line = lines[idx];
  const local = frame - Math.round(line.start * fps);
  return (
    <CaptionLineView
      key={idx}
      text={line.text}
      fontSize={fontSize}
      bottom={bottom}
      local={local}
    />
  );
};

const CaptionLineView: React.FC<{
  text: string;
  fontSize: number;
  bottom: number;
  local: number;
}> = ({ text, fontSize, bottom, local }) => {
  const enter = interpolate(local, [0, 7], [0, 1], { extrapolateRight: 'clamp' });
  const y = interpolate(local, [0, 7], [16, 0], { extrapolateRight: 'clamp' });

  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        right: 0,
        bottom,
        display: 'flex',
        justifyContent: 'center',
        paddingLeft: 120,
        paddingRight: 120,
        opacity: enter,
        transform: `translateY(${y}px)`,
      }}
    >
      <div
        style={{
          display: 'inline-block',
          maxWidth: 1620,
          background: 'rgba(0,0,0,0.82)',
          borderRadius: 12,
          padding: '16px 34px',
          border: '1px solid rgba(255,255,255,0.08)',
        }}
      >
        <div
          style={{
            fontFamily: FONT,
            fontSize,
            fontWeight: 700,
            color: TEXT,
            lineHeight: 1.35,
            letterSpacing: 1.5,
            textAlign: 'center',
            whiteSpace: 'nowrap',
          }}
        >
          {text}
        </div>
      </div>
    </div>
  );
};

// ============================================================
// 底部进度条
// ============================================================

const ProgressBar: React.FC<{ accent: string }> = ({ accent }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const w = interpolate(frame, [0, Math.max(1, durationInFrames - 1)], [0, 100], {
    extrapolateRight: 'clamp',
  });
  return (
    <div style={{ position: 'absolute', left: 0, bottom: 0, width: '100%', height: 4 }}>
      <div
        style={{
          width: `${w}%`,
          height: '100%',
          background: `linear-gradient(90deg, ${accent}, ${accent}88)`,
        }}
      />
    </div>
  );
};

// ============================================================
// 主组件
// ============================================================

export const KouboVideo: React.FC<KouboProps> = (props) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const titleFrames = Math.round((props.titleCardDuration || 0) * fps);
  const inTitleCard = titleFrames > 0 && frame < titleFrames;
  // 分屏模式：右栏是原稿 PPT 页，左栏是逻辑图。slides 为空时退回原中置卡版式。
  const split = (props.slides || []).length > 0;

  return (
    <AbsoluteFill style={{ backgroundColor: BG_BASE, fontFamily: FONT }}>
      <Background accent={props.accent} brand={props.brand} />

      <Audio src={staticFile(props.audioSrc)} />
      {props.bgmSrc ? (
        <Audio src={staticFile(props.bgmSrc)} volume={props.bgmVolume ?? 0.12} />
      ) : null}

      <HeaderBar title={props.title} subtitle={props.subtitle} brand={props.brand} />
      <SectionTicker sections={props.sections} fps={fps} accent={props.accent} />

      {split ? (
        <>
          <SplitDivider accent={props.accent} />
          <LeftStage
            cards={props.cards}
            title={props.title}
            accent={props.accent}
            brand={props.brand}
            fps={fps}
          />
          <PptStage slides={props.slides!} accent={props.accent} fps={fps} />
        </>
      ) : (
        <CenterStage
          cards={props.cards}
          title={props.title}
          fps={fps}
          accent={props.accent}
          brand={props.brand}
        />
      )}

      <CaptionTrack
        lines={props.lines}
        fps={fps}
        fontSize={props.fontSize}
        bottom={props.captionBottom}
      />
      {props.showProgress ? <ProgressBar accent={props.accent} /> : null}

      {inTitleCard ? (
        <TitleCard
          title={props.title}
          subtitle={props.subtitle}
          accent={props.accent}
          brand={props.brand}
        />
      ) : null}
    </AbsoluteFill>
  );
};
