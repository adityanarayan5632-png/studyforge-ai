interface Block {
  type: "h1" | "h2" | "list" | "paragraph";
  content: string | string[];
}

function parseNotes(raw: string): Block[] {
  const lines = raw.split("\n");
  const blocks: Block[] = [];
  let currentList: string[] = [];

  const flushList = () => {
    if (currentList.length) {
      blocks.push({ type: "list", content: currentList });
      currentList = [];
    }
  };

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) continue;

    if (/^#{1,2}\s+/.test(line)) {
      flushList();
      const level = line.startsWith("##") ? "h2" : "h1";
      blocks.push({ type: level, content: line.replace(/^#{1,2}\s+/, "") });
      continue;
    }

    if (/^[-*•]\s+/.test(line)) {
      currentList.push(line.replace(/^[-*•]\s+/, ""));
      continue;
    }

    flushList();
    blocks.push({ type: "paragraph", content: line });
  }
  flushList();

  return blocks;
}

export function NotesViewer({ raw }: { raw: string }) {
  const blocks = parseNotes(raw);

  return (
    <div className="space-y-3">
      {blocks.map((block, i) => {
        if (block.type === "h1") {
          return (
            <h2
              key={i}
              className="font-display text-xl text-ember-400 border-b border-ink-700 pb-2 pt-4 first:pt-0"
            >
              {block.content as string}
            </h2>
          );
        }
        if (block.type === "h2") {
          return (
            <h3 key={i} className="font-display text-base text-parchment-100 pt-2">
              {block.content as string}
            </h3>
          );
        }
        if (block.type === "list") {
          return (
            <ul key={i} className="list-disc space-y-1.5 pl-5 text-sm text-parchment-300">
              {(block.content as string[]).map((item, j) => (
                <li key={j}>{item}</li>
              ))}
            </ul>
          );
        }
        return (
          <p key={i} className="text-sm leading-relaxed text-parchment-300">
            {block.content as string}
          </p>
        );
      })}
    </div>
  );
}
