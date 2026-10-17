#!/usr/bin/env python3
"""Test the actual patched Warext NodeEvaluatorCache Java source inside GitHub Actions.

No generated archives, no local deliverables. A short-lived GitHub runner tempdir
contains only javac stubs for the surrounding Leaf/vanilla APIs. The real
NodeEvaluatorCache source is never copied or replaced by an implementation mock.
"""

from pathlib import Path
import subprocess
import sys
import tempfile


STUBS = {
    "net/minecraft/world/level/pathfinder/BinaryHeap.java": r"""
package net.minecraft.world.level.pathfinder;
public final class BinaryHeap {}
""",
    "net/minecraft/world/level/pathfinder/Node.java": r"""
package net.minecraft.world.level.pathfinder;
public final class Node {}
""",
    "net/minecraft/world/level/pathfinder/NodeEvaluator.java": r"""
package net.minecraft.world.level.pathfinder;
public class NodeEvaluator {
    public final int owner;
    public final int featureBits;
    public NodeEvaluator(int owner, int featureBits) {
        this.owner = owner;
        this.featureBits = featureBits;
    }
}
""",
    "org/apache/commons/lang3/Validate.java": r"""
package org.apache.commons.lang3;
public final class Validate {
    public static void isTrue(boolean ok, String message) {
        if (!ok) throw new IllegalArgumentException(message);
    }
    public static <T> T notNull(T object, String message) {
        if (object == null) throw new IllegalArgumentException(message);
        return object;
    }
}
""",
    "org/dreeam/leaf/config/modules/async/AsyncPathfinding.java": r"""
package org.dreeam.leaf.config.modules.async;
public final class AsyncPathfinding {
    public static int asyncPathfindingMaxThreads = 4;
}
""",
    "org/dreeam/leaf/async/path/NodeEvaluatorGenerator.java": r"""
package org.dreeam.leaf.async.path;
import net.minecraft.world.level.pathfinder.NodeEvaluator;
public interface NodeEvaluatorGenerator {
    NodeEvaluator generate(int bits);
}
""",
    "org/dreeam/leaf/async/path/NodeEvaluatorFeatures.java": r"""
package org.dreeam.leaf.async.path;
import net.minecraft.world.level.pathfinder.NodeEvaluator;
public final class NodeEvaluatorFeatures {
    public static int fromNodeEvaluator(NodeEvaluator evaluator) {
        return evaluator.featureBits;
    }
    public static int unpack(int bits) { return bits; }
}
""",
    "org/dreeam/leaf/async/path/WarextNodeEvaluatorPoolTest.java": r"""
package org.dreeam.leaf.async.path;

import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import net.minecraft.world.level.pathfinder.NodeEvaluator;

public final class WarextNodeEvaluatorPoolTest {

    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    private static NodeEvaluator local(int feature) {
        return new NodeEvaluator(-1, feature);
    }

    private static void verifyBoundedPool() throws Exception {
        final AtomicInteger generated = new AtomicInteger();
        final NodeEvaluatorGenerator generator = bits -> {
            generated.incrementAndGet();
            return new NodeEvaluator(100, bits);
        };
        final NodeEvaluator features = local(101);
        final List<NodeEvaluator> values = new ArrayList<>();
        for (int i = 0; i < 64; i++)
            values.add(NodeEvaluatorCache.takeNodeEvaluator(generator, features));
        check(generated.get() == 64, "Initial checkout must allocate 64 evaluators");
        for (NodeEvaluator value : values)
            NodeEvaluatorCache.returnNodeEvaluator(value);
        verifyRetainedBounds(4);

        values.clear();
        for (int i = 0; i < 64; i++)
            values.add(NodeEvaluatorCache.takeNodeEvaluator(generator, features));
        check(generated.get() == 124,
            "Expected exactly four returned evaluators to survive cap=4 (generated "
                + generated.get() + ")");
        for (NodeEvaluator value : values)
            NodeEvaluatorCache.returnNodeEvaluator(value);
        verifyRetainedBounds(4);
    }

    private static void verifyGeneratorFeatureIsolation() {
        final NodeEvaluatorGenerator a = bits -> new NodeEvaluator(111, bits);
        final NodeEvaluatorGenerator b = bits -> new NodeEvaluator(222, bits);
        final NodeEvaluator a1 = NodeEvaluatorCache.takeNodeEvaluator(a, local(7));
        final NodeEvaluator b1 = NodeEvaluatorCache.takeNodeEvaluator(b, local(7));
        final NodeEvaluator c1 = NodeEvaluatorCache.takeNodeEvaluator(a, local(8));
        NodeEvaluatorCache.returnNodeEvaluator(a1);
        NodeEvaluatorCache.returnNodeEvaluator(b1);
        NodeEvaluatorCache.returnNodeEvaluator(c1);

        final NodeEvaluator againA = NodeEvaluatorCache.takeNodeEvaluator(a, local(7));
        final NodeEvaluator againB = NodeEvaluatorCache.takeNodeEvaluator(b, local(7));
        final NodeEvaluator againC = NodeEvaluatorCache.takeNodeEvaluator(a, local(8));
        check(againA == a1 && againB == b1 && againC == c1,
            "Cross-generator or cross-feature pooling violated identity isolation");
        NodeEvaluatorCache.returnNodeEvaluator(againA);
        NodeEvaluatorCache.returnNodeEvaluator(againB);
        NodeEvaluatorCache.returnNodeEvaluator(againC);

        boolean rejected = false;
        try {
            NodeEvaluatorCache.returnNodeEvaluator(againA);
        } catch (IllegalArgumentException expected) {
            rejected = true;
        }
        check(rejected, "Double return must be rejected");

        final NodeEvaluator discarded = NodeEvaluatorCache.takeNodeEvaluator(a, local(15));
        NodeEvaluatorCache.removeNodeEvaluator(discarded);
        rejected = false;
        try {
            NodeEvaluatorCache.returnNodeEvaluator(discarded);
        } catch (IllegalArgumentException expected) {
            rejected = true;
        }
        check(rejected, "Removed evaluator must not be returned");
    }

    private static void verifyConcurrentTakeAndReturn() throws Exception {
        final NodeEvaluatorGenerator generator = bits -> new NodeEvaluator(333, bits);
        final NodeEvaluator features = local(333);
        final Set<NodeEvaluator> checkedOut = ConcurrentHashMap.newKeySet();
        final AtomicBoolean duplicate = new AtomicBoolean();
        final int workers = 12;
        final int iterations = 1_500;
        final CountDownLatch start = new CountDownLatch(1);
        ExecutorService pool = Executors.newFixedThreadPool(workers);
        final List<Future<?>> futures = new ArrayList<>();
        try {
            for (int w = 0; w < workers; ++w) {
                futures.add(pool.submit(() -> {
                    try {
                        start.await();
                        for (int i = 0; i < iterations; ++i) {
                            final NodeEvaluator e =
                                NodeEvaluatorCache.takeNodeEvaluator(generator, features);
                            if (!checkedOut.add(e)) duplicate.set(true);
                            Thread.onSpinWait();
                            if (!checkedOut.remove(e)) duplicate.set(true);
                            NodeEvaluatorCache.returnNodeEvaluator(e);
                        }
                    } catch (InterruptedException error) {
                        Thread.currentThread().interrupt();
                        throw new RuntimeException(error);
                    }
                }));
            }
            start.countDown();
            for (Future<?> future : futures)
                future.get(25, TimeUnit.SECONDS);
            check(!duplicate.get(), "An evaluator was checked out by multiple workers");
            check(checkedOut.isEmpty(), "Leaked checked-out evaluators");
            verifyRetainedBounds(4);
        } finally {
            pool.shutdownNow();
            check(pool.awaitTermination(10, TimeUnit.SECONDS),
                "Pool test workers could not stop");
        }
    }

    private static void verifyRetainedBounds(int limit) throws Exception {
        final Field poolsField = NodeEvaluatorCache.class.getDeclaredField("NODE_EVALUATORS");
        poolsField.setAccessible(true);
        final java.util.Map<?, ?> pools = (java.util.Map<?, ?>) poolsField.get(null);
        for (Object pool : pools.values()) {
            final Field retainedField = pool.getClass().getDeclaredField("retained");
            final Field queueField = pool.getClass().getDeclaredField("queue");
            retainedField.setAccessible(true);
            queueField.setAccessible(true);
            final int count = ((AtomicInteger) retainedField.get(pool)).get();
            final int queueSize =
                ((java.util.Queue<?>) queueField.get(pool)).size();
            check(count >= 0 && count <= limit,
                "Pool retained count exceeds configured cap: " + count);
            check(queueSize == count,
                "Pool queue size and atomic retained count disagree after quiescence");
        }
    }

    public static void main(String[] args) throws Exception {
        System.setProperty("warext.pathfinding.evaluator-pool-cap", "4");
        verifyBoundedPool();
        verifyGeneratorFeatureIsolation();
        verifyConcurrentTakeAndReturn();
        System.out.println("PASS: bounded O(1) evaluator pool, feature/identity isolation, concurrent checkout/return");
    }
}
""",
}


def main(source: Path) -> None:
    if not source.is_file():
        raise SystemExit("Patched Java source missing: " + str(source))
    with tempfile.TemporaryDirectory(prefix="warext-ci-evaluator-pool-") as temp:
        root = Path(temp)
        files = [str(source)]
        for relative, body in STUBS.items():
            file = root / "src" / relative
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(body.strip() + "\n", encoding="utf-8")
            files.append(str(file))
        output = root / "classes"
        output.mkdir()
        subprocess.run(
            ["javac", "-encoding", "UTF-8", "-d", str(output), *files],
            check=True,
            timeout=35,
        )
        subprocess.run(
            ["java", "-ea", "-cp", str(output),
             "org.dreeam.leaf.async.path.WarextNodeEvaluatorPoolTest"],
            check=True,
            timeout=45,
        )


if __name__ == "__main__":
    default = Path(
        "upstream-src/leaf-server/src/main/java/org/dreeam/leaf/async/path/NodeEvaluatorCache.java"
    )
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else default)
