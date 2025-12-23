#!/usr/bin/env python3
"""Take screenshot of library page with golden dataset."""

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # Go to library page
    page.goto("http://localhost:5173/library")
    page.wait_for_load_state("networkidle")

    # Uncheck "Show finished only" if it's limiting results
    checkbox = page.locator('input[type="checkbox"]').first
    if checkbox.is_checked():
        checkbox.uncheck()
        page.wait_for_timeout(1000)

    # Wait for content to load
    page.wait_for_timeout(2000)

    # Take screenshot
    page.screenshot(path="/tmp/skillforge-library-restored.png", full_page=True)
    print("Screenshot saved to /tmp/skillforge-library-restored.png")

    # Check API directly
    response = page.request.get("http://localhost:8500/api/v1/library?limit=5")
    data = response.json()
    print(f"\nLibrary API: {data['total']} total analyses")
    for item in data["items"][:5]:
        print(f"  - {item['title'] or 'Untitled'} ({item['status']})")

    browser.close()
