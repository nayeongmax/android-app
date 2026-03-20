/* =====================================================
   횡단면도 웹 앱 - 메인 애플리케이션 로직
   ===================================================== */

// ==================== UI 초기화 ====================
document.addEventListener('DOMContentLoaded', () => {
    initNoTabs();
    initPresetNames();
    refreshTable();
    refreshDrawPhoto();
});

function initNoTabs() {
    const container = document.getElementById('noTabs');
    for (let i = 0; i < 10; i++) {
        const btn = document.createElement('button');
        btn.className = 'no-tab' + (i === 0 ? ' active' : '');
        btn.textContent = `NO.${i + 1}`;
        btn.onclick = () => switchNo(i);
        container.appendChild(btn);
    }
}

function initPresetNames() {
    const container = document.getElementById('presetNames');
    for (const name of PRESET_NAMES) {
        const btn = document.createElement('button');
        btn.className = 'preset-btn';
        btn.textContent = name;
        btn.onclick = () => { document.getElementById('inpName').value = name; };
        container.appendChild(btn);
    }
}

// ==================== NO 탭 전환 ====================
function switchNo(idx) {
    appData.currentNo = idx;
    appData.selectedRow = -1;
    document.querySelectorAll('.no-tab').forEach((btn, i) => {
        btn.classList.toggle('active', i === idx);
    });
    document.getElementById('inputHeader').textContent = `NO.${idx + 1} 측점 데이터`;
    refreshTable();
    refreshDrawPhoto();
}

// ==================== 서브탭 전환 ====================
function switchSubTab(tab) {
    document.querySelectorAll('.sub-tab').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });
    document.querySelectorAll('.tab-content').forEach(el => {
        el.classList.toggle('active', el.id === `tab-${tab}`);
    });
}

// ==================== 테이블 관리 ====================
function refreshTable() {
    const tbody = document.getElementById('dataTableBody');
    tbody.innerHTML = '';
    const data = tableData();

    for (let i = 0; i < data.length; i++) {
        const tr = document.createElement('tr');
        if (i === appData.selectedRow) tr.className = 'selected';
        tr.onclick = () => selectRow(i);

        for (const val of data[i]) {
            const td = document.createElement('td');
            td.textContent = val;
            tr.appendChild(td);
        }
        tbody.appendChild(tr);
    }
}

function selectRow(idx) {
    appData.selectedRow = idx;
    const row = tableData()[idx];
    document.getElementById('inpName').value = row[0];
    document.getElementById('inpDL').value = row[1];
    document.getElementById('inpDH').value = row[2];
    document.getElementById('inpNote').value = row[3];
    refreshTable();
}

function parseDLH() {
    const dl = parseFloat(document.getElementById('inpDL').value || '0');
    const dh = parseFloat(document.getElementById('inpDH').value || '0');
    if (isNaN(dl) || isNaN(dh)) {
        showToast('DL, DH는 숫자로 입력하세요.');
        return null;
    }
    return [dl, dh];
}

function addRow() {
    const vals = parseDLH();
    if (!vals) return;
    const [dl, dh] = vals;
    const data = tableData();
    data.push([
        document.getElementById('inpName').value,
        Number.isInteger(dl) ? dl : dl,
        Number.isInteger(dh) ? dh : dh,
        document.getElementById('inpNote').value,
    ]);
    document.getElementById('inpName').value = '';
    document.getElementById('inpNote').value = '';
    appData.selectedRow = data.length - 1;
    refreshTable();
}

function editRow() {
    if (appData.selectedRow < 0) {
        showToast('수정할 행을 선택하세요.');
        return;
    }
    const vals = parseDLH();
    if (!vals) return;
    const [dl, dh] = vals;
    tableData()[appData.selectedRow] = [
        document.getElementById('inpName').value,
        dl, dh,
        document.getElementById('inpNote').value,
    ];
    refreshTable();
}

function deleteRow() {
    if (appData.selectedRow < 0) {
        showToast('삭제할 행을 선택하세요.');
        return;
    }
    tableData().splice(appData.selectedRow, 1);
    appData.selectedRow = Math.min(appData.selectedRow, tableData().length - 1);
    refreshTable();
}

function clearAll() {
    showConfirm(`NO.${appData.currentNo + 1}의 모든 측점을 삭제하시겠습니까?`, () => {
        appData.allTableData[appData.currentNo] = [];
        appData.selectedRow = -1;
        refreshTable();
    });
}

function moveRow(dir) {
    const i = appData.selectedRow;
    const data = tableData();
    const j = i + dir;
    if (i < 0 || j < 0 || j >= data.length) return;
    [data[i], data[j]] = [data[j], data[i]];
    appData.selectedRow = j;
    refreshTable();
}

function loadDefaults() {
    appData.allTableData[appData.currentNo] = DEFAULT_DATA.map(r => [...r]);
    appData.selectedRow = -1;
    refreshTable();
    showToast('기본값이 로드되었습니다.');
}

