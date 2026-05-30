using System.Text;

namespace Casa.Lexicon.Build;

internal static class WordNorm
{
    public static string Normalize(ReadOnlySpan<char> word)
    {
        if (word.IsEmpty)
            return string.Empty;

        var s = word.ToString().Trim().ToLowerInvariant();
        return s.Normalize(NormalizationForm.FormC);
    }

    public static string Normalize(string word) => Normalize(word.AsSpan());
}
