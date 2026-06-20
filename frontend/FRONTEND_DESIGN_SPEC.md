# TripCraft Frontend Design Specification

**Visual Style**: Subtle Tech (微科技风)
**Version**: 1.0
**Date**: 2026-06-17

---

## 1. Visual Design Language

### 1.1 Color Palette

```css
:root {
  /* Primary Background - Deep Space */
  --bg-primary: #0a0e17;           /* Main background */
  --bg-secondary: #121829;         /* Card/panel backgrounds */
  --bg-tertiary: #1a2332;          /* Elevated surfaces */

  /* Surface Layers - Glass Morphism */
  --surface-glass: rgba(18, 24, 41, 0.7);  /* Glass effect base */
  --surface-border: rgba(99, 179, 237, 0.15); /* Subtle cyan border */

  /* Primary Accent - Electric Cyan */
  --accent-primary: #63b3ed;       /* Main interactive color */
  --accent-primary-glow: rgba(99, 179, 237, 0.4); /* Glow effect */
  --accent-secondary: #4fd1c5;     /* Teal for success states */

  /* Semantic Colors */
  --status-running: #f6ad55;       /* Amber for running agents */
  --status-success: #68d391;       /* Green for completed */
  --status-error: #fc8181;         /* Red for errors */
  --status-queued: #718096;        /* Gray for queued */

  /* Text Hierarchy */
  --text-primary: #e2e8f0;         /* High emphasis */
  --text-secondary: #a0aec0;       /* Medium emphasis */
  --text-muted: #718096;           /* Low emphasis */

  /* Special Effects */
  --glow-subtle: 0 0 20px rgba(99, 179, 237, 0.15);
  --glow-medium: 0 0 30px rgba(99, 179, 237, 0.25);
  --glow-strong: 0 0 40px rgba(99, 179, 237, 0.35);
}
```

### 1.2 Typography

```css
/* Primary Font - Modern Sans */
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;

/* Monospace for data */
font-family-mono: 'JetBrains Mono', 'Fira Code', monospace;

/* Type Scale */
--text-xs: 0.75rem;    /* 12px - labels, badges */
--text-sm: 0.875rem;   /* 14px - secondary text */
--text-base: 1rem;     /* 16px - body text */
--text-lg: 1.125rem;   /* 18px - large body */
--text-xl: 1.25rem;    /* 20px - section headers */
--text-2xl: 1.5rem;    /* 24px - card titles */
--text-3xl: 1.875rem;  /* 30px - page titles */
--text-4xl: 2.25rem;   /* 36px - hero text */
```

### 1.3 Spacing & Grid

```css
/* Spacing Scale */
--space-1: 0.25rem;   /* 4px */
--space-2: 0.5rem;    /* 8px */
--space-3: 0.75rem;   /* 12px */
--space-4: 1rem;      /* 16px */
--space-5: 1.25rem;   /* 20px */
--space-6: 1.5rem;    /* 24px */
--space-8: 2rem;      /* 32px */
--space-10: 2.5rem;   /* 40px */
--space-12: 3rem;     /* 48px */

/* Layout Grid */
--sidebar-width: 420px;  /* Left panel */
--content-max-width: 1440px;
--grid-gap: var(--space-6);
```

### 1.4 Effects & Treatments

```css
/* Glass Card Effect */
.glass-card {
  background: var(--surface-glass);
  backdrop-filter: blur(12px);
  border: 1px solid var(--surface-border);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

/* Subtle Glow on Hover */
.glass-card:hover {
  border-color: rgba(99, 179, 237, 0.3);
  box-shadow: var(--glow-subtle), 0 8px 32px rgba(0, 0, 0, 0.3);
}

/* Accent Glow for Primary Actions */
.accent-glow {
  box-shadow: 0 0 20px var(--accent-primary-glow);
}

/* Gradient Accent Border */
.gradient-border {
  position: relative;
}
.gradient-border::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  padding: 1px;
  background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
}
```

---

## 2. Layout Concept

### 2.1 Main Structure

