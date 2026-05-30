using System.Text.Json.Serialization;

namespace Casa.Lexicon.Build;

[JsonSerializable(typeof(HeadwordReport))]
[JsonSerializable(typeof(Dictionary<string, HeadwordReport>))]
internal sealed partial class LexiconJsonContext : JsonSerializerContext;

internal sealed record HeadwordReport
{
    public string? StoreDir { get; init; }
    public string? SourceStore { get; init; }
    public string? Out { get; init; }
    public int UniqueHeadwords { get; init; }
    public string? Mode { get; init; }
    public string? Locale { get; init; }
}
