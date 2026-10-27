## Design decisions and tradeoffs

**1. Single pod, two servers (REST :8000 + MCP :8001) sharing one SQLite.**
- *Tradeoff:* couples the control plane and the data plane; a crash takes both; SQLite limits horizontal scale.
- *Rationale:* one PVC, one image, one rollout — simplest correct MVP. Production split: REST and MCP as separate Deployments over Postgres.

**2. Identity propagated to MCP sessions via `contextvars`, not request‑scoped DB reads.**
- *Tradeoff:* contextvars are per‑async‑task; must set at the ASGI boundary before the session task spawns.
- *Rationale:* lets a long‑lived Streamable‑HTTP session attribute every later `tools/call` to the authenticating user without re‑parsing headers per call — this is how the audit log shows `member` vs `admin` correctly.

**3. Tool collision handled by `<server>__<tool>` prefixing + split‑at‑call‑time routing.**
- *Tradeoff:* tool names grow; a server literally named with `__` would confuse the split (rejected at registration).
- *Rationale:* the spec requires two servers to expose the same tool name; prefixing is the only scheme that survives aggregation into one flat list.

**4. Declarative Helm for everything (incl. provisioning), vs the imperative K8s‑client approach common in prior art.**
- *Tradeoff:* dynamic per‑store releases need the controller to render+apply charts at runtime (heavier RBAC).
- *Rationale:* the assignment mandates Helm and forbids Kustomize; declarative releases give clean cascading teardown (delete namespace = delete release objects) and reviewable values per store.

**5. WooCommerce over REST + OAuth 1.0a, not WP‑CLI.**
- *Tradeoff:* must sign each request and match the hostAlias to the configured site URL or signatures fail.
- *Rationale:* REST crosses pod boundaries cleanly; WP‑CLI needs `kubectl exec`/filesystem and is unusable for per‑request MCP calls.

**6. `nip.io` wildcards instead of `/etc/hosts` + port‑forward.**
- *Tradeoff:* depends on public DNS resolving to 127.0.0.1.
- *Rationale:* zero host‑file mutation, works identically for every reviewer's machine.

**7. No hardcoded credentials anywhere (keys generated at first boot, bcrypt‑hashed).**
- *Tradeoff:* first‑boot keys print once to the seed log and must be captured.
- *Rationale:* a leaked repo never leaks a live key; revocation is a single `is_active=False`.