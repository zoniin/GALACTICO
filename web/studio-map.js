const WIDTH = 660,
  HEIGHT = 346;
const pad = 18,
  pitchW = WIDTH - 2 * pad,
  pitchH = HEIGHT - 2 * pad;
const ramp = [
  [0, 32, 90, 126, 0],
  [0.08, 48, 134, 166, 85],
  [0.28, 69, 204, 175, 180],
  [0.52, 182, 230, 88, 224],
  [0.75, 255, 195, 73, 244],
  [1, 255, 105, 49, 255],
];
function paintDensity(ctx, points) {
  if (!points.length) return;
  const w = 150,
    h = 79,
    heat = new Float32Array(w * h);
  for (const { x, y } of points) {
    const cx = (x * (w - 1)) / 100,
      cy = (y * (h - 1)) / 100;
    for (let j = Math.max(0, Math.floor(cy - 13)); j <= Math.min(h - 1, cy + 13); j++) {
      for (let i = Math.max(0, Math.floor(cx - 13)); i <= Math.min(w - 1, cx + 13); i++) {
        heat[j * w + i] += Math.exp(-((i - cx) ** 2 + (j - cy) ** 2) / 39);
      }
    }
  }
  const layer = document.createElement('canvas');
  layer.width = w;
  layer.height = h;
  const lc = layer.getContext('2d'),
    img = lc.createImageData(w, h);
  const max = heat.reduce((a, b) => Math.max(a, b), 0);
  for (let i = 0; i < heat.length; i++) {
    const v = heat[i] / max;
    if (v < 0.012) continue;
    let k = 1;
    while (k < ramp.length - 1 && v > ramp[k][0]) k++;
    const a = ramp[k - 1],
      b = ramp[k],
      f = (v - a[0]) / (b[0] - a[0]);
    for (let c = 0; c < 4; c++) img.data[4 * i + c] = a[c + 1] + (b[c + 1] - a[c + 1]) * f;
  }
  lc.putImageData(img, 0, 0);
  ctx.drawImage(layer, pad, pad, pitchW, pitchH);
}
function markings(ctx) {
  ctx.strokeStyle = '#dcece79c';
  ctx.lineWidth = 1.8;
  ctx.strokeRect(pad, pad, pitchW, pitchH);
  ctx.beginPath();
  ctx.moveTo(WIDTH / 2, pad);
  ctx.lineTo(WIDTH / 2, HEIGHT - pad);
  ctx.stroke();
  ctx.beginPath();
  ctx.arc(WIDTH / 2, HEIGHT / 2, 44, 0, 2 * Math.PI);
  ctx.stroke();
  for (const sign of [1, -1]) {
    const x = sign === 1 ? pad : WIDTH - pad;
    ctx.strokeRect(x, HEIGHT * 0.25, sign * pitchW * 0.16, HEIGHT * 0.5);
    ctx.strokeRect(x, HEIGHT * 0.38, sign * pitchW * 0.059, HEIGHT * 0.24);
    ctx.beginPath();
    ctx.arc(x + sign * pitchW * 0.11, HEIGHT / 2, 2.5, 0, 2 * Math.PI);
    ctx.fillStyle = '#dcece7b0';
    ctx.fill();
  }
}
export function draw(canvas, points, slot, roleMode) {
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#193c40';
  ctx.fillRect(0, 0, WIDTH, HEIGHT);
  for (let i = 0; i < 10; i += 2) {
    ctx.fillStyle = '#20464a';
    ctx.fillRect(pad + (i * pitchW) / 10, pad, pitchW / 10, pitchH);
  }
  if (roleMode && slot) {
    const x = pad + ((100 - slot.y) * pitchW) / 100,
      y = pad + (slot.x * pitchH) / 100;
    ctx.save();
    ctx.beginPath();
    ctx.rect(pad, pad, pitchW, pitchH);
    ctx.clip();
    ctx.fillStyle = '#b6a4ff69';
    ctx.strokeStyle = '#dbceff';
    ctx.setLineDash([7, 5]);
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.ellipse(x, y, 62, 44, 0, 0, 2 * Math.PI);
    ctx.fill();
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = 'white';
    ctx.beginPath();
    ctx.arc(x, y, 6, 0, 2 * Math.PI);
    ctx.fill();
    ctx.restore();
  } else paintDensity(ctx, points);
  markings(ctx);
}
export function readEvents(text) {
  const lines = text
    .trim()
    .replace(/^\uFEFF/, '')
    .split(/\r?\n/);
  const columns = lines
    .shift()
    .toLowerCase()
    .split(',')
    .map((s) => s.trim());
  const xi = columns.indexOf('x'),
    yi = columns.indexOf('y'),
    ti = columns.indexOf('type');
  if (xi < 0 || yi < 0) throw Error('The first row must include x and y.');
  if (!lines.length || lines.length > 15000)
    throw Error('Use between 1 and 15,000 coordinate rows.');
  return lines.map((line, index) => {
    const cells = line.split(',').map((s) => s.trim()),
      x = Number(cells[xi]),
      y = Number(cells[yi]);
    if (
      !cells[xi] ||
      !cells[yi] ||
      !Number.isFinite(x) ||
      !Number.isFinite(y) ||
      x < 0 ||
      x > 100 ||
      y < 0 ||
      y > 100
    )
      throw Error('Check x and y on row ' + (index + 2) + '.');
    return { x, y, type: ti >= 0 && cells[ti] ? cells[ti].slice(0, 45) : 'Action' };
  });
}
