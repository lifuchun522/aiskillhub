/**
 * 口播成片 —— props 数据结构
 * 与 scripts/prepare_props.py 输出的 props.json 一一对应
 */

export type CardKind =
  // —— 文本型 ——
  | 'bullets' // 并列要点
  | 'stat' // 单个数字
  | 'quote' // 一句话
  // —— 结构型（图解）——
  | 'flow' // 流程链：A → B → C → D（因果 / 步骤）
  | 'quad' // 四宫格分解：一个命题拆成四个并列面
  | 'map' // 映射：左列 → 右列，逐行连线
  | 'compare' // 对比：左右两栏对照
  | 'split' // 分解：一个整体向下拆成若干部分
  | 'integrate' // 集成：多个来源向上汇聚成一个结果
  | 'pyramid' // 层次：自下而上的能力层级
  | 'relation'; // 关系：中心节点与周边要素的关联

export type CaptionLine = {
  /** 起始秒 */
  start: number;
  /** 结束秒 */
  end: number;
  /** 单行文本（已按 maxlen 切好，一行一屏） */
  text: string;
};

export type SectionMark = {
  /** 起始秒 */
  start: number;
  text: string;
};

/** 分屏模式右栏的 PPT 页（每页在原稿中占据一段时间） */
export type SlidePage = {
  start: number;
  end: number;
  /** 相对 public 目录的图片路径 */
  src: string;
  /** 页码（从 1 开始） */
  index: number;
};

export type ContentCard = {
  start: number;
  end: number;
  kind: CardKind;
  title?: string;

  /** bullets / quad / flow 步骤 / split 子项 / pyramid 层级（自下而上） / relation 周边要素 */
  items?: string[];
  /** compare / map 左栏标题、条目 */
  leftTitle?: string;
  left?: string[];
  /** compare / map 右栏标题、条目 */
  rightTitle?: string;
  right?: string[];

  /** relation 中心节点文案 */
  center?: string;
  /** integrate 的多个来源 */
  inputs?: string[];
  /** integrate 汇聚后的结果 */
  output?: string;

  /** stat 的数字 / 单位 */
  value?: string;
  unit?: string;
  /** quote 的正文；其它类型作为底部小注 */
  note?: string;
};

export type KouboProps = {
  title: string;
  subtitle?: string;
  audioSrc: string;
  audioDuration: number;
  fps: number;
  width: number;
  height: number;
  /** 主强调色（字幕高亮 / 连接线 / 重点框） */
  accent: string;
  /** 品牌色（左上角竖条 / 次级标记） */
  brand: string;
  lines: CaptionLine[];
  sections: SectionMark[];
  cards: ContentCard[];
  /** 片头标题卡时长（秒），0 = 不要片头 */
  titleCardDuration: number;
  /** 字幕距底部像素 */
  captionBottom: number;
  /** 字幕字号 */
  fontSize: number;
  showProgress: boolean;
  bgmSrc?: string;
  bgmVolume?: number;
  /** 分屏模式：非空时启用「左逻辑图 + 右 PPT 页」版式 */
  slides?: SlidePage[];
};
