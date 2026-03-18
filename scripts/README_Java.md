# CleanText (Java)

Standalone Java version of the TEI cleaner for Michigan Digital Library (EEBO-TCP) XML. Produces plain text ready for VARD. No external JARs—uses only the Java standard library.

**Requirements:** Java 8 or later.

**Compile:**

```bash
javac CleanText.java
```

**Run:**

```bash
# Input XML → output to <filename>_cleaned_for_vard.txt
java CleanText document.xml

# Custom output path
java CleanText document.xml -o ready_for_vard.txt

# Optional change log (placeholder; Python version has full log)
java CleanText document.xml -o out.txt --log log.txt

# Plain text input (no TEI extraction, only cleaning)
java CleanText extracted.txt -o cleaned.txt
```

Send your friend `CleanText.java`; he can compile and run it with the Java he already has.
