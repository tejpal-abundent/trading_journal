/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_TEJ_CAPITAL_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
