// Offline asset conversion only; AXIS does not load this script or need Node.js.
// SPDX-License-Identifier: GPL-2.0-or-later
const fs = require('node:fs/promises');
const path = require('node:path');
const sharp = require('sharp');

async function main() {
  const manifest = JSON.parse(await fs.readFile(path.join(__dirname, 'manifest.json'), 'utf8'));
  for (const icon of manifest.icons) {
    const source = path.join(__dirname, icon.file.replace(/\.gif$/, '.svg'));
    const { data, info } = await sharp(source, { density: 384 })
      .resize(icon.width, icon.height)
      .ensureAlpha()
      .raw()
      .toBuffer({ resolveWithObject: true });

    // GIF has binary transparency. Matte antialiased edges against AXIS's
    // existing #d9d9d9 button face, keeping empty pixels fully transparent.
    for (let i = 0; i < data.length; i += 4) {
      const alpha = data[i + 3] / 255;
      for (let c = 0; c < 3; c++) {
        data[i + c] = Math.round(data[i + c] * alpha + 217 * (1 - alpha));
      }
      data[i + 3] = alpha < 0.04 ? 0 : 255;
    }
    await sharp(data, { raw: info })
      .gif({ colours: 128, dither: 0, effort: 10 })
      .toFile(path.join(__dirname, '..', icon.file));
  }
  console.log(`Rendered ${manifest.icons.length} static toolbar GIFs.`);
}

main().catch(error => { console.error(error); process.exitCode = 1; });
