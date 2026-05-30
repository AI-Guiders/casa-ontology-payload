namespace Casa.Lexicon.Build;

internal static class StoreIds
{
    public const string EnFolk = "sss-en-folk-v0";
    public const string AfanIngest = "sss-afan-v0";
}

internal sealed record CorpusSpec(string Id, string StoreId, string HeadwordsRel, int MinWords);

internal static class CorpusQuad
{
    public static readonly CorpusSpec EnGeneral = new(
        "en-general",
        "sss-en-general-v0",
        "lab/corpus/en-general-v0/headwords.v1.txt",
        5000);

    public static readonly CorpusSpec EnTech = new(
        "en-tech",
        "sss-en-tech-v0",
        "lab/corpus/en-tech-v0/headwords.v1.txt",
        200);

    public static readonly CorpusSpec RuGeneral = new(
        "ru-general",
        "sss-ru-general-v0",
        "lab/corpus/ru-general-v0/headwords.v1.txt",
        10_000);

    public static readonly CorpusSpec RuTech = new(
        "ru-tech",
        "sss-ru-tech-v0",
        "lab/corpus/ru-tech-v0/headwords.v1.txt",
        200);

    public static IEnumerable<CorpusSpec> All => [EnGeneral, EnTech, RuGeneral, RuTech];

    public static CorpusSpec? TryGet(string id) =>
        All.FirstOrDefault(c => c.Id.Equals(id, StringComparison.OrdinalIgnoreCase));
}
