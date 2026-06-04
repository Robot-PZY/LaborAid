/** 将证据 AI 分析长文解析为栏目卡片（兼容 ## / ### / 加粗序号标题） */

export type EvidenceAnalysisSection = {
  title: string;
  body: string;
};

function cleanTitle(raw: string): string {
  return raw
    .replace(/^\d+[\.\)、]\s*/, '')
    .replace(/\*\*/g, '')
    .replace(/：$/, '')
    .trim();
}

function cleanBody(raw: string): string {
  return raw
    .replace(/^---+$/gm, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

/** 按 Markdown 标题拆分 */
function splitByHeadings(text: string): EvidenceAnalysisSection[] {
  const lines = text.split('\n');
  const sections: EvidenceAnalysisSection[] = [];
  let currentTitle = '';
  let buf: string[] = [];

  const flush = () => {
    const body = cleanBody(buf.join('\n'));
    if (currentTitle && body) {
      sections.push({ title: currentTitle, body });
    } else if (!currentTitle && body) {
      sections.push({ title: '分析摘要', body: body.slice(0, 400) });
    }
    buf = [];
  };

  for (const line of lines) {
    const h2 = line.match(/^##\s+(.+)$/);
    const h3 = line.match(/^###\s+(.+)$/);
    const boldNum = line.match(/^\*\*\s*\d+[\.\)、]?\s*(.+?)\*\*\s*$/);
    const titleLine = h2 || h3 || boldNum;
    if (titleLine) {
      flush();
      currentTitle = cleanTitle(titleLine[1]);
      continue;
    }
    if (line.match(/^---+$/)) continue;
    buf.push(line);
  }
  flush();
  return sections;
}

/** 按「1. **标题**」类段落拆分（无 ## 时） */
function splitByNumberedBlocks(text: string): EvidenceAnalysisSection[] {
  const parts = text.split(/(?=\n\s*\d+[\.\)、]\s*\*\*)/);
  const sections: EvidenceAnalysisSection[] = [];
  for (const part of parts) {
    const m = part.match(/^\s*\d+[\.\)、]\s*\*\*(.+?)\*\*\s*[：:]?\s*([\s\S]*)/);
    if (m) {
      const body = cleanBody(m[2]);
      if (body) sections.push({ title: cleanTitle(m[1]), body: body.slice(0, 500) });
    }
  }
  return sections;
}

export function parseEvidenceAnalysis(text: string): {
  sections: EvidenceAnalysisSection[];
} {
  const raw = (text || '').trim();
  if (!raw) return { sections: [] };

  let sections = splitByHeadings(raw);
  if (sections.length < 2) {
    sections = splitByNumberedBlocks(raw);
  }

  if (sections.length >= 2) {
    return { sections: sections.slice(0, 8) };
  }

  // 兜底：截取首段作摘要 + 单卡
  const firstPara = raw.split(/\n\n+/)[0]?.slice(0, 280) || raw.slice(0, 280);
  return {
    sections: [{ title: '分析要点', body: firstPara }],
  };
}
