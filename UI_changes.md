# UI Changes Made to MDT Agent System

This document details all UI and frontend modifications introduced to support dynamic, color-coded Mermaid visualizations and improved report display functionality.

## 1. index.html Updates

- **Mermaid Container ID**: Changed the `div` ID from `mermaidGraph` to `workflowDiagram` to match the JavaScript selector.
  ```html
  <!-- Before -->
  <div id="mermaidGraph" class="mermaid">...

  <!-- After -->
  <div id="workflowDiagram" class="mermaid">...
  ```

- **Ensure Markdown Library**: Confirmed inclusion of `marked.js` via CDN for markdown parsing:
  ```html
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  ```

## 2. app.js (Frontend Script) Enhancements

### 2.1 Mermaid Initialization

- Set `startOnLoad: false` to render diagrams manually.
- Removed static `classDef` definitions; styles are now defined dynamically in the Mermaid definition string.
- Added a `parseError` handler to gracefully display parse errors in the UI.

```js
mermaid.initialize({
  startOnLoad: false,
  theme: 'neutral',
  flowchart: { ... },
  parseError: (err) => { /* display user-friendly error */ }
});
```

### 2.2 Agent-State Tracking

- Introduced `agentMap` to map backend `agent_id` values to Mermaid node IDs and display names.
- Added `nodeStates` object to store each agent's current state (`inactive`, `running`, `complete`, `error`).

```js
const agentMap = {
  coordinator: { id: 'Coord', name: 'Coordinator' },
  ehr_agent:   { id: 'EHR',   name: 'EHR Agent' },
  ...
};
let nodeStates = {};
```

### 2.3 Initial and Reset Rendering

- **Initial Render**: On page load, initialized all `nodeStates` to `inactive` and invoked `renderMermaidDiagram()` after a short delay.
- **resetVisualization()**: Added to clear previous state, reset agent statuses (without clearing the `currentRunId`), and re-render the diagram at simulation start.

```js
function resetVisualization() {
  // reset nodeStates to 'inactive', set coordinator to 'running'
  renderMermaidDiagram();
}
```

### 2.4 Server-Sent Events (SSE) Handling

- Refactored `connectSSE(runId)`:
  - Listens for specific `status_update` events (
    `eventSource.addEventListener('status_update', ...)`).
  - Handles `REPORT` and `report` events to call `displayReport()`.
  - Handles `complete` and `ping` events with specialized logic.
  - Maintains fallback to `onmessage` for any untyped messages.

```js
eventSource.addEventListener('status_update', (evt) => {
  const data = JSON.parse(evt.data);
  if (data.status === 'REPORT') displayReport(data.data);
  else updateWorkflowVisualization(data);
});
```

### 2.5 Dynamic Visualization Updates

- **updateWorkflowVisualization(data)**:
  - Normalizes incoming `agent_id` strings (e.g., `EvaluationAgent` → `evaluation_agent`).
  - Delegates to `updateAgentState(agentKey, status, message)`.
- **updateAgentState(agentKey, status, message)**:
  - Maps statuses to CSS classes: `running`, `complete`, `error`.
  - Updates `nodeStates[agentKey]` and calls `renderMermaidDiagram()` only when a state changes.

```js
function updateAgentState(key, status) {
  // map status to newState
  if (newState !== nodeStates[key]) {
    nodeStates[key] = newState;
    renderMermaidDiagram();
  }
}
```

### 2.6 renderMermaidDiagram()

- Switched to `graph LR` for left-to-right layout.
- Dynamically builds the Mermaid definition string:
  1. `classDef` blocks for each state style.
  2. Node definitions using `agentMap`.
  3. Static connections from `Coord` to each agent.
  4. `class <Node> <state>;` lines for each node based on `nodeStates.`
- Displays a loading indicator while rendering.
- Uses a `<details>` element to show error messages and the failing diagram definition if rendering fails.

```js
async function renderMermaidDiagram() {
  const def = `graph LR ... classDef ... class NodeId state; ...`;
  try {
    diagramContainer.innerHTML = '<div class="loading">Rendering...</div>';
    const { svg } = await mermaid.render(svgId, def);
    diagramContainer.innerHTML = svg;
  } catch (err) {
    diagramContainer.innerHTML = `<details>...error details...</details>`;
  }
}
```

### 2.7 View Switching and Report Display

- **switchView(viewType)**:
  - Now re-queries the DOM inside the function.
  - Safely checks for element existence before calling `classList`.
- **displaySummary(summaryData)**:
  - Retrieves the `markdownOutput` element inside the function.
  - Uses `marked.parse()` to render markdown.

```js
function switchView(type) {
  const btn = document.getElementById(type + 'ViewBtn');
  if (btn) btn.classList.add('active');
}
```

### 2.8 Drag-and-Drop Enhancements

- Wrapped all `fileDropArea` event listener attachments inside an existence check:
  ```js
  const fileDropArea = document.querySelector('.file-input-container');
  if (fileDropArea) {
    ['dragenter','drop'].forEach(ev=>fileDropArea.addEventListener(ev,handler));
  }
  ```
- Added null-checks in `highlight()` and `unhighlight()` before calling `fileDropArea.classList`.

## 3. Summary

These UI changes enable:

- A live, color-coded Mermaid diagram reflecting agent status transitions.
- Initial diagram render before simulation starts.
- Robust SSE handling with auto-fallbacks for missing events.
- Enhanced report display with collapsible sections and markdown summary.
- Defensive coding to prevent uncaught `null` references on missing DOM elements.

Use this file to reapply the UI modifications step-by-step in your codebase. If you have any questions or need further clarifications, let me know! 