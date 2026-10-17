#!/usr/bin/env python3
"""Compile the real generated Warext async-save scheduler against minimal API stubs.

Run on GitHub Actions after patch_engine_263.py, before building the Paperclip JAR.
The test verifies queue fairness, per-key coalescing/ordering, and worker recovery.
Temporary Java classes live only in the GitHub Actions runner (no local packages).
"""

from pathlib import Path
import subprocess
import sys
import tempfile


STUBS = {
    "net/minecraft/util/Util.java": r"""
package net.minecraft.util;
public final class Util {
    public static void onThreadException(Thread thread, Throwable error) {
        error.printStackTrace();
    }
}
""",
    "org/apache/logging/log4j/Logger.java": r"""
package org.apache.logging.log4j;
public class Logger {
    public void error(String message, Object key, Object error) {
        System.err.println(message.replace("{}", String.valueOf(key)) + ": " + error);
    }
}
""",
    "org/apache/logging/log4j/LogManager.java": r"""
package org.apache.logging.log4j;
public final class LogManager {
    public static Logger getLogger(String name) { return new Logger(); }
}
""",
    "org/dreeam/leaf/config/modules/async/AsyncPlayerDataSave.java": r"""
package org.dreeam.leaf.config.modules.async;
public final class AsyncPlayerDataSave {
    public static volatile boolean enabled = true;
}
""",
    "org/dreeam/leaf/performance/WarextCpuBudget.java": r"""
package org.dreeam.leaf.performance;
public final class WarextCpuBudget {
    public static int ioWorkers() { return 1; }
}
""",
    "com/google/common/util/concurrent/ThreadFactoryBuilder.java": r"""
package com.google.common.util.concurrent;
import java.util.concurrent.ThreadFactory;
public final class ThreadFactoryBuilder {
    private int priority = Thread.NORM_PRIORITY;
    private String format = "test-%d";
    private Thread.UncaughtExceptionHandler handler;
    public ThreadFactoryBuilder setPriority(int value) { priority = value; return this; }
    public ThreadFactoryBuilder setNameFormat(String value) { format = value; return this; }
    public ThreadFactoryBuilder setUncaughtExceptionHandler(Thread.UncaughtExceptionHandler value) {
        handler = value; return this;
    }
    public ThreadFactory build() {
        final int p = priority;
        final String name = format;
        final Thread.UncaughtExceptionHandler h = handler;
        final java.util.concurrent.atomic.AtomicInteger count = new java.util.concurrent.atomic.AtomicInteger();
        return work -> {
            Thread t = new Thread(work);
            t.setName(String.format(name, count.incrementAndGet()));
            t.setPriority(p);
            if (h != null) t.setUncaughtExceptionHandler(h);
            return t;
        };
    }
}
""",
    "org/dreeam/leaf/performance/AsyncSaveFairnessSmoke.java": r"""
package org.dreeam.leaf.performance;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import org.dreeam.leaf.async.AsyncPlayerDataSaving;

public final class AsyncSaveFairnessSmoke {

    private static void check(boolean valid, String message) {
        if (!valid) throw new AssertionError(message);
    }

    public static void main(String[] args) throws Exception {
        AsyncPlayerDataSaving.init();
        try {
            runQueueFairness();
            runErrorRecovery();
            AsyncPlayerDataSaving.IO_POOL.shutdown();
            check(AsyncPlayerDataSaving.IO_POOL.awaitTermination(10, TimeUnit.SECONDS),
                "The single I/O worker did not stop cleanly");
            AsyncPlayerDataSaving.IO_POOL = Executors.newFixedThreadPool(2);
            runPerKeySerialisation();
        } finally {
            AsyncPlayerDataSaving.IO_POOL.shutdownNow();
            AsyncPlayerDataSaving.IO_POOL.awaitTermination(10, TimeUnit.SECONDS);
        }
        System.out.println("PASS: async-save fair queueing, coalescing, error recovery, per-key exclusion");
    }

    private static void runQueueFairness() throws Exception {
        final CountDownLatch started = new CountDownLatch(1);
        final CountDownLatch unblock = new CountDownLatch(1);
        final List<String> order = java.util.Collections.synchronizedList(new ArrayList<>());
        AsyncPlayerDataSaving.submitLatest("hot-world", () -> {
            started.countDown();
            try {
                if (!unblock.await(5, TimeUnit.SECONDS))
                    throw new IllegalStateException("hot writer wait timed out");
            } catch (InterruptedException ex) {
                Thread.currentThread().interrupt();
                throw new RuntimeException(ex);
            }
            order.add("hot-first");
        });
        check(started.await(5, TimeUnit.SECONDS), "First hot write never started");

        for (int i = 0; i < 1_000; ++i)
            AsyncPlayerDataSaving.submitLatest("hot-world", () -> order.add("STALE"));
        AsyncPlayerDataSaving.submitLatest("cold-player", () -> order.add("cold"));
        AsyncPlayerDataSaving.submitLatest("hot-world", () -> order.add("hot-latest"));
        unblock.countDown();

        AsyncPlayerDataSaving.awaitLatest("hot-world", 10_000L);
        AsyncPlayerDataSaving.awaitLatest("cold-player", 10_000L);
        check(order.equals(List.of("hot-first", "cold", "hot-latest")),
            "Cold player starved or stale snapshots executed: " + order);
    }

    private static void runErrorRecovery() throws Exception {
        AsyncPlayerDataSaving.submitLatest("error", () -> {
            throw new IllegalStateException("intentional test exception");
        });
        AsyncPlayerDataSaving.awaitLatest("error", 10_000L);
        final AtomicInteger completed = new AtomicInteger();
        AsyncPlayerDataSaving.submitLatest("healthy", completed::incrementAndGet);
        AsyncPlayerDataSaving.awaitLatest("healthy", 10_000L);
        check(completed.get() == 1, "I/O pool stopped making progress after an exception");
    }

    private static void runPerKeySerialisation() throws Exception {
        final AtomicInteger concurrent = new AtomicInteger();
        final AtomicInteger peak = new AtomicInteger();
        final AtomicInteger completed = new AtomicInteger();
        final Runnable work = () -> {
            final int active = concurrent.incrementAndGet();
            peak.accumulateAndGet(active, Math::max);
            try {
                Thread.sleep(2L);
                completed.incrementAndGet();
            } catch (InterruptedException error) {
                Thread.currentThread().interrupt();
            } finally {
                concurrent.decrementAndGet();
            }
        };
        for (int i = 0; i < 500; ++i)
            AsyncPlayerDataSaving.submitLatest("same-player", work);
        AsyncPlayerDataSaving.awaitLatest("same-player", 10_000L);
        check(peak.get() == 1, "Concurrent writes executed for the same player");
        check(completed.get() > 0, "No player saves executed");
    }
}
""",
}


def run(java_source: Path) -> None:
    if not java_source.is_file():
        raise SystemExit("Generated Warext scheduler not found: " + str(java_source))
    with tempfile.TemporaryDirectory(prefix="warext-ci-save-smoke-") as temp:
        root = Path(temp)
        sources = [str(java_source)]
        for rel, code in STUBS.items():
            file = root / "src" / rel
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(code.strip() + "\n", encoding="utf-8")
            sources.append(str(file))
        output = root / "classes"
        output.mkdir()
        subprocess.run(["javac", "-encoding", "UTF-8", "-d", str(output), *sources], check=True)
        subprocess.run(
            ["java", "-ea", "-cp", str(output),
             "org.dreeam.leaf.performance.AsyncSaveFairnessSmoke"],
            check=True,
            timeout=40,
        )


if __name__ == "__main__":
    default = Path("upstream-src/leaf-server/src/main/java/org/dreeam/leaf/async/AsyncPlayerDataSaving.java")
    run(Path(sys.argv[1]) if len(sys.argv) > 1 else default)
