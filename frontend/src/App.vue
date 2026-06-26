<template>
  <div id="app-root">
    <router-view />
  </div>
</template>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background-color: var(--bg-page);
  color: var(--text-primary);
  transition: background-color 0.3s ease, color 0.3s ease;
}

/* ── Light theme (default) ── */
:root {
  /* Text */
  --text-primary: #333;
  --text-secondary: #666;
  --text-tertiary: #999;
  --text-muted: #bbb;
  --text-link: #1976d2;
  --text-inverse: #fff;

  /* Backgrounds */
  --bg-page: #f5f5f5;
  --bg-card: #fff;
  --bg-surface: #fafafa;
  --bg-hover: #f0f0f0;
  --bg-active: #e3f2fd;

  /* Borders */
  --border-default: #e0e0e0;
  --border-light: #eef0f3;
  --border-input: #d0d0d0;

  /* Interactive */
  --color-primary: #1976d2;
  --color-primary-hover: #1565c0;
  --color-primary-light: #e3f2fd;
  --color-primary-border: #bbdefb;
  --color-success: #2e7d32;
  --color-success-light: #e8f5e9;
  --color-warning: #ef6c00;
  --color-warning-light: #fff3e0;
  --color-danger: #c62828;
  --color-danger-light: #ffebee;
  --color-danger-border: #e57373;

  /* Special */
  --overlay: rgba(0, 0, 0, 0.4);
  --shadow-sm: 0 2px 12px rgba(0, 0, 0, 0.08);
  --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.15);

  /* Tables */
  --table-header-bg: #f5f5f5;
  --table-header-border: #d0d4db;
  --table-row-alt: #f8f9fb;
  --table-row-hover: #e3f0fa;

  /* Code */
  --code-bg: #f6f8fa;
  --code-text: #333;
  --code-border: #dde0e4;

  /* Graph (vis-network) */
  --graph-bg: #fafafa;
  --graph-node-font: #444;
  --graph-edge-color: #ccc;
  --graph-edge-font: #888;
  --graph-highlight: #409eff;
  --graph-node-border: #fff;

  /* Graph entity type default (types override via API) */
  --graph-type-default: #607d8b;

  /* Charts */
  --chart-colors: #1976d2, #26a69a, #ef6c00, #ab47bc, #5e35b1, #00897b, #d81b60, #43a047;
}

/* ── Dark theme ── */
.dark {
  --text-primary: #e0e0e0;
  --text-secondary: #aaa;
  --text-tertiary: #888;
  --text-muted: #666;
  --text-link: #64b5f6;
  --text-inverse: #1e1e1e;

  --bg-page: #121212;
  --bg-card: #1e1e1e;
  --bg-surface: #252525;
  --bg-hover: #333;
  --bg-active: #1a3a5c;

  --border-default: #333;
  --border-light: #2a2a2a;
  --border-input: #444;

  --color-primary: #64b5f6;
  --color-primary-hover: #42a5f5;
  --color-primary-light: #1a3a5c;
  --color-primary-border: #2a4a6a;
  --color-success: #4caf50;
  --color-success-light: #1b3a1b;
  --color-warning: #ff9800;
  --color-warning-light: #3a2a10;
  --color-danger: #ef5350;
  --color-danger-light: #3a1a1a;
  --color-danger-border: #5a2020;

  --overlay: rgba(0, 0, 0, 0.6);
  --shadow-sm: 0 2px 12px rgba(0, 0, 0, 0.4);
  --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.5);

  --table-header-bg: #2a2a2a;
  --table-header-border: #3a3a3a;
  --table-row-alt: #222;
  --table-row-hover: #1a2a3a;

  --code-bg: #1a1a2e;
  --code-text: #a6e3a1;
  --code-border: #2a2a3e;

  --graph-bg: #1e1e1e;
  --graph-node-font: #ccc;
  --graph-edge-color: #555;
  --graph-edge-font: #aaa;
  --graph-highlight: #64b5f6;
  --graph-node-border: #333;

  --graph-type-default: #78909c;

  --chart-colors: #64b5f6, #4db6ac, #ffb74d, #ce93d8, #9575cd, #4db6ac, #f06292, #81c784;
}
</style>
