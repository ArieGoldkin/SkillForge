import { test, expect } from '@playwright/test';

// CORRECT URL: Uses artifact_id (not analysis_id)
// f3507dfd-3cca-4520-abf5-e8b12f97fc35 is the artifact for LangGraph Cloud article
const ARTIFACT_ID = "f3507dfd-3cca-4520-abf5-e8b12f97fc35";
const ANALYSIS_ID = "47637e29-9875-498d-84cd-25820dbb1155";

test.describe('Artifact Quality Audit', () => {
  test('Verify Mermaid, TOC, and Collapsibles render correctly', async ({ page }) => {
    // Console tracking
    const consoleErrors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });

    // Navigate to CORRECT artifact URL
    const url = `http://localhost:5173/artifact/${ARTIFACT_ID}?analysisId=${ANALYSIS_ID}`;
    console.log(`\n🔍 Navigating to: ${url}`);

    await page.goto(url);
    await page.waitForLoadState('networkidle');

    // Check for error state first
    const hasError = await page.locator('text=Failed to load').count();
    if (hasError > 0) {
      await page.screenshot({ path: '/tmp/audit_error.png' });
      console.log('❌ Error state detected - see /tmp/audit_error.png');
      throw new Error('Page shows error state');
    }

    // Wait for markdown content
    await page.waitForSelector('.markdown-preview, [class*="markdown"]', { timeout: 15000 });
    console.log('✅ Markdown content loaded');

    // Wait for Mermaid to render (async)
    await page.waitForTimeout(4000);

    // ====== COMPREHENSIVE AUDIT ======
    console.log('\n' + '='.repeat(60));
    console.log('📋 ARTIFACT QUALITY AUDIT');
    console.log('='.repeat(60));

    // 📊 MERMAID DIAGRAMS
    const mermaidContainers = await page.locator('[data-testid="mermaid-diagram"], .mermaid-container').count();
    const mermaidSvgs = await page.locator('.mermaid-container svg, [data-testid="mermaid-diagram"] svg').count();
    const mermaidErrors = await page.locator('.mermaid-error').count();

    console.log(`\n📊 MERMAID DIAGRAMS:`);
    console.log(`   Containers: ${mermaidContainers}`);
    console.log(`   SVGs rendered: ${mermaidSvgs}`);
    console.log(`   Render errors: ${mermaidErrors}`);
    const mermaidPass = mermaidSvgs > 0 && mermaidErrors === 0;
    console.log(`   Status: ${mermaidPass ? '✅ PASS' : '❌ FAIL'}`);

    // 📑 TABLE OF CONTENTS
    const tocNav = await page.locator('[data-testid="table-of-contents"], .toc-nav').count();
    const tocLinks = await page.locator('[data-testid="table-of-contents"] button, .toc-nav button').count();
    const tocWithType = await page.locator('.toc-nav button[type="button"], [data-testid="table-of-contents"] button[type="button"]').count();

    console.log(`\n📑 TABLE OF CONTENTS:`);
    console.log(`   TOC element found: ${tocNav > 0}`);
    console.log(`   Navigation links: ${tocLinks}`);
    console.log(`   Buttons with type="button": ${tocWithType}`);
    const tocPass = tocNav > 0 && tocLinks > 0;
    console.log(`   Status: ${tocPass ? '✅ PASS' : '❌ FAIL'}`);

    // 🔽 COLLAPSIBLE SECTIONS
    const detailsCount = await page.locator('details').count();
    const summaryCount = await page.locator('summary').count();

    // Test interactivity if collapsibles exist
    let collapseWorks = false;
    if (detailsCount > 0) {
      const firstDetails = page.locator('details').first();
      const wasOpen = await firstDetails.getAttribute('open');
      await page.locator('summary').first().click();
      await page.waitForTimeout(200);
      const nowOpen = await firstDetails.getAttribute('open');
      collapseWorks = (wasOpen === null) !== (nowOpen === null);
    }

    console.log(`\n🔽 COLLAPSIBLE SECTIONS:`);
    console.log(`   <details> elements: ${detailsCount}`);
    console.log(`   <summary> elements: ${summaryCount}`);
    console.log(`   Toggle works: ${detailsCount > 0 ? collapseWorks : 'N/A'}`);
    console.log(`   Status: ${detailsCount > 0 ? '✅ FOUND' : '⚠️ NONE IN CONTENT'}`);

    // ♿ ACCESSIBILITY
    const tocSvgAriaHidden = await page.locator('.toc-nav svg[aria-hidden="true"]').count();
    const tocSvgTotal = await page.locator('.toc-nav svg').count();
    const headingsWithId = await page.locator('.markdown-preview h1[id], .markdown-preview h2[id], .markdown-preview h3[id]').count();
    const totalHeadings = await page.locator('.markdown-preview h1, .markdown-preview h2, .markdown-preview h3').count();

    console.log(`\n♿ ACCESSIBILITY:`);
    console.log(`   TOC SVGs aria-hidden: ${tocSvgAriaHidden}/${tocSvgTotal}`);
    console.log(`   Headings with IDs: ${headingsWithId}/${totalHeadings}`);
    const a11yPass = tocSvgAriaHidden === tocSvgTotal || tocSvgTotal === 0;
    console.log(`   Status: ${a11yPass ? '✅ PASS' : '❌ FAIL'}`);

    // 🚨 CONSOLE ERRORS
    console.log(`\n🚨 CONSOLE ERRORS: ${consoleErrors.length}`);
    if (consoleErrors.length > 0) {
      consoleErrors.slice(0, 5).forEach(e => console.log(`   ❌ ${e.slice(0, 80)}`));
    } else {
      console.log('   ✅ No console errors');
    }

    // 📏 PAGE METRICS
    const pageHeight = await page.evaluate(() => document.body.scrollHeight);
    const bodyText = await page.locator('body').innerText();
    const wordCount = bodyText.split(/\s+/).filter(w => w.length > 0).length;

    console.log(`\n📏 PAGE METRICS:`);
    console.log(`   Page height: ${pageHeight}px`);
    console.log(`   Word count: ${wordCount}`);

    // 📸 SCREENSHOTS
    await page.screenshot({ path: '/tmp/artifact_audit_viewport.png' });
    await page.screenshot({ path: '/tmp/artifact_audit_full.png', fullPage: true });
    console.log(`\n📸 Screenshots: /tmp/artifact_audit_*.png`);

    // ====== FINAL SUMMARY ======
    const allPass = mermaidPass && tocPass && a11yPass;
    console.log('\n' + '='.repeat(60));
    console.log(`OVERALL: ${allPass ? '✅ ALL CHECKS PASSED' : '⚠️ ISSUES FOUND'}`);
    console.log('='.repeat(60) + '\n');

    // Assertions
    expect(mermaidContainers, 'Should have Mermaid containers').toBeGreaterThan(0);
    expect(mermaidSvgs, 'Mermaid SVGs should render').toBeGreaterThan(0);
    expect(mermaidErrors, 'No Mermaid errors').toBe(0);
    expect(tocNav, 'TOC should exist').toBeGreaterThan(0);
    expect(tocLinks, 'TOC should have links').toBeGreaterThan(0);
  });
});
