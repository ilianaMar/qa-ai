import { expect, type Page } from "@playwright/test";

/** Page Object for the chat UI — methods used by the chatPage fixture. */
export class ChatPage {
  constructor(readonly page: Page) {}

  async open(): Promise<void> {
    await this.page.goto("/");
    await expect(this.page.getByTestId("brand")).toBeVisible();
    await expect(this.page.getByTestId("mode-badge")).toContainText("mode:");
  }

  async send(message: string): Promise<void> {
    await this.page.getByTestId("message").fill(message);
    await this.page.getByTestId("send-btn").click();
    await expect(this.page.getByTestId("bubble-agent").last()).toBeVisible({
      timeout: 20_000,
    });
  }

  async lastAgentText(): Promise<string> {
    return this.page.getByTestId("bubble-agent").last().getByTestId("bubble-text").innerText();
  }

  async toolNames(): Promise<string[]> {
    return this.page.getByTestId("bubble-agent").last().getByTestId("tool-name").allTextContents();
  }

  async selectLanguage(lang: "en" | "bg"): Promise<void> {
    await this.page.getByTestId("language").selectOption(lang);
  }

  async selectUser(userId: string): Promise<void> {
    await this.page.getByTestId("user-id").selectOption(userId);
  }

  async clickScenario(label: string): Promise<void> {
    await this.page.getByTestId("scenario-chip").filter({ hasText: label }).click();
  }

  async clickReset(): Promise<void> {
    await this.page.getByTestId("reset-btn").click();
  }

  lastToolPayload() {
    return this.page.getByTestId("bubble-agent").last().getByTestId("tool-payload");
  }

  lastToolCall() {
    return this.page.getByTestId("bubble-agent").last().getByTestId("tool-call");
  }

  toolCallByName(name: string) {
    return this.lastToolCall().filter({
      has: this.page.getByTestId("tool-name").filter({ hasText: name }),
    });
  }
}
