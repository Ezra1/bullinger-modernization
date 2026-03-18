import javax.xml.parsers.*;
import org.w3c.dom.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.regex.*;

/**
 * Clean text from Michigan Digital Library (EEBO-TCP) TEI XML for use with VARD.
 *
 * Run on any TEI XML file from the Text Creation Partnership (Michigan/EEBO-TCP)
 * to extract body text, remove typographic artifacts, and produce plain text
 * ready for VARD (Variant Detector).
 *
 *   javac CleanText.java
 *   java CleanText document.xml
 *   java CleanText document.xml -o ready_for_vard.txt
 *   java CleanText already_extracted.txt -o cleaned.txt
 *
 * If input is .xml, extracts body text from TEI (head -> ##, p -> paragraphs,
 * gap -> [illegible], note -> [note N]). If input is .txt, only runs cleaning.
 *
 * Requires Java 8+. No external JARs; uses only standard library.
 */
public class CleanText {

    private static final String TEI_NS = "http://www.tei-c.org/ns/1.0";

    // Line-break hyphen chars (DIVIDES, BROKEN BAR)
    private static final String LINE_BREAK_HYPHENS = "\u2223\u00A6";

    private static final Pattern LINE_BREAK_HYPHEN_PATTERN;
    static {
        String quoted = Pattern.quote(LINE_BREAK_HYPHENS);
        LINE_BREAK_HYPHEN_PATTERN = Pattern.compile("[" + quoted + "]\\n?");
    }

    private static final Map<String, String> ABBREVIATIONS = new LinkedHashMap<>();
    static {
        ABBREVIATIONS.put("ye", "the");
        ABBREVIATIONS.put("yt", "that");
        ABBREVIATIONS.put("wt", "with");
    }

    private static final Pattern AMP_PATTERN = Pattern.compile(" & ");
    private static final Pattern GAP_BULLET = Pattern.compile("•");
    private static final Pattern GAP_UNCLEAR = Pattern.compile("〈◊〉");
    private static final Pattern GAP_ILLEGIBLE = Pattern.compile("\\[\\s*illegible\\s*\\]", Pattern.CASE_INSENSITIVE);
    private static final Pattern ROMAN_NUMERAL = Pattern.compile("\\s*\\.([xvidclm]+)[.,]", Pattern.CASE_INSENSITIVE);
    private static final Pattern MULTI_SPACE = Pattern.compile(" +");
    private static final Pattern SPACE_BEFORE_PUNCT = Pattern.compile(" +([.,;:!?\\]\\)])");
    private static final Pattern MULTI_NEWLINE = Pattern.compile("\n{3,}");

    // ----- TEI extraction -----

    private static String extractTeiBody(Path path) throws Exception {
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        factory.setNamespaceAware(true);
        DocumentBuilder builder = factory.newDocumentBuilder();
        Document doc;
        try (InputStream in = Files.newInputStream(path)) {
            doc = builder.parse(in);
        }
        doc.getDocumentElement().normalize();

        NodeList bodies = doc.getElementsByTagNameNS(TEI_NS, "body");
        if (bodies.getLength() == 0) return "";

        Element body = (Element) bodies.item(0);
        List<String> lines = new ArrayList<>();
        int[] noteCounter = { 0 };
        walkBody(body, lines, noteCounter);

        while (!lines.isEmpty() && lines.get(lines.size() - 1).isEmpty())
            lines.remove(lines.size() - 1);
        return lines.isEmpty() ? "" : String.join("\n", lines);
    }

