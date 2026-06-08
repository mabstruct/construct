---
id: card-api-gateway-patterns
title: "API Gateway Architectural Patterns"
epistemic_type: concept
created: 2026-04-12
confidence: 3
source_tier: 2
domains:
  - api-gateways
content_categories:
  - architecture-patterns
lifecycle: growing
tags: [api-gateway, microservices, architecture, patterns]
---

## Summary
API gateways serve as the single entry point for client requests in a microservices architecture, handling cross-cutting concerns like authentication, rate limiting, and request routing.

## Key Patterns
- Reverse proxy with routing to backend services
- Authentication and authorization enforcement
- Rate limiting and throttling
- Response transformation and aggregation
- Protocol translation (REST, gRPC, WebSocket)
