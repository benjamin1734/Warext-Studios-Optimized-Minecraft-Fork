# Warext Server Engine 26.3 exp.25

Experimental performance update on the Leaf 26.3 Build #4 base. This release groups improvements in **three different core subsystems** rather than using one version for one minor change.

## 1. Entity Tracker — allocation stability across variable entity counts
- Future and join-context arrays now grow geometrically only when their **capacity** is insufficient, instead of being reallocated every time the entity task count changes.
- Existing `futureCount` is authoritative: reused over-capacity Future arrays never schedule or join inactive slots.
- `TrackerCtx.handle` takes an explicit active joined-context count and flushes only populated entries rather than iterating the full allocated capacity.
- After handling, only the active joined-context references are cleared; reused arrays do not pin entity tracker contexts, and capacity is retained for future ticks.
- Existing exp.24 snapshot tail cleanup and bounded packet-list retention remain enabled.

## 2. ChunkCache — cold sparse clear memory and CPU policy
- The existing hot chunk removal path stays **free of shrink rehashes**, preserving protection from sudden mass-unload p99 spikes.
- An explicit `ChunkCache.clear()` when table capacity exceeds eight times its initial capacity **and** fewer than half of initial-capacity entries remain reclaims the oversized key/value arrays.
- This replaces an O(huge capacity) clear on sparse maps with freshly allocated initial-capacity arrays; normal dense clears keep the capacity to avoid excessive shrink/regrow cycles.
- The single-entry cache and null-key flags are invalidated as before.

## 3. Async Pathfinding — bounded saturation diagnostic cost
- Replace a non-atomic shared warning timestamp with a monotonic `System.nanoTime()`-based AtomicLong CAS gate.
- Under concurrent executor queue saturation, emit at most one warning per 30-second interval across worker/caller threads instead of redundant logging.
- Preserve existing queue bounds, worker budget, user-configured rejection policy and path execution semantics.

## Delivery and compatibility
- Keep pinned upstream Leaf Build #4 (`4b0dcd264996f18b48f783c58390a9090ba1964b`), the exp.23 O(1) evaluator pool, exp.22 async-save fairness, and exp.24 tracker memory improvements.
- No fixed CPU count or heap size is assumed.
- No new benchmark/test suites were developed for this release at the user's request. Existing GitHub Actions build and smoke gates remain mandatory.
- On successful CI, publish **runnable JAR and full patched Java source** via GitHub Releases only.

The changes reduce identifiable allocation and logging costs. No numeric MSPT/TPS/RAM improvement is claimed without controlled comparative measurements.
