using System.Text.Json;
using Casa.Lexicon.Build;

return Cli.Run(args);

internal static class Cli
{
    public static int Run(string[] args)
    {
        if (args.Length == 0 || args[0] is "-h" or "--help")
        {
            PrintHelp();
            return args.Length == 0 ? 1 : 0;
        }

        try
        {
            var root = PayloadRoot.Resolve(args);
            var cmd = args[0].ToLowerInvariant();
            var tail = SkipRootArgs(args);

            return cmd switch
            {
                "quad" => RunQuad(root, tail),
                "export-store" => RunExportStore(root, tail),
                "tech" => RunTech(root, tail),
                _ => Unknown(cmd),
            };
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine(ex.Message);
            return 1;
        }
    }

    private static int RunQuad(string root, string[] args)
    {
        var mode = EnGeneralMode.Folk;
        string? corpusId = null;

        for (var i = 0; i < args.Length; i++)
        {
            if (args[i] == "--en-general-mode" && i + 1 < args.Length)
            {
                mode = args[++i] switch
                {
                    "gutenberg" => EnGeneralMode.Gutenberg,
                    "folk" => EnGeneralMode.Folk,
                    _ => throw new ArgumentException("Use folk or gutenberg"),
                };
            }
            else if (args[i] == "--corpus-id" && i + 1 < args.Length)
            {
                corpusId = args[++i];
            }
        }

        if (corpusId is not null)
        {
            WriteJson(QuadHeadwordBuilder.BuildOne(root, corpusId, mode));
            return 0;
        }

        WriteJson(QuadHeadwordBuilder.BuildAll(root, mode));
        return 0;
    }

    private static int RunExportStore(string root, string[] args)
    {
        var storeId = Require(args, "--store-id");
        var outRel = GetOptional(args, "--out");
        var storeDir = Path.Combine(root, "lab", "agent-stores", storeId);
        var outPath = outRel is not null
            ? Path.IsPathRooted(outRel) ? outRel : Path.Combine(root, outRel)
            : throw new ArgumentException("--out required for export-store");

        var rep = FieldStateHeadwordExporter.ExportFromStore(storeDir, outPath) with { SourceStore = storeId };
        WriteJson(rep);
        return 0;
    }

    private static int RunTech(string root, string[] args)
    {
        var locale = Require(args, "--locale");
        var outRel = Require(args, "--out");
        if (locale is not "en" and not "ru")
            throw new ArgumentException("locale must be en or ru");

        var spec = locale == "en" ? CorpusQuad.EnTech : CorpusQuad.RuTech;
        var rep = QuadHeadwordBuilder.BuildTechCorpus(root, locale, spec);
        WriteJson(rep);
        return 0;
    }

    private static string[] SkipRootArgs(string[] args)
    {
        var list = new List<string>();
        for (var i = 1; i < args.Length; i++)
        {
            if (args[i] is "--root" or "-r" && i + 1 < args.Length)
            {
                i++;
                continue;
            }

            list.Add(args[i]);
        }

        return list.ToArray();
    }

    private static string Require(string[] args, string flag)
    {
        for (var i = 0; i < args.Length - 1; i++)
        {
            if (args[i] == flag)
                return args[i + 1];
        }

        throw new ArgumentException($"Missing {flag}");
    }

    private static string? GetOptional(string[] args, string flag)
    {
        for (var i = 0; i < args.Length - 1; i++)
        {
            if (args[i] == flag)
                return args[i + 1];
        }

        return null;
    }

    private static void WriteJson(HeadwordReport value) =>
        Console.WriteLine(JsonSerializer.Serialize(value, LexiconJsonContext.Default.HeadwordReport));

    private static void WriteJson(Dictionary<string, HeadwordReport> value) =>
        Console.WriteLine(
            JsonSerializer.Serialize(value, LexiconJsonContext.Default.DictionaryStringHeadwordReport));

    private static int Unknown(string cmd)
    {
        Console.Error.WriteLine($"Unknown command: {cmd}");
        PrintHelp();
        return 2;
    }

    private static void PrintHelp() =>
        Console.WriteLine(
            """
            casa-lexicon-build (Native AOT) — quad dictionary headwords for CASA lexicon stores

            Commands:
              quad [--en-general-mode folk|gutenberg] [--corpus-id id]
              export-store --store-id <id> --out <path>
              tech --locale en|ru --out <path>

            Global:
              --root | -r <casa-ontology-payload>

            Examples:
              casa-lexicon-build quad -r .
              casa-lexicon-build export-store --store-id lexicon-en-folk --out lab/corpus/en-general-v0/headwords.v1.txt
            """);
}

internal static class PayloadRoot
{
    public static string Resolve(string[] args)
    {
        for (var i = 0; i < args.Length - 1; i++)
        {
            if (args[i] is "--root" or "-r")
                return Path.GetFullPath(args[i + 1]);
        }

        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var marker = Path.Combine(dir.FullName, "tools", "t9_runtime_v0.py");
            if (File.Exists(marker))
                return dir.FullName;
            dir = dir.Parent;
        }

        throw new InvalidOperationException(
            "Cannot find casa-ontology-payload root. Pass --root <path>.");
    }
}
