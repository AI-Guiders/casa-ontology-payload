using System.Buffers.Binary;
using System.Text;

namespace Casa.Act;

/// <summary>Lab oracle: LTM0 bytes reader. Prod boot uses CASA import → field RAM.</summary>
public static class LtmPackV0
{
    private static ReadOnlySpan<byte> Magic => "LTM0"u8;

    public static VkLattice ReadLattice(ReadOnlySpan<byte> data)
    {
        if (data.Length < 20)
            throw new InvalidDataException("truncated LTM");
        if (!data[..4].SequenceEqual(Magic))
            throw new InvalidDataException("bad LTM magic");

        var ver = BinaryPrimitives.ReadUInt16LittleEndian(data[4..]);
        if (ver != 1)
            throw new InvalidDataException($"unsupported LTM version: {ver}");

        var w = BinaryPrimitives.ReadUInt16LittleEndian(data[6..]);
        var h = (int)BinaryPrimitives.ReadUInt32LittleEndian(data[8..]);
        var vocabN = BinaryPrimitives.ReadUInt32LittleEndian(data[12..]);
        var placeN = BinaryPrimitives.ReadUInt32LittleEndian(data[16..]);
        var off = 20;
        var vocab = new string[vocabN];
        for (var i = 0; i < vocabN; i++)
        {
            var ln = BinaryPrimitives.ReadUInt16LittleEndian(data[off..]);
            off += 2;
            vocab[i] = Encoding.UTF8.GetString(data.Slice(off, ln));
            off += ln;
        }

        var cells = new List<string>[w * h];
        for (var i = 0; i < cells.Length; i++)
            cells[i] = [];

        for (var p = 0; p < placeN; p++)
        {
            var ti = BinaryPrimitives.ReadUInt16LittleEndian(data[off..]);
            var x = data[off + 2];
            var y = data[off + 3];
            off += 4;
            var idx = y * w + x;
            cells[idx].Add(vocab[ti]);
        }

        return new VkLattice(w, h, cells);
    }

    public static VkLattice ReadLatticeFile(string path) =>
        ReadLattice(File.ReadAllBytes(path));
}

public sealed record VkLattice(int Width, int Height, List<string>[] Cells);

/// <summary>
/// Lab oracle only — prod: PhysicalKeyEvent[] → CASA runtime (field compose decode).
/// </summary>
public static class VkFieldDecoder
{
    public const string LatticeId = "L0_vk_map";

    public static Dictionary<(string LayoutId, string KeyId), string> IndexFromLattice(VkLattice lattice)
    {
        var idx = new Dictionary<(string, string), string>();
        foreach (var cell in lattice.Cells)
        {
            foreach (var token in cell)
            {
                if (!token.StartsWith("E:vk.physical.", StringComparison.Ordinal))
                    continue;
                var body = token[2..];
                var parts = body.Split('|', 3);
                if (parts.Length != 3)
                    continue;
                if (!parts[1].StartsWith("layout.", StringComparison.Ordinal))
                    continue;
                var keyId = parts[0]["vk.physical.".Length..];
                var layoutId = parts[1]["layout.".Length..];
                var ch = CharFromEdgeDst(parts[2]);
                if (ch is not null)
                    idx[(layoutId, keyId)] = ch;
            }
        }
        return idx;
    }

    private static string? CharFromEdgeDst(string dst)
    {
        const string output = "output.";
        if (dst.StartsWith(output, StringComparison.Ordinal) && dst.Length > output.Length)
            return dst[output.Length..];
        return CharFromGraphemeConcept(dst);
    }

    private static string? CharFromGraphemeConcept(string conceptId)
    {
        const string latn = "grapheme.latn.";
        const string cyrl = "grapheme.cyrl.";
        if (conceptId.StartsWith(latn, StringComparison.Ordinal) && conceptId.Length > latn.Length)
            return conceptId.Substring(latn.Length, 1);
        if (conceptId.StartsWith(cyrl, StringComparison.Ordinal) && conceptId.Length > cyrl.Length)
            return conceptId.Substring(cyrl.Length, 1);
        return null;
    }

    public static string DecodeEvents(
        IEnumerable<PhysicalKeyEvent> events,
        string layoutId,
        IReadOnlyDictionary<(string LayoutId, string KeyId), string> index)
    {
        var sb = new StringBuilder();
        foreach (var ev in events)
        {
            if (!string.Equals(ev.Action, "down", StringComparison.OrdinalIgnoreCase))
                continue;
            if (index.TryGetValue((layoutId, ev.KeyId), out var ch) && ch.Length > 0)
                sb.Append(ch[0]);
        }
        return sb.ToString();
    }

    public static IReadOnlyDictionary<string, string> DecodeBranches(
        IEnumerable<PhysicalKeyEvent> events,
        IReadOnlyDictionary<(string LayoutId, string KeyId), string> index)
    {
        var layouts = index.Keys
            .Select(k => k.LayoutId)
            .Where(id => !id.Contains(".shift", StringComparison.Ordinal))
            .Distinct(StringComparer.Ordinal)
            .Order()
            .ToArray();
        var outMap = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var layout in layouts)
            outMap[layout] = DecodeEvents(events, layout, index);
        return outMap;
    }
}
