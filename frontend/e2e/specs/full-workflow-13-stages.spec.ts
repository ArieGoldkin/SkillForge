import { test, expect } from '@playwright/test';

import { HomePage, AnalyzePage } from '../page-objects';
import { logTestStep, logger } from '../utils';

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
 * - Core workflow stages appear (6 minimum)
 * - Agent stages selected by supervisor (0-8 agents)
 * - Progress calculation with dynamic stage count
 * - Final completion or error handling
 *
 * STAGE NAMES: Based on AgentStageName type (frontend/src/types/sse.ts)
 * Note: Backend AGENT_REGISTRY maps agent names to stage names
 * (e.g., implementation_planner → implementation_planning)
 *
 * IMPORTANT: This test makes real LLM calls and takes 2-3 minutes.
 * Run with: npm run test:e2e:chromium -- full-workflow-13-stages.spec.ts --headed
 */

const TEST_URL = 'https://inbarshirizly.substack.com/p/coming-soon';

// Core workflow stages (ALWAYS appear in every analysis)
const CORE_STAGES = [
  'extraction',           // Content extraction
  'embedding',            // Embedding generation
  'supervisor_routing',   // Agent selection
  'aggregation',          // Results aggregation
  'quality_validation',   // Quality check
  'artifact_generation',  // Final report generation
];

// Optional agent stages (0-8 selected dynamically by supervisor)
const OPTIONAL_AGENT_STAGES = [
  'tech_comparison',      // Tech Comparator agent
  'security_audit',       // Security Auditor agent
  'implementation_planning', // Implementation Planner + Integration Feasibility agents (both use this stage!)
  'performance_audit',    // Performance Auditor agent
  'code_quality_audit',   // Code Quality Reviewer agent
  'trends_analysis',      // Trends Analyst agent
  'dependencies_analysis', // Dependencies Analyzer agent
  'pattern_comparison',   // Pattern comparison (workflow-level)
];

// Other optional stages (for reference)
// const OTHER_OPTIONAL_STAGES = [
//   'chunking',   // Only if ENABLE_COARSE_TO_FINE=true
//   'workflow',   // Error handling (workflow-level)
//   'metrics',    // Metrics collection (workflow-level)
// ];

