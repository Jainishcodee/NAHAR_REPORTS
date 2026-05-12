/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Default API base URL (dev). The user can override it in Settings. */
  readonly VITE_API_BASE_URL?: string;
}
interface ImportMeta {
  readonly env: ImportMetaEnv;
}
