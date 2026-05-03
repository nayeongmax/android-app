export default function NoTabs({ currentNo, onSwitch }) {
  return (
    <div className="flex gap-1 p-1.5 bg-dark-panel overflow-x-auto">
      {Array.from({ length: 6 }, (_, i) => (
        <button
          key={i}
          onClick={() => onSwitch(i)}
          className={`px-4 py-2 rounded text-sm font-medium whitespace-nowrap transition-colors ${
            i === currentNo
              ? 'bg-accent text-white font-bold'
              : 'bg-dark-field text-hint hover:bg-dark-border'
          }`}
        >
          NO.{i + 1}
        </button>
      ))}
    </div>
  );
}
