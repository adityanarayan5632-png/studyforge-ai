import { Spinner } from "@/components/ui/Primitives";
import type { ChatMessage } from "@/lib/types";

export function ChatThread({
  messages,
  pending,
}: {
  messages: ChatMessage[];
  pending: boolean;
}) {
  return (
    <div className="flex flex-col gap-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
        >
          <div
            className={`max-w-[80%] rounded-xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
              message.role === "user"
                ? "bg-ember-500 text-ink-950"
                : "border border-ink-600 bg-ink-800 text-parchment-100"
            }`}
          >
            {message.content}
          </div>
        </div>
      ))}
      {pending && (
        <div className="flex justify-start">
          <div className="flex items-center gap-2 rounded-xl border border-ink-600 bg-ink-800 px-4 py-3 text-sm text-parchment-500">
            <Spinner /> Thinking...
          </div>
        </div>
      )}
    </div>
  );
}
