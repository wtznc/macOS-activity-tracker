# Roadmap

Long-term vision for macOS Activity Tracker.

---

## Current State (v1.0)

- Menu bar app with start/stop tracking
- Per-minute JSON storage with app usage data
- Window title detection (8 apps supported)
- AFK detection (5 min threshold)
- Manual HTTP sync with bearer auth
- Fast mode (app-only) vs detailed mode (app + window titles)

---

## Epic 1: Smart Sync

**Goal:** Seamless, reliable background synchronization

| Feature | Description | Priority |
|---------|-------------|----------|
| Auto-sync | Background sync at configurable intervals (15m/1h/daily) | High |
| Retry logic | Exponential backoff for failed syncs | High |
| Offline queue | Queue syncs when offline, flush on reconnect | Medium |
| Sync indicator | Menu bar badge showing sync status/pending count | Medium |
| Conflict resolution | Handle clock skew and duplicate data | Low |

---

## Epic 2: Privacy & Filtering

**Goal:** User control over what gets tracked

| Feature | Description | Priority |
|---------|-------------|----------|
| App blacklist | Exclude specific apps from tracking (e.g., 1Password) | High |
| Window title redaction | Regex-based title sanitization | High |
| Incognito mode | One-click pause that discards data | Medium |
| Sensitive app detection | Auto-detect banking/password apps | Medium |
| Domain filtering | Exclude URLs containing patterns | Low |

---

## Epic 3: Analytics Dashboard

**Goal:** Insights into productivity patterns

| Feature | Description | Priority |
|---------|-------------|----------|
| Daily summary | Menu bar dropdown with today's top apps | High |
| Weekly report | Local HTML report generation | Medium |
| Focus score | Calculate deep work vs context switching | Medium |
| Trend detection | "You spent 40% more time in Slack this week" | Low |
| Export formats | CSV, JSON, SQLite dump | Low |

---

## Epic 4: Extended Detection

**Goal:** Richer activity context

| Feature | Description | Priority |
|---------|-------------|----------|
| Browser URL tracking | Capture domain/path from Chrome, Safari, Firefox, Arc | High |
| Project detection | Infer project from window title patterns | Medium |
| Meeting detection | Detect Zoom/Meet/Teams calls | Medium |
| Document tracking | Track active document in Office/iWork apps | Low |
| Git repo detection | Associate coding time with repositories | Low |

---

## Epic 5: User Experience

**Goal:** Polish and accessibility

| Feature | Description | Priority |
|---------|-------------|----------|
| Settings UI | Native preferences window for all config | High |
| Onboarding | First-run setup wizard with permissions guide | Medium |
| Keyboard shortcuts | Global hotkeys for start/stop/incognito | Medium |
| Notifications | Optional alerts for milestones or focus breaks | Low |
| Widget support | macOS widget showing current session | Low |

---

## Epic 6: Data Management

**Goal:** Control over stored data

| Feature | Description | Priority |
|---------|-------------|----------|
| Auto-cleanup | Delete local data older than N days | High |
| Storage stats | Show disk usage in settings | Medium |
| Data export | One-click export all data | Medium |
| Selective delete | Remove specific days/apps from history | Low |
| Encryption at rest | Encrypt local JSON files | Low |

---

## Epic 7: Integrations

**Goal:** Connect with productivity ecosystem

| Feature | Description | Priority |
|---------|-------------|----------|
| Toggl import/export | Bidirectional sync with Toggl | Medium |
| Calendar correlation | Match tracking with calendar events | Medium |
| Webhook support | POST to arbitrary endpoints on events | Medium |
| Raycast extension | Quick actions and stats via Raycast | Low |
| Shortcuts support | macOS Shortcuts automation | Low |

---

## Epic 8: Performance & Reliability

**Goal:** Rock-solid background operation

| Feature | Description | Priority |
|---------|-------------|----------|
| Launch at login | Optional auto-start on boot | High |
| Crash recovery | Resume tracking after unexpected quit | High |
| Memory optimization | Reduce footprint for long-running sessions | Medium |
| Battery impact | Adaptive polling based on power source | Medium |
| Health checks | Self-diagnostics in menu bar | Low |

---

## Quick Wins (< 1 day each)

- [ ] Add "Copy today's summary" to menu bar
- [ ] Show total tracked time in menu bar title
- [ ] Add "Open data folder" menu item
- [ ] Configurable AFK threshold via menu
- [ ] Dark/light mode icon variants

---

## Technical Debt

- [ ] Expand window title support beyond 8 hardcoded apps
- [ ] Replace AppleScript with pure Accessibility API
- [ ] Add structured logging with log levels
- [ ] Database option for large datasets (SQLite)
- [ ] Async HTTP sync to prevent UI blocking

---

## Non-Goals

- Cross-platform support (this is macOS-native by design)
- Keystroke/mouse logging (privacy-first approach)
- Screenshot capture
- Employee monitoring features

---

## Contributing

Pick an epic, open an issue to discuss approach, submit PR. See `CONTRIBUTING.md` for setup.
