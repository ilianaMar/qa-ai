import { type APIRequestContext, expect } from "@playwright/test";

export type ChatBody = {
  reply: string;
  language?: string;
  agent_mode?: string;
  tool_calls: Array<{
    name: string;
    arguments: Record<string, unknown>;
    result: unknown;
    error: string | null;
    denied: boolean;
  }>;
};

export async function resetStore(request: APIRequestContext): Promise<void> {
  const res = await request.post("/_qa/reset");
  expect(res.ok()).toBeTruthy();
}

export async function chat(
  request: APIRequestContext,
  message: string,
  opts: {
    userId?: string;
    language?: string;
    fault?: string;
  } = {},
): Promise<ChatBody> {
  const payload: Record<string, string> = {
    message,
    user_id: opts.userId ?? "123",
    language: opts.language ?? "en",
  };
  if (opts.fault) payload.fault = opts.fault;

  const res = await request.post("/chat", { data: payload });
  expect(res.ok(), await res.text()).toBeTruthy();
  return (await res.json()) as ChatBody;
}

export function toolNames(body: ChatBody): string[] {
  return body.tool_calls.map((t) => t.name);
}

export function firstTool(body: ChatBody, name: string) {
  const tool = body.tool_calls.find((t) => t.name === name);
  if (!tool) {
    throw new Error(`Tool ${name} not found in ${JSON.stringify(body.tool_calls)}`);
  }
  return tool;
}
