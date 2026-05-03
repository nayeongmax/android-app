import { useRef, useState, useCallback } from 'react';
import { getPoints } from '../utils/data';
import { renderCrossSection } from '../utils/renderCanvas';
import { Download, FileImage, ChevronLeft, ChevronRight, ImagePlus, Trash2 } from 'lucide-react';

export default function DrawMode({ state, dispatch }) {
  const canvasRef = useRef(null);
  const [drawn, setDrawn] = useState(false);
  const [status, setStatus] = useState('');
  const fileInputRef = useRef(null);

  const no = state.currentNo;
  const data = state.allTableData[no];
  const sec = state.sections[no];
  const opts = { unit: state.unit, titleText: state.titleText, optLabels: state.optLabels, optDims: state.optDims, optGrid: state.optGrid, optHatch: state.optHatch };

  const draw = useCallback(() => {
    const pts = getPoints(data);
    if (pts.length < 2) { setStatus('측점이 2개 이상 필요합니다.'); return; }
    renderCrossSection(canvasRef.current, pts, no, opts);
    setDrawn(true);
    const s = state.unit === 'm' ? 0.001 : 1;
    const xs = pts.map(p => p.l * s);
    const totalW = (Math.max(...xs) - Math.min(...xs)) / s;
    setStatus(`[NO.${no + 1}]  측점 ${pts.length}개 | 전체폭 ${totalW.toLocaleString()} mm | 완료`);
  }, [data, no, opts, state.unit]);

  const savePNG = () => {
    const pts = getPoints(data);
    if (pts.length < 2) return;
    const off = document.createElement('canvas');
    renderCrossSection(off, pts, no, opts);
    off.toBlob(blob => {
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `cross_section_NO${no + 1}.png`;
      a.click(); URL.revokeObjectURL(a.href);
    }, 'image/png');
  };

  const savePDF = () => {
    const pts = getPoints(data);
    if (pts.length < 2) return;
    const off = document.createElement('canvas');
    renderCrossSection(off, pts, no, opts);
    const crossData = off.toDataURL('image/png');
    const blockW = off.width, blockH = off.height;
    const crossImg = new Image();
    crossImg.onload = () => {
      const render = (photoImg) => {
        const pdf = document.createElement('canvas');
        pdf.width = blockW;
        pdf.height = photoImg ? blockH * 2 : blockH;
        const ctx = pdf.getContext('2d');
        ctx.fillStyle = 'white';
        ctx.fillRect(0, 0, pdf.width, pdf.height);
        ctx.drawImage(crossImg, 0, 0, blockW, blockH);
        if (photoImg) ctx.drawImage(photoImg, 0, blockH, blockW, blockH);
        pdf.toBlob(blob => {
          const a = document.createElement('a');
          a.href = URL.createObjectURL(blob);
          a.download = `cross_section_NO${no + 1}.png`;
          a.click(); URL.revokeObjectURL(a.href);
        }, 'image/png');
      };
      if (sec.photos.length > 0) {
        const pi = new Image();
        pi.onload = () => render(pi);
        pi.src = sec.photos[sec.photoIdx].dataUrl;
      } else { render(null); }
    };
    crossImg.src = crossData;
  };

  const toggleOpt = (key) => dispatch({ type: 'TOGGLE_OPT', key });
  const toggleUnit = () => dispatch({ type: 'TOGGLE_UNIT' });

  const addPhoto = () => fileInputRef.current?.click();
  const handleFiles = (e) => {
    for (const file of e.target.files) {
      const reader = new FileReader();
      reader.onload = (ev) => dispatch({ type: 'ADD_PHOTO', dataUrl: ev.target.result, name: file.name });
      reader.readAsDataURL(file);
    }
    e.target.value = '';
  };

  const optBtn = (key, label) => (
    <button onClick={() => toggleOpt(key)}
      className={`flex-1 py-1.5 rounded text-xs font-medium transition-colors ${state[`opt${key.charAt(0).toUpperCase() + key.slice(1)}`] ? 'bg-[#388060] text-white' : 'bg-dark-field text-hint'}`}>
      {label}
    </button>
  );

  return (
    <div className="flex flex-col gap-2 p-2">
      {/* Options */}
      <div className="flex gap-1">
        {optBtn('labels', '측점명')}
        {optBtn('dims', '치수선')}
        {optBtn('grid', '격자')}
        {optBtn('hatch', '해치')}
        <button onClick={toggleUnit} className="px-3 py-1.5 rounded text-xs font-medium bg-[#604890] text-white">
          {state.unit}
        </button>
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <button onClick={draw} className="flex-1 flex items-center justify-center gap-1 bg-success text-white py-2 rounded text-sm font-medium hover:opacity-85">
          횡단면도 그리기
        </button>
        <button onClick={savePNG} className="flex-1 flex items-center justify-center gap-1 bg-accent text-white py-2 rounded text-sm font-medium hover:opacity-85">
          <Download size={14} /> PNG
        </button>
        <button onClick={savePDF} className="flex-1 flex items-center justify-center gap-1 bg-[#8c4030] text-white py-2 rounded text-sm font-medium hover:opacity-85">
          <FileImage size={14} /> PDF
        </button>
      </div>

      {/* Canvas */}
      <div className="bg-[#0f1420] rounded-md overflow-hidden">
        <canvas ref={canvasRef} width={1200} height={900} style={{ width: '100%', height: 'auto', display: drawn ? 'block' : 'none' }} />
        {!drawn && <div className="py-12 text-center text-hint text-sm">횡단면도를 그리려면<br />[횡단면도 그리기]를 누르세요</div>}
      </div>

      {/* Photo Section */}
      <div>
        <div className="flex items-center gap-1 bg-dark-panel rounded-t-md px-2 py-1">
          <button onClick={() => dispatch({ type: 'PREV_PHOTO' })} className="p-1 rounded bg-dark-field hover:bg-dark-border"><ChevronLeft size={14} /></button>
          <span className="flex-1 text-center text-xs text-hint">
            {sec.photos.length > 0 ? `현장사진 ${sec.photoIdx + 1}/${sec.photos.length}` : '현장사진 없음'}
          </span>
          <button onClick={() => dispatch({ type: 'NEXT_PHOTO' })} className="p-1 rounded bg-dark-field hover:bg-dark-border"><ChevronRight size={14} /></button>
          <button onClick={addPhoto} className="flex items-center gap-1 text-xs bg-success text-white px-2 py-1 rounded hover:opacity-85">
            <ImagePlus size={12} /> 추가
          </button>
          <button onClick={() => dispatch({ type: 'DELETE_PHOTO' })} className="flex items-center gap-1 text-xs bg-danger text-white px-2 py-1 rounded hover:opacity-85">
            <Trash2 size={12} />
          </button>
          <input ref={fileInputRef} type="file" accept="image/*" multiple className="hidden" onChange={handleFiles} />
        </div>
        <div className="bg-[#0a0e18] rounded-b-md flex items-center justify-center overflow-hidden" style={{ aspectRatio: '4/3' }}>
          {sec.photos.length > 0
            ? <img src={sec.photos[sec.photoIdx].dataUrl} className="w-full h-full object-contain" />
            : <span className="text-hint text-sm">사진을 추가하면 횡단면도와 비교할 수 있습니다</span>
          }
        </div>
      </div>

      {status && <div className="text-xs text-hint px-2">{status}</div>}
    </div>
  );
}
