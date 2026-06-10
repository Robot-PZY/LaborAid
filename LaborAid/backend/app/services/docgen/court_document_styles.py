"""法院文书排版 CSS — 与 word_export_native.py 参数完全一致。"""

COURT_DOCUMENT_CSS = """
.court-document {
  font-family: "FangSong_GB2312", "仿宋_GB2312", "FangSong", "仿宋", "STFangsong", serif;
  font-size: 16pt;
  line-height: 28.8pt;
  color: #000;
  max-width: 210mm;
  margin: 0 auto;
  padding: 3.7cm 2.6cm 3.5cm 2.8cm;
  background: #fff;
  box-sizing: border-box;
  min-height: 297mm;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
.court-document h1,
.court-document h1.center {
  font-family: "FZXiaoBiaoSong-B05S", "方正小标宋简体", "方正小标宋", "SimSun", "宋体", serif;
  font-size: 22pt;
  text-align: center;
  line-height: 28.8pt;
  margin: 0 0 18pt 0;
  font-weight: normal;
  text-indent: 0;
  color: #000;
}
.court-document h2 {
  font-family: "SimHei", "黑体", "STHeiti", "Microsoft YaHei", sans-serif;
  font-size: 16pt;
  font-weight: bold;
  margin: 10pt 0 2pt 0;
  line-height: 28.8pt;
  text-indent: 0;
  color: #000;
}
.court-document h3 {
  font-family: "KaiTi", "楷体", "STKaiti", "SimKai", serif;
  font-size: 16pt;
  font-weight: bold;
  margin: 8pt 0 2pt 0;
  line-height: 28.8pt;
  text-indent: 0;
  color: #000;
}
.court-document h4 {
  font-family: "FangSong_GB2312", "仿宋_GB2312", "FangSong", "仿宋", serif;
  font-size: 14pt;
  font-weight: bold;
  margin: 6pt 0 2pt 0;
  line-height: 28.8pt;
  text-indent: 0;
  color: #000;
}
.court-document p {
  text-indent: 0.74cm;
  margin: 0;
  text-align: justify;
  line-height: 28.8pt;
  color: #000;
}
.court-document p.no-indent,
.court-document .no-indent {
  text-indent: 0;
}
.court-document .center {
  text-align: center;
  text-indent: 0;
}
.court-document .right-align {
  text-align: right;
  text-indent: 0;
}
.court-document strong,
.court-document em,
.court-document li,
.court-document td,
.court-document th {
  color: #000;
}
.court-document strong {
  font-weight: bold;
}
.court-document a {
  color: #000;
  text-decoration: none;
}
.court-document table {
  border-collapse: collapse;
  width: 100%;
  margin: 6pt 0 8pt 0;
  font-size: 14pt;
}
.court-document th,
.court-document td {
  border: 1px solid #000;
  padding: 4pt 6pt;
  text-align: left;
  vertical-align: top;
  text-indent: 0;
  line-height: 24pt;
}
.court-document th {
  font-weight: bold;
  background-color: #D9E2F3;
  text-align: center;
}
.court-document ol.legal-list {
  padding-left: 0;
  margin: 0;
  list-style: none;
  counter-reset: legal-item;
}
.court-document ol.legal-list li {
  counter-increment: legal-item;
  position: relative;
  padding-left: 1.2cm;
  margin: 0;
  text-indent: 0;
  line-height: 28.8pt;
  text-align: justify;
}
.court-document ol.legal-list li::before {
  content: counter(legal-item) ". ";
  position: absolute;
  left: 0;
  font-weight: normal;
}
.court-document ol {
  padding-left: 1.2cm;
  margin: 0;
}
.court-document ul {
  list-style: none;
  padding-left: 0.74cm;
  margin: 0;
}
.court-document li {
  margin-bottom: 0;
  text-indent: 0;
  line-height: 28.8pt;
}
/* 模板变量缺失提示高亮 */
.court-document .template-hint {
  color: #cc0000;
  font-weight: bold;
  background-color: #fff3cd;
  padding: 0 2pt;
  border-radius: 2pt;
}
"""
