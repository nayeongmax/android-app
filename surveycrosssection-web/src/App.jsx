import { useReducer } from 'react';
import { createInitialState, DEFAULT_DATA } from './utils/data';
import NoTabs from './components/NoTabs';
import InputMode from './components/InputMode';
import DrawMode from './components/DrawMode';

function reducer(state, action) {
  switch (action.type) {
    case 'SWITCH_NO':
      return { ...state, currentNo: action.idx, selectedRow: -1 };
    case 'SET_TAB':
      return { ...state, activeTab: action.tab };
    case 'UPDATE_TABLE': {
      const next = [...state.allTableData];
      next[state.currentNo] = action.data;
      return { ...state, allTableData: next };
    }
    case 'SELECT_ROW':
      return { ...state, selectedRow: action.idx };
    case 'TOGGLE_OPT': {
      const prop = `opt${action.key.charAt(0).toUpperCase() + action.key.slice(1)}`;
      return { ...state, [prop]: !state[prop] };
    }
    case 'TOGGLE_UNIT':
      return { ...state, unit: state.unit === 'mm' ? 'm' : 'mm' };
    case 'ADD_PHOTO': {
      const secs = [...state.sections];
      const sec = { ...secs[state.currentNo] };
      sec.photos = [...sec.photos, { dataUrl: action.dataUrl, name: action.name, note: '' }];
      if (sec.photos.length === 1) sec.photoIdx = 0;
      secs[state.currentNo] = sec;
      return { ...state, sections: secs };
    }
    case 'PREV_PHOTO': {
      const secs = [...state.sections];
      const sec = { ...secs[state.currentNo] };
      if (sec.photos.length === 0) return state;
      sec.photoIdx = (sec.photoIdx - 1 + sec.photos.length) % sec.photos.length;
      secs[state.currentNo] = sec;
      return { ...state, sections: secs };
    }
    case 'NEXT_PHOTO': {
      const secs = [...state.sections];
      const sec = { ...secs[state.currentNo] };
      if (sec.photos.length === 0) return state;
      sec.photoIdx = (sec.photoIdx + 1) % sec.photos.length;
      secs[state.currentNo] = sec;
      return { ...state, sections: secs };
    }
    case 'DELETE_PHOTO': {
      const secs = [...state.sections];
      const sec = { ...secs[state.currentNo] };
      if (sec.photos.length === 0) return state;
      sec.photos = sec.photos.filter((_, i) => i !== sec.photoIdx);
      sec.photoIdx = Math.max(0, Math.min(sec.photoIdx, sec.photos.length - 1));
      secs[state.currentNo] = sec;
      return { ...state, sections: secs };
    }
    default:
      return state;
  }
}

export default function App() {
  const [state, dispatch] = useReducer(reducer, null, createInitialState);

  return (
    <div className="flex flex-col min-h-dvh">
      {/* Header */}
      <header className="text-center py-4 px-4 bg-gradient-to-br from-[#1a2540] to-[#2a3a5a] border-b-2 border-accent">
        <h1 className="text-lg font-bold tracking-wide">횡단면도 작성 프로그램</h1>
        <p className="text-[11px] text-hint mt-0.5">현장 횡단면 실측 도면 작성 도구</p>
      </header>

      {/* NO Tabs */}
      <NoTabs currentNo={state.currentNo} onSwitch={(i) => dispatch({ type: 'SWITCH_NO', idx: i })} />

      {/* Sub Tabs */}
      <div className="flex gap-0.5 p-1 bg-dark-bg">
        {['input', 'draw'].map(tab => (
          <button
            key={tab}
            onClick={() => dispatch({ type: 'SET_TAB', tab })}
            className={`flex-1 py-2.5 rounded text-sm font-medium transition-colors ${
              state.activeTab === tab ? 'bg-success text-white font-bold' : 'bg-dark-field text-hint hover:bg-dark-border'
            }`}
          >
            {tab === 'input' ? '입력' : '그리기'}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1">
        {state.activeTab === 'input' ? (
          <InputMode
            data={state.allTableData[state.currentNo]}
            selectedRow={state.selectedRow}
            onUpdate={(data) => dispatch({ type: 'UPDATE_TABLE', data })}
            onSelect={(idx) => dispatch({ type: 'SELECT_ROW', idx })}
          />
        ) : (
          <DrawMode state={state} dispatch={dispatch} />
        )}
      </div>
    </div>
  );
}