```
┌─────────────────────────────────────────────────────────────────┐
│  Header (60px) - Logo + Plan Status + Quick Actions             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐  ┌─────────────────────────────────────┐  │
│  │                  │  │                                     │  │
│  │   Left Panel     │  │        Right Panel (Tabs)           │  │
│  │   (420px)        │  │        (Flexible width)             │  │
│  │                  │  │                                     │  │
│  │  ┌────────────┐  │  │  ┌─────────────────────────────┐   │  │
│  │  │ Planning   │  │  │  │  Itinerary | Map | History  │   │  │
│  │  │ Form       │  │  │  │           | Chat            │   │  │
│  │  └────────────┘  │  │  └─────────────────────────────┘   │  │
│  │                  │  │                                     │  │
│  │  ┌────────────┐  │  │                                     │  │
│  │  │ Agent      │  │  │                                     │  │
│  │  │ Timeline   │  │  │                                     │  │
│  │  └────────────┘  │  │                                     │  │
│  │                  │  │                                     │  │
│  │  ┌────────────┐  │  │                                     │  │
│  │  │ Memory     │  │  │                                     │  │
│  │  │ Panel      │  │  │                                     │  │
│  │  └────────────┘  │  │                                     │  │
│  │                  │  │                                     │  │
│  └──────────────────┘  └─────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 State-Based Navigation

The interface uses **progressive disclosure** with smooth transitions between states:

1. **IDLE** → Planning form prominent, other panels collapsed/minimized
2. **STREAMING** → Agent timeline expands, real-time updates animate in
3. **COMPLETE** → Itinerary/Map/History tabs become prominent
4. **REFINING** → Chat panel expands, contextual editing

---

## 3. Component Hierarchy

### 3.1 Component Tree

```
App (Layout)
├── Header
│   ├── Logo (animated icon)
│   ├── PlanStatusBadge
│   └── QuickActions (export, share, settings)
│
├── LeftPanel
│   ├── PlanningForm (collapsible when complete)
│   │   ├── DestinationInput (with autocomplete)
│   │   ├── DateRangePicker
│   │   ├── BudgetSlider (with visual feedback)
│   │   ├── TravelerProfile (adults/children/seniors)
│   │   ├── InterestTags (multi-select chips)
│   │   └── SubmitButton (with loading state)
│   │
│   ├── AgentTimeline (expandable during streaming)
│   │   ├── TimelineHeader (progress indicator)
│   │   └── AgentCard[] (6 agents)
│   │       ├── AgentIcon (animated status)
│   │       ├── AgentName
│   │       ├── StatusBadge
│   │       └── ProgressBar
│   │
│   └── MemoryPanel (collapsible)
│       ├── HistoricalPlans
│       └── LongTermMemory
│
└── RightPanel (Tabbed)
    ├── TabHeader
    │   ├── ItineraryTab
    │   ├── MapTab
    │   ├── HistoryTab
    │   └── ChatTab
    │
    ├── ItineraryView
    │   ├── SummaryCard (destination, dates, total cost)
    │   ├── DayAccordion[]
    │   │   ├── DayHeader (day number, date, cost)
    │   │   └── TimelineItem[]
    │   │       ├── TimeMarker
    │   │       ├── ItemIcon (type-based)
    │   │       ├── ItemDetails
    │   │       └── SourceBadge
    │   └── CostBreakdown (visual chart)
    │
    ├── MapPanel
    │   ├── DayFilter (pill buttons)
    │   ├── MapContainer
    │   └── RouteInfo (distance, duration)
    │
    ├── RevisionHistory
    │   ├── VersionSelector (v1, v2, v3)
    │   ├── CriticCommentCard[]
    │   │   ├── SeverityBadge
    │   │   ├── DimensionTag
    │   │   └── Suggestion
    │   └── IterationComparison
    │
    └── AdjustmentChat
        ├── ChatHeader (with plan context)
        ├── MessageList
        │   ├── UserMessage
        │   └── SystemMessage
        │       ├── TextResponse
        │       ├── ActionConfirmation
        │       └── PatchPreview
        ├── ChatInput
        └── QuickActions (suggestion chips)
