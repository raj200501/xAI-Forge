interface FiltersBarProps {
  query: string;
  provider: string;
  providers: string[];
  durationMin: string;
  durationMax: string;
  toolCallsMin: string;
  onChange: (next: {
    query: string;
    provider: string;
    durationMin: string;
    durationMax: string;
    toolCallsMin: string;
  }) => void;
}

export default function FiltersBar({
  query,
  provider,
  providers,
  durationMin,
  durationMax,
  toolCallsMin,
  onChange,
}: FiltersBarProps) {
  return (
    <div className="filters-bar">
      <input
        type="search"
        placeholder="Search traces..."
        value={query}
        onChange={(event) => onChange({ query: event.target.value, provider, durationMin, durationMax, toolCallsMin })}
      />
      <select
        value={provider}
        onChange={(event) => onChange({ query, provider: event.target.value, durationMin, durationMax, toolCallsMin })}
      >
        <option value="all">All providers</option>
        {providers.map((item) => (
          <option key={item} value={item}>
            {item}
          </option>
        ))}
      </select>
      <input
        type="number"
        min={0}
        placeholder="Min duration (s)"
        value={durationMin}
        onChange={(event) => onChange({ query, provider, durationMin: event.target.value, durationMax, toolCallsMin })}
      />
      <input
        type="number"
        min={0}
        placeholder="Max duration (s)"
        value={durationMax}
        onChange={(event) => onChange({ query, provider, durationMin, durationMax: event.target.value, toolCallsMin })}
      />
      <input
        type="number"
        min={0}
        placeholder="Min tool calls"
        value={toolCallsMin}
        onChange={(event) => onChange({ query, provider, durationMin, durationMax, toolCallsMin: event.target.value })}
      />
    </div>
  );
}
