using System.Text.Json;
using System.Text.RegularExpressions;

namespace Casa.Lexicon.Build;

/// <summary>Extract L2 headwords from field_state.json without Python.</summary>
internal static partial class FieldStateHeadwordExporter
{
    private const string L2WordLegacy = "L2_word";
    private const string L2WordPrefix = "L2_word_";
    private const string L2EnPrefix = "L2_en_word_";

    [GeneratedRegex(@"(?:\bW:|C:lang\.word\.)([a-z]+(?:'[a-z]+)?)", RegexOptions.IgnoreCase)]
    private static partial Regex InlineWordToken();

    [GeneratedRegex(@"C:lang\.word\.([a-zа-яё0-9_\-]+)", RegexOptions.IgnoreCase)]
    private static partial Regex ConceptCellToken();

    public static HeadwordReport ExportFromStore(string storeDir, string outPath, int minVotes = 1)
    {
        var fieldState = Path.Combine(storeDir, "field_state.json");
        if (!File.Exists(fieldState))
            throw new FileNotFoundException($"field_state missing: {fieldState}");

        var votes = CollectVotes(fieldState);
        var words = votes
            .Where(kv => kv.Value >= minVotes)
            .Select(kv => kv.Key)
            .Order(StringComparer.Ordinal)
            .ToList();

        var storeName = Path.GetFileName(Path.GetFullPath(storeDir));
        HeadwordFiles.Write(outPath, words, header: $"extracted from {storeName}");

        return new HeadwordReport
        {
            StoreDir = Path.GetFullPath(storeDir),
            Out = Path.GetFullPath(outPath),
            UniqueHeadwords = words.Count,
        };
    }

    private static Dictionary<string, int> CollectVotes(string fieldStatePath)
    {
        var text = File.ReadAllText(fieldStatePath);
        var votes = new Dictionary<string, int>(StringComparer.Ordinal);

        foreach (Match m in ConceptCellToken().Matches(text))
        {
            var w = WordNorm.Normalize(m.Groups[1].Value);
            if (w.Length > 0)
                votes[w] = Math.Max(votes.GetValueOrDefault(w), 1);
        }

        foreach (Match m in InlineWordToken().Matches(text))
        {
            var w = WordNorm.Normalize(m.Groups[1].Value);
            if (w.Length > 0)
                votes[w] = votes.GetValueOrDefault(w) + 1;
        }

        if (votes.Count > 0)
            return votes;

        return CollectVotesStreaming(fieldStatePath);
    }

    /// <summary>Fallback: Utf8JsonReader walk when regex finds nothing.</summary>
    private static Dictionary<string, int> CollectVotesStreaming(string fieldStatePath)
    {
        var bytes = File.ReadAllBytes(fieldStatePath);
        var reader = new Utf8JsonReader(bytes);
        var votes = new Dictionary<string, int>(StringComparer.Ordinal);
        var st = new ParseState();

        while (reader.Read())
        {
            switch (reader.TokenType)
            {
                case JsonTokenType.PropertyName:
                    HandlePropertyName(reader.GetString() ?? string.Empty, st);
                    break;

                case JsonTokenType.StartObject:
                    if (st.PendingLatticesMap)
                    {
                        st.InLatticesMap = true;
                        st.PendingLatticesMap = false;
                    }

                    break;

                case JsonTokenType.StartArray:
                    if (st.ActiveLattice is not null && st.PendingCellsArray)
                    {
                        st.InCellsArray = true;
                        st.PendingCellsArray = false;
                        st.CellArrayDepth = 0;
                    }
                    else if (st.InCellsArray)
                    {
                        st.CellArrayDepth++;
                    }

                    break;

                case JsonTokenType.EndArray:
                    if (st.InCellsArray)
                    {
                        if (st.CellArrayDepth > 0)
                            st.CellArrayDepth--;
                        else
                            st.InCellsArray = false;
                    }

                    break;

                case JsonTokenType.String:
                    if (st.InCellsArray && st.CellArrayDepth > 0)
                        TryAddToken(reader.GetString(), votes);
                    break;
            }
        }

        return votes;
    }

    private static void HandlePropertyName(string name, ParseState st)
    {
        if (name == "cylinders")
        {
            st.InCylinders = true;
            return;
        }

        if (st.InCylinders && name == "cyl_memory")
        {
            st.InCylMemory = true;
            return;
        }

        if (name == "sss")
        {
            st.InSss = true;
            return;
        }

        if ((st.InCylMemory || st.InSss) && name == "lattices")
        {
            st.PendingLatticesMap = true;
            return;
        }

        if (!st.InLatticesMap)
            return;

        if (IsLexiconLattice(name))
        {
            st.ActiveLattice = name;
            st.PendingCellsArray = false;
            st.InCellsArray = false;
            return;
        }

        if (st.ActiveLattice is not null)
        {
            if (name == "cells")
                st.PendingCellsArray = true;
            else
            {
                st.ActiveLattice = null;
                st.PendingCellsArray = false;
                st.InCellsArray = false;
            }
        }
    }

    private static void TryAddToken(string? token, Dictionary<string, int> votes)
    {
        if (string.IsNullOrEmpty(token))
            return;

        if (token.StartsWith("C:", StringComparison.Ordinal))
            token = token[2..];

        if (token.StartsWith("W:", StringComparison.Ordinal))
        {
            var w = WordNorm.Normalize(token.AsSpan(2));
            if (w.Length > 0)
                votes[w] = votes.GetValueOrDefault(w) + 1;
            return;
        }

        if (token.StartsWith("lang.word.", StringComparison.Ordinal))
        {
            var w = WordNorm.Normalize(token.AsSpan("lang.word.".Length));
            if (w.Length > 0)
                votes[w] = Math.Max(votes.GetValueOrDefault(w), 1);
        }
    }

    private static bool IsLexiconLattice(string id) =>
        id == L2WordLegacy
        || id.StartsWith(L2WordPrefix, StringComparison.Ordinal)
        || id.StartsWith(L2EnPrefix, StringComparison.Ordinal);

    private sealed class ParseState
    {
        public bool InCylinders;
        public bool InCylMemory;
        public bool InSss;
        public bool PendingLatticesMap;
        public bool InLatticesMap;
        public string? ActiveLattice;
        public bool PendingCellsArray;
        public bool InCellsArray;
        public int CellArrayDepth;
    }
}
