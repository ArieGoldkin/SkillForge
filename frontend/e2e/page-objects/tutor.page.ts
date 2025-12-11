import type { Page, Locator } from '@playwright/test';
import { expect } from '@playwright/test';
import { BasePage } from './base.page';

/**
 * Page object for the Tutor page (Socratic tutoring chat).
 * Handles chat interactions and session management.
 */
export class TutorPage extends BasePage {
  readonly messageInput: Locator;
  readonly sendButton: Locator;
  readonly messageList: Locator;
  readonly userMessages: Locator;
  readonly assistantMessages: Locator;
  readonly typingIndicator: Locator;
  readonly sessionInfo: Locator;

  constructor(page: Page) {
    super(page);
    this.messageInput = page.getByPlaceholder(/type.*message|ask.*question/i);
    this.sendButton = page.getByRole('button', { name: /send/i });
    this.messageList = page.getByTestId('message-list');
    this.userMessages = page.locator('[data-message-role="user"]');
    this.assistantMessages = page.locator('[data-message-role="assistant"]');
    this.typingIndicator = page.getByTestId('typing-indicator');
    this.sessionInfo = page.getByTestId('session-info');
  }

  async goto(sessionId: string) {
    await this.navigate(`/tutor/${sessionId}`);
  }

  async sendMessage(message: string) {
    await this.messageInput.fill(message);
    await this.sendButton.click();
  }

  async waitForResponse(timeout = 30000) {
    // Wait for typing indicator to appear and disappear
    await expect(this.typingIndicator).toBeVisible({ timeout: 5000 }).catch(() => {
      // Typing indicator might be very brief
    });
    await expect(this.typingIndicator).toBeHidden({ timeout });
  }

  async getMessageCount(): Promise<{ user: number; assistant: number }> {
    return {
      user: await this.userMessages.count(),
      assistant: await this.assistantMessages.count(),
    };
  }

  async expectUserMessageCount(count: number) {
    await expect(this.userMessages).toHaveCount(count);
  }

  async expectAssistantMessageCount(count: number) {
    await expect(this.assistantMessages).toHaveCount(count);
  }

  async expectTyping() {
    await expect(this.typingIndicator).toBeVisible();
  }

  async getLastAssistantMessage(): Promise<string> {
    const lastMessage = this.assistantMessages.last();
    return (await lastMessage.textContent()) || '';
  }
}
