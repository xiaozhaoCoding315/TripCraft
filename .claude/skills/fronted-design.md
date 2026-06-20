---
name: fronted-design
description: Design TripCraft frontend screens, React component structure, UX flows, and visual hierarchy before implementation.
---

# Fronted Design

Use this skill when designing TripCraft frontend UI/UX or React implementation details.

## Note

The skill name intentionally follows the user's requested spelling: `fronted-design`.

## Design principles

- Make the multi-agent planning process visible and understandable.
- Prioritize a clean travel-planning dashboard experience.
- Use progressive disclosure: input → live progress → result → map/history/chat refinement.
- Design for real data: loading, empty, error, partial API failure, and fallback states.
- Keep UI components reusable and data-driven.

## TripCraft frontend surfaces

Consider these core areas:

1. **Planning form**
   - destination, date range/days, budget, travelers, mobility constraints, interests, preferences.
2. **Agent progress timeline**
   - Weather, Transport, Accommodation, Attraction, Itinerary, Critic, Orchestrator status.
   - WebSocket-driven events with running/success/error/retrying states.
3. **Itinerary result**
   - daily cards, timeline items, transport, attractions, meals, hotel, costs, source badges.
4. **Map visualization**
   - Amap route and markers, day filter, clickable POI details.
5. **Revision history**
   - critic comments and v1 → v2 → v3 changes.
6. **Conversational adjustment**
   - chat panel for add/replace/reorder/slow down operations with precise patch feedback.

## React planning checklist

When invoked, produce:

- Page layout and interaction flow.
- Component tree.
- State model and API/WebSocket integration points.
- Key UI states: idle, loading, streaming progress, complete, error, editing.
- Styling direction suitable for the existing project setup.
- Accessibility and responsive behavior notes.

## Output format

Return:

```markdown
## Frontend Design
...

## Component Structure
...

## State & API Integration
...

## Implementation Steps
...

## Approval needed
请确认是否按这个前端设计开始实现。
```