    private static void walkBody(Element el, List<String> lines, int[] noteCounter) {
        NodeList children = el.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            Node n = children.item(i);
            if (n.getNodeType() != Node.ELEMENT_NODE) continue;
            Element child = (Element) n;
            String local = child.getLocalName();
            if (local == null) continue;
            switch (local) {
                case "head":
                    String headText = headText(child);
                    lines.add("## " + headText);
                    lines.add("");
                    break;
                case "p":
                    String para = paragraphText(child, noteCounter);
                    if (!para.isEmpty()) {
                        lines.add(para);
                        lines.add("");
                    }
                    break;
                case "div":
                    walkBody(child, lines, noteCounter);
                    break;
                default:
                    break;
            }
        }
    }

    private static String headText(Element el) {
        return normalizeSpace(elementTextOnly(el));
    }

    private static String paragraphText(Element pEl, int[] noteCounter) {
        return normalizeSpace(inlineTextAndTail(pEl, noteCounter));
    }

    private static String elementTextOnly(Element el) {
        StringBuilder sb = new StringBuilder();
        for (Node c = el.getFirstChild(); c != null; c = c.getNextSibling()) {
            if (c.getNodeType() == Node.TEXT_NODE)
                sb.append(c.getNodeValue());
            else if (c.getNodeType() == Node.ELEMENT_NODE) {
                Element ce = (Element) c;
                String local = ce.getLocalName();
                if ("g".equals(local) || "pb".equals(local)) continue;
                sb.append(elementTextOnly(ce));
            }
        }
        return sb.toString();
    }

    private static String inlineTextAndTail(Element el, int[] noteCounter) {
        StringBuilder sb = new StringBuilder();
        for (Node c = el.getFirstChild(); c != null; c = c.getNextSibling()) {
            if (c.getNodeType() == Node.TEXT_NODE)
                sb.append(c.getNodeValue());
            else if (c.getNodeType() == Node.ELEMENT_NODE) {
                Element ce = (Element) c;
                String local = ce.getLocalName();
                if ("gap".equals(local))
                    sb.append("[illegible]");
                else if ("note".equals(local)) {
                    noteCounter[0]++;
                    sb.append("[note ").append(noteCounter[0]).append("]");
                } else if ("g".equals(local) || "pb".equals(local)) {
                    // skip
                } else
                    sb.append(inlineTextAndTail(ce, noteCounter));
            }
        }
        return sb.toString();
    }

    private static String normalizeSpace(String s) {
        if (s == null) return "";
        return s.trim().replaceAll("\\s+", " ");
    }

    private static String loadInput(Path path) throws Exception {
        String name = path.getFileName().toString().toLowerCase(Locale.ROOT);
        if (name.endsWith(".xml"))
            return extractTeiBody(path);
        return new String(Files.readAllBytes(path), StandardCharsets.UTF_8);
    }

    // ----- Cleaning stages -----

    private static String stage1LineBreakRejoin(String text) {
        return LINE_BREAK_HYPHEN_PATTERN.matcher(text).replaceAll("");
    }

    private static String stage2Abbreviations(String line) {
        String out = line;
        for (Map.Entry<String, String> e : ABBREVIATIONS.entrySet()) {
            Pattern p = Pattern.compile("\\b" + Pattern.quote(e.getKey()) + "\\b");
            out = p.matcher(out).replaceAll(Matcher.quoteReplacement(e.getValue()));
        }
        out = AMP_PATTERN.matcher(out).replaceAll(" and ");
        return out;
    }

    private static String stage3GapNormalization(String line) {
        String out = GAP_BULLET.matcher(line).replaceAll("[illegible]");
        out = GAP_UNCLEAR.matcher(out).replaceAll("[illegible]");
        out = GAP_ILLEGIBLE.matcher(out).replaceAll("[illegible]");
        return out;
    }

    private static String stage3bRomanNumeralDots(String line) {
        Matcher m = ROMAN_NUMERAL.matcher(line);
        StringBuffer sb = new StringBuffer();
        while (m.find()) {
            String num = m.group(1);
            String tail = m.group(0).substring(m.group(0).length() - 1);
            m.appendReplacement(sb, Matcher.quoteReplacement(" " + num + tail));
        }
        m.appendTail(sb);
        return MULTI_SPACE.matcher(sb.toString().trim()).replaceAll(" ").trim();
    }

    private static String stage4Whitespace(String line) {
        String s = MULTI_SPACE.matcher(line).replaceAll(" ");
        s = SPACE_BEFORE_PUNCT.matcher(s).replaceAll("$1");
        return s.trim();
    }

    private static String runAllStages(String text) {
        text = stage1LineBreakRejoin(text);
        String[] lineArr = text.split("\n", -1);
        List<String> lines = new ArrayList<>(Arrays.asList(lineArr));
        for (int i = 0; i < lines.size(); i++) {
            String line = lines.get(i);
            line = stage2Abbreviations(line);
            line = stage3GapNormalization(line);
            line = stage3bRomanNumeralDots(line);
            line = stage4Whitespace(line);
            lines.set(i, line);
        }
        String cleaned = String.join("\n", lines);
        cleaned = MULTI_NEWLINE.matcher(cleaned).replaceAll("\n\n");
        return cleaned.trim();
    }

    public static void main(String[] args) {
        if (args.length == 0) {
            System.err.println("Usage: java CleanText <input.xml|input.txt> [-o output.txt] [--log log.txt]");
            System.exit(1);
        }
        Path input = Paths.get(args[0]);
        if (!Files.exists(input)) {
            System.err.println("Input file not found: " + input);
            System.exit(1);
        }

        Path output = null;
        Path logPath = null;
        for (int i = 1; i < args.length; i++) {
            if ("-o".equals(args[i]) && i + 1 < args.length)
                output = Paths.get(args[++i]);
            else if ("--log".equals(args[i]) && i + 1 < args.length)
                logPath = Paths.get(args[++i]);
        }

        if (output == null) {
            String stem = input.getFileName().toString();
            int dot = stem.lastIndexOf('.');
            if (dot > 0) stem = stem.substring(0, dot);
            output = input.getParent().resolve(stem + "_cleaned_for_vard.txt");
        }

        try {
            if (input.getFileName().toString().toLowerCase(Locale.ROOT).endsWith(".xml"))
                System.err.println("Extracting body text from TEI XML...");
            String text = loadInput(input);
            String cleaned = runAllStages(text);
            Files.createDirectories(output.getParent());
            Files.write(output, cleaned.getBytes(StandardCharsets.UTF_8));

            if (logPath != null) {
                Files.createDirectories(logPath.getParent());
                Files.write(logPath, "(Log not implemented in Java version)\n".getBytes(StandardCharsets.UTF_8));
            }

            System.out.println("Output: " + output.toAbsolutePath());
        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
            e.printStackTrace();
            System.exit(1);
        }
    }
}
