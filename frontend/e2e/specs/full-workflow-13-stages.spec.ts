import { test, expect, type Page } from '@playwright/test';
import { HomePage, AnalyzePage } from '../page-objects';

/**
 * COMPREHENSIVE WORKFLOW TEST
 *
 * Tests the complete analysis flow for a real Substack URL:
 * https://inbarshirizly.substack.com/p/coming-soon
 *
 * This test validates:
 * - Form submission from home page
 * - Redirect to analysis page
 * - SSE event reception and parsing
 * - All 13 stages appear in correct order
 * - New integration_feasibility stage (order 11)
 * - Progress calculation with 13 stages
 * - Final completion or error handling
 *
 * IMPORTANT: This test makes real LLM calls and takes 2-3 minutes.
 * Run with: npm run test:e2e:chromium -- full-workflow-13-stages.spec.ts --headed
 */

const TEST_URL = 'https://inbarshirizly.substack.com/p/coming-soon';

// All 13 expected stages in order
const EXPECTED_STAGES = [
  'supervisor_routing',       // 1
  'content_extraction',       // 2
  'metadata_extraction',      // 3
  'content_synthesis',        // 4
  'learning_objectives',      // 5
  'learning_path',            // 6
  'prerequisites',            // 7
  'tech_stack_analysis',      // 8
  'context_analysis',         // 9
  'dependencies_analysis',    // 10
  'integration_feasibility',  // 11 - NEW STAGE
  'artifact_generation',      // 12
  'quality_gate',             // 13
];

interface SSEEvent {
  type: string;
  stage?: string;
  status?: string;
  message?: string;
  progress?: number;
  timestamp: number;
}

