import { ReactNode } from "react";

function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? (
      <strong key={i} className="font-semibold text-ink">
        {part.slice(2, -2)}
      </strong>
    ) : (
      <span key={i}>{part}</span>
    )
  );
}

export function ChatMarkdown({ text }: { text: string }) {
  const lines = (text || "").replace(/\r\n/g, "\n").split("\n");
  const nodes: ReactNode[] = [];
  let bullets: string[] = [];

  const flushList = () => {
    if (!bullets.length) return;
    const items = bullets;
    bullets = [];
    nodes.push(
      <ul key={`ul-${nodes.length}`} className="my-2 list-disc space-y-1.5 pl-5 text-sm leading-relaxed">
        {items.map((item, i) => (
          <li key={i}>{inline(item)}</li>
        ))}
      </ul>
    );
  };

  lines.forEach((line, i) => {
    const heading = /^(#{1,6})\s+(.+)$/.exec(line.trim());
    if (heading) {
      flushList();
      const level = heading[1].length;
      const cls =
        level <= 2
          ? "mt-5 font-display text-2xl font-semibold tracking-tight text-ink"
          : "mt-4 font-display text-xl font-semibold tracking-tight text-ink";
      nodes.push(
        <p key={`h-${i}`} className={cls}>
          {inline(heading[2])}
        </p>
      );
      return;
    }
    if (/^\s*[-*]\s+/.test(line)) {
      bullets.push(line.replace(/^\s*[-*]\s+/, ""));
      return;
    }
    flushList();
    if (!line.trim()) {
      nodes.push(<div key={`sp-${i}`} className="h-2" />);
      return;
    }
    nodes.push(
      <p key={`p-${i}`} className="text-sm leading-relaxed text-ink">
        {inline(line)}
      </p>
    );
  });
  flushList();
  return <div className="space-y-0.5">{nodes}</div>;
}
