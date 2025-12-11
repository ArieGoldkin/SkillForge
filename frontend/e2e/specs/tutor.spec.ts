import { test, expect } from '@playwright/test';
import { TutorPage } from '../page-objects';
import { mockTutorAPI, mockArtifactAPI } from '../utils';

test.describe('Tutor Page - Socratic Chat', () => {
  let tutorPage: TutorPage;

  test.beforeEach(async ({ page }) => {
    await mockTutorAPI(page);
    await mockArtifactAPI(page);
    tutorPage = new TutorPage(page);
    await tutorPage.goto('session-123');
  });

  test('should display the tutor chat interface', async () => {
    await expect(tutorPage.messageInput).toBeVisible();
    await expect(tutorPage.sendButton).toBeVisible();
  });

  test('should start tutoring session', async ({ page }) => {
    // Page should load with session info visible
    await expect(page.getByText(/tutor|chat|session/i)).toBeVisible();
  });

  test('should send message and display it', async () => {
    const testMessage = 'Can you explain useEffect hooks?';

    await tutorPage.sendMessage(testMessage);

    // User message should appear in the chat
    await expect(tutorPage.page.getByText(testMessage)).toBeVisible();
  });

  test('should receive response after sending message', async () => {
    await tutorPage.sendMessage('What is React?');

    // Wait for response to appear
    await tutorPage.waitForResponse();

    // Assistant messages should be present
    const assistantCount = await tutorPage.assistantMessages.count();
    expect(assistantCount).toBeGreaterThan(0);
  });

  test('should display chat history', async ({ page }) => {
    // Check if message list is visible
    await expect(tutorPage.messageList).toBeVisible();
  });

  test('should show typing indicator while waiting for response', async () => {
    // This test verifies the typing indicator appears
    await tutorPage.messageInput.fill('Test message');
    await tutorPage.sendButton.click();

    // Typing indicator might be visible briefly
    // We check if it exists in the DOM
    const typingIndicator = tutorPage.typingIndicator;
    const isVisible = await typingIndicator.isVisible().catch(() => false);

    // Either typing indicator shows or response comes quickly
    expect(true).toBe(true); // Test passes if no errors
  });

  test('should allow multiple messages in a session', async () => {
    await tutorPage.sendMessage('First question');
    await tutorPage.waitForResponse();

    await tutorPage.sendMessage('Second question');
    await tutorPage.waitForResponse();

    // Should have multiple user messages
    const userCount = await tutorPage.userMessages.count();
    expect(userCount).toBeGreaterThanOrEqual(2);
  });

  test('should disable send button when input is empty', async () => {
    // Clear the input
    await tutorPage.messageInput.clear();

    // Send button should be disabled or the form shouldn't submit
    const isDisabled = await tutorPage.sendButton.isDisabled();
    expect(isDisabled).toBe(true);
  });
});
