"use client";

import { useEffect, useState } from "react";
import { PageTitle } from "@/components/shell";
import { Button, Card, ErrorText, Field, inputClass } from "@/components/ui";
import { api } from "@/lib/api";

type Tool = { name: string; description: string; input_schema: { properties?: Record<string, { type: string }>; required?: string[] } };

export default function McpPage() {
  const [tools, setTools] = useState<Tool[]>([]);
  const [name, setName] = useState("get_dashboard");
  const [args, setArgs] = useState("{}");
  const [result, setResult] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api<{ tools: Tool[] }>("/api/mcp/tools")
      .then((r) => {
        setTools(r.tools || []);
        if (r.tools?.[0]) setName(r.tools[0].name);
      })
      .catch((e) => setError(e.message));
  }, []);

  async function call() {
    setError("");
    setResult("");
    try {
      const parsed = args.trim() ? JSON.parse(args) : {};
      const res = await api<{ result: unknown }>("/mcp", {
        method: "POST",
        body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "tools/call", params: { name, arguments: parsed } }),
      });
      setResult(JSON.stringify(res.result ?? res, null, 2));
    } catch (e) {
      setError(e instanceof Error ? e.message : "MCP call failed");
    }
  }

  return (
    <div>
      <PageTitle kicker="Phase 3" title="MCP integrations" />
      <p className="mb-6 max-w-2xl text-sm text-mist">
        Atelier exposes an HTTP MCP-style server at <code>POST /mcp</code>. Other agents can list and call tools with your Bearer token. This page is the local catalog.
      </p>
      <ErrorText error={error} />
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <Card>
          <h2 className="font-display text-2xl">Tools</h2>
          <ul className="mt-4 space-y-3">
            {tools.map((t) => (
              <li key={t.name}>
                <button className="text-left" onClick={() => setName(t.name)}>
                  <span className="font-medium">{t.name}</span>
                  <span className="mt-1 block text-sm text-mist">{t.description}</span>
                </button>
              </li>
            ))}
          </ul>
        </Card>
        <Card className="space-y-3">
          <h2 className="font-display text-2xl">Try a tool</h2>
          <Field label="Tool">
            <select className={inputClass} value={name} onChange={(e) => setName(e.target.value)}>
              {tools.map((t) => (
                <option key={t.name}>{t.name}</option>
              ))}
            </select>
          </Field>
          <Field label="Arguments JSON">
            <textarea className={inputClass} rows={5} value={args} onChange={(e) => setArgs(e.target.value)} />
          </Field>
          <Button onClick={call}>Call</Button>
          {result && <pre className="max-h-80 overflow-auto whitespace-pre-wrap text-xs">{result}</pre>}
        </Card>
      </div>
    </div>
  );
}
