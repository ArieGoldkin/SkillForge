# Performance Monitoring Setup

This directory contains the performance monitoring infrastructure for SkillForge, implementing the requirements from issue #401.

## Architecture

### React Scan (Development Monitoring)
- **Purpose**: Visual performance debugging during development
- **Activation**: Automatically enabled in development mode
- **Features**:
  - Automatic render detection and highlighting
  - Performance toolbar with real-time metrics
  - Unnecessary render warnings
  - No code changes required

### Web Vitals (Production RUM Analytics)
- **Purpose**: Production performance monitoring and analytics
- **Activation**: Enabled in production, optional in development
- **Features**:
  - Core Web Vitals tracking (LCP, CLS, INP, FCP, TTFB)
  - Attribution data for debugging root causes
  - Google Analytics 4 integration
  - Custom analytics endpoint support

## Environment Variables

Create a `.env` file with the following variables:

```bash
# Google Analytics Measurement ID for Web Vitals tracking
VITE_GA_MEASUREMENT_ID=G-XXXXXXXXXX

# Custom analytics endpoint for Web Vitals data
VITE_ANALYTICS_ENDPOINT=https://your-analytics-endpoint.com/api/web-vitals

# Enable Web Vitals tracking in development (default: disabled)
VITE_ENABLE_WEB_VITALS_DEV=false
```

## Google Analytics Setup

1. Create a GA4 property at [Google Analytics](https://analytics.google.com)
2. Get your Measurement ID (format: G-XXXXXXXXXX)
3. Set `VITE_GA_MEASUREMENT_ID` in your environment variables
4. Add Google Analytics script to your HTML head:

```html
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=YOUR_MEASUREMENT_ID"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'YOUR_MEASUREMENT_ID');
</script>
```

## Custom Analytics Endpoint

For custom analytics, implement an endpoint that accepts:

```typescript
interface WebVitalsPayload {
  timestamp: number
  metric: 'CLS' | 'INP' | 'LCP' | 'FCP' | 'TTFB'
  value: number
  delta: number
  rating: 'good' | 'needs-improvement' | 'poor'
  id: string
  attribution?: {
    // Metric-specific attribution data
    [key: string]: any
  }
  userAgent: string
  url: string
}
```

## Development Testing

1. **React Scan**: Open the app in development mode, you should see:
   - Colored outlines around components that re-render
   - Performance toolbar in bottom-right corner
   - Console logs showing render information

2. **Web Vitals**: Set `VITE_ENABLE_WEB_VITALS_DEV=true` to enable in development:
   - Console logs showing metric values and ratings
   - Attribution data for debugging

3. **Performance Tests**: Run the performance test suite:
   ```bash
   npm run test -- --run src/features/analysis/components/progress/__tests__/ProgressTracker.performance.test.tsx
   ```

## Current Implementation Status

### ✅ What's Working (Delivered for Issue #401)

#### 1. **React Scan - Visual Performance Monitoring**
- ✅ **Development-only activation** - Zero production overhead
- ✅ **Visual render feedback** - Colored outlines show slow renders
- ✅ **Automatic detection** - No code changes required
- ✅ **Toolbar with metrics** - Real-time render counts and performance insights
- ✅ **Unnecessary render warnings** - Gray outlines for wasteful re-renders

#### 2. **Web Vitals RUM - Production Analytics**
- ✅ **Core Web Vitals tracking** - LCP, CLS, INP, FCP, TTFB
- ✅ **Attribution data** - Which elements cause performance issues
- ✅ **Google Analytics 4 integration** - Historical performance trending
- ✅ **Batched reporting** - Prevents network spam
- ✅ **Custom analytics endpoint support** - For internal dashboards

#### 3. **SSE-Specific Performance Tracking**
- ✅ **Connection performance monitoring** - Track SSE connection times
- ✅ **Event processing metrics** - Monitor event throughput
- ✅ **Analysis flow performance** - Track complex state transitions
- ✅ **Automatic performance marks** - Browser performance timeline integration

#### 4. **Infrastructure & Tooling**
- ✅ **Performance service architecture** - Modular, extensible design
- ✅ **Environment variable configuration** - Development vs production controls
- ✅ **Console logging** - Development debugging support
- ✅ **TypeScript safety** - Full type coverage for all metrics

### 🚧 Known Limitations (Future Enhancements)

#### CI/CD Performance Regression Detection
- **Current Status**: Basic infrastructure in place, but Vitest React Profiler had compatibility issues
- **Alternative**: Manual render budget checks in existing tests
- **Future**: Custom performance regression testing framework

#### Automated Render Budget Enforcement
- **Current Status**: Manual budget checks and console warnings
- **Future**: Automated CI failures on budget violations

## Usage Examples

### Development Monitoring
```typescript
// Open app in development - React Scan automatically shows:
// - Colored outlines around re-rendering components
// - Performance toolbar in bottom-right
// - Console logs with render counts
npm run dev
```

### Production Analytics Setup
```bash
# Set environment variables
VITE_GA_MEASUREMENT_ID=G-XXXXXXXXXX
VITE_ANALYTICS_ENDPOINT=https://your-analytics-endpoint.com/api/web-vitals

# Deploy - Web Vitals automatically track and report
npm run build && npm run preview
```

### SSE Performance Tracking
```typescript
// Automatic tracking in useSSE hook:
// - Connection establishment time
// - Event processing throughput
// - State update performance
import { useSSE } from '@hooks/useSSE'

const { isConnected, events } = useSSE(analysisId)
// Performance data automatically tracked
```

## Production Monitoring

1. **Enable environment variables** in production
2. **Monitor Google Analytics** for Core Web Vitals reports
3. **Set up alerts** for poor-performing metrics:
   - LCP > 2.5s
   - CLS > 0.1
   - INP > 200ms

## Performance Budgets

Consider setting up performance budgets:

```javascript
// In your build tool configuration
{
  budgets: [
    {
      type: 'bundle',
      name: 'main',
      maximumWarning: '500kb',
      maximumError: '1mb'
    }
  ]
}
```

## Troubleshooting

### React Scan Not Showing
- Ensure you're in development mode
- Check browser console for initialization errors
- Verify `react-scan` package is installed

### Web Vitals Not Reporting
- Check environment variables are set correctly
- Verify Google Analytics is properly initialized
- Ensure custom endpoint is accessible (if configured)

### High Bundle Size
- Web Vitals library is ~2KB gzipped
- React Scan is development-only (tree-shaken in production)
- Consider lazy-loading analytics scripts

## Future Enhancements

- **CI/CD Performance Regression**: Automated performance testing
- **Performance Profiling**: Advanced component profiling
- **Real User Monitoring**: Enhanced RUM with user context
- **Performance Alerts**: Slack/Discord notifications for issues
