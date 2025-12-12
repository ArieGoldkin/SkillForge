// Real API helpers for E2E testing against actual backend
export {
  getApiBaseUrl,
  createAnalysis,
  getAnalysis,
  getLibrary,
  getCompletedAnalysis,
  getArtifact,
  waitForBackend,
  createTutorSession,
  getTutorSession,
  sendTutorMessage,
  waitForAssistantResponse,
  sendMessageAndWaitForResponse,
} from './api-helpers';

// Test utilities
export {
  waitForRequest,
  waitForResponse,
  waitForNetworkIdle,
  getClipboardContent,
  setMobileViewport,
  setTabletViewport,
  setDesktopViewport,
  generateTestId,
  waitWithTimeout,
  retryWithBackoff,
} from './test-helpers';

// Legacy mock exports (kept for reference, will be removed)
// TODO: Remove these once all tests are migrated to real API
export {
  mockAnalyzeAPI,
  mockSSEStream,
  mockSSEStreamFailure,
  mockArtifactAPI,
  mockLibraryAPI,
  mockEmptyLibraryAPI,
  mockTutorAPI,
  mockAPIError,
  mockNetworkFailure,
  mockAllAPIs,
} from './mock-api';
