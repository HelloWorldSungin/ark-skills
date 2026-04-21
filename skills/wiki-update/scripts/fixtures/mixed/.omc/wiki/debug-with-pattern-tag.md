---
title: JWT Refresh Race Condition
tags: [debugging, pattern]
category: debugging
confidence: high
---

# JWT Refresh Race

Concurrent refresh causes double-issuance. Lock on user_id.
