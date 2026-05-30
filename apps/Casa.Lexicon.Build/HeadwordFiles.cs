using System.Globalization;
using System.Text;

namespace Casa.Lexicon.Build;

internal static class HeadwordFiles
{
    public static List<string> Read(string path)
    {
        var words = new List<string>();
        foreach (var line in File.ReadLines(path, Encoding.UTF8))
        {
            var raw = line.Split('#', 2)[0].Trim();
            if (raw.Length == 0 || raw.StartsWith('#'))
                continue;
            var w = WordNorm.Normalize(raw);
            if (w.Length > 0)
                words.Add(w);
        }

        return words.Distinct().ToList();
    }

    public static void Write(string path, IReadOnlyList<string> words, string? header = null)
    {
        var dir = Path.GetDirectoryName(path);
        if (!string.IsNullOrEmpty(dir))
            Directory.CreateDirectory(dir);

        var sb = new StringBuilder();
        if (!string.IsNullOrEmpty(header))
            sb.AppendLine(string.Create(CultureInfo.InvariantCulture, $"# {header}"));
        foreach (var w in words)
            sb.AppendLine(w);
        File.WriteAllText(path, sb.ToString(), Encoding.UTF8);
    }
}
