using System.Text.RegularExpressions;

namespace Casa.Lexicon.Build;

internal enum EnGeneralMode
{
    Folk,
    Gutenberg,
}

internal static partial class QuadHeadwordBuilder
{
    private static readonly HashSet<string> GutenbergStop = new(
        """
        a an and are as at be been but by can could did do does doing done for from had has
        have he her hers him his i if in into is it its me my no nor not of on or our ours
        out she should so some such than that the their them then there these they this those
        to too up us was we were what when where which who whom why will with would you your yours
        """.Split(' ', StringSplitOptions.RemoveEmptyEntries),
        StringComparer.Ordinal);

    public static Dictionary<string, HeadwordReport> BuildAll(string root, EnGeneralMode enMode) =>
        CorpusQuad.All.ToDictionary(c => c.Id, c => BuildOne(root, c.Id, enMode), StringComparer.Ordinal);

    public static HeadwordReport BuildOne(string root, string corpusId, EnGeneralMode enMode) =>
        corpusId switch
        {
            "en-general" => enMode == EnGeneralMode.Folk
                ? ExportOrFail(
                    root,
                    StoreIds.EnFolk,
                    Path.Combine(root, CorpusQuad.EnGeneral.HeadwordsRel),
                    CorpusQuad.EnGeneral.MinWords)
                : BuildEnGutenberg(root, Path.Combine(root, CorpusQuad.EnGeneral.HeadwordsRel)),
            "ru-general" => BuildRuGeneralFrequency(root),
            "en-tech" => BuildTechCorpus(root, "en", CorpusQuad.EnTech),
            "ru-tech" => BuildTechCorpus(root, "ru", CorpusQuad.RuTech),
            _ => throw new ArgumentException($"Unknown corpus-id: {corpusId}"),
        };

    private static HeadwordReport BuildRuGeneralFrequency(string root)
    {
        var outPath = Path.Combine(root, CorpusQuad.RuGeneral.HeadwordsRel);
        if (!File.Exists(outPath))
        {
            throw new FileNotFoundException(
                $"Missing {outPath}. Run: python tools/fetch_ru_frequency_headwords_v0.py");
        }

        var words = HeadwordFiles.Read(outPath);
        if (words.Count < CorpusQuad.RuGeneral.MinWords)
        {
            throw new InvalidOperationException(
                $"ru-general: only {words.Count} headwords (need >={CorpusQuad.RuGeneral.MinWords}). "
                + "Run fetch_ru_frequency_headwords_v0.py");
        }

        return new HeadwordReport
        {
            SourceStore = "detcorpus-50k-cc0",
            Out = Path.GetFullPath(outPath),
            UniqueHeadwords = words.Count,
            Mode = "frequency",
        };
    }

    private static HeadwordReport ExportOrFail(
        string root,
        string storeId,
        string outPath,
        int minWords)
    {
        var storeDir = Path.Combine(root, "lab", "agent-stores", storeId);
        var rep = FieldStateHeadwordExporter.ExportFromStore(storeDir, outPath);
        if (rep.UniqueHeadwords < minWords)
        {
            throw new InvalidOperationException(
                $"{storeId}: only {rep.UniqueHeadwords} headwords (need >={minWords}). "
                + "Rebuild field_state from ltm or pick a store with a full L2 lexicon.");
        }

        rep = rep with { SourceStore = storeId };
        return rep;
    }

    private static HeadwordReport BuildEnGutenberg(string root, string outPath)
    {
        var corpusDir = Path.Combine(root, "lab", "corpus", "en-folk-v0");
        var freq = new Dictionary<string, int>(StringComparer.Ordinal);
        if (!Directory.Exists(corpusDir))
            throw new DirectoryNotFoundException($"Missing corpus dir: {corpusDir}");

        foreach (var path in Directory.EnumerateFiles(corpusDir, "*.txt"))
        {
            var text = File.ReadAllText(path).ToLowerInvariant();
            foreach (Match m in GutenbergEnWord().Matches(text))
            {
                var w = WordNorm.Normalize(m.Value);
                if (w.Length >= 2 && w.All(static c => c <= 127) && !GutenbergStop.Contains(w))
                    freq[w] = freq.GetValueOrDefault(w) + 1;
            }
        }

        var words = freq.Keys.Order(StringComparer.Ordinal).ToList();
        if (words.Count < CorpusQuad.EnGeneral.MinWords)
            throw new InvalidOperationException($"en-general gutenberg: only {words.Count} headwords");

        HeadwordFiles.Write(outPath, words, header: "en-general gutenberg folk");
        return new HeadwordReport
        {
            UniqueHeadwords = words.Count,
            Out = Path.GetFullPath(outPath),
            Mode = "gutenberg",
        };
    }

    public static HeadwordReport BuildTechCorpus(string root, string locale, CorpusSpec spec)
    {
        var outPath = Path.Combine(root, spec.HeadwordsRel);
        var seeds = new[] { Path.Combine(root, "lab", "corpus", $"{locale}-tech-v0", "seed.v1.txt") };
        var scanRoots = new[]
        {
            Path.Combine(root, "design"),
            Path.Combine(root, "tools"),
            Path.Combine(root, "apps"),
            Path.Combine(root, "lab"),
            Path.Combine(root, "..", "cascade-ide", "docs"),
            Path.Combine(root, "..", "..", "..", "knowledge"),
        };

        var words = TechHeadwordBuilder.Build(locale, scanRoots, seeds);
        if (words.Count < spec.MinWords)
            throw new InvalidOperationException($"{spec.Id}: only {words.Count} headwords");

        HeadwordFiles.Write(outPath, words, header: $"tech {locale}");
        return new HeadwordReport
        {
            Locale = locale,
            UniqueHeadwords = words.Count,
            Out = Path.GetFullPath(outPath),
        };
    }

    [GeneratedRegex(@"[a-z]+(?:'[a-z]+)?", RegexOptions.IgnoreCase)]
    private static partial Regex GutenbergEnWord();
}
