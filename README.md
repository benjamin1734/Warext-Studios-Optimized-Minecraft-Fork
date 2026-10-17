# Warext Server Engine

High-performance Minecraft server engine focused on low MSPT, low p95/p99 tick latency, efficient CPU scheduling, reduced allocation/GC pressure and low memory overhead.

## Current target
- Minecraft line: 26.3
- Java: 25
- Release line: `26.3-exp.26` (previous published release; all **future** JARs are built on a private local builder, with GitHub used solely for source and Release storage)
- Goal: minimize MSPT, p95/p99 tick latency, CPU time per tick, allocation/GC pressure and RAM use while preserving broad Paper ecosystem compatibility.

## Performance profiles

### Balanced — default
Recommended general-purpose profile.

```bash
java -Dwarext.profile=balanced -jar Warext-Server-Engine-26.3.jar nogui
```

Balanced enables optimized async pathfinding automatically on suitable multi-core CPUs, enables Dynamic Activation of Brain with its compatibility blacklist and the optimized KD-tree entity-activation implementation, reserves a share of the JVM-visible CPU capacity for the main tick thread/GC/networking, and leaves the experimental async entity tracker disabled by default.

### Extreme
For high-entity servers where maximum tick throughput matters more than conservative compatibility.

```bash
java -Dwarext.profile=extreme -jar Warext-Server-Engine-26.3.jar nogui
```

Extreme enables the optimized multi-threaded entity tracker, experimental entity-activation/random-tick/sleeping-block-entity/DAB optimizers, and gives a larger share of the shared async CPU budget to pathfinding/tracking.

### Compatibility

```bash
java -Dwarext.profile=compatibility -jar Warext-Server-Engine-26.3.jar nogui
```

Use this when plugin compatibility matters more than experimental async performance.

## CPU overrides

Automatic CPU budgeting derives defaults from the processors visible to the JVM (including CPU quotas when supported). No particular core count or RAM capacity is assumed. For production use, choose Java heap settings according to your actual server resources and plugin workload. Explicit Paper thread settings take priority; manual overrides are available when benchmarking a specific host:

- `-Dwarext.cpu.reserve=N`
- `-Dwarext.cpu.pathfinding-threads=N`
- `-Dwarext.cpu.tracker-threads=N`
- `-Dwarext.cpu.io-workers=N`
- `-Dwarext.cpu.chunk-workers=N`
- `-Dwarext.kdtree.linear-threshold=N`

The automatic scheduler reserves CPU headroom instead of letting every subsystem independently consume all logical processors.

## Pregeneration and experimental features

For offline world generation, select `-Dwarext.profile=pregeneration`; after generation return to a normal serving profile. The chunk worker budget automatically scales with available processing capacity, and explicit Paper/Moonrise worker settings are preserved.

The direct ticking-chunk set lookup from exp.19 is **disabled by default** at `performance.chunk.direct-ticking-set-lookups.enabled`. It requires a server restart when changed. Previously published CI builds checked it with an independent live-holder parity check; this is not a substitute for long-running production workload testing.

## Main optimization areas

- Adaptive multi-core pathfinding, with preallocated bounded FIFO task queue storage (reduced per-task node allocations).
- Shared CPU budgeting across async systems; background I/O headroom discounts optional async components disabled by the active performance profile.
- NodeEvaluator generator/feature isolation with a bounded, constant-time atomic retention counter (eliminates O(n) concurrent-queue size checks in the hot return path).
- Async entity-tracker context, snapshot, packet-buffer and interpolation allocation reductions.
- Geometric reusable tracker Future/join buffers with active-count-only processing, avoiding per-tick array churn as entity task counts fluctuate.
- Tracker context burst buffers reclaimed only after subsequent quiet ticks; configurable `-Dwarext.tracker.context-list-trim-threshold=N` (default 4096).
- Release stale entity references on snapshot shrink and avoid retaining unusually large packet-list backing arrays after burst-heavy ticks. Override with `-Dwarext.tracker.packet-list-retain-capacity=N` (default 256, minimum 16, maximum 4096).
- Fair async save coalescing: one write per I/O queue turn keeps busy world/player saves from starving unrelated player/world keys; off-thread NBT compression retained.
- Async mob-spawn failure recovery.
- Entity activation/despawn/natural-spawn spatial lookup allocation reductions.
- Adaptive small-player linear nearest-player fast path.
- ChunkCache p99 rehash-spike avoidance, plus cold sparse-clear array capacity reclamation to reduce retained heap and excessive array fills.
- Collision buffer reuse.
- Random-tick/precipitation lookup reuse.
- Async path lifecycle cleanup and bounded path queues, with monotonic atomic rate-limited saturation diagnostics.
- Entity encode-id caching.
- Light packet ThreadLocal retention cleanup.
- Hardware-adaptive scheduler defaults, balanced DAB defaults, Alternate Current defaults for new configs, and chunk-packet metadata allocation reductions.
- Reusable packet-NBT DataOutput adapter to reduce per-object serialization allocation and GC pressure.
- Reusable nearest-item sensor scratch storage, bulk modified-UTF packet encoding with bounded thread-local scratch memory, and hardware-adaptive path-burst protection. Brain-memory result lists remain freshly allocated to preserve reference semantics.
- Balanced pathfinding scales steady/burst workers with the detected CPU budget and a bounded queue; no fixed CPU model or RAM size is assumed.
- Deterministic Java concurrency regression tests for async-save fairness, superseded-write coalescing, error recovery and per-key exclusion.
- Compile and stress-test the real patched Java NodeEvaluatorCache against simultaneous checkout/return, generator isolation and the configured retention cap.
- Runtime Java 25 startup/shutdown smoke tests for balanced, extreme, compatibility and pregeneration profiles.
- Reproducible builds pinned to a tested upstream commit.
- Legacy startup smoke scripts remain available for local diagnosis; GitHub Actions no longer compiles or publishes Warext binaries.

## Private local build and GitHub storage policy

**GitHub is a repository and Releases artifact store only. No GitHub Actions/CI remote compilation or publishing is permitted.** Future versions must be incremented before publication; do not overwrite previously published JARs.

The private/offline-from-GitHub compilation environment needs **JDK 25+**, Git, Python 3, local Gradle wrapper support and an authenticated `gh` CLI for **uploading already compiled assets**. In a clean local clone of the source repository, use:

```bash
bash build-tools/build-local.sh publish
```

The script creates a temporary, isolated build directory, fetches the exact pinned Leaf commit, applies the complete Paper/Leaf patch stack and Warext patches, compiles the server with the **local machine's JDK**, packages the fully patched source tree, verifies hashes and uploads the existing local JAR, ZIP and metadata to GitHub Releases. Temporary build files are deleted on exit. The binary is **not** built by GitHub.

For the next development release increment `build-tools/VERSION` first, push the updated source to GitHub, then run the private local compiler to publish the new version. This policy applies to exp.27 onward; previously released exp.26 was built using the old GitHub Actions system.

The compiler verifies the JAR's existence and checksums but does not establish production performance or plugin compatibility. Additional workload testing is independent from the compilation and release process.

## Licensing and attribution

Warext Server Engine uses and modifies open-source upstream components. Required upstream attribution and license details are kept in `LICENSE.md`.
