# Warext Server Engine 26.3 exp.23

Experimental performance maintenance on Leaf 26.3 build #4 (Paper/Moonrise), keeping the proven exp.22 async-save fairness scheduling.

## Constant-time, bounded async pathfinder evaluator pooling
- Replaced an **O(n)** `ConcurrentLinkedQueue.size()` call in the hot `NodeEvaluatorCache.returnNodeEvaluator` path with an **O(1)** atomic retained-slot counter per generator/feature pool.
- Use compare-and-set to reserve storage before offering a returned evaluator. Concurrent borrowers decrement after successful dequeue.
- Keep the previous dynamic retained-pool cap: explicit `-Dwarext.pathfinding.evaluator-pool-cap=N` clamped 1..128; otherwise the worker-adjusted range of 4..32.
- Preserve generator **identity** and evaluator feature isolation. Never introduce a global lock, ThreadLocal evaluator pool, or per-checkout expensive pool walks.
- Drop surplus evaluators from burst pathfinding rather than retaining more than the configured memory budget.
- Concurrent operations may briefly reserve a slot before queue insertion; this is a safe bounded-reuse tradeoff rather than a performance guarantee.

## Regression test
- Added a GitHub Actions test that uses `javac` to compile the **real generated patched** `NodeEvaluatorCache.java` against minimal API stubs and runs:
  - 64 simultaneously checked-out evaluators and exact bounded retention at cap=4.
  - Generator identity / feature-bit reuse isolation.
  - Double-return and removed-object rejection.
  - 12-worker, 18,000-operation simultaneous take/return stress, no duplicate checkouts, and counter/queue parity at quiescence.
- Re-run exp.22 async save ordering/fairness Java regression, full Paperclip Java 25 build and existing startup, worldgen, and save/reload smoke tests.

## Release
- Pinned upstream: Leaf 26.3 build #4, `4b0dcd264996f18b48f783c58390a9090ba1964b`.
- No fixed CPU or RAM assumptions.
- Source and JAR are built, tested and published **only on GitHub Actions**; no user-side ZIP files.

**Measurement:** This removes an algorithmically linear operation and validates concurrency correctness, but does not prove a specific MSPT improvement relative to Leaf without controlled benchmarks.
