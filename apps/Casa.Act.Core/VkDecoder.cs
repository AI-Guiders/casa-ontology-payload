using System.Text.Json;

namespace Casa.Act;

public sealed class LayoutTable
{
    public required string LayoutId { get; init; }
    public required IReadOnlyDictionary<string, string> Map { get; init; }

    public string Decode(IEnumerable<PhysicalKeyEvent> events)
    {
        var chars = new List<char>();
        foreach (var ev in events)
        {
            if (!string.Equals(ev.Action, "down", StringComparison.OrdinalIgnoreCase))
                continue;
            if (Map.TryGetValue(ev.KeyId, out var ch) && ch.Length > 0)
                chars.Add(ch[0]);
        }
        return new string(chars.ToArray());
    }
}

public static class LayoutTableLoader
{
    public static LayoutTable LoadFromJson(string json, string? layoutIdOverride = null)
    {
        using var doc = JsonDocument.Parse(json);
        var root = doc.RootElement;
        var layoutId = layoutIdOverride
            ?? root.GetProperty("layout_id").GetString()
            ?? throw new InvalidOperationException("layout_id missing");
        var map = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var prop in root.GetProperty("map").EnumerateObject())
            map[prop.Name] = prop.Value.GetString() ?? "";
        return new LayoutTable { LayoutId = layoutId, Map = map };
    }

    public static LayoutTable LoadFromFile(string path) =>
        LoadFromJson(File.ReadAllText(path));
}

public sealed class VkDecoder
{
    private readonly IReadOnlyDictionary<string, LayoutTable> _tables;

    public VkDecoder(IEnumerable<LayoutTable> tables)
    {
        _tables = tables.ToDictionary(t => t.LayoutId, StringComparer.Ordinal);
    }

    public IReadOnlyDictionary<string, string> DecodeBranches(IEnumerable<PhysicalKeyEvent> events) =>
        _tables.ToDictionary(
            kv => kv.Key,
            kv => kv.Value.Decode(events),
            StringComparer.Ordinal);
}
