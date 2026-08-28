"use client";

import { FormEvent, useEffect, useState } from "react";
import { PageTitle } from "@/components/shell";
import { ChatMarkdown } from "@/components/Markdown";
import { Button, Card, ErrorText, inputClass } from "@/components/ui";
import { api } from "@/lib/api";

type Msg = { role: string; content: string };
type Convo = { id: number; title: string };
type Source = { title?: string; category?: string };
type SuggestedMemory = { key: string; value: string; category?: string };

export default function CoachPage() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [cid, setCid] = useState<number | null>(null);
  const [convos, setConvos] = useState<Convo[]>([]);
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [demo, setDemo] = useState(false);
  const [memNote, setMemNote] = useState("");
  const [sources, setSources] = useState<Source[]>([]);
  const [pendingMemories, setPendingMemories] = useState<SuggestedMemory[]>([]);

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
    setError("");
    try {
      const row = await api<{ messages: Msg[] }>(`/api/career/conversations/${id}`);
      setCid(id);
      setMessages(row.messages?.length ? row.messages : []);
      setSources([]);
      setPendingMemories([]);
      setDemo(false);
      setMemNote("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not open that conversation");
    }
  }

  async function confirmMemories() {
    setError("");
    try {
      await api("/api/career/memories/confirm", {
        method: "POST",
        body: JSON.stringify({ memories: pendingMemories }),
      });
      setMemNote(`Saved to career memory: ${pendingMemories.map((x) => x.key).join(", ")}`);
      setPendingMemories([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save to memory");
    }
  }

  function newChat() {
    setCid(null);
    setSources([]);
    setPendingMemories([]);
    setDemo(false);
    setMemNote("");
    setMessages([
      {
        role: "assistant",
        content: "New conversation. Your profile and career memory still apply.",
      },
    ]);
  }

  async function removeConvo(c: Convo) {
    if (!confirm(`Delete “${c.title || "this conversation"}”?`)) return;
    setError("");
    try {
      await api(`/api/career/conversations/${c.id}`, { method: "DELETE" });
      if (cid === c.id) newChat();
      await loadConvos();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete the conversation");
    }
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
        sources?: Source[];
        suggested_memories?: SuggestedMemory[];
      }>("/api/career/chat", {
        method: "POST",
        body: JSON.stringify({ message: userMsg, conversation_id: cid }),
      });
      setCid(res.conversation_id);
      setDemo(Boolean(res.demo));
      setMessages((m) => [...m, { role: "assistant", content: res.reply }]);
      setSources(res.sources || []);
      setPendingMemories(res.suggested_memories || []);
      loadConvos();
    } catch (err) {
      setMessages((m) => (m[m.length - 1]?.content === userMsg ? m.slice(0, -1) : m));
      setText(userMsg);
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
            <div
              key={c.id}
              className={`group flex items-center gap-1 rounded-lg pr-1 ${cid === c.id ? "bg-cream" : "hover:bg-cream/60"}`}
            >
              <button
                onClick={() => openConvo(c.id)}
                className="min-w-0 flex-1 truncate px-2 py-1.5 text-left text-sm"
              >
                {c.title || "Untitled"}
              </button>
              <button
                onClick={() => removeConvo(c)}
                aria-label={`Delete ${c.title || "conversation"}`}
                title="Delete conversation"
                className="px-1 text-xs text-mist opacity-0 transition-opacity hover:text-copper focus:opacity-100 group-hover:opacity-100"
              >
                ✕
              </button>
            </div>
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
          {sources.length > 0 && (
            <p className="mt-3 text-xs text-mist">
              Grounded in: {sources.map((s) => s.title).filter(Boolean).join(" · ")}
            </p>
          )}
          {pendingMemories.length > 0 && (
            <div className="mt-3 rounded-xl border border-copper/30 bg-copper/5 px-3 py-2 text-xs">
              <p className="text-mist">Remember this for future conversations?</p>
              <ul className="mt-1 space-y-0.5">
                {pendingMemories.map((m) => (
                  <li key={m.key}>
                    <span className="text-mist">{m.key}:</span> {m.value}
                  </li>
                ))}
              </ul>
              <div className="mt-2 flex gap-2">
                <Button variant="ghost" onClick={confirmMemories}>
                  Save to memory
                </Button>
                <Button variant="ghost" onClick={() => setPendingMemories([])}>
                  Not now
                </Button>
              </div>
            </div>
          )}
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
