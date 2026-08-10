import { expect, test } from "../src/fixture";

test("home loads with scenario chips", async ({ page, chatPage }) => {
  await chatPage.open();
  const chips = page.getByTestId("scenario-chip");
  await expect(chips.first()).toBeVisible();
  expect(await chips.count()).toBeGreaterThanOrEqual(5);
  await expect(page.getByTestId("thread")).toContainText("scenario");
});

test("order status shows get_order in tool inspector", async ({ chatPage }) => {
  await chatPage.open();
  await chatPage.send("Where is my order 456?");

  expect(await chatPage.toolNames()).toEqual(["get_order"]);
  const reply = (await chatPage.lastAgentText()).toLowerCase();
  expect(reply).toContain("456");
  expect(reply).toContain("shipped");
  await expect(chatPage.lastToolCall()).not.toHaveClass(/denied|error/);
});

test("create order chip triggers create_order tool", async ({ page, chatPage }) => {
  await chatPage.open();
  await chatPage.clickScenario("Create order");
  await expect(page.getByTestId("message")).toHaveValue(/Create an order/i);
  await page.getByTestId("send-btn").click();
  await expect(page.getByTestId("bubble-agent").last()).toBeVisible({ timeout: 20_000 });

  expect(await chatPage.toolNames()).toEqual(["create_order"]);
  const payload = await chatPage.lastToolPayload().innerText();
  expect(payload.toLowerCase()).toContain("usb cable");
  expect(payload).toContain("19.9");
  expect(payload).toMatch(/"order_id":\s*"\d+"/);
});

test("create user flow in UI", async ({ chatPage }) => {
  await chatPage.open();
  await chatPage.send("Create user Maria email maria@example.com phone +359888111222");

  expect(await chatPage.toolNames()).toEqual(["create_user"]);
  const reply = await chatPage.lastAgentText();
  expect(reply).toContain("Maria");
  expect(reply).toContain("maria@example.com");
});

test("foreign order shows denied tool card", async ({ chatPage }) => {
  await chatPage.open();
  await chatPage.selectLanguage("bg");
  await chatPage.selectUser("123");
  await chatPage.send("Покажи ми поръчката на друг потребител 789.");

  expect(await chatPage.toolNames()).toContain("get_order");
  await expect(chatPage.toolCallByName("get_order")).toHaveClass(/denied/);
  const reply = (await chatPage.lastAgentText()).toLowerCase();
  expect(reply).not.toContain("econt");
  expect(reply).not.toContain("eco987654");
});

test("reset mock data shows status note", async ({ page, chatPage }) => {
  await chatPage.open();
  await chatPage.clickReset();
  await expect(page.locator(".status-note")).toContainText("tickets table cleared", {
    timeout: 10_000,
  });
});
