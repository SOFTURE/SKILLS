---
project: "Example clinic"
roadmap: payments
version: 1
status: waiting
backlog: context/backlog/roadmap-payments/
trigger: "the owner opens a payment provider account"
created: 2026-10-15
updated: 2026-10-15
---

# Roadmap payments: deposits at booking

## At a glance

| ID | Change | Outcome | Depends on | Mode | Status |
| --- | --- | --- | --- | --- | --- |
| **PY-1** | `deposit-at-booking` | a deposit is taken at booking | — | autonomous | blocked (provider account) |

## Items

### PY-1: Deposit at booking
- **Change ID:** `deposit-at-booking`
- **Status:** blocked (provider account)

### PY-2: Refund a deposit
- **Change ID:** `refund-deposit`
- **Status:** proposed

## Owner decisions and checks
- [ ] **PY-1**: pick the payment provider. Gates PY-1.
