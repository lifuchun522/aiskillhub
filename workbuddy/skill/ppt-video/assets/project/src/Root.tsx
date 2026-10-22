import React from 'react';
import { CalculateMetadataFunction, Composition } from 'remotion';
import { CardGallery } from './Gallery';
import { KouboProps, KouboVideo } from './KouboVideo';

/**
 * 默认 props —— 只作为 Studio 预览兜底。
 * 正式渲染时由 scripts/prepare_props.py 生成的 props.json 完整覆盖。
 */
const defaultProps: KouboProps = {
  title: '口播视频',
  subtitle: '',
  audioSrc: 'audio.mp3',
  audioDuration: 10,
  fps: 30,
  width: 1920,
  height: 1080,
  accent: '#FFD400',
  brand: '#CC0000',
  lines: [{ start: 0, end: 10, text: '把口播 mp3 和逐字稿放进来，就能出片。' }],
  sections: [],
  cards: [],
  titleCardDuration: 0,
  captionBottom: 150,
  fontSize: 52,
  showProgress: true,
  bgmVolume: 0.12,
};

/** 用时长的秒数反推总帧数，宽高/帧率也允许被 props 覆盖 */
export const calculateKouboMetadata: CalculateMetadataFunction<KouboProps> = ({ props }) => {
  const fps = props.fps || 30;
  return {
    durationInFrames: Math.max(1, Math.ceil((props.audioDuration || 10) * fps)),
    fps,
    width: props.width || 1920,
    height: props.height || 1080,
  };
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="KouboVideo"
        component={KouboVideo}
        durationInFrames={300}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={defaultProps}
        calculateMetadata={calculateKouboMetadata}
      />
      {/* 设计自检用：把所有内容卡竖向排开定格，一次渲染即可比对全部图解结构 */}
      <Composition
        id="CardGallery"
        component={CardGallery}
        durationInFrames={2}
        fps={30}
        width={1920}
        height={570 * Math.max(1, defaultProps.cards.length || 8)}
        defaultProps={{
          cards: defaultProps.cards,
          accent: defaultProps.accent,
          brand: defaultProps.brand,
        }}
        calculateMetadata={({ props }) => ({
          durationInFrames: 2,
          fps: 30,
          width: 1920,
          height: 570 * Math.max(1, (props.cards || []).length || 8),
        })}
      />
    </>
  );
};