// ==================== 그리기 ====================
function drawCrossSection() {
    const no = appData.currentNo;
    const pts = getPoints(no);
    if (pts.length < 2) {
        showToast(`NO.${no + 1}의 측점이 2개 이상 필요합니다.`);
        return;
    }

    const canvas = document.getElementById('drawCanvas');
    const placeholder = document.getElementById('canvasPlaceholder');
    placeholder.style.display = 'none';
    canvas.style.display = 'block';

    renderCrossSection(canvas, pts, no);
    appData.sections[no].drawn = true;

    const unit = appData.unit;
    const s = unit === 'm' ? 0.001 : 1.0;
    const xs = pts.map(p => p.l * s);
    const totalW = (Math.max(...xs) - Math.min(...xs)) / s;
    document.getElementById('drawStatus').textContent =
        `[NO.${no + 1}]  측점 ${pts.length}개 | 전체폭 ${totalW.toLocaleString()} mm | 완료`;
}

// ==================== 그리기 옵션 ====================
function toggleOpt(key) {
    const prop = 'opt' + key.charAt(0).toUpperCase() + key.slice(1);
    appData[prop] = !appData[prop];
    const btn = document.getElementById('opt' + key.charAt(0).toUpperCase() + key.slice(1));
    btn.classList.toggle('active', appData[prop]);
}

function toggleUnit() {
    appData.unit = appData.unit === 'mm' ? 'm' : 'mm';
    document.getElementById('unitBtn').textContent = appData.unit;
}

// ==================== 현장사진 관리 ====================
function addDrawPhoto() {
    document.getElementById('drawPhotoFileInput').click();
}

function handleDrawPhotoFiles(event) {
    const files = event.target.files;
    if (!files.length) return;
    const sec = appData.sections[appData.currentNo];
    for (const file of files) {
        const reader = new FileReader();
        reader.onload = (e) => {
            sec.photos.push({dataUrl: e.target.result, name: file.name, note: ''});
            if (sec.photos.length === 1) sec.photoIdx = 0;
            refreshDrawPhoto();
        };
        reader.readAsDataURL(file);
    }
    event.target.value = '';
}

function refreshDrawPhoto() {
    const sec = appData.sections[appData.currentNo];
    const counter = document.getElementById('drawPhotoCounter');
    const placeholder = document.getElementById('drawPhotoPlaceholder');
    const img = document.getElementById('drawPhotoImage');

    if (!sec.photos.length) {
        counter.textContent = '현장사진 없음';
        placeholder.style.display = 'block';
        img.style.display = 'none';
        return;
    }

    const idx = sec.photoIdx;
    const entry = sec.photos[idx];
    counter.textContent = `현장사진 ${idx + 1}/${sec.photos.length}`;
    placeholder.style.display = 'none';
    img.style.display = 'block';
    img.src = entry.dataUrl;
}

function prevDrawPhoto() {
    const sec = appData.sections[appData.currentNo];
    if (!sec.photos.length) return;
    sec.photoIdx = (sec.photoIdx - 1 + sec.photos.length) % sec.photos.length;
    refreshDrawPhoto();
}

function nextDrawPhoto() {
    const sec = appData.sections[appData.currentNo];
    if (!sec.photos.length) return;
    sec.photoIdx = (sec.photoIdx + 1) % sec.photos.length;
    refreshDrawPhoto();
}

function deleteDrawPhoto() {
    const sec = appData.sections[appData.currentNo];
    if (!sec.photos.length) return;
    showConfirm('현재 사진을 삭제하시겠습니까?', () => {
        sec.photos.splice(sec.photoIdx, 1);
        sec.photoIdx = Math.max(0, Math.min(sec.photoIdx, sec.photos.length - 1));
        refreshDrawPhoto();
    });
}

// ==================== 저장/내보내기 ====================
function savePNG() {
    const no = appData.currentNo;
    const pts = getPoints(no);
    if (pts.length < 2) {
        showToast('측점 데이터가 2개 이상 필요합니다.');
        return;
    }

    const offCanvas = document.createElement('canvas');
    renderCrossSection(offCanvas, pts, no);

    offCanvas.toBlob(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `cross_section_NO${no + 1}_${timestamp()}.png`;
        a.click();
        URL.revokeObjectURL(url);
        showToast('PNG 저장 완료!');
    }, 'image/png');
}

