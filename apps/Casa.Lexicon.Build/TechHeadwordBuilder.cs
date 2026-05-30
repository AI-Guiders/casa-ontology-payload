using System.Text.RegularExpressions;

namespace Casa.Lexicon.Build;

internal static partial class TechHeadwordBuilder
{
    private static readonly HashSet<string> EnStop = new(
        """
        the and for are was with this that from have has had not but you your our their
        will can may also into its than them then when what which who how all any each
        """.Split(' ', StringSplitOptions.RemoveEmptyEntries),
        StringComparer.Ordinal);

    private static readonly HashSet<string> ScanExtensions = new(StringComparer.OrdinalIgnoreCase)
    {
        ".md", ".json", ".cs", ".py", ".toml", ".txt",
    };

    public static List<string> Build(
        string locale,
        IReadOnlyList<string> scanRoots,
        IReadOnlyList<string> seedPaths,
        int minFreq = 1,
        int minLen = 2,
        int maxLen = 48)
    {
        var freq = new Dictionary<string, int>(StringComparer.Ordinal);

        foreach (var seed in seedPaths)
        {
            if (!File.Exists(seed))
                continue;
            foreach (var w in HeadwordFiles.Read(seed))
                freq[w] = freq.GetValueOrDefault(w) + 10;
        }

        var isRu = locale.StartsWith("ru", StringComparison.OrdinalIgnoreCase);
        foreach (var root in scanRoots)
        {
            if (!Directory.Exists(root))
                continue;
            foreach (var path in Directory.EnumerateFiles(root, "*.*", SearchOption.AllDirectories))
            {
                if (!ShouldScan(path))
                    continue;
                ScanFile(path, isRu, freq);
            }
        }

        return freq
            .Where(kv => kv.Value >= minFreq && kv.Key.Length >= minLen && kv.Key.Length <= maxLen)
            .Select(kv => kv.Key)
            .Order(StringComparer.Ordinal)
            .ToList();
    }

    private static bool ShouldScan(string path)
    {
        if (!ScanExtensions.Contains(Path.GetExtension(path)))
            return false;

        var parts = path.Split(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        if (parts.Any(p => p.StartsWith('.') && p is not "." and not ".."))
            return false;
        if (parts.Contains("node_modules") || parts.Contains("bin") || parts.Contains("obj"))
            return false;
        return true;
    }

    private static void ScanFile(string path, bool isRu, Dictionary<string, int> freq)
    {
        string text;
        try
        {
            text = File.ReadAllText(path);
        }
        catch (IOException)
        {
            return;
        }

        if (isRu)
        {
            foreach (Match m in RuWord().Matches(text.ToLowerInvariant()))
            {
                var w = WordNorm.Normalize(m.Value);
                if (w.Length >= 2)
                    freq[w] = freq.GetValueOrDefault(w) + 1;
            }

            foreach (Match m in CyrillicId().Matches(text))
            {
                var w = WordNorm.Normalize(m.Value.ToLowerInvariant());
                if (w.Length >= 2)
                    freq[w] = freq.GetValueOrDefault(w) + 1;
            }
        }
        else
        {
            foreach (Match m in EnWord().Matches(text.ToLowerInvariant()))
            {
                var w = WordNorm.Normalize(m.Value);
                if (w.Length >= 2 && !EnStop.Contains(w))
                    freq[w] = freq.GetValueOrDefault(w) + 1;
            }

            foreach (Match m in LatinId().Matches(text))
            {
                var w = WordNorm.Normalize(m.Value.ToLowerInvariant());
                if (w.Length >= 2 && !EnStop.Contains(w))
                    freq[w] = freq.GetValueOrDefault(w) + 1;
            }
        }

        foreach (Match m in ConceptWord().Matches(text))
        {
            var w = WordNorm.Normalize(m.Groups[1].Value.Replace("_", string.Empty));
            if (w.Length > 0)
                freq[w] = freq.GetValueOrDefault(w) + 3;
        }
    }

    [GeneratedRegex(@"[а-яё]+(?:-[а-яё]+)?", RegexOptions.IgnoreCase)]
    private static partial Regex RuWord();

    [GeneratedRegex(@"[a-z]+(?:'[a-z]+)?", RegexOptions.IgnoreCase)]
    private static partial Regex EnWord();

    [GeneratedRegex(@"lang\.word\.([a-zа-яё0-9_\-]+)", RegexOptions.IgnoreCase)]
    private static partial Regex ConceptWord();

    [GeneratedRegex(@"\b[A-Za-z_][A-Za-z0-9_]{2,}\b")]
    private static partial Regex LatinId();

    [GeneratedRegex(@"\b[А-Яа-яЁё_][А-Яа-яЁё0-9_]{2,}\b")]
    private static partial Regex CyrillicId();
}
