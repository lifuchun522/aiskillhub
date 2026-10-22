import React from 'react';
import { AbsoluteFill } from 'remotion';
import { CardBody } from './CardBody';
import { ContentCard } from './types';

/**
 * CardGallery —— 设计校验收用合成
 *
 * 把所有内容卡按固定尺寸竖向排布、动画定格在「完全入场」状态，
 * 一次渲染即可横向比对所有图解结构（流程 / 分解 / 集成 / 对比 / 映射 / 关系 / 层次）。
 * 平时渲染成片不用它，只在改卡片设计后用来快速自检。
 */

const FONT = '"Microsoft YaHei", "PingFang SC", "Noto Sans SC", sans-serif';
const CELL_H = 570;
const CARD_W = 1320;
const SETTLED = 200; // 定格帧：足够让所有入场动画走完

export const CardGallery: React.FC<{ cards: ContentCard[]; accent: string; brand: string }> = ({
  cards,
  accent,
  brand,
}) => (
  <AbsoluteFill style={{ backgroundColor: '#0B0E14' }}>
    <AbsoluteFill
      style={{ background: 'linear-gradient(158deg, #0B0E14 0%, #101A26 46%, #0A1520 100%)' }}
    />
    {cards.map((card, i) => (
      <div
        key={i}
        style={{
          position: 'absolute',
          left: (1920 - CARD_W) / 2,
          top: i * CELL_H + 24,
          width: CARD_W,
        }}
      >
        <div
          style={{
            fontFamily: FONT,
            fontSize: 18,
            fontWeight: 700,
            color: accent,
            letterSpacing: 3,
            marginBottom: 10,
          }}
        >
          {String(i + 1).padStart(2, '0')} · {card.kind}
        </div>
        <div
          style={{
            background: 'rgba(255,255,255,0.045)',
            border: '1px solid rgba(255,255,255,0.10)',
            borderLeft: `5px solid ${accent}`,
            borderRadius: 18,
            padding: '44px 56px',
            boxShadow: '0 24px 80px rgba(0,0,0,0.45)',
          }}
        >
          {card.title ? (
            <div
              style={{
                fontFamily: FONT,
                fontSize: 44,
                fontWeight: 800,
                color: '#FFFFFF',
                letterSpacing: 3,
                marginBottom: 34,
              }}
            >
              {card.title}
            </div>
          ) : null}
          <CardBody card={card} accent={accent} brand={brand} local={SETTLED} />
        </div>
      </div>
    ))}
  </AbsoluteFill>
);
