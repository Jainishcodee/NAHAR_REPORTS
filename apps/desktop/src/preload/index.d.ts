import type { DesktopApi } from '../shared/types';

declare global {
  interface Window {
    /** Bridge exposed by src/preload/index.ts (Electron main-process features). */
    api: DesktopApi;
  }
}

export {};
