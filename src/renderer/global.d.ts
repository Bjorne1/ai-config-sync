import type { DeskSyncApi } from './lib/models';

declare global {
  interface Window {
    deskSync: DeskSyncApi;
  }
}

export {};
