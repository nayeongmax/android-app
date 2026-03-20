/* =====================================================
   횡단면도 웹 앱 - Canvas 렌더링 엔진
   ===================================================== */

function renderCrossSection(canvas, pts, noIdx) {
    const ctx = canvas.getContext('2d');
    const unit = appData.unit;
    const s = unit === 'm' ? 0.001 : 1.0;

    const xs = pts.map(p => p.l * s);
    const ys = pts.map(p => p.h * s);
    const names = pts.map(p => p.name);

    const xmin = Math.min(...xs), xmax = Math.max(...xs);
    const ymin = Math.min(...ys), ymax = Math.max(...ys);
    const xSpan = xmax - xmin || 1;
    const ySpan = Math.max(ymax - ymin, 100 * s);
    const groundBottom = ymin - ySpan * 0.35;

    // Canvas dimensions & DPR
    const dpr = window.devicePixelRatio || 1;
    const cw = 1200, ch = 900;
    canvas.width = cw * dpr;
    canvas.height = ch * dpr;
    canvas.style.width = '100%';
    canvas.style.height = 'auto';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    // Drawing area margins
    const margin = {top: 80, right: 60, bottom: 100, left: 80};
    const plotW = cw - margin.left - margin.right;
    const plotH = ch - margin.top - margin.bottom;

    // Coordinate mapping
    const xm = xSpan * 0.06;
    const ymTop = ySpan * 0.72;
    const dataXmin = xmin - xm, dataXmax = xmax + xm;
    const dataYmin = groundBottom - ySpan * 0.06;
    const dataYmax = ymax + ymTop;
    const dataW = dataXmax - dataXmin;
    const dataH = dataYmax - dataYmin;

    function toCanvasX(v) { return margin.left + ((v - dataXmin) / dataW) * plotW; }
    function toCanvasY(v) { return margin.top + plotH - ((v - dataYmin) / dataH) * plotH; }

    // Background
    ctx.fillStyle = '#FFFFFF';
    ctx.fillRect(0, 0, cw, ch);

    // Grid
    if (appData.optGrid) {
        drawGrid(ctx, margin, plotW, plotH, dataXmin, dataXmax, dataYmin, dataYmax, toCanvasX, toCanvasY, s, unit);
    }

    // Hatching (ground fill)
    if (appData.optHatch) {
        const cxs = xs.map(toCanvasX);
        const cys = ys.map(toCanvasY);
        const cBot = toCanvasY(groundBottom);
        ctx.beginPath();
        ctx.moveTo(cxs[0], cBot);
        for (let i = 0; i < cxs.length; i++) ctx.lineTo(cxs[i], cys[i]);
        ctx.lineTo(cxs[cxs.length - 1], cBot);
        ctx.closePath();
        ctx.fillStyle = 'rgba(200, 169, 110, 0.55)';
        ctx.fill();

        // Lower layer
        ctx.fillStyle = 'rgba(139, 105, 20, 0.35)';
        const cBot2 = toCanvasY(groundBottom - ySpan * 0.05);
        ctx.fillRect(cxs[0], cBot, cxs[cxs.length - 1] - cxs[0], cBot2 - cBot);
    }

    // Road pavement
    const roadXs = xs.filter((x, i) => Math.abs(ys[i]) < 1e-6);
    if (roadXs.length >= 2) {
        const paveT = ySpan * 0.04;
        const rx0 = toCanvasX(Math.min(...roadXs));
        const rx1 = toCanvasX(Math.max(...roadXs));
        const ry0 = toCanvasY(0);
        const ry1 = toCanvasY(-paveT);
        ctx.fillStyle = 'rgba(58, 58, 58, 0.85)';
        ctx.fillRect(rx0, ry0, rx1 - rx0, ry1 - ry0);
    }

    // Terrain line
    const cxs = xs.map(toCanvasX);
    const cys = ys.map(toCanvasY);
    ctx.beginPath();
    ctx.moveTo(cxs[0], cys[0]);
    for (let i = 1; i < cxs.length; i++) ctx.lineTo(cxs[i], cys[i]);
    ctx.strokeStyle = '#222222';
    ctx.lineWidth = 2.5;
    ctx.stroke();

    // Points
    for (let i = 0; i < cxs.length; i++) {
        ctx.beginPath();
        ctx.arc(cxs[i], cys[i], 4, 0, Math.PI * 2);
        ctx.fillStyle = '#000000';
        ctx.fill();
    }

    // Road center line (x=0)
    const cx0 = toCanvasX(0);
    ctx.beginPath();
    ctx.setLineDash([8, 4]);
    ctx.moveTo(cx0, margin.top);
    ctx.lineTo(cx0, margin.top + plotH);
    ctx.strokeStyle = 'rgba(255, 0, 0, 0.7)';
    ctx.lineWidth = 1.2;
    ctx.stroke();
    ctx.setLineDash([]);

    // Reference line H=0
    const cy0 = toCanvasY(0);
    ctx.beginPath();
    ctx.setLineDash([4, 4]);
    ctx.moveTo(margin.left, cy0);
    ctx.lineTo(margin.left + plotW, cy0);
    ctx.strokeStyle = 'rgba(65, 105, 225, 0.6)';
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.setLineDash([]);

    // Labels
    if (appData.optLabels) {
        drawLabels(ctx, cxs, cys, names, xSpan, toCanvasX);
    }

    // Dimensions
    if (appData.optDims) {
        drawDimensions(ctx, xs, ys, cxs, cys, s, unit, xSpan, ySpan, groundBottom, toCanvasX, toCanvasY);
    }

    // Title
    ctx.fillStyle = '#000000';
    ctx.font = 'bold 18px "Noto Sans KR", sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(`${appData.titleText}  [NO.${noIdx + 1}]`, cw / 2, 35);

    // Axes labels
    ctx.font = '12px "Noto Sans KR", sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(`수평거리 (${unit})`, margin.left + plotW / 2, ch - 15);
    ctx.save();
    ctx.translate(18, margin.top + plotH / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText(`높이 (${unit})`, 0, 0);
    ctx.restore();

    // Legend
    drawLegend(ctx, cw, ch);
}

function drawGrid(ctx, margin, plotW, plotH, dataXmin, dataXmax, dataYmin, dataYmax, toCanvasX, toCanvasY, s, unit) {
    ctx.strokeStyle = 'rgba(0,0,0,0.1)';
    ctx.lineWidth = 0.5;
    ctx.setLineDash([2, 3]);

    const xRange = dataXmax - dataXmin;
    const yRange = dataYmax - dataYmin;
    const xStep = niceStep(xRange, 8);
    const yStep = niceStep(yRange, 6);

    const xStart = Math.ceil(dataXmin / xStep) * xStep;
    const yStart = Math.ceil(dataYmin / yStep) * yStep;

    ctx.font = '10px "Noto Sans KR", sans-serif';
    ctx.fillStyle = '#666';

    for (let x = xStart; x <= dataXmax; x += xStep) {
        const cx = toCanvasX(x);
        ctx.beginPath();
        ctx.moveTo(cx, margin.top);
        ctx.lineTo(cx, margin.top + plotH);
        ctx.stroke();
        ctx.textAlign = 'center';
        const label = unit === 'mm' ? (x / s).toFixed(0) : x.toFixed(2);
        ctx.fillText(label, cx, margin.top + plotH + 16);
    }

    for (let y = yStart; y <= dataYmax; y += yStep) {
        const cy = toCanvasY(y);
        ctx.beginPath();
        ctx.moveTo(margin.left, cy);
        ctx.lineTo(margin.left + plotW, cy);
        ctx.stroke();
        ctx.textAlign = 'right';
        const label = unit === 'mm' ? (y / s).toFixed(0) : y.toFixed(2);
        ctx.fillText(label, margin.left - 8, cy + 4);
    }

    ctx.setLineDash([]);
}

function niceStep(range, targetTicks) {
    const rough = range / targetTicks;
    const mag = Math.pow(10, Math.floor(Math.log10(rough)));
    const frac = rough / mag;
    let nice;
    if (frac <= 1.5) nice = 1;
    else if (frac <= 3) nice = 2;
    else if (frac <= 7) nice = 5;
    else nice = 10;
    return nice * mag;
}

function drawLabels(ctx, cxs, cys, names, xSpan, toCanvasX) {
    ctx.font = '11px "Noto Sans KR", sans-serif';
    const charW = 8;
    const levelRight = {};

    for (let i = 0; i < cxs.length; i++) {
        const name = names[i];
        if (!name) continue;
        const x = cxs[i], y = cys[i];
        const hw = charW * name.length / 2;
        let chosen = 7;
        for (let lvl = 0; lvl < 8; lvl++) {
            if (x - hw > (levelRight[lvl] || -Infinity) + charW * 0.5) {
                chosen = lvl;
                break;
            }
        }
        levelRight[chosen] = x + hw;
        const offsetY = 15 + chosen * 20;

        // Connection line for elevated labels
        if (chosen > 0) {
            ctx.beginPath();
            ctx.moveTo(x, y);
            ctx.lineTo(x, y - offsetY + 6);
            ctx.strokeStyle = '#BBBBBB';
            ctx.lineWidth = 0.6;
            ctx.stroke();
        }

        // Label box
        const tw = ctx.measureText(name).width + 10;
        const th = 18;
        const bx = x - tw / 2;
        const by = y - offsetY - th;

        ctx.fillStyle = 'rgba(255,255,255,0.88)';
        ctx.strokeStyle = '#AAAAAA';
        ctx.lineWidth = 0.6;
        roundRect(ctx, bx, by, tw, th, 4);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = '#222';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(name, x, by + th / 2);
    }
    ctx.textBaseline = 'alphabetic';
}

function drawDimensions(ctx, xs, ys, cxs, cys, s, unit, xSpan, ySpan, groundBottom, toCanvasX, toCanvasY) {
    const fmt = unit === 'mm'
        ? (v => `${v >= 0 ? '+' : ''}${(v / s).toFixed(0)} mm`)
        : (v => `${v >= 0 ? '+' : ''}${v.toFixed(3)} m`);

    // Height dimensions
    ctx.font = '10px "Noto Sans KR", sans-serif';
    const cy0 = toCanvasY(0);
    for (let i = 0; i < xs.length; i++) {
        if (Math.abs(ys[i]) < 1e-9) continue;
        const cx = cxs[i], cy = cys[i];
        const clr = ys[i] > 0 ? '#CC0000' : '#0044CC';

        // Arrow line
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(cx, cy0);
        ctx.strokeStyle = clr;
        ctx.lineWidth = 0.9;
        ctx.stroke();
        drawArrowHead(ctx, cx, cy, cx, cy0, clr);
        drawArrowHead(ctx, cx, cy0, cx, cy, clr);

        // Value text
        ctx.fillStyle = clr;
        ctx.textAlign = 'left';
        ctx.fillText(fmt(ys[i]), cx + 4, (cy + cy0) / 2 + 4);
    }

    // Horizontal distances
    const dimY = toCanvasY(groundBottom + ySpan * 0.06);
    const tickH = 6;
    ctx.strokeStyle = '#333';
    ctx.fillStyle = '#222';
    ctx.lineWidth = 0.8;

    for (let i = 0; i < xs.length - 1; i++) {
        const x0 = cxs[i], x1 = cxs[i + 1];

        // Horizontal line
        ctx.beginPath();
        ctx.moveTo(x0, dimY);
        ctx.lineTo(x1, dimY);
        ctx.stroke();

        // Tick marks
        for (const xp of [x0, x1]) {
            ctx.beginPath();
            ctx.moveTo(xp, dimY - tickH);
            ctx.lineTo(xp, dimY + tickH);
            ctx.stroke();
        }

        // Distance text
        const dist = xs[i + 1] - xs[i];
        const label = unit === 'mm' ? (dist / s).toFixed(0) : dist.toFixed(3);
        ctx.textAlign = 'center';
        ctx.font = '10px "Noto Sans KR", sans-serif';
        ctx.fillText(label, (x0 + x1) / 2, dimY - tickH - 4);
    }

    // Total width
    if (cxs.length >= 2) {
        const topY = toCanvasY(Math.max(...ys) + ySpan * 0.30);
        ctx.beginPath();
        ctx.moveTo(cxs[0], topY);
        ctx.lineTo(cxs[cxs.length - 1], topY);
        ctx.strokeStyle = 'darkblue';
        ctx.lineWidth = 1.2;
        ctx.stroke();
        drawArrowHead(ctx, cxs[cxs.length - 1], topY, cxs[0], topY, 'darkblue');
        drawArrowHead(ctx, cxs[0], topY, cxs[cxs.length - 1], topY, 'darkblue');

        const total = xs[xs.length - 1] - xs[0];
        const totalLabel = unit === 'mm' ? `전체폭  ${(total / s).toFixed(0)} mm` : `전체폭  ${total.toFixed(3)} m`;
        ctx.font = 'bold 13px "Noto Sans KR", sans-serif';
        ctx.fillStyle = 'darkblue';
        ctx.textAlign = 'center';
        ctx.fillText(totalLabel, (cxs[0] + cxs[cxs.length - 1]) / 2, topY - 8);
    }
}

function drawArrowHead(ctx, fromX, fromY, toX, toY, color) {
    const angle = Math.atan2(toY - fromY, toX - fromX);
    const len = 6;
    ctx.beginPath();
    ctx.moveTo(toX, toY);
    ctx.lineTo(toX - len * Math.cos(angle - 0.4), toY - len * Math.sin(angle - 0.4));
    ctx.lineTo(toX - len * Math.cos(angle + 0.4), toY - len * Math.sin(angle + 0.4));
    ctx.closePath();
    ctx.fillStyle = color;
    ctx.fill();
}

function drawLegend(ctx, cw, ch) {
    const items = [
        {color: '#222222', dash: false, lw: 2.5, label: '현황지반선'},
        {color: 'rgba(58,58,58,0.85)', dash: false, lw: 8, label: '도로 포장면', rect: true},
        {color: 'red', dash: true, lw: 1.2, label: '도로중심선'},
        {color: 'royalblue', dash: true, lw: 1, label: '기준고 (H=0)'},
    ];

    const legendW = items.length * 140;
    const startX = (cw - legendW) / 2;
    const y = ch - 40;

    ctx.font = '11px "Noto Sans KR", sans-serif';

    for (let i = 0; i < items.length; i++) {
        const item = items[i];
        const x = startX + i * 140;

        if (item.rect) {
            ctx.fillStyle = item.color;
            ctx.fillRect(x, y - 4, 24, 8);
        } else {
            ctx.beginPath();
            if (item.dash) ctx.setLineDash([4, 3]);
            ctx.moveTo(x, y);
            ctx.lineTo(x + 24, y);
            ctx.strokeStyle = item.color;
            ctx.lineWidth = item.lw;
            ctx.stroke();
            ctx.setLineDash([]);
        }

        ctx.fillStyle = '#333';
        ctx.textAlign = 'left';
        ctx.fillText(item.label, x + 30, y + 4);
    }
}

function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
}