function savePDF() {
    const no = appData.currentNo;
    const pts = getPoints(no);
    if (pts.length < 2) {
        showToast('측점 데이터가 2개 이상 필요합니다.');
        return;
    }

    const sec = appData.sections[no];
    const hasPhoto = sec.photos.length > 0;

    const offCanvas = document.createElement('canvas');
    renderCrossSection(offCanvas, pts, no);
    const crossImgData = offCanvas.toDataURL('image/png');

    const scale = 3;

    const crossImg = new Image();
    crossImg.onload = () => {
        const renderPDF = (photoImg) => {
            const blockW = offCanvas.width;
            const blockH = offCanvas.height;

            const pdfCanvas = document.createElement('canvas');
            pdfCanvas.width = blockW;
            if (photoImg) {
                pdfCanvas.height = blockH * 2;
            } else {
                pdfCanvas.height = blockH;
            }

            const ctx = pdfCanvas.getContext('2d');
            ctx.fillStyle = 'white';
            ctx.fillRect(0, 0, pdfCanvas.width, pdfCanvas.height);

            // Cross-section (top, full bleed)
            ctx.drawImage(crossImg, 0, 0, blockW, blockH);

            if (photoImg) {
                // Photo (bottom, same size, no margin)
                const photoRatio = photoImg.width / photoImg.height;
                const blockRatio = blockW / blockH;
                let pw, ph;
                if (photoRatio > blockRatio) {
                    pw = blockW;
                    ph = pw / photoRatio;
                } else {
                    ph = blockH;
                    pw = ph * photoRatio;
                }
                const px = (blockW - pw) / 2;
                const py = blockH + (blockH - ph) / 2;
                ctx.drawImage(photoImg, px, py, pw, ph);
            }

            pdfCanvas.toBlob(blob => {
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `cross_section_NO${no + 1}_${timestamp()}.png`;
                a.click();
                URL.revokeObjectURL(url);
                showToast(photoImg ? '횡단면도 + 현장사진 저장 완료!' : '횡단면도 저장 완료!');
            }, 'image/png');
        };

        if (hasPhoto) {
            const photoImg = new Image();
            photoImg.onload = () => renderPDF(photoImg);
            photoImg.src = sec.photos[sec.photoIdx].dataUrl;
        } else {
            renderPDF(null);
        }
    };
    crossImg.src = crossImgData;
}

function exportCSV() {
    const no = appData.currentNo;
    const data = appData.allTableData[no];
    let csv = '\uFEFF측점명,DL(mm),DH(mm),비고\n'; // BOM for Excel
    for (const row of data) {
        csv += row.map(v => `"${v}"`).join(',') + '\n';
    }

    const blob = new Blob([csv], {type: 'text/csv;charset=utf-8;'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cross_section_NO${no + 1}_${timestamp()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    showToast(`NO.${no + 1} CSV 내보내기 완료!`);
}

function importCSV() {
    document.getElementById('csvFileInput').click();
}

function handleCSVFile(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
        const text = e.target.result;
        const lines = text.split('\n');
        const no = appData.currentNo;
        let count = 0;

        for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || trimmed.startsWith('#') || trimmed.startsWith('측점명')) continue;

            // Handle quoted CSV
            const parts = parseCSVLine(trimmed);
            if (parts.length < 2) continue;

            try {
                let name, dl, dh, note;
                if (parts.length === 2) {
                    name = ''; dl = parseFloat(parts[0]); dh = parseFloat(parts[1]); note = '';
                } else {
                    name = parts[0];
                    dl = parseFloat(parts[1]);
                    dh = parseFloat(parts[2]);
                    note = parts[3] || '';
                }
                if (isNaN(dl) || isNaN(dh)) continue;
                appData.allTableData[no].push([name, dl, dh, note]);
                count++;
            } catch (e) { continue; }
        }

        refreshTable();
        showToast(`NO.${no + 1}에 ${count}개 측점 가져오기 완료!`);
    };
    reader.readAsText(file, 'UTF-8');
    event.target.value = '';
}

function parseCSVLine(line) {
    const result = [];
    let current = '';
    let inQuotes = false;
    for (const ch of line) {
        if (ch === '"') { inQuotes = !inQuotes; }
        else if (ch === ',' && !inQuotes) { result.push(current.trim()); current = ''; }
        else { current += ch; }
    }
    result.push(current.trim());
    return result;
}

// ==================== 유틸리티 ====================
function timestamp() {
    const d = new Date();
    return `${d.getFullYear()}${String(d.getMonth()+1).padStart(2,'0')}${String(d.getDate()).padStart(2,'0')}_${String(d.getHours()).padStart(2,'0')}${String(d.getMinutes()).padStart(2,'0')}${String(d.getSeconds()).padStart(2,'0')}`;
}

function showToast(msg) {
    const toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 2500);
}

function showConfirm(msg, onYes) {
    const overlay = document.getElementById('modalOverlay');
    document.getElementById('modalTitle').textContent = '확인';
    document.getElementById('modalMsg').textContent = msg;
    overlay.style.display = 'flex';

    const yesBtn = document.getElementById('modalYes');
    const noBtn = document.getElementById('modalNo');

    const cleanup = () => {
        overlay.style.display = 'none';
        yesBtn.onclick = null;
        noBtn.onclick = null;
    };

    yesBtn.onclick = () => { onYes(); cleanup(); };
    noBtn.onclick = cleanup;
}
