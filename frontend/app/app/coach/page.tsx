"use client";

import { FormEvent, useEffect, useState } from "react";
import { PageTitle } from "@/components/shell";
import { ChatMarkdown } from "@/components/Markdown";
import { Button, Card, ErrorText, inputClass } from "@/components/ui";
import { api } from "@/lib/api";

type Msg = { role: string; content: string };
type Convo = { id: number; title: string };

export default function CoachPage() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [cid, setCid] = useState<number | null>(null);
  const [convos, setConvos] = useState<Convo[]>([]);
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [demo, setDemo] = useState(false);
  const [memNote, setMemNote] = useState("");

  async function loadConvos() {
    try {
      setConvos(await api<Convo[]>("/api/career/conversations"));
    } catch {
      /* not signed in yet */
    }
  }

  useEffect(() => {
    setMessages([
      {
        role: "assistant",
        content:
          "I coach from your saved profile for whatever career you are actually in — architecture, arts, healthcare, teaching, computing, or anything else. Ask to compare two roles, pressure-test a goal, or tell me what feels stuck. Skill-gap and roadmaps have dedicated studios if you want the structured workflow.",
      },
    ]);
    loadConvos();
  }, []);

  async function openConvo(id: number) {
    const row = await api<{ messages: Msg[] }>(`/api/career/conversations/${id}`);
    setCid(id);
    setMessages(row.messages?.length ? row.messages : []);
  }

  function newChat() {
    setCid(null);
    setMessages([
      {
        role: "assistant",
        content: "New conversation. Your profile and career memory still apply.",
      },
    ]);
  }

  async function send(e: FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    const userMsg = text;
    setText("");
    setMessages((m) => [...m, { role: "user", content: userMsg }]);
    setBusy(true);
    setError("");
    setMemNote("");
    try {
      const res = await api<{
        reply: string;
        conversation_id: number;
        demo?: boolean;
        saved_memories?: { key: string }[];
      }>("/api/career/chat", {
        method: "POST",
        body: JSON.stringify({ message: userMsg, conversation_id: cid }),
      });
      setCid(res.conversation_id);
      setDemo(Boolean(res.demo));
      setMessages((m) => [...m, { role: "assistant", content: res.reply }]);
      if (res.saved_memories?.length) {
        setMemNote(`Saved to career memory: ${res.saved_memories.map((x) => x.key).join(", ")}`);
      }
      loadConvos();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageTitle
        kicker="Pillar 01"
        title="Career coach"
        action={
          <div className="flex gap-2">
            <Button href="/app/coach/skill-gap" variant="ghost">
              Skill-gap
            </Button>
            <Button href="/app/coach/roadmap" variant="ink">
              Roadmap
            </Button>
          </div>
        }
      />
      {demo && (
        <p className="mb-3 text-xs text-copper">
          Demo fallback — the model did not return a live reply. Check LLM settings if you added a key.
        </p>
      )}
      {memNote && <p className="mb-3 text-xs text-moss">{memNote}</p>}
      <ErrorText error={error} />
      <div className="grid gap-4 lg:grid-cols-[220px_1fr]">
        <Card className="h-fit space-y-2">
          <Button variant="ghost" className="w-full" onClick={newChat}>
            New chat
          </Button>
          <div className="text-xs uppercase tracking-wider text-mist">History</div>
          {convos.map((c) => (
            <button
              key={c.id}
              onClick={() => openConvo(c.id)}
              className={`block w-full truncate rounded-lg px-2 py-1.5 text-left text-sm ${
                cid === c.id ? "bg-cream" : "hover:bg-cream/60"
              }`}
            >
              {c.title || "Untitled"}
            </button>
          ))}
          {convos.length === 0 && <p className="text-xs text-mist">No saved chats yet.</p>}
        </Card>
        <Card className="flex min-h-[28rem] flex-col">
          <div className="flex-1 space-y-4 overflow-y-auto">
            {messages.map((m, i) => (
              <div
                key={i}
                className={
                  m.role === "user" ? "ml-12 rounded-2xl bg-cream px-4 py-3" : "mr-12 text-sm leading-relaxed"
                }
              >
                {m.role === "assistant" ? <ChatMarkdown text={m.content} /> : m.content}
              </div>
            ))}
          </div>
          <form onSubmit={send} className="mt-4 flex gap-2">
            <input
              className={inputClass}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Compare AI Engineer vs Data Scientist for my profile…"
            />
            <Button type="submit" disabled={busy}>
              {busy ? "…" : "Send"}
            </Button>
          </form>
        </Card>
      </div>
      <p className="mt-4 text-xs text-mist">
        Guidance is grounded in your profile. It is not a guarantee of employment.
      </p>
    </div>
  );
}