```

### 3.2 Component Refactoring Plan

| Current Component | Action | Changes |
|------------------|--------|---------|
| **App.tsx** | Refactor | Add Header, adjust layout spacing |
| **PlanningForm.tsx** | Enhance | Add glow effects, animated submit button |
| **AgentTimeline.tsx** | Major Redesign | Add animated agent cards, pulse effects |
| **ItineraryView.tsx** | Enhance | Add cost visualization, timeline animations |
| **MapPanel.tsx** | Minor Update | Match color theme, add route info |
| **MemoryPanel.tsx** | Minor Update | Glass card styling |
| **AdjustmentChat.tsx** | Enhance | Message animations, typing indicators |
| **RevisionHistory.tsx** | Enhance | Iteration visualization |

---

## 4. Key UI States

### 4.1 Idle State (Initial)

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                    ┌─────────────────────┐                  │
│                    │   ✈️ Create Your    │                  │
│                    │   Dream Journey     │                  │
│                    └─────────────────────┘                  │
│                                                             │
│    ┌───────────────────────────────────────────────────┐   │
│    │                                                   │   │
│    │   Where would you like to go?                     │   │
│    │   [Destination Input with glow effect]            │   │
│    │                                                   │   │
│    │   When?                                           │   │
│    │   [Date Range Picker]                             │   │
│    │                                                   │   │
│    │   Budget                                          │   │
│    │   ═══════════════════○═══════════  ¥15,000        │   │
│    │                                                   │   │
│    │   Who's traveling?                                │   │
│    │   [Adults: 2] [Children: 0] [Seniors: 0]         │   │
│    │                                                   │   │
│    │   Interests                                       │   │
│    │   [🏔️ Nature] [🏛️ Culture] [🍜 Food] [📸 Photo]  │   │
│    │                                                   │   │
│    │   ─────────────────────────────────────────────   │   │
│    │   [✨ Generate My Adventure]                      │   │
│    │                                                   │   │
│    └───────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Design Notes:**
- Large, inviting hero text with subtle gradient
- Form card with glass effect and glow border
- Input fields with subtle cyan glow on focus
- Submit button with pulsing glow animation
- Background: subtle particle animation (low opacity)

### 4.2 Streaming Progress State

```
┌─────────────────────────────────────────────────────────────┐
│  🎯 Planning your journey to Tokyo...          [Cancel]     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                                                     │   │
│  │  ⚡ Weather Agent        ████████████░░  85%        │   │
│  │     "Analyzing Tokyo weather for March..."          │   │
│  │                                                     │   │
│  │  🚄 Transport Agent      ██████████░░░░  70%        │   │
│  │     "Searching flight options..."                    │   │
│  │                                                     │   │
│  │  🏨 Accommodation Agent  ████████░░░░░░  60%        │   │
│  │     "Finding hotels in Shibuya..."                  │   │
│  │                                                     │   │
│  │  🎡 Attraction Agent     ██████░░░░░░░░  45%        │   │
│  │     "Curating must-see spots..."                    │   │
│  │                                                     │   │
│  │  📋 Itinerary Agent      ░░░░░░░░░░░░░░  Waiting    │   │
│  │     "Waiting for data..."                           │   │
│  │                                                     │   │
│  │  🔍 Critic Agent         ░░░░░░░░░░░░░░  Waiting    │   │
│  │     "Standing by..."                                │   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  💡 Tip: Our AI agents are gathering real-time data...      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Design Notes:**
- Each agent card has icon with pulse animation when running
- Progress bars with gradient fill and subtle glow
- Completed agents show checkmark with green glow
- Background particles speed up during streaming

### 4.3 Complete Result State

