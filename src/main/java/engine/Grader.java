package engine;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.regex.Pattern;

import engine.text.Locale;

/**
 * Runs koan series and writes one JSON row per koan, for the Classroom 50 autograder.
 *
 * <pre>
 * java -cp &lt;classes&gt; engine.Grader &lt;out.json&gt; &lt;SeriesClass&gt;...
 * java -cp &lt;classes&gt; engine.Grader --list &lt;out.json&gt; &lt;SeriesClass&gt;...
 * </pre>
 *
 * Each SeriesClass is a class name in the {@code sensei} package, such as {@code AboutLoopsKoans}.
 * The JSON goes to a file, not stdout, so student output cannot corrupt it.
 * In package {@code engine} to read {@link Koan}'s package-private fields.
 */
public final class Grader {
    private static final Locale LOCALE = Locale.en;
    private static final Pattern ANSI = Pattern.compile("\u001b\\[[0-9;]*m");

    private Grader() {
    }

    public static void main(final String[] args) throws Exception {
        final boolean listOnly = args.length > 0 && args[0].equals("--list");
        final List<String> rest = Arrays.asList(args).subList(listOnly ? 1 : 0, args.length);
        if (rest.isEmpty()) {
            throw new IllegalArgumentException("Usage: engine.Grader [--list] <out.json> <SeriesClass>...");
        }

        final Path out = Path.of(rest.get(0));
        final List<String> rows = new ArrayList<>();
        for (final String seriesClass : rest.subList(1, rest.size())) {
            for (final Koan koan : loadSeries(seriesClass)) {
                rows.add(listOnly ? listRow(seriesClass, koan) : runRow(seriesClass, koan));
            }
        }

        Files.writeString(out, "[\n" + String.join(",\n", rows) + "\n]\n", StandardCharsets.UTF_8);
        // Student code stuck in an infinite loop keeps running in a daemon thread; exit explicitly.
        System.exit(0);
    }

    @SuppressWarnings("unchecked")
    private static List<Koan> loadSeries(final String seriesClass) throws ReflectiveOperationException {
        return (List<Koan>) Class.forName("sensei." + seriesClass).getField("koans").get(null);
    }

    private static String listRow(final String seriesClass, final Koan koan) {
        return "  {" + commonFields(seriesClass, koan) + "}";
    }

    private static String runRow(final String seriesClass, final Koan koan) {
        final TestSensei.TestSenseiResult[] results = TestSensei.execute(koan, LOCALE);
        int failed = 0;
        String message = "";
        for (final TestSensei.TestSenseiResult result : results) {
            if (!result.testResult().succeeded()) {
                if (failed == 0) {
                    message = ANSI.matcher(result.outputCapture().capturedStdOutAsString()).replaceAll("");
                }
                failed++;
            }
        }
        return "  {" + commonFields(seriesClass, koan)
            + ", \"failedAssertions\": " + failed
            + ", \"passed\": " + (failed == 0)
            + ", \"message\": " + quote(message) + "}";
    }

    private static String commonFields(final String seriesClass, final Koan koan) {
        return "\"seriesClass\": " + quote(seriesClass)
            + ", \"series\": " + quote(koan.koanClass.get(LOCALE).simpleClassName)
            + ", \"koan\": " + quote(koan.koanName.get(LOCALE))
            + ", \"assertions\": " + koan.tests.length;
    }

    private static String quote(final String s) {
        final StringBuilder sb = new StringBuilder(s.length() + 2).append('"');
        for (int i = 0; i < s.length(); i++) {
            final char c = s.charAt(i);
            if (c == '"' || c == '\\') {
                sb.append('\\').append(c);
            } else if (c < 0x20 || c == 0x7f || c == 0x2028 || c == 0x2029) {
                sb.append(String.format("\\u%04x", (int) c));
            } else {
                sb.append(c);
            }
        }
        return sb.append('"').toString();
    }
}
