import { useState } from 'react';
import { PRESET_NAMES, DEFAULT_DATA } from '../utils/data';
import { ChevronUp, ChevronDown, Plus, Pencil, Trash2, XCircle } from 'lucide-react';

export default function InputMode({ data, selectedRow, onUpdate, onSelect }) {
  const [name, setName] = useState('');
  const [dl, setDl] = useState('');
  const [dh, setDh] = useState('');
  const [note, setNote] = useState('');

  const selectRow = (i) => {
    onSelect(i);
    const row = data[i];
    setName(String(row[0]));
    setDl(String(row[1]));
    setDh(String(row[2]));
    setNote(String(row[3]));
  };

  const addRow = () => {
    const d = parseFloat(dl || '0'), h = parseFloat(dh || '0');
    if (isNaN(d) || isNaN(h)) return;
    const next = [...data, [name, d, h, note]];
    onUpdate(next);
    onSelect(next.length - 1);
    setName(''); setNote('');
  };

  const editRow = () => {
    if (selectedRow < 0) return;
    const d = parseFloat(dl || '0'), h = parseFloat(dh || '0');
    if (isNaN(d) || isNaN(h)) return;
    const next = [...data];
    next[selectedRow] = [name, d, h, note];
    onUpdate(next);
  };

  const deleteRow = () => {
    if (selectedRow < 0) return;
    const next = data.filter((_, i) => i !== selectedRow);
    onUpdate(next);
    onSelect(Math.min(selectedRow, next.length - 1));
  };

  const clearAll = () => {
    if (confirm('모든 측점을 삭제하시겠습니까?')) {
      onUpdate([]);
      onSelect(-1);
    }
  };

  const moveRow = (dir) => {
    const j = selectedRow + dir;
    if (selectedRow < 0 || j < 0 || j >= data.length) return;
    const next = [...data];
    [next[selectedRow], next[j]] = [next[j], next[selectedRow]];
    onUpdate(next);
    onSelect(j);
  };

  const loadDefaults = () => {
    onUpdate(DEFAULT_DATA.map(r => [...r]));
    onSelect(-1);
  };

  return (
    <div className="flex flex-col gap-2 p-2">
      {/* Header */}
      <div className="flex justify-between items-center bg-dark-panel rounded-md px-3 py-2">
        <span className="text-sm font-bold">측점 데이터</span>
        <button onClick={loadDefaults} className="text-xs bg-accent px-3 py-1.5 rounded text-white hover:opacity-80">
          기본값 로드
        </button>
      </div>

      {/* Table */}
      <div className="max-h-[280px] overflow-y-auto rounded-md border border-dark-border">
        <table className="w-full text-xs">
          <thead className="sticky top-0 z-10">
            <tr className="bg-[#214070] text-white">
              <th className="py-2 px-1 font-semibold">측점명</th>
              <th className="py-2 px-1 font-semibold">DL(mm)</th>
              <th className="py-2 px-1 font-semibold">DH(mm)</th>
              <th className="py-2 px-1 font-semibold">비고</th>
            </tr>
          </thead>
          <tbody>
            {data.map((row, i) => (
              <tr
                key={i}
                onClick={() => selectRow(i)}
                className={`cursor-pointer transition-colors ${
                  i === selectedRow ? 'bg-accent/60' : i % 2 === 0 ? 'bg-dark-field/60' : 'bg-dark-panel/60'
                } hover:bg-accent/30`}
              >
                {row.map((val, j) => (
                  <td key={j} className="py-1.5 px-1 text-center">{val}</td>
                ))}
              </tr>
            ))}
            {data.length === 0 && (
              <tr><td colSpan={4} className="py-6 text-center text-hint">데이터 없음</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Move Buttons */}
      <div className="flex gap-2">
        <button onClick={() => moveRow(-1)} className="flex-1 flex items-center justify-center gap-1 bg-dark-field py-1.5 rounded text-xs hover:bg-dark-border">
          <ChevronUp size={14} /> UP
        </button>
        <button onClick={() => moveRow(1)} className="flex-1 flex items-center justify-center gap-1 bg-dark-field py-1.5 rounded text-xs hover:bg-dark-border">
          <ChevronDown size={14} /> DOWN
        </button>
      </div>

      {/* Input Form */}
      <div className="bg-dark-panel rounded-md p-3 flex flex-col gap-2">
        <div className="grid grid-cols-2 gap-2">
          <input value={name} onChange={e => setName(e.target.value)} placeholder="측점명"
            className="bg-dark-field border border-dark-border rounded px-2.5 py-2 text-sm text-white placeholder-hint outline-none focus:border-accent" />
          <input value={dl} onChange={e => setDl(e.target.value)} placeholder="DL (mm)" type="number" step="any"
            className="bg-dark-field border border-dark-border rounded px-2.5 py-2 text-sm text-white placeholder-hint outline-none focus:border-accent" />
          <input value={dh} onChange={e => setDh(e.target.value)} placeholder="DH (mm)" type="number" step="any"
            className="bg-dark-field border border-dark-border rounded px-2.5 py-2 text-sm text-white placeholder-hint outline-none focus:border-accent" />
          <input value={note} onChange={e => setNote(e.target.value)} placeholder="비고"
            className="bg-dark-field border border-dark-border rounded px-2.5 py-2 text-sm text-white placeholder-hint outline-none focus:border-accent" />
        </div>

        {/* Presets */}
        <div className="flex flex-wrap gap-1">
          {PRESET_NAMES.map(n => (
            <button key={n} onClick={() => setName(n)}
              className="text-[10px] bg-[#2e5090] px-2 py-1 rounded text-white hover:bg-[#3a6ab0]">
              {n}
            </button>
          ))}
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          <button onClick={addRow} className="flex-1 flex items-center justify-center gap-1 bg-success text-white py-2 rounded text-sm font-medium hover:opacity-85">
            <Plus size={14} /> 추가
          </button>
          <button onClick={editRow} className="flex-1 flex items-center justify-center gap-1 bg-accent text-white py-2 rounded text-sm font-medium hover:opacity-85">
            <Pencil size={14} /> 수정
          </button>
          <button onClick={deleteRow} className="flex-1 flex items-center justify-center gap-1 bg-danger text-white py-2 rounded text-sm font-medium hover:opacity-85">
            <Trash2 size={14} /> 삭제
          </button>
          <button onClick={clearAll} className="flex-1 flex items-center justify-center gap-1 bg-[#802020] text-white py-2 rounded text-sm font-medium hover:opacity-85">
            <XCircle size={14} /> 전체삭제
          </button>
        </div>
      </div>
    </div>
  );
}
