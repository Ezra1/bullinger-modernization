from typing import List

# Demo data
strs = ["Testing", "Happy", "Man of man", ">", "$", "/", "\\", "To be in Christ is joy"]


class Solution:
    def encoding(self, strs: List[str]) -> str:
        """
        Encode a list of strings into a single string.

        Strategy: prefix each string with its length (digits), then a sentinel '#',
        then the string itself. Because the length can be multiple digits, the
        decoder scans for '#' to find where the length ends.
        """
        encoded = ""
        for s in strs:
            encoded += f"{len(s)}#{s}"
        return encoded

    def decoding(self, s: str) -> List[str]:
        """
        Decode a string produced by `encoding` back into the original list.

        We walk the encoded string with an index so we can jump past each segment:
          1) Read digits until the '#' separator to recover the length.
          2) Slice exactly that many characters for the payload.
        """
        res: List[str] = []
        i = 0
        n = len(s)

        while i < n:
            # Step 1: parse the length (one or more digits) until the '#'.
            j = i
            while j < n and s[j] != "#":
                if not s[j].isdigit():
                    raise ValueError(f"Expected digit for length at position {j}, got {s[j]!r}")
                j += 1
            if j >= n:
                raise ValueError("Malformed input: missing '#' separator")

            length = int(s[i:j])  # substring of digits

            # Step 2: slice out the payload of that length immediately after '#'.
            start = j + 1
            end = start + length
            if end > n:
                raise ValueError("Malformed input: declared length exceeds available data")
            res.append(s[start:end])

            # Move index to the start of the next encoded segment.
            i = end

        return res


solution = Solution()

if __name__ == "__main__":
    encoded = solution.encoding(strs)
    print("encoded:", encoded)
    decoded = solution.decoding(encoded)
    print("decoded:", decoded)
