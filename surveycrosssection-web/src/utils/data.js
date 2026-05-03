export const DEFAULT_DATA = [
  ["좌측경계",   -8000,   500, "용지경계"],
  ["좌측법면끝",  2500,  -500, ""],
  ["좌측측구",    700,  -400, "U형측구"],
  ["좌측길어깨",  800,   400, ""],
  ["좌측차로끝", 2500,     0, ""],
  ["도로중심",   1500,     0, "기준점"],
  ["우측차로끝", 1500,     0, ""],
  ["우측길어깨", 2500,     0, ""],
  ["우측측구",    800,  -400, "U형측구"],
  ["우측법면끝",  700,   400, ""],
  ["우측경계",   2500,   500, "용지경계"],
];

export const PRESET_NAMES = [
  "도로중심", "차도끝", "길어깨끝", "측구", "다이크",
  "법면시작", "법면끝", "용지경계", "수로", "소단",
];

export function getPoints(data) {
  const pts = [];
  let cumL = 0, cumH = 0, prevDL = 0;
  for (const row of data) {
    const dl = parseFloat(row[1]) || 0;
    const dh = parseFloat(row[2]) || 0;
    if (row[0] === '도로중심' && dl === 0 && prevDL > 0) {
      cumL += prevDL;
    } else {
      cumL += dl;
    }
    cumH += dh;
    pts.push({ name: row[0], l: cumL, h: cumH, note: row[3] || '' });
    prevDL = dl;
  }
  const center = pts.find(p => p.name === '도로중심');
  if (center) {
    const offset = center.l;
    for (const p of pts) p.l -= offset;
  }
  return pts;
}

export function createInitialState() {
  return {
    allTableData: Array.from({ length: 6 }, () => DEFAULT_DATA.map(r => [...r])),
    sections: Array.from({ length: 6 }, () => ({ photos: [], photoIdx: 0 })),
    currentNo: 0,
    selectedRow: -1,
    optLabels: true,
    optDims: true,
    optGrid: true,
    optHatch: true,
    unit: 'mm',
    titleText: '횡단면도',
    activeTab: 'input',
    drawn: Array(6).fill(false),
  };
}
