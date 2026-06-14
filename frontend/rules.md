# Frontend Development Rules

1. **No legacy components**: React class components are banned. Use functional components and custom React hooks.
2. **Type checks**: No TypeScript `any`. All properties, components, and payloads must be statically typed.
3. **Verbatim Module Syntax**: Type imports must use `import type { ... }` rather than value imports.
4. **WebSocket Hooks**: Isolate WebSocket registry listeners and reconnect mechanisms inside custom hooks (`useWorkflowSocket.ts`).
5. **Aesthetics**: Premium Dark UX layout containing dynamic stepper indicators, collapsible workspace tabs, and chat alignment.
