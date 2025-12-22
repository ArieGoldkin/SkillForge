import * as path from 'path';
import * as fs from 'fs';

/**
 * Storage State Management Utilities
 * 
 * Helper functions for managing Playwright storageState.json files.
 * Used for validating, refreshing, and managing browser state across tests.
 */

export interface StorageState {
  cookies: Array<{
    name: string;
    value: string;
    domain: string;
    path: string;
    expires: number;
    httpOnly: boolean;
    secure: boolean;
    sameSite: 'Strict' | 'Lax' | 'None';
  }>;
  origins: Array<{
    origin: string;
    localStorage: Array<{ name: string; value: string }>;
    sessionStorage: Array<{ name: string; value: string }>;
  }>;
}

/**
 * Get the path to the storageState.json file
 */
export function getStorageStatePath(): string {
  return path.join(process.cwd(), '.auth', 'storageState.json');
}

/**
 * Check if storageState file exists
 */
export function storageStateExists(): boolean {
  const statePath = getStorageStatePath();
  return fs.existsSync(statePath);
}

/**
 * Read and parse storageState file
 */
export function readStorageState(): StorageState | null {
  const statePath = getStorageStatePath();
  
  if (!fs.existsSync(statePath)) {
    return null;
  }

  try {
    const content = fs.readFileSync(statePath, 'utf-8');
    const state = JSON.parse(content) as StorageState;
    return validateStorageState(state) ? state : null;
  } catch (error) {
    console.error('Failed to read storageState:', error);
    return null;
  }
}

/**
 * Validate storageState structure
 */
export function validateStorageState(state: unknown): state is StorageState {
  if (!state || typeof state !== 'object') {
    return false;
  }

  const s = state as Record<string, unknown>;
  
  // Check cookies array
  if (!Array.isArray(s.cookies)) {
    return false;
  }

  // Check origins array
  if (!Array.isArray(s.origins)) {
    return false;
  }

  // Validate each origin
  for (const origin of s.origins) {
    if (typeof origin !== 'object' || origin === null) {
      return false;
    }

    if (typeof (origin as { origin?: unknown }).origin !== 'string') {
      return false;
    }

    if (!Array.isArray((origin as { localStorage?: unknown }).localStorage)) {
      return false;
    }

    if (!Array.isArray((origin as { sessionStorage?: unknown }).sessionStorage)) {
      return false;
    }
  }

  return true;
}

/**
 * Check if storageState needs refresh (older than specified age)
 */
export function shouldRefreshStorageState(maxAgeMs: number = 60 * 60 * 1000): boolean {
  const statePath = getStorageStatePath();
  
  if (!fs.existsSync(statePath)) {
    return true;
  }

  try {
    const stats = fs.statSync(statePath);
    const ageMs = Date.now() - stats.mtimeMs;
    return ageMs > maxAgeMs;
  } catch (error) {
    console.error('Failed to check storageState age:', error);
    return true;
  }
}

/**
 * Get storageState file statistics
 */
export function getStorageStateStats(): {
  exists: boolean;
  size: number;
  ageMs: number;
  isValid: boolean;
} | null {
  const statePath = getStorageStatePath();
  
  if (!fs.existsSync(statePath)) {
    return {
      exists: false,
      size: 0,
      ageMs: 0,
      isValid: false,
    };
  }

  try {
    const stats = fs.statSync(statePath);
    const state = readStorageState();
    
    return {
      exists: true,
      size: stats.size,
      ageMs: Date.now() - stats.mtimeMs,
      isValid: state !== null,
    };
  } catch (error) {
    console.error('Failed to get storageState stats:', error);
    return null;
  }
}

/**
 * Delete storageState file (for cleanup or forced refresh)
 */
export function deleteStorageState(): boolean {
  const statePath = getStorageStatePath();
  
  if (!fs.existsSync(statePath)) {
    return false;
  }

  try {
    fs.unlinkSync(statePath);
    return true;
  } catch (error) {
    console.error('Failed to delete storageState:', error);
    return false;
  }
}

/**
 * Ensure .auth directory exists
 */
export function ensureAuthDirectory(): string {
  const authDir = path.join(process.cwd(), '.auth');
  
  if (!fs.existsSync(authDir)) {
    fs.mkdirSync(authDir, { recursive: true });
  }
  
  return authDir;
}
