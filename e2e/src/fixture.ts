/**
 * Playwright fixtures — see https://playwright.dev/docs/test-fixtures
 *
 * Pattern:
 * 1. Declare fixture types
 * 2. base.extend({ fixtureName: async ({ deps }, use) => { setup; await use(value); cleanup } })
 * 3. Tests import { test, expect } from this file and destructure fixtures: async ({ chatPage }) => ...
 */
import { test as base, expect } from "@playwright/test";
import { resetStore } from "../../api/helpers";
import { ChatPage } from "./chat-page";

type UiFixtures = {
  chatPage: ChatPage;
};

export const test = base.extend<UiFixtures>({
  chatPage: async ({ page, request }, use) => {
    // setup (runs before the test)
    await resetStore(request);
    const chatPage = new ChatPage(page);
    await use(chatPage);

    // cleanup (runs after the test) — none needed for now
  },
});

export { expect };