```
┌─────────────────────────────────────────────────────────────┐
│  📍 Tokyo Adventure • 7 Days • ¥15,000 • v2 (Optimized)    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Day 1-2  │  │ Day 3-4  │  │ Day 5-6  │  │ Day 7    │   │
│  │ Tokyo    │  │ Hakone   │  │ Kyoto    │  │ Osaka    │   │
│  │ ¥4,500   │  │ ¥3,200   │  │ ¥4,800   │  │ ¥2,500   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  📅 Day 1: Arrival in Tokyo                        │   │
│  │  ──────────────────────────────────────────────────│   │
│  │                                                     │   │
│  │  09:00  ✈️  Arrive at Narita Airport                │   │
│  │          Source: Amap • ¥800                        │   │
│  │                                                     │   │
│  │  10:30  🚄  Narita Express → Shibuya                │   │
│  │          Source: Amap • ¥30                         │   │
│  │                                                     │   │
│  │  11:30  🏨  Check-in at Shibuya Excel Hotel         │   │
│  │          Source: Amap RAG • ¥120/night              │   │
│  │                                                     │   │
│  │  13:00  🍜  Lunch at Ichiran Ramen                  │   │
│  │          Source: RAG Match • ¥85                    │   │
│  │                                                     │   │
│  │  14:30  🎡  Explore Shibuya Crossing & Center-gai   │   │
│  │          Source: Amap • Free                        │   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  💰 Cost Breakdown                                  │   │
│  │  ════════════════════════════════════════════════  │   │
│  │                                                     │   │
│  │  Transport    ████████████░░░░  40%  ¥6,000        │   │
│  │  Hotels       ████████░░░░░░░░  30%  ¥4,500        │   │
│  │  Food         ██████░░░░░░░░░░  20%  ¥3,000        │   │
│  │  Attractions  ████░░░░░░░░░░░░  10%  ¥1,500        │   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Design Notes:**
- Day cards are collapsible accordions with smooth animation
- Timeline items slide in with staggered animation
- Cost breakdown uses horizontal bar chart with gradient fills
- Source badges are small, subtle chips

### 4.4 Error States

**Form Validation:**
```tsx
// Input with error state
<div className="form-field error">
  <input className="glow-border-error" />
  <span className="error-message fade-in">
    ⚠️ Please enter a valid destination
  </span>
</div>
```

**API Error (Non-blocking):**
```tsx
// Toast notification
<div className="toast error slide-in-right">
  <span className="toast-icon">⚠️</span>
  <span className="toast-message">
    Weather data unavailable, using seasonal averages
  </span>
  <button className="toast-dismiss">✕</button>
</div>
```

---

## 5. Dynamic Elements

### 5.1 Background Effects

**Particle System (CSS only, lightweight):**
```css
.particles-bg {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
  background-image:
    radial-gradient(2px 2px at 20px 30px, rgba(99, 179, 237, 0.15), transparent),
    radial-gradient(2px 2px at 40px 70px, rgba(99, 179, 237, 0.1), transparent),
    radial-gradient(1px 1px at 90px 40px, rgba(99, 179, 237, 0.15), transparent),
    radial-gradient(2px 2px at 130px 80px, rgba(99, 179, 237, 0.1), transparent),
    radial-gradient(1px 1px at 160px 120px, rgba(99, 179, 237, 0.12), transparent);
  background-size: 200px 150px;
  animation: particleDrift 60s linear infinite;
}

@keyframes particleDrift {
  from { transform: translateY(0); }
  to { transform: translateY(-150px); }
}
```

**Gradient Mesh (CSS):**
```css
.gradient-mesh {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
  background:
    radial-gradient(ellipse at 20% 80%, rgba(99, 179, 237, 0.08) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 20%, rgba(79, 209, 197, 0.06) 0%, transparent 50%),
    radial-gradient(ellipse at 40% 40%, rgba(99, 179, 237, 0.04) 0%, transparent 40%);
}
```

### 5.2 Micro-Interactions

**Button Hover:**
```css
.btn-primary {
  background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: var(--glow-medium);
}

.btn-primary:active {
  transform: translateY(0);
  box-shadow: var(--glow-subtle);
}
```

**Input Focus:**
```css
.input-field {
  border: 1px solid var(--surface-border);
  transition: all 0.3s ease;
}

