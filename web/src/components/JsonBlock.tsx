import { useState } from "react";

interface JsonBlockProps {
  data: unknown;
}

export default function JsonBlock({ data }: JsonBlockProps) {
  const [expanded, setExpanded] = useState(false);
  const content = JSON.stringify(data, null, 2) || "";
  const preview = content.length > 280 ? `${content.slice(0, 280)}...` : content;
  return (
    <div className="json-block">
      <button
        className="ghost-button"
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
      >
        {expanded ? "Collapse" : "Expand"}
      </button>
      <pre>{expanded ? content : preview}</pre>
    </div>
  );
}