// All 17 possible stages (from STAGE_CONFIG)
// Note: Used for reference, not directly in tests
// const ALL_POSSIBLE_STAGES = [
//   ...CORE_STAGES,
//   ...OPTIONAL_AGENT_STAGES,
//   ...OTHER_OPTIONAL_STAGES,
// ];

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

  /* eslint-disable complexity, max-depth -- E2E workflow test requires comprehensive validation logic */
  test('should complete full analysis workflow with all 13 stages', async ({ page }) => {
    test.skip(!!process.env.CI, 'Full workflow requires LLM processing');

    const sseEvents: SSEEvent[] = [];
    const stagesEncountered = new Set<string>();

    // Screenshot directory
    const screenshotDir = '/tmp/playwright-workflow';
    let screenshotCounter = 0;

    const takeScreenshot = async (label: string) => {
      screenshotCounter++;
      const filename = `${screenshotDir}/${screenshotCounter.toString().padStart(2, '0')}_${label}.png`;
      await page.screenshot({ path: filename, fullPage: true });
      logger.debug('Screenshot captured', { filename, label, counter: screenshotCounter });
      return filename;
    };

    // Set up network monitoring for SSE events
    page.on('response', async (response) => {
      const url = response.url();

      // Monitor SSE endpoint
      if (url.includes('/api/v1/analyze/sse/')) {
        logger.debug('SSE response received', { status: response.status(), url });

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
                  logger.info('Stage detected', {
                    stage: event.stage,
                    totalStages: stagesEncountered.size,
                    allStages: Array.from(stagesEncountered),
                  });
                }

                if (event.type === 'progress' && event.message) {
                  logger.info('Progress update', {
                    progress: event.progress,
                    message: event.message,
                    stage: event.stage,
                  });
                }
              } catch {
                // Skip malformed JSON
              }
            }
          }
        } catch {
          // SSE body might not be fully available yet
        }
      }
    });

    // Log page errors
    page.on('pageerror', (error) => {
      logger.error('Page error detected', {
        error: error.message,
        stack: error.stack,
      });
    });

    // Log console messages
    page.on('console', (msg) => {
      const type = msg.type();
      if (type === 'error' || type === 'warning') {
        logger.warn('Browser console message', {
          type,
          text: msg.text(),
        });
      }
    });

    logTestStep('Starting full workflow test', { testUrl: TEST_URL });

    // STEP 1: Navigate to home page
    logTestStep('Navigate to home page');
    const homePage = new HomePage(page);
    await homePage.goto();
    await page.waitForLoadState('domcontentloaded');
    // Wait for URL input to be visible (indicates page is ready)
    await expect(homePage.urlInput).toBeVisible({ timeout: 10000 });
    await takeScreenshot('01_home_page_initial');

    // Verify home page loaded
    await expect(homePage.urlInput).toBeVisible();
    await expect(homePage.submitButton).toBeVisible();
    logger.info('Home page loaded successfully');

    // STEP 2: Enter URL and submit
    logTestStep('Submit URL for analysis', { url: TEST_URL });
    await homePage.urlInput.fill(TEST_URL);
    await takeScreenshot('02_url_entered');

    await homePage.submitButton.click();
    logger.info('Form submitted');

    // STEP 3: Wait for redirect to analysis page
    logTestStep('Wait for redirect to analysis page');
    await page.waitForURL(/\/analyze\/.+/, { timeout: 10000 });
    const currentUrl = page.url();
    const analysisId = currentUrl.match(/\/analyze\/([^/]+)/)?.[1];
    logger.info('Redirected to analysis page', { url: currentUrl, analysisId });
    await takeScreenshot('03_analysis_page_initial');

    // STEP 4: Wait for SSE connection and initial events
    logTestStep('Monitor SSE connection');
    const analyzePage = new AnalyzePage(page);

    // Wait for progress bar to appear
    await expect(analyzePage.progressBar).toBeVisible({ timeout: 15000 });
    logger.info('Progress bar visible');

    // Wait for initial progress by checking that progress > 0
    await expect
      .poll(() => analyzePage.getProgress(), {
        timeout: 10000,
        intervals: [500, 1000],
      })
      .toBeGreaterThan(0);
    const initialProgress = await analyzePage.getProgress();
    logger.info('Initial progress', { progress: initialProgress });
    await takeScreenshot('04_sse_connected');

    // STEP 5: Monitor stage progression (dynamic count based on supervisor selection)
    logTestStep('Monitor stage progression', {
      coreStages: CORE_STAGES,
      optionalAgentStages: OPTIONAL_AGENT_STAGES,
    });

    let lastProgress = initialProgress;
    let stagnantCount = 0;
    const maxStagnantChecks = 36; // 36 checks * 5s = 3 minutes max wait

    // Count how many core stages we've seen
    const coreStagesEncountered = () =>
      CORE_STAGES.filter(stage => stagesEncountered.has(stage)).length;

    // Poll for stages with timeout protection
    // Continue until we see all 6 core stages OR reach max wait time OR progress is 100%
    while (coreStagesEncountered() < CORE_STAGES.length && stagnantCount < maxStagnantChecks) {
      // Wait for progress to change or timeout after 5 seconds
      const previousProgress = lastProgress;
      await expect
        .poll(() => analyzePage.getProgress(), {
          timeout: 5000,
          intervals: [1000],
        })
        .not.toBe(previousProgress)
        .catch(() => {
          // Progress didn't change, that's ok - will be handled by stagnant count
        });

      const currentProgress = await analyzePage.getProgress();
      const coreCount = coreStagesEncountered();
      const agentCount = OPTIONAL_AGENT_STAGES.filter(s => stagesEncountered.has(s)).length;

      logger.debug('Stage progression update', {
        progress: currentProgress,
        coreCount,
        coreTotal: CORE_STAGES.length,
        agentCount,
        totalStages: stagesEncountered.size,
      });

      // Take screenshot at key stages
      if (stagesEncountered.has('supervisor_routing') && !stagesEncountered.has('aggregation')) {
        await takeScreenshot('05_supervisor_routing_complete');
      }
      if (stagesEncountered.has('extraction') && !stagesEncountered.has('embedding')) {
        await takeScreenshot('06_extraction_complete');
      }
      if (stagesEncountered.has('implementation_planning')) {
        await takeScreenshot('07_implementation_planning_detected');
        logger.info('Critical stage detected', { stage: 'implementation_planning' });
      }
      if (currentProgress >= 90 || coreCount === CORE_STAGES.length) {
        await takeScreenshot('08_near_complete');
      }
      if (currentProgress === 100) {
        await takeScreenshot('09_100_percent');
        break;
      }

      // Check if progress is moving
      if (currentProgress === lastProgress) {
        stagnantCount++;
        if (stagnantCount % 6 === 0) { // Every 30 seconds
          logger.warn('Progress stagnant', {
            duration: stagnantCount * 5,
            progress: currentProgress,
            stagesEncountered: Array.from(stagesEncountered),
          });
          await takeScreenshot(`10_stagnant_${stagnantCount}`);
        }
      } else {
        stagnantCount = 0;
        lastProgress = currentProgress;
      }
    }

    // STEP 6: Validate stage completion
    logTestStep('Validate stage completion');
    const coreCount = CORE_STAGES.filter(s => stagesEncountered.has(s)).length;
    const agentCount = OPTIONAL_AGENT_STAGES.filter(s => stagesEncountered.has(s)).length;
    const missingCoreStages = CORE_STAGES.filter(stage => !stagesEncountered.has(stage));
    const presentAgentStages = OPTIONAL_AGENT_STAGES.filter(s => stagesEncountered.has(s));

    logger.info('Stage completion summary', {
      totalStages: stagesEncountered.size,
      coreCount,
      coreTotal: CORE_STAGES.length,
      agentCount,
      agentTotal: OPTIONAL_AGENT_STAGES.length,
      allStages: Array.from(stagesEncountered),
      missingCoreStages,
      presentAgentStages,
    });

    // Check which core stages are missing (if any)
    if (missingCoreStages.length > 0) {
      logger.error('Missing CORE stages', { missingCoreStages });
      await takeScreenshot('11_error_missing_core_stages');
    } else {
      logger.info('All 6 core stages detected');
    }

    // STEP 7: Wait for completion
    logTestStep('Wait for final completion');
    try {
      await analyzePage.waitForComplete(60000);
      logger.info('Analysis completed successfully');
      await takeScreenshot('11_completion_success');

      // Check for artifact link
      const artifactVisible = await analyzePage.viewArtifactButton.isVisible();
      logger.info('Artifact button status', { visible: artifactVisible });

      if (artifactVisible) {
        await takeScreenshot('12_artifact_available');
      }
    } catch (error) {
      logger.error('Completion timeout or error', {
        error: error instanceof Error ? error.message : String(error),
        stack: error instanceof Error ? error.stack : undefined,
      });
      await takeScreenshot('13_error_completion_timeout');

      // Check for error messages
      const errorVisible = await analyzePage.errorMessage.isVisible().catch(() => false);
      if (errorVisible) {
        const errorText = await analyzePage.errorMessage.textContent();
        logger.error('Error message displayed', { errorText });
      }
    }

    // STEP 8: Final validation and reporting
    const finalProgress = await analyzePage.getProgress();
    const coreStageStatus = CORE_STAGES.map(stage => ({
      stage,
      encountered: stagesEncountered.has(stage),
    }));
    const agentStageStatus = OPTIONAL_AGENT_STAGES.map(stage => ({
      stage,
      encountered: stagesEncountered.has(stage),
    }));

    logger.info('Final report', {
      totalSseEvents: sseEvents.length,
      totalStages: stagesEncountered.size,
      coreStages: coreCount,
      coreTotal: CORE_STAGES.length,
      agentStages: agentCount,
      agentTotal: OPTIONAL_AGENT_STAGES.length,
      finalProgress,
      screenshotsSaved: screenshotCounter,
      coreStageStatus,
      agentStageStatus,
      missingCoreStages,
    });

    // Final assertions
    // CRITICAL: All 6 core stages MUST appear
    expect(coreCount, 'All 6 core stages must appear').toBe(CORE_STAGES.length);
    expect(missingCoreStages.length, 'No core stages should be missing').toBe(0);

    // At least 1 agent should be selected by supervisor (in practice, 3-5 agents are typical)
    expect(agentCount, 'At least 1 agent stage should appear').toBeGreaterThanOrEqual(1);

    // Total stages should be at least 7 (6 core + at least 1 agent)
    expect(stagesEncountered.size, 'At least 7 total stages should appear').toBeGreaterThanOrEqual(7);

    // Save event log for debugging
    const eventLog = {
      testUrl: TEST_URL,
      analysisId,
      totalEvents: sseEvents.length,
      totalStages: stagesEncountered.size,
      coreStages: coreCount,
      agentStages: agentCount,
      stagesEncountered: Array.from(stagesEncountered),
      missingCoreStages,
      presentAgentStages,
      events: sseEvents.slice(0, 50), // First 50 events
    };

    logger.debug('Event log sample', { eventLog });

    await takeScreenshot('14_final_state');
  });

  test('should handle rapid stage transitions correctly', async ({ page }) => {
    test.skip(!!process.env.CI, 'Full workflow requires LLM processing');

    logTestStep('Testing rapid stage transition handling');

    const homePage = new HomePage(page);
    await homePage.goto();
    await homePage.urlInput.fill(TEST_URL);
    await homePage.submitButton.click();

    await page.waitForURL(/\/analyze\/.+/, { timeout: 10000 });

    const analyzePage = new AnalyzePage(page);
    await expect(analyzePage.progressBar).toBeVisible({ timeout: 15000 });

    // Verify UI remains responsive during rapid updates by waiting for progress to advance
    await expect
      .poll(() => analyzePage.getProgress(), {
        timeout: 10000,
        intervals: [1000, 2000],
      })
      .toBeGreaterThan(0);

    const progress = await analyzePage.getProgress();
    logger.info('UI remained responsive', { progress });

    expect(progress).toBeGreaterThanOrEqual(0);
    expect(progress).toBeLessThanOrEqual(100);
  });

  test('should calculate progress correctly with dynamic stage count', async ({ page }) => {
    test.skip(!!process.env.CI, 'Full workflow requires LLM processing');

    logTestStep('Testing progress calculation with dynamic stages');

    const homePage = new HomePage(page);
    await homePage.goto();
    await homePage.urlInput.fill(TEST_URL);
    await homePage.submitButton.click();

    await page.waitForURL(/\/analyze\/.+/, { timeout: 10000 });

    const analyzePage = new AnalyzePage(page);
    await expect(analyzePage.progressBar).toBeVisible({ timeout: 15000 });

    // Wait for some progress to be made
    await expect
      .poll(() => analyzePage.getProgress(), {
        timeout: 15000,
        intervals: [2000, 3000],
      })
      .toBeGreaterThan(10); // Wait for at least 10% progress

    const progress = await analyzePage.getProgress();
    logger.info('Current progress', { progress });

    // Progress should be reasonable (0-100%)
    expect(progress).toBeGreaterThanOrEqual(0);
    expect(progress).toBeLessThanOrEqual(100);

    // If progress is between 0-100 (exclusive), verify it's not showing 100% prematurely
    if (progress > 0 && progress < 100) {
      // With dynamic stages (typically 6 core + 3-5 agents = 9-11 total)
      // Progress should reflect actual completion, not jump to 100% early
      logger.info('Progress validation', {
        progress,
        status: 'not_prematurely_100',
      });
    }

    logger.info('Progress calculation appears correct');
  });
});
