const fs = require('fs');
const path = require('path');
const { Resvg } = require('@resvg/resvg-js');

const root = path.join(__dirname, '..');
const svgDir = path.join(root, 'svg');
const pngDir = path.join(root, 'png');

if (!fs.existsSync(pngDir)) fs.mkdirSync(pngDir, { recursive: true });

const fontOpts = {
  loadSystemFonts: true,
  defaultFontFamily: 'Arial',
};

const files = process.argv.slice(2).length
  ? process.argv.slice(2)
  : fs.readdirSync(svgDir).filter((f) => f.endsWith('.svg'));

for (const file of files) {
  try {
    let svg = fs.readFileSync(path.join(svgDir, file), 'utf8');
    svg = svg.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F]/g, '');
    const resvg = new Resvg(svg, {
      fitTo: { mode: 'width', value: 1600 },
      font: fontOpts,
      background: 'transparent',
    });
    fs.writeFileSync(path.join(pngDir, file.replace(/\.svg$/, '.png')), resvg.render().asPng());
    console.log('OK', file);
  } catch (err) {
    console.error('FAIL', file, err.message);
    process.exitCode = 1;
  }
}
