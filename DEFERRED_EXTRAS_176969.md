# Deferred from PR #176969 (opt-in "Add local energy site" sub-entry flow)

This branch (`fm/176969-deferred-extras`) is a snapshot of the original PR head
`dc9a332a6d8c` — it retains the full, pre-slim implementation. The slimmed PR
head keeps only the minimum needed to land the opt-in add-flow local Powerwall
control. Everything below was **pulled out** of the PR and preserved here for a
follow-up backlog item. The diff between the slimmed PR head and this branch is
exactly the deferred work.

## What was deferred and why it can wait

1. **Sub-entry reconfigure flow** (`async_step_reconfigure`, the reconfigure
   branch of `_async_save_credentials`, `_cloud_energy_site`, the
   `reconfigure`/`reconfigure_successful` strings, and their tests).
   - Why it can wait: the add flow already lets a user pair a site. Editing an
     existing subentry's credentials is a convenience — until then a user can
     remove and re-add. Deferring it also removed the only place that held an
     `EnergySiteRouter` in the config flow, which let us reach the cloud pairing
     endpoints directly through the cloud `EnergySite` instead of unwrapping the
     router's cloud secondary (the captain's review point). Re-adding reconfigure
     later must restore that unwrap (or wrap pairing endpoints on the router).

2. **Verification-timeout in-place retry** (`async_step_retry`, the
   `_register_authorized_client` split, the `PENDING_VERIFICATION_TIMEOUT`
   branches in `_async_begin_pairing`/`async_step_pair`, the `retry` string,
   and its tests).
   - Why it can wait: the approval window expiring is an edge case; the user can
     restart the add flow to get a fresh window. Nice UX, not required to land.

3. **502 gateway-unreachable handling** (`PowerwallUnreachableError`,
   `_is_gateway_unreachable`, the `powerwall_unreachable` abort/error strings,
   the 502 branches in pairing, and their tests).
   - Why it can wait: a bodyless/JSON 502 from the gateway-relay currently just
     surfaces as `cannot_connect`, which is correct if less specific. The
     dedicated retryable-502 messaging is a refinement.

4. **Unused `gateway_id` model field** (`TeslemetryEnergyData.gateway_id` and its
   assignment from `product.get("gateway_id")`).
   - Why it can wait: it was dead — stored but never read after the setup-time
     gateway-identity mismatch check was removed earlier in the PR. If a future
     PR reintroduces gateway-identity binding, restore it then.

## Retained in the slimmed PR (core)

- The opt-in add flow: select site -> register key -> approve -> credentials ->
  verify LAN -> create subentry bound to the existing device.
- Runtime local-control wiring: subentry resolution, `EnergySiteRouter`
  (local-first, cloud-fallback) construction, RSA key caching, stale-subentry
  pruning against the product inventory.
- Local health check kept: `PowerwallLookupError` (failed lookup != absent key)
  and `PowerwallKeyRejectedError` (unapproved key vs bad password) — both are
  correctness guards for the core pairing/credentials steps.
- Core pairing tests, rerouted from the reconfigure entry point to the add flow.
