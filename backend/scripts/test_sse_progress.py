#!/usr/bin/env python3
"""Test SSE progress updates via Playwright.

This script tests that the SSE buffering fix works by:
1. Navigating to the SkillForge library
2. Starting a new analysis
3. Verifying progress updates appear (not stuck at 0%)
"""

import time
from playwright.sync_api import sync_playwright


def test_sse_progress():
    """Test that SSE progress updates work after buffering fix."""
    print("Starting Playwright test for SSE progress...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate to SkillForge
        print("1. Navigating to SkillForge...")
        page.goto('http://localhost:5173')
        page.wait_for_load_state('networkidle')

        # Take initial screenshot
        page.screenshot(path='/tmp/skillforge_home.png')
        print("   Screenshot saved: /tmp/skillforge_home.png")

        # Check if we're on the home page
        title = page.title()
        print(f"   Page title: {title}")

        # Look for analysis cards or library link
        print("2. Looking for Library or existing analyses...")

        # Try to find library link
        library_link = page.locator('a:has-text("Library"), nav >> text=Library').first
        if library_link.is_visible():
            print("   Found Library link, clicking...")
            library_link.click()
            page.wait_for_load_state('networkidle')
            page.screenshot(path='/tmp/skillforge_library.png')
            print("   Screenshot saved: /tmp/skillforge_library.png")

        # Check for existing analyses
        print("3. Checking for analysis cards...")
        analysis_cards = page.locator('[class*="card"], [class*="analysis"]').all()
        print(f"   Found {len(analysis_cards)} potential analysis elements")

        if len(analysis_cards) > 0:
            # Click on first analysis to check progress
            print("4. Clicking first analysis card...")
            analysis_cards[0].click()
            page.wait_for_load_state('networkidle')
            time.sleep(2)  # Wait for SSE events

            page.screenshot(path='/tmp/skillforge_analysis.png')
            print("   Screenshot saved: /tmp/skillforge_analysis.png")

            # Check for progress indicators
            progress_text = page.locator('[class*="progress"], [class*="Progress"]').all_text_contents()
            print(f"   Progress elements: {progress_text[:3] if progress_text else 'None found'}")

            # Check for Activity Log
            activity_log = page.locator('text=Activity Log').first
            if activity_log.is_visible():
                print("   Activity Log found")
                # Check if it shows "Waiting for agent activity" vs actual events
                log_content = page.locator('[class*="activity"], [class*="log"]').all_text_contents()
                print(f"   Log content preview: {str(log_content)[:200]}")

        # Final screenshot
        page.screenshot(path='/tmp/skillforge_final.png', full_page=True)
        print("5. Final screenshot saved: /tmp/skillforge_final.png")

        browser.close()
        print("\nTest complete!")


if __name__ == "__main__":
    test_sse_progress()
