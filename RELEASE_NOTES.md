# Warext Server Engine 26.3 exp.24

Experimental high-load Entity Tracker allocation and memory-retention update based on Leaf 26.3 build #4.

## Entity Tracker 2.0: avoid retaining unloaded entities
- The asynchronously processed `trackerSnapshot` entity array is reused to avoid allocations on every tracking tick.
- Prior to this update, elements beyond the currently active slice were never cleared after the world entity count decreased. That allowed removed/unloaded entities to remain strongly referenced through the reusable array.
- The tracker now records the previously active snapshot length and clears **only the stale tail when entity count shrinks**. At zero entities it clears the previous active slice once.
- Does not add work to the stable-size and growing-entity fast paths, and does not change how the worker reads the active entity range.
- Snapshot arrays still reuse capacity to avoid full-size allocations on every tick.

## Bounded packet-list retention
- Each TrackerCtx pools previously used per-connection packet lists.
- Burst-heavy ticks can grow an individual ObjectArrayList backing array far beyond usual packet counts. Reusing an oversized backing array indefinitely retains unnecessary memory.
- Packet batches with a backing capacity larger than `-Dwarext.tracker.packet-list-retain-capacity=N` (default 256, bounded to 16..4096) are **discarded from the reuse pool after send and clear**; normally sized batches are still pooled.
- Existing per-context pool limit (64 packet lists) is retained. No extra copies are made in the send path.

## Delivery / constraints
- Inherit Leaf 26.3 build #4 with pinned upstream commit `4b0dcd264996f18b48f783c58390a9090ba1964b` and the unchanged exp.23 O(1) NodeEvaluator pool and exp.22 fair save queue.
- No assumptions about a particular host's CPU or RAM.
- **No additional benchmark suite or new test code in this development step.** Existing mandatory GitHub Actions compile, smoke, source package and release gates stay in place.
- Publish runnable Paperclip JAR and complete patched-source ZIP only through GitHub Releases after main branch CI success.

**Expected effect:** reduced retained heap after large entity/packet bursts, not a guaranteed higher TPS; no controlled Leaf comparison has been measured.
