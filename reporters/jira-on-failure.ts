import { existsSync, readFileSync } from "fs";
import { resolve } from "path";
import type {
  FullConfig,
  FullResult,
  Reporter,
  TestCase,
  TestResult,
} from "@playwright/test/reporter";

type JiraEnv = {
  baseUrl: string;
  email: string;
  apiToken: string;
  projectKey: string;
  issueType: string;
  enabled: boolean;
};

function loadDotEnv(filePath: string): void {
  if (!existsSync(filePath)) return;
  for (const line of readFileSync(filePath, "utf8").split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq <= 0) continue;
    const key = trimmed.slice(0, eq).trim();
    let value = trimmed.slice(eq + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    if (!(key in process.env)) process.env[key] = value;
  }
}

function truthy(value: string | undefined): boolean {
  return ["1", "true", "yes", "on"].includes((value || "").toLowerCase());
}

function jiraEnv(): JiraEnv {
  loadDotEnv(resolve(process.cwd(), ".env"));
  const baseUrl = (process.env.JIRA_BASE_URL || "").replace(/\/$/, "");
  const email = process.env.JIRA_EMAIL || "";
  const apiToken = process.env.JIRA_API_TOKEN || "";
  const projectKey = process.env.JIRA_PROJECT_KEY || "";
  const issueType = process.env.JIRA_ISSUE_TYPE || "Story";
  const enabled =
    truthy(process.env.JIRA_ON_TEST_FAILURE) && Boolean(baseUrl && email && apiToken && projectKey);
  return { baseUrl, email, apiToken, projectKey, issueType, enabled };
}

function adfFromText(text: string) {
  const paragraphs = text.split("\n").map((line) => ({
    type: "paragraph",
    content: line ? [{ type: "text", text: line }] : [],
  }));
  return {
    type: "doc",
    version: 1,
    content: paragraphs.length ? paragraphs : [{ type: "paragraph", content: [] }],
  };
}

function failureDetails(test: TestCase, result: TestResult): string {
  const errors = result.errors.map((e) => e.message || e.value || String(e)).join("\n\n");
  const attachments = result.attachments
    .map((a) => `- ${a.name}${a.path ? ` (${a.path})` : ""}`)
    .join("\n");
  return [
    `Test: ${test.title}`,
    `File: ${test.location.file}:${test.location.line}`,
    `Project: ${test.parent.project()?.name || "unknown"}`,
    `Status: ${result.status}`,
    `Duration: ${result.duration}ms`,
    "",
    "Error:",
    errors || "(no error message)",
    "",
    "Attachments:",
    attachments || "(none)",
    "",
    "App logs (if server was running): data/logs/app.log",
    "Created automatically by Playwright Jira reporter (JIRA_ON_TEST_FAILURE=true).",
  ].join("\n");
}

async function createJiraIssue(
  env: JiraEnv,
  summary: string,
  description: string,
): Promise<string | null> {
  const auth = Buffer.from(`${env.email}:${env.apiToken}`).toString("base64");
  const res = await fetch(`${env.baseUrl}/rest/api/3/issue`, {
    method: "POST",
    headers: {
      Authorization: `Basic ${auth}`,
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      fields: {
        project: { key: env.projectKey },
        summary: summary.slice(0, 255),
        description: adfFromText(description),
        issuetype: { name: env.issueType },
        labels: ["qa-ai", "test-failure", "playwright"],
      },
    }),
  });
  if (!res.ok) {
    const body = await res.text();
    console.error(`[jira-on-failure] API ${res.status}: ${body.slice(0, 400)}`);
    return null;
  }
  const data = (await res.json()) as { key?: string };
  return data.key || null;
}

class JiraOnFailureReporter implements Reporter {
  private env: JiraEnv = jiraEnv();
  private failures: Array<{ test: TestCase; result: TestResult }> = [];

  onBegin(_config: FullConfig): void {
    if (!this.env.enabled) {
      console.log(
        "[jira-on-failure] disabled (set JIRA_ON_TEST_FAILURE=true and JIRA_* in .env to enable)",
      );
      return;
    }
    console.log(
      `[jira-on-failure] enabled → project ${this.env.projectKey} (${this.env.issueType})`,
    );
  }

  onTestEnd(test: TestCase, result: TestResult): void {
    if (!this.env.enabled) return;
    if (result.status === "failed" || result.status === "timedOut") {
      this.failures.push({ test, result });
    }
  }

  async onEnd(_result: FullResult): Promise<void> {
    if (!this.env.enabled || this.failures.length === 0) return;

    for (const { test, result } of this.failures) {
      const summary = `[QA-AI][FAIL] ${test.title}`.slice(0, 255);
      const key = await createJiraIssue(this.env, summary, failureDetails(test, result));
      if (key) {
        console.log(`[jira-on-failure] created ${this.env.baseUrl}/browse/${key}`);
      }
    }
  }
}

export default JiraOnFailureReporter;
