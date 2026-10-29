package org.frc;

import engine.Koan;
import engine.text.Locale;
import engine.TestSensei;
import sensei.AboutArraysKoans;
import sensei.AboutInterfacesKoans;
import sensei.Wisdom;

import java.util.List;

public class Main {
    private static final List<List<List<Koan>>> ALL_SUITE_LISTS = List.of(
        Wisdom.koans,
        // Bonuses
        List.of(
            AboutArraysKoans.koans,
            AboutInterfacesKoans.koans
        )
    );

    private record RunResult(int totalKoans, int totalAssertions, int succeededAssertions) {
        public static final RunResult ZERO = new RunResult(0, 0, 0);

        public RunResult recordAssertion(boolean assertionSucceeded) {
            return new RunResult(totalKoans, totalAssertions + 1, succeededAssertions + (assertionSucceeded ? 1 : 0));
        }

        public RunResult append(RunResult other) {
            return new RunResult(totalKoans + other.totalKoans, totalAssertions + other.totalAssertions, succeededAssertions + other.succeededAssertions);
        }

        public boolean hasFailures() {
            return succeededAssertions < totalAssertions;
        }
    }

    public static void main(String[] args) {
        var result = executeSuiteListsIn(Locale.en);

        System.out.printf("%n%s/%s assertions executed successfully in %s koans.%n", result.succeededAssertions, result.totalAssertions, result.totalKoans);

        if (result.hasFailures()) {
            System.exit(1);
        }
    }

    private static RunResult executeSuiteListsIn(Locale locale) {
        var runResult = RunResult.ZERO;
        for(final var suiteList: ALL_SUITE_LISTS) {
            runResult = runResult.append(executeSuitesIn(locale, suiteList));
        }
        return runResult;
    }

    private static RunResult executeSuitesIn(Locale locale, List<List<Koan>> suites) {
        var runResult = RunResult.ZERO;
        for(final var suite: suites) {
            runResult = runResult.append(executeSuiteIn(locale, suite));
        }
        return runResult;
    }

    private static RunResult executeSuiteIn(Locale locale, List<Koan> suite) {
        var runResult = RunResult.ZERO;
        for(final var koan: suite) {
            runResult = runResult.append(executeKoanIn(locale, koan));
        }
        return runResult;
    }

    private static RunResult executeKoanIn(Locale locale, Koan koan) {
        var runResult = new RunResult(1,0, 0);
        final var results = TestSensei.execute(koan, locale);
        for(final var result: results) {
            if (!result.testResult().succeeded()) {
                System.out.printf("%s failed in %s%n%s", result, result.testResult().testOutput().locale, result.outputCapture().capturedStdOutAsString());
            }
            runResult = runResult.recordAssertion(result.testResult().succeeded());
        }
        return runResult;
    }
}
