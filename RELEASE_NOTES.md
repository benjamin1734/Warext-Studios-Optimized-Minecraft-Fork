# Warext Server Engine 26.3 exp.26

Experimental multi-system optimization update. Pinned to Leaf 26.3 Build #4 and Paper/Moonrise from exp.21, preserving Warext improvements through exp.25. Java 25 remains the runtime baseline.

## Four optimization areas

### 1. Async Pathfinding / GC
- Replace the bounded linked-list-backed pathfinding work queue (`LinkedBlockingQueue`) with a preallocated `ArrayBlockingQueue` of the **same configured capacity**.
- Removes a newly allocated queue node for each enqueued path task while keeping bounded FIFO scheduling and existing overload/rejection policy semantics.
- Under high contention array-backed queues may trade allocation reduction for a single lock; **no blanket TPS/MSPT gain claimed**.

### 2. Async Entity Tracker memory after bursts
- The seven reusable per-context `ObjectArrayList` buffers are trimmed **only after a quiet tick** follows an exceptionally large burst.
- Preserves burst-sized backing arrays while workload remains high to avoid repeated trim/grow allocation cycles.
- `-Dwarext.tracker.context-list-trim-threshold=N` optionally sets the capacity threshold (default 4096, clamped 512–65536); quiet lists are trimmed to 256 slots.
- Snapshot stale-reference cleanup, capped packet batch arrays and geometric future/join buffers from exp.24–25 remain intact.

### 3. Adaptive CPU scheduling / save workers
- Background I/O headroom now accounts for optional pathfinder and entity tracker defaults **only when their performance profile enables them**.
- Balanced no longer reserves CPU for the extreme-only async tracker; pregeneration no longer reserves workers for either default-disabled subsystem.
- Actual I/O worker count remains conservative, max 2 by auto policy, with explicit `warext.cpu.io-workers` override retained. Per-server CPU quotas and custom thread overrides remain applicable; no fixed core or RAM assumption.

### 4. Asynchronous data saves / allocation
- Reuse one stable `Runnable` per active player/world save key when rescheduling the next coalesced snapshot.
- Avoid per-reschedule lambda allocation while retaining exp.22's one-write-per-queue-turn fairness, latest-snapshot merging, per-key exclusion and completion-future semantics.

## Publishing
- No new benchmark/test systems are written for exp.26, as requested.
- Existing GitHub Actions patch application, Java scheduler/evaluator regression checks, complete Paperclip Java 25 build, source ZIP packaging, and multiple server-profile/worldgen/save smoke gates **remain required before release**.
- JAR, full patched Java sources and checksum/metadata files are produced only in GitHub Actions and published in GitHub Releases.
- No numerical performance improvements or production-readiness are claimed without controlled comparison against the same Leaf baseline.
