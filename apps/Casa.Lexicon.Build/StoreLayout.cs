namespace Casa.Lexicon.Build;

internal static class StoreIds
{
    public const string EnFolk = "lexicon-en-folk";
    public const string AfanIngest = "ingest-ref-afan";
}

internal sealed record CorpusSpec(string Id, string StoreId, string HeadwordsRel, int MinWords);

internal static class CorpusQuad
{
    public static readonly CorpusSpec EnGeneral = new(
        "en-general",
        "lexicon-en-general",
        "lab/corpus/en-general-v0/headwords.v1.txt",
        5000);

    public static readonly CorpusSpec EnTech = new(
        "en-tech",
        "lexicon-en-tech",
        "lab/corpus/en-tech-v0/headwords.v1.txt",
        200);

    public static readonly CorpusSpec RuGeneral = new(
        "ru-general",
        "lexicon-ru-general",
        "lab/corpus/ru-general-v0/headwords.v1.txt",
        10_000);

    public static readonly CorpusSpec RuTech = new(
        "ru-tech",
        "lexicon-ru-tech",
        "lab/corpus/ru-tech-v0/headwords.v1.txt",
        200);

    public static IEnumerable<CorpusSpec> All => [EnGeneral, EnTech, RuGeneral, RuTech];

    public static CorpusSpec? TryGet(string id) =>
        All.FirstOrDefault(c => c.Id.Equals(id, StringComparison.OrdinalIgnoreCase));
}
