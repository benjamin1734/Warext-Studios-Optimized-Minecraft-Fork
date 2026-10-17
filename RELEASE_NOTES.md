# Warext Server Engine 26.3 exp.22

Experimental Minecraft 26.3 performance and correctness update on Leaf build #4.

## Fair async-save scheduling
- Previously a continuously updated world/player could drain all its coalesced snapshots in one I/O worker turn, starving unrelated save keys under sustained load.
- The scheduler now executes **one write snapshot per queue turn** and re-enqueues the newest pending snapshot at the tail of the I/O queue. This provides fairness across players and worlds without changing per-key serialization, latest-snapshot coalescing or the completion future used by load/backup ordering.
- Rejected reschedules are logged and fail the completion future instead of leaving a key silently stuck as scheduled.
- Added an independent **real Java scheduler** smoke test: 1,000 superseded writes coalesce into one pending snapshot; a cold player's save runs before that latest hot snapshot; a failed task does not poison the worker; two I/O workers never overlap writes for the same key.
- Preserve the configurable hardware-neutral I/O worker budget. No fixed CPU/RAM assumptions.

## Upstream and compatibility
- Remains pinned to Leaf 26.3 build #4, commit `4b0dcd264996f18b48f783c58390a9090ba1964b`.
- Retains exp.21 Paper/Moonrise `PalettedContainer.read` anti-xray compatibility fix.
- The JAR and complete patched Java source are produced and published through GitHub Actions only.

## Release validation
- Apply exact pinned Leaf/Paper patch stack followed by all Warext patches.
- Compile and run the Java async-save fairness/concurrency regression test directly against the **generated Java source**.
- Build runnable Java 25 Paperclip JAR, package the complete modified source tree on GitHub Actions and check SHA256 sums.
- Run balanced, extreme, pregeneration, compatibility, worldgen/save-reload, optional ticking-cache, and lazy container server smoke tests.
- Publish exp.22 assets to GitHub Releases only after main workflow success.

**Performance claim:** The fairness test proves deterministic I/O queue ordering and per-key isolation under its synthetic workload; it does not establish a universal TPS/MSPT uplift.