.input-field:focus {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 3px rgba(99, 179, 237, 0.1), var(--glow-subtle);
}
```

**Card Hover:**
```css
.glass-card {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.glass-card:hover {
  transform: translateY(-4px);
  border-color: rgba(99, 179, 237, 0.3);
  box-shadow: var(--glow-subtle), 0 12px 40px rgba(0, 0, 0, 0.4);
}
```

**Agent Card Pulse (when running):**
```css
.agent-card.running {
  border-color: var(--status-running);
  animation: pulseGlow 2s ease-in-out infinite;
}

@keyframes pulseGlow {
  0%, 100% {
    box-shadow: 0 0 20px rgba(246, 173, 85, 0.2);
  }
  50% {
    box-shadow: 0 0 30px rgba(246, 173, 85, 0.4);
  }
}
```

### 5.3 Transition Animations

**Page/State Transitions:**
```css
/* Fade + Slide */
.page-enter {
  opacity: 0;
  transform: translateY(20px);
}

.page-enter-active {
  opacity: 1;
  transform: translateY(0);
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Staggered list items */
.timeline-item {
  opacity: 0;
  transform: translateX(-20px);
  animation: slideInRight 0.5s ease forwards;
}

.timeline-item:nth-child(1) { animation-delay: 0.1s; }
.timeline-item:nth-child(2) { animation-delay: 0.2s; }
.timeline-item:nth-child(3) { animation-delay: 0.3s; }
/* ... */

@keyframes slideInRight {
  to {
    opacity: 1;
    transform: translateX(0);
  }
}
```

**Accordion Animation:**
```css
.accordion-content {
  overflow: hidden;
  transition: max-height 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.accordion-content.expanded {
  max-height: 1000px; /* Adjust based on content */
}
```

### 5.4 Loading States

**Skeleton Loader:**
```css
.skeleton {
  background: linear-gradient(
    90deg,
    var(--bg-tertiary) 25%,
    rgba(99, 179, 237, 0.1) 50%,
    var(--bg-tertiary) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 8px;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

**Button Loading State:**
```css
.btn-loading {
  position: relative;
  pointer-events: none;
}

.btn-loading::after {
  content: '';
  position: absolute;
  width: 20px;
  height: 20px;
  border: 2px solid transparent;
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
```

---

## 6. Implementation Approach

### 6.1 CSS Strategy

**Option A: CSS Modules (Recommended)**
```tsx
// PlanningForm.module.css
.formCard {
  composes: glass-card;
  padding: var(--space-6);
}

.submitButton {
  composes: btn-primary accent-glow;
  width: 100%;
  height: 48px;
  font-size: var(--text-lg);
}
```

**Benefits:**
- Scoped styles (no conflicts)
- TypeScript autocompletion
- Works with existing project structure

### 6.2 Animation Patterns

**Framer Motion Integration:**
```tsx
import { motion, AnimatePresence } from 'framer-motion';

// Page transition wrapper
<motion.div
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  exit={{ opacity: 0, y: -20 }}
  transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
>
  {children}
</motion.div>

// Staggered list
<motion.ul
  initial="hidden"
  animate="visible"
  variants={{
    visible: { transition: { staggerChildren: 0.1 } }
  }}
>
  {items.map(item => (
    <motion.li
      key={item.id}
      variants={{
        hidden: { opacity: 0, x: -20 },
        visible: { opacity: 1, x: 0 }
      }}
    >
      {item.content}
    </motion.li>
  ))}
</motion.ul>
```

### 6.3 Performance Considerations

1. **Lazy Loading:**
   ```tsx
   const MapPanel = React.lazy(() => import('./components/MapPanel'));
   ```

2. **Memoization:**
   ```tsx
   const MemoizedTimeline = React.memo(TimelineItem);
   ```

3. **Virtual Scrolling (for long lists):**
   ```tsx
   import { FixedSizeList } from 'react-window';
   ```

4. **Animation Performance:**
   - Use `transform` and `opacity` for animations (GPU-accelerated)
   - Avoid animating `width`, `height`, `top`, `left`
   - Use `will-change` sparingly for complex animations

### 6.4 Accessibility

```tsx
// Focus management
<button
  aria-label="Generate travel plan"
  aria-busy={isLoading}
  aria-disabled={isDisabled}
>

// Screen reader announcements
<div role="status" aria-live="polite">
  {`Planning progress: ${completedAgents} of ${totalAgents} agents complete`}
</div>

// Keyboard navigation
<div
  role="tablist"
  onKeyDown={handleKeyNavigation}
>
  {tabs.map(tab => (
    <button
      key={tab.id}
      role="tab"
      aria-selected={activeTab === tab.id}
      aria-controls={`${tab.id}-panel`}
    >
      {tab.label}
    </button>
  ))}
</div>
```

---

## 7. Surface-Specific Designs

### 7.1 Planning Form Enhancements

**Current Issues:**
- Basic form layout
- Static submit button
- No visual feedback on interactions

**New Design:**
1. **Destination Input:**
   - Glowing border on focus
   - Autocomplete dropdown with blur background
   - Icon animation on valid input

2. **Budget Slider:**
   - Gradient fill track
   - Glow effect on thumb
   - Real-time currency formatting

3. **Interest Tags:**
   - Chip design with hover glow
   - Selected state with accent color
   - Scale animation on select

4. **Submit Button:**
   - Gradient background
   - Pulsing glow animation
   - Loading spinner state
   - Success checkmark animation

### 7.2 Agent Timeline Redesign

**Current Issues:**
- Basic list layout
- Static status indicators
- Limited visual hierarchy

**New Design:**
1. **Agent Cards:**
   - Horizontal cards with icon, name, status, progress
   - Running: amber pulse animation
   - Success: green checkmark with sparkle
   - Error: red alert with shake animation
   - Queued: gray with fade effect

2. **Progress Visualization:**
   - Circular progress indicator per agent
   - Overall progress bar at top
   - Time elapsed / estimated remaining

3. **Data Stream Animation:**
   - Small dots flowing from agents to itinerary
   - Visual representation of data aggregation

### 7.3 Itinerary View Enhancements

**Current Issues:**
- Static accordion layout
- Basic timeline design
- No cost visualization

**New Design:**
1. **Day Cards:**
   - Horizontal scrollable cards
   - Day thumbnail (map preview or key attraction photo)
   - Cost badge with glow
   - Expand with 3D tilt effect

2. **Timeline Items:**
   - Left-aligned timeline with vertical line
   - Icon bubbles with type-based colors
   - Slide-in animation on expand
   - Source badges as small pills

3. **Cost Breakdown:**
   - Horizontal stacked bar chart
   - Category icons and percentages
   - Animate on scroll into view

### 7.4 Map Panel Updates

**Current Issues:**
- Basic map container
- Limited route information

**New Design:**
1. **Day Filter:**
   - Pill-shaped buttons
   - Active state with glow
   - Smooth slide animation between days

2. **Route Info:**
   - Floating card over map
   - Distance and duration stats
   - Transport mode icons

3. **Map Container:**
   - Rounded corners with glow border
   - Dark theme map style
   - Animated markers

### 7.5 Adjustment Chat Enhancement

**Current Issues:**
- Basic chat layout
- No typing indicators
- Limited message types

**New Design:**
1. **Chat Header:**
   - Plan context summary
   - Quick action chips

2. **Messages:**
   - User messages: right-aligned, accent border
   - System messages: left-aligned, glass background
   - Typing indicator: animated dots
   - Action cards: highlighted with glow

3. **Input Area:**
   - Glow border on focus
   - Suggestion chips below
   - Send button with icon animation

---

## 8. New Components to Create

### 8.1 Header Component

```tsx
// Header.tsx
const Header: React.FC = () => {
  return (
    <header className="header glass-card">
      <div className="logo">
        <LogoIcon className="logo-icon pulse" />
        <span className="logo-text">TripCraft</span>
      </div>
      <PlanStatusBadge />
      <QuickActions />
    </header>
  );
};
```

### 8.2 CostBreakdown Component

```tsx
// CostBreakdown.tsx
interface CostBreakdownProps {
  categories: {
    name: string;
    amount: number;
    color: string;
    icon: string;
  }[];
  total: number;
}

const CostBreakdown: React.FC<CostBreakdownProps> = ({ categories, total }) => {
  return (
    <div className="cost-breakdown glass-card">
      <h3>Cost Breakdown</h3>
      <div className="bar-chart">
        {categories.map(cat => (
          <div
            key={cat.name}
            className="bar-segment"
            style={{
              width: `${(cat.amount / total) * 100}%`,
              backgroundColor: cat.color
            }}
          />
        ))}
      </div>
      <div className="legend">
        {categories.map(cat => (
          <div key={cat.name} className="legend-item">
            <span className="legend-icon">{cat.icon}</span>
            <span className="legend-label">{cat.name}</span>
            <span className="legend-value">¥{cat.amount.toLocaleString()}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
```

### 8.3 AnimatedBackground Component

```tsx
// AnimatedBackground.tsx
const AnimatedBackground: React.FC = () => {
  return (
    <div className="animated-background">
      <div className="gradient-mesh" />
      <div className="particles-bg" />
    </div>
  );
};
```

---

## 9. Implementation Steps

### Phase 1: Foundation (Days 1-2)

1. **Update Global Styles**
   - Add CSS variables to `app.css`
   - Create utility classes for glass effects
   - Add animation keyframes

2. **Create AnimatedBackground Component**
   - Implement particle system
   - Add gradient mesh
   - Integrate into App.tsx

3. **Refactor App Layout**
   - Add Header component
   - Update spacing and layout grid
   - Implement state-based panel visibility

### Phase 2: Core Components (Days 3-5)

1. **Enhance PlanningForm**
   - Add glow effects to inputs
   - Implement animated submit button
   - Add form validation animations

2. **Redesign AgentTimeline**
   - Create new AgentCard component
   - Add pulse animations for running state
   - Implement progress indicators

3. **Enhance ItineraryView**
   - Add cost breakdown chart
   - Implement timeline animations
   - Create day card thumbnails

### Phase 3: Supporting Components (Days 6-7)

1. **Update MapPanel**
   - Add day filter pills
   - Implement route info card
   - Match theme styling

2. **Enhance AdjustmentChat**
   - Add typing indicators
   - Implement message animations
   - Create quick action chips

3. **Update MemoryPanel**
   - Apply glass card styling
   - Add hover effects

### Phase 4: Polish & Integration (Days 8-10)

1. **Add Page Transitions**
   - Implement Framer Motion AnimatePresence
   - Add staggered animations

2. **Performance Optimization**
   - Lazy load MapPanel
   - Add React.memo to expensive components
   - Implement skeleton loaders

3. **Accessibility Audit**
   - Add ARIA labels
   - Test keyboard navigation
   - Verify screen reader support

---

## 10. File Structure

```
frontend/src/
├── components/
│   ├── layout/
│   │   ├── Header.tsx
│   │   ├── Header.module.css
│   │   ├── AnimatedBackground.tsx
│   │   └── AnimatedBackground.module.css
│   │
│   ├── planning/
│   │   ├── PlanningForm.tsx
│   │   ├── PlanningForm.module.css
│   │   ├── DestinationInput.tsx
│   │   └── BudgetSlider.tsx
│   │
│   ├── agents/
│   │   ├── AgentTimeline.tsx
│   │   ├── AgentTimeline.module.css
│   │   └── AgentCard.tsx
│   │
│   ├── itinerary/
│   │   ├── ItineraryView.tsx
│   │   ├── ItineraryView.module.css
│   │   ├── DayCard.tsx
│   │   ├── TimelineItem.tsx
│   │   └── CostBreakdown.tsx
│   │
│   ├── map/
│   │   ├── MapPanel.tsx
│   │   ├── MapPanel.module.css
│   │   └── DayFilter.tsx
│   │
│   ├── chat/
│   │   ├── AdjustmentChat.tsx
│   │   ├── AdjustmentChat.module.css
│   │   ├── ChatMessage.tsx
│   │   └── TypingIndicator.tsx
│   │
│   └── history/
│       ├── RevisionHistory.tsx
│       ├── RevisionHistory.module.css
│       └── MemoryPanel.tsx
│
├── styles/
│   ├── variables.css      (CSS custom properties)
│   ├── utilities.css      (Glass card, glow effects)
│   ├── animations.css     (Keyframes)
│   └── app.css            (Global styles - update existing)
│
├── App.tsx                 (Update with new layout)
└── main.tsx               (Add Framer Motion AnimatePresence)
```

---

## 11. Approval Needed

**请确认是否按这个前端设计开始实现。**

### Key Decisions Made:
1. **Visual Style**: Subtle tech (微科技风) - professional with sci-fi accents
2. **Color Palette**: Deep space blues with electric cyan accents
3. **Layout**: Two-panel layout retained, enhanced with glass morphism
4. **Animations**: Framer Motion + CSS animations for performance
5. **CSS Strategy**: CSS Modules for scoped styles
6. **Background**: Subtle particle system + gradient mesh

### What This Design Achieves:
- ✅ Novel yet professional aesthetic
- ✅ Dynamic without being distracting
- ✅ Tech-forward with cyan glows and glass effects
- ✅ Progressive disclosure maintained
- ✅ All existing features preserved
- ✅ Performance-conscious animations

### Next Steps Upon Approval:
1. Create CSS variables and utility classes
2. Build AnimatedBackground component
3. Refactor existing components one by one
4. Add new components (Header, CostBreakdown)
5. Test and polish animations

---

**End of Design Specification**