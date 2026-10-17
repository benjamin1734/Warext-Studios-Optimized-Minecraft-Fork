# Leaf 26.3 upstream comparison — 2026-10-17

## Compared revisions
- Leaf upstream repository: `Winds-Studio/Leaf`, branch `ver/26.3`.
- Old pinned upstream (Warext 26.3-exp.20): `0edc7f3b7d79b0e2e16a0ed1df8278c02c73537f` — Leaf build #3 (2026-10-05).
- New pinned upstream candidate (Warext 26.3-exp.21): `4b0dcd264996f18b48f783c58390a9090ba1964b` — Leaf build #4 (2026-10-15), commit #954.
- GitHub API compare: one upstream commit, 17 changed paths, +195/-486 lines in upstream (renames counted by API). These are **upstream changes**, not a Warext net source-line comparison.
- Paper commit pin: `1c92a6c3a42deda2fbefdec1a0d90d696313ff3b` → `f68a55a8964e02b11a0951b971951963da5f0276`.
- Channel: experimental; Leaf does not yet list a stable 26.3 build.

## Main upstream differences and compatibility risks

| Leaf build #4 change | Warext exp.20 behavior | Integration risk or follow-up |
| --- | --- | --- |
| Paper upstream commit updated in `gradle.properties` | Builds Paper base from Leaf build #3 | Regenerate Leaf/Paper source patches and compile; source offsets and APIs changed. |
| Purpur Bukkit API/server patch refreshed | Warext applies custom API brand and Paper compatibility changes | Check plugin command/API contract and successful `applyAllPatches`. |
| Moonrise/Paper now provide `FastHashMapPalette`; Leaf removed obsolete `LithiumHashPalette.java` and archived its previous patch | Warext compact bit storage and palette-read optimizations are applied after Leaf patches | Ensure the original optimized Palette decoding semantics remain correct; verify save/reload and block palette parity. Do not reintroduce obsolete Lithium palette class. |
| Moonrise/Paper worldgen optimization supersedes older C2ME Beardifier path; upstream moved patch into archived set | Warext additionally precomputes Aquifer centers in pregeneration mode | Avoid duplicate worldgen rewrites and check fixed-seed generation, End biome cache, and chunk serialization. |
| Leaf parallel-world-ticking / CraftWorld patch offsets and code adjusted | Warext has async pathfinding/entity tracking, and optional direct Moonrise ticking set lookup | Keep experimental ticking-set cache disabled by default and parity test chunk-holder lifecycle under new Paper. |
| Changes to `PalettedContainer`, `LevelChunk`, `Identifier`, hopper and recipe patches | Warext path contains hot-path collection and serialization optimizations | Test world load/unload, palette correctness, hopper/recipe plugin behavior and collision/random-tick semantics; no performance claim until measurement. |
| Terminal JLine implementation dependency updated | Previously built against earlier Paper dependencies | Build Java 25 on GitHub Actions and verify startup/clean shutdown. |

## Warext-specific patches to retain
- Hardware-neutral worker counts with explicit JVM/Paper/property overrides; no special-casing of 4 CPUs or 6 GB.
- Balanced, extreme, compatibility and pregeneration profiles.
- Async pathfinding pool fixes, packet/tracker buffer reuse and p99-tail safeguards.
- Pregeneration chunk NBT bounded drain, End biome cache, Aquifer center precompute and compact palette optimization.
- Experimental `performance.chunk.direct-ticking-set-lookups.enabled` OFF by default, optional `-Dwarext.debug.validate-ticking-sets=true`.

## GitHub-only validation
1. Pin new Leaf SHA and increment candidate to `26.3-exp.21`.
2. Run CI on `update/leaf-26.3-build4` **without publishing releases**; handle any upstream patch-script mismatch on this branch.
3. CI must apply Leaf patches then Warext patches, build runnable JAR and run all profile, worldgen, reload, optional ticking-cache checks.
4. On success, merge into `main` and let the protected release steps publish both the JAR and patched-source ZIP in the GitHub Release.
5. If CI fails, retain `main` and exp.20 unchanged; fix the exact failing upstream patch/hunk rather than substituting or ignoring it.

## Interpreting performance
Build success is not evidence of faster MSPT. Benchmark identical worlds, plugins, online players, view/simulation distance, heap and CPUs with separate p50/p95/p99 MSPT, tick CPU time, GC pauses, heap usage, chunk generation speed and error logs. Do not declare a universal % improvement without these measurements.

Primary evidence: https://github.com/Winds-Studio/Leaf/compare/0edc7f3...4b0dcd2 and https://www.leafmc.one/en/download/26.3

## Build #4 integration verification — 2026-10-17

- **Resolved actual upstream drift:** generated `PalettedContainer.read(FriendlyByteBuf)` now invokes `this.addPresetValues()` after `this.data = newData`, rather than the previous Paper palette-read `this.updateData(this.data)`. The Warext compact uniform-palette code now matches either upstream read tail, compacts before the anti-xray preset restoration, and preserves the Paper `addPresetValues()` call. A missing/ambiguous upstream anchor still fails closed with a targeted source excerpt; it is never silently skipped.
- **Candidate GitHub Actions run:** https://github.com/benjamin1734/Warext-Studis-Optimized-Minecraft-Fork/actions/runs/39026189978 — all checks **passed**: pinned Leaf fetch and patch stack; Warext performance patches; Java 25 Paperclip build; release JAR and full patched-source ZIP packaging; balanced/extreme/pregeneration/compatibility profile, CPU adaptation, End/Aquifer generation, world save/reload, lazy container and experimental ticking-cache smoke steps in the workflow's combined smoke-test script.
- No JAR/ZIP files created or retained locally: GitHub Actions performed source application and packaging. Candidate branch intentionally did not publish a Release. A separate post-merge `main` run must publish and verify the exp.21 release assets.
- **Measurement limitation:** build and smoke-test success establish integration compatibility under these test cases, not superior TPS/MSPT/CPS. Wider plugin matrix and controlled Leaf-vs-Warext benchmarks remain outstanding.
