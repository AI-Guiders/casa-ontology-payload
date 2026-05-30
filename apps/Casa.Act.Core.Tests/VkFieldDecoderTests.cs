using System.Text.Json;
using Xunit;

namespace Casa.Act.Tests;

public class VkFieldDecoderTests
{
    private static string PayloadRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var ltm = Path.Combine(dir.FullName, "examples", "agent-core", "vk-layouts-v0", "ltm", "l0", "L0_vk_map.ltm");
            if (File.Exists(ltm))
                return dir.FullName;
            dir = dir.Parent;
        }
        throw new InvalidOperationException("casa-ontology-payload root not found");
    }

    private static IReadOnlyDictionary<(string LayoutId, string KeyId), string> LoadIndex()
    {
        var root = PayloadRoot();
        var path = Path.Combine(root, "examples", "agent-core", "vk-layouts-v0", "ltm", "l0", "L0_vk_map.ltm");
        var lattice = LtmPackV0.ReadLatticeFile(path);
        return VkFieldDecoder.IndexFromLattice(lattice);
    }

    [Fact]
    public void Attach_command_decodes_on_qwerty()
    {
        var index = LoadIndex();
        var events = new[]
        {
            new PhysicalKeyEvent("Slash"),
            new PhysicalKeyEvent("KeyA"),
            new PhysicalKeyEvent("KeyT"),
            new PhysicalKeyEvent("KeyT"),
            new PhysicalKeyEvent("KeyA"),
            new PhysicalKeyEvent("KeyC"),
            new PhysicalKeyEvent("KeyH"),
        };
        var text = VkFieldDecoder.DecodeEvents(events, "qwerty_us", index);
        Assert.Equal("/attach", text);
    }

    [Fact]
    public void Mama_prose_decodes_on_jcuken()
    {
        var index = LoadIndex();
        var events = new[]
        {
            new PhysicalKeyEvent("KeyV"),
            new PhysicalKeyEvent("KeyF"),
            new PhysicalKeyEvent("KeyV"),
            new PhysicalKeyEvent("KeyF"),
        };
        var text = VkFieldDecoder.DecodeEvents(events, "jcuken_ru", index);
        Assert.Equal("мама", text);
    }

    [Fact]
    public void Layout_parity_cues_match_json_fixture()
    {
        var root = PayloadRoot();
        var cuesPath = Path.Combine(root, "examples", "exp_bilingual_v0", "layout_parity_cues.v1.json");
        using var doc = JsonDocument.Parse(File.ReadAllText(cuesPath));
        var index = LoadIndex();

        foreach (var item in doc.RootElement.EnumerateArray())
        {
            var id = item.GetProperty("id").GetString();
            var layout = item.GetProperty("expect_winner_layout").GetString()!;
            var expect = item.GetProperty("expect_grapheme").GetString()!;
            var events = item.GetProperty("events").EnumerateArray()
                .Select(e => new PhysicalKeyEvent(e.GetProperty("key_id").GetString()!))
                .ToArray();
            var text = VkFieldDecoder.DecodeEvents(events, layout, index);
            Assert.True(expect == text, $"{id}: expected {expect}, got {text}");
        }
    }
}
