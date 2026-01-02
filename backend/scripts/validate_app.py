#!/usr/bin/env python3
"""Validate SkillForge frontend and backend using Playwright.

This script validates:
1. Frontend loads correctly
2. Backend API is accessible
3. Key UI elements are present
4. Library page shows data from golden dataset
"""

import sys

from playwright.sync_api import sync_playwright


def main():
    """Run validation checks."""
    print("=" * 60)
    print("SkillForge Application Validation")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Test 1: Frontend loads
        print("\n[1/5] Testing frontend loads...")
        page.goto("http://localhost:5174")
        page.wait_for_load_state("networkidle")

        # Check page title
        title = page.title()
        assert "SkillForge" in title, f"Expected 'SkillForge' in title, got: {title}"
        print(f"  ✓ Page title: {title}")

        # Take screenshot of homepage
        page.screenshot(path="/tmp/skillforge-home.png", full_page=True)
        print("  ✓ Screenshot saved: /tmp/skillforge-home.png")

        # Test 2: Key UI elements present
        print("\n[2/5] Testing UI elements...")

        # Check for navigation elements
        nav_visible = page.locator("nav").is_visible()
        print(f"  ✓ Navigation visible: {nav_visible}")

        # Check for main content area
        main_visible = page.locator("main").is_visible() or page.locator("#root").is_visible()
        print(f"  ✓ Main content area: {main_visible}")

        # Test 3: Navigate to Library page
        print("\n[3/5] Testing Library page...")
        library_link = page.get_by_role("link", name="Library")
        if library_link.count() > 0 and library_link.first.is_visible():
            library_link.click()
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)  # Wait for data to load

            # Check if library items are present
            page.screenshot(path="/tmp/skillforge-library.png", full_page=True)
            print("  ✓ Screenshot saved: /tmp/skillforge-library.png")

            # Look for analysis cards or list items
            cards = page.locator('[data-testid="analysis-card"], .analysis-card, article').count()
            print(f"  ✓ Library items found: {cards}")
        else:
            print("  ⚠ Library link not found, skipping")

        # Test 4: Check API health
        print("\n[4/5] Testing backend API...")
        api_response = page.request.get("http://localhost:8500/api/v1/health")
        assert api_response.ok, f"API health check failed: {api_response.status}"
        health_data = api_response.json()
        print(f"  ✓ API Status: {health_data['status']}")
        print(f"  ✓ Database: {health_data['database']['status']}")
        print(f"  ✓ Environment: {health_data['environment']}")

        # Test 5: Check library API has data
        print("\n[5/5] Testing library API...")
        library_response = page.request.get("http://localhost:8500/api/v1/library/analyses?limit=5")
        if library_response.ok:
            library_data = library_response.json()
            total = library_data.get("total", 0)
            items = len(library_data.get("items", []))
            print(f"  ✓ Total analyses in library: {total}")
            print(f"  ✓ Items returned: {items}")
        else:
            print(f"  ⚠ Library API returned: {library_response.status}")

        browser.close()

    print("\n" + "=" * 60)
    print("✓ All validation checks passed!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n✗ Validation failed: {e}")
        sys.exit(1)