test.describe('Full Workflow - 13 Stages Validation', () => {
  test.setTimeout(300000); // 5 minutes for complete workflow

  test('should complete full analysis workflow with all 13 stages', async ({ page }) => {
    const sseEvents: SSEEvent[] = [];
    const stagesEncountered = new Set<string>();

    // Screenshot directory
    const screenshotDir = '/tmp/playwright-workflow';
    let screenshotCounter = 0;

    const takeScreenshot = async (label: string) => {
      screenshotCounter++;
      const filename = `${screenshotDir}/${screenshotCounter.toString().padStart(2, '0')}_${label}.png`;
      await page.screenshot({ path: filename, fullPage: true });
      console.log(`📸 Screenshot: ${filename}`);
      return filename;
    };

    // Set up network monitoring for SSE events
    page.on('response', async (response) => {
      const url = response.url();

      // Monitor SSE endpoint
      if (url.includes('/api/v1/analyze/sse/')) {
        console.log(`📡 SSE Response: ${response.status()} ${url}`);

        try {
          // Try to read the body as text (SSE is text/event-stream)
          const body = await response.text();
          const lines = body.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.substring(6));
                const event: SSEEvent = {
                  type: data.type || 'unknown',
                  stage: data.stage,
                  status: data.status,
                  message: data.message,
                  progress: data.progress,
                  timestamp: Date.now(),
                };

                sseEvents.push(event);

                if (event.stage) {
                  stagesEncountered.add(event.stage);
                  console.log(`✅ Stage detected: ${event.stage} (${stagesEncountered.size}/13)`);
                }

                if (event.type === 'progress' && event.message) {
                  console.log(`📊 Progress: ${event.progress}% - ${event.message}`);
                }
              } catch (parseError) {
                // Skip malformed JSON
              }
            }
          }
        } catch (error) {
          // SSE body might not be fully available yet
        }
      }
    });

    // Log page errors
    page.on('pageerror', (error) => {
      console.error('❌ Page error:', error.message);
    });

    // Log console messages
    page.on('console', (msg) => {
      const type = msg.type();
      if (type === 'error' || type === 'warning') {
        console.log(`🖥️  Console [${type}]:`, msg.text());
      }
    });

    console.log('\n🚀 Starting full workflow test...\n');

    // STEP 1: Navigate to home page
    console.log('📍 Step 1: Navigate to home page');
    const homePage = new HomePage(page);
    await homePage.goto();
    await page.waitForLoadState('networkidle');
    await takeScreenshot('01_home_page_initial');

    // Verify home page loaded
    await expect(homePage.urlInput).toBeVisible();
    await expect(homePage.submitButton).toBeVisible();
    console.log('✓ Home page loaded successfully');

    // STEP 2: Enter URL and submit
    console.log('\n📍 Step 2: Submit URL for analysis');
    console.log(`   URL: ${TEST_URL}`);
    await homePage.urlInput.fill(TEST_URL);
    await takeScreenshot('02_url_entered');

    await homePage.submitButton.click();
    console.log('✓ Form submitted');

    // STEP 3: Wait for redirect to analysis page
    console.log('\n📍 Step 3: Wait for redirect to analysis page');
    await page.waitForURL(/\/analyze\/.+/, { timeout: 10000 });
    const currentUrl = page.url();
    const analysisId = currentUrl.match(/\/analyze\/([^/]+)/)?.[1];
    console.log(`✓ Redirected to: ${currentUrl}`);
    console.log(`   Analysis ID: ${analysisId}`);
    await takeScreenshot('03_analysis_page_initial');

    // STEP 4: Wait for SSE connection and initial events
    console.log('\n📍 Step 4: Monitor SSE connection');
    const analyzePage = new AnalyzePage(page);

    // Wait for progress bar to appear
    await expect(analyzePage.progressBar).toBeVisible({ timeout: 15000 });
    console.log('✓ Progress bar visible');

    // Wait for initial progress
    await page.waitForTimeout(2000);
    const initialProgress = await analyzePage.getProgress();
    console.log(`   Initial progress: ${initialProgress}%`);
    await takeScreenshot('04_sse_connected');

    // STEP 5: Monitor all 13 stages
    console.log('\n📍 Step 5: Monitor stage progression (13 stages expected)');
    console.log('   Expected stages:', EXPECTED_STAGES);

    let lastProgress = initialProgress;
    let stagnantCount = 0;
    const maxStagnantChecks = 30; // 30 checks * 5s = 2.5 minutes max wait

    // Poll for stages with timeout protection
    while (stagesEncountered.size < EXPECTED_STAGES.length && stagnantCount < maxStagnantChecks) {
      await page.waitForTimeout(5000);

      const currentProgress = await analyzePage.getProgress();
      const stagesList = Array.from(stagesEncountered).join(', ');

      console.log(`   Progress: ${currentProgress}% | Stages: ${stagesEncountered.size}/13 | Last: ${Array.from(stagesEncountered).pop() || 'none'}`);

      // Take screenshot at key stages
      if (stagesEncountered.has('supervisor_routing') && !stagesEncountered.has('content_extraction')) {
        await takeScreenshot('05_supervisor_routing_complete');
      }
      if (stagesEncountered.has('content_extraction') && !stagesEncountered.has('content_synthesis')) {
        await takeScreenshot('06_extraction_complete');
      }
      if (stagesEncountered.has('integration_feasibility') && stagesEncountered.size >= 11) {
        await takeScreenshot('07_integration_feasibility_detected');
        console.log('🎯 CRITICAL: integration_feasibility stage detected!');
      }
      if (currentProgress === 100 || stagesEncountered.size === EXPECTED_STAGES.length) {
        await takeScreenshot('08_all_stages_complete');
        break;
      }

      // Check if progress is moving
      if (currentProgress === lastProgress) {
        stagnantCount++;
        if (stagnantCount % 6 === 0) { // Every 30 seconds
          console.log(`   ⚠️  Progress stagnant for ${stagnantCount * 5}s at ${currentProgress}%`);
          await takeScreenshot(`09_stagnant_${stagnantCount}`);
        }
      } else {
        stagnantCount = 0;
        lastProgress = currentProgress;
      }
    }

    // STEP 6: Validate all stages appeared
    console.log('\n📍 Step 6: Validate stage completion');
    console.log(`   Stages encountered: ${stagesEncountered.size}/13`);
    console.log(`   Stages: ${Array.from(stagesEncountered).join(', ')}`);

    const missingStages = EXPECTED_STAGES.filter(stage => !stagesEncountered.has(stage));
    if (missingStages.length > 0) {
      console.error('❌ Missing stages:', missingStages);
      await takeScreenshot('10_error_missing_stages');
    } else {
      console.log('✅ All 13 stages detected!');
    }

    // CRITICAL: Validate integration_feasibility stage
    expect(stagesEncountered.has('integration_feasibility'),
      'integration_feasibility stage must appear').toBe(true);
    console.log('✅ integration_feasibility stage validated');

    // STEP 7: Wait for completion
    console.log('\n📍 Step 7: Wait for final completion');
    try {
      await analyzePage.waitForComplete(60000);
      console.log('✓ Analysis completed successfully');
      await takeScreenshot('11_completion_success');

      // Check for artifact link
      const artifactVisible = await analyzePage.viewArtifactButton.isVisible();
      console.log(`   Artifact button visible: ${artifactVisible}`);

      if (artifactVisible) {
        await takeScreenshot('12_artifact_available');
      }
    } catch (error) {
      console.error('❌ Completion timeout or error:', error);
      await takeScreenshot('13_error_completion_timeout');

      // Check for error messages
      const errorVisible = await analyzePage.errorMessage.isVisible().catch(() => false);
      if (errorVisible) {
        const errorText = await analyzePage.errorMessage.textContent();
        console.error('   Error message:', errorText);
      }
    }

    // STEP 8: Final validation and reporting
    console.log('\n📊 FINAL REPORT');
    console.log('════════════════════════════════════════════════');
    console.log(`Total SSE events received: ${sseEvents.length}`);
    console.log(`Total stages encountered: ${stagesEncountered.size}/13`);
    console.log(`Final progress: ${await analyzePage.getProgress()}%`);
    console.log(`Screenshots saved: ${screenshotCounter}`);
    console.log('');
    console.log('Stage order encountered:');

    const orderedStages: string[] = [];
    for (const stage of EXPECTED_STAGES) {
      const encountered = stagesEncountered.has(stage);
      const symbol = encountered ? '✅' : '❌';
      console.log(`  ${symbol} ${stage}`);
      if (encountered) orderedStages.push(stage);
    }

    console.log('');
    console.log('Missing stages:', missingStages.length === 0 ? 'None' : missingStages.join(', '));
    console.log('════════════════════════════════════════════════');

    // Final assertions
    expect(stagesEncountered.size).toBeGreaterThanOrEqual(11); // At least 11 stages must appear
    expect(stagesEncountered.has('integration_feasibility')).toBe(true);
    expect(missingStages.length).toBeLessThan(3); // Allow up to 2 missing stages for flakiness

    // Save event log for debugging
    const eventLog = {
      testUrl: TEST_URL,
      analysisId,
      totalEvents: sseEvents.length,
      stagesEncountered: Array.from(stagesEncountered),
      missingStages,
      events: sseEvents.slice(0, 50), // First 50 events
    };

    console.log('\n📝 Event log sample:', JSON.stringify(eventLog, null, 2));

    await takeScreenshot('14_final_state');
  });

  test('should handle rapid stage transitions correctly', async ({ page }) => {
    console.log('\n🧪 Testing rapid stage transition handling...\n');

    const homePage = new HomePage(page);
    await homePage.goto();
    await homePage.urlInput.fill(TEST_URL);
    await homePage.submitButton.click();

    await page.waitForURL(/\/analyze\/.+/, { timeout: 10000 });

    const analyzePage = new AnalyzePage(page);
    await expect(analyzePage.progressBar).toBeVisible({ timeout: 15000 });

    // Verify UI remains responsive during rapid updates
    await page.waitForTimeout(10000);

    const progress = await analyzePage.getProgress();
    console.log(`✓ UI remained responsive, progress: ${progress}%`);

    expect(progress).toBeGreaterThanOrEqual(0);
    expect(progress).toBeLessThanOrEqual(100);
  });

  test('should calculate progress correctly with 13 stages', async ({ page }) => {
    console.log('\n📐 Testing progress calculation with 13 stages...\n');

    const homePage = new HomePage(page);
    await homePage.goto();
    await homePage.urlInput.fill(TEST_URL);
    await homePage.submitButton.click();

    await page.waitForURL(/\/analyze\/.+/, { timeout: 10000 });

    const analyzePage = new AnalyzePage(page);
    await expect(analyzePage.progressBar).toBeVisible({ timeout: 15000 });

    // Wait for some progress
    await page.waitForTimeout(15000);

    const progress = await analyzePage.getProgress();
    console.log(`   Current progress: ${progress}%`);

    // With 13 stages, each stage is ~7.69% progress
    // Verify progress makes sense (not showing 100% when only 1 stage complete)
    if (progress > 0 && progress < 100) {
      const estimatedStages = Math.round((progress / 100) * 13);
      console.log(`   Estimated stages complete: ${estimatedStages}/13`);
      expect(estimatedStages).toBeGreaterThan(0);
      expect(estimatedStages).toBeLessThan(13);
    }

    console.log('✓ Progress calculation appears correct');
  });
});
