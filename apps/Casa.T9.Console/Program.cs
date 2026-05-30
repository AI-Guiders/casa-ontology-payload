using System.Diagnostics;
using System.Text.Json;
using Casa.Act;

namespace Casa.T9.ConsoleApp;

internal static class Program
{
    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        PropertyNameCaseInsensitive = true,
    };

    public static async Task<int> Main(string[] args)
    {
        var payloadRoot = ResolvePayloadRoot(args);
        var physicalKeys = args.Contains("--physical-keys");
        var python = Environment.GetEnvironmentVariable("CASA_PYTHON") ?? "python";
        var runtime = physicalKeys
            ? Path.Combine(payloadRoot, "tools", "cide_act_bridge_v0.py")
            : Path.Combine(payloadRoot, "tools", "t9_runtime_v0.py");

        if (!File.Exists(runtime))
        {
            Console.Error.WriteLine($"Missing runtime: {runtime}");
            return 2;
        }

        Console.WriteLine("CASA Bilingual T9 — interactive demo");
        Console.WriteLine($"Payload: {payloadRoot}");
        Console.WriteLine("Type letters (co → cow | сова). Backspace removes. Enter=flush. Esc=quit.");
        Console.WriteLine();

        using var proc = StartPythonServe(python, payloadRoot, runtime);
        await using var stdin = proc.StandardInput;
        using var stdout = proc.StandardOutput;

        var readyLine = await stdout.ReadLineAsync();
        if (readyLine is null)
        {
            Console.Error.WriteLine("Python runtime exited before ready.");
            return 3;
        }

        using var readyDoc = JsonDocument.Parse(readyLine);
        if (readyDoc.RootElement.TryGetProperty("boot_ms", out var bootMs))
            Console.WriteLine($"Field ready ({bootMs.GetInt32()} ms boot).");

        var prefix = "";
        while (true)
        {
            var key = Console.ReadKey(intercept: true);
            if (key.Key == ConsoleKey.Escape)
                break;
            if (key.Key == ConsoleKey.Enter)
            {
                Console.WriteLine();
                continue;
            }
            if (key.Key == ConsoleKey.Backspace)
            {
                if (prefix.Length > 0)
                    prefix = prefix[..^1];
            }
            else if (!char.IsControl(key.KeyChar))
            {
                prefix += key.KeyChar;
            }
            else
            {
                continue;
            }

            Console.Write($"\r> {prefix}   ");

            var req = JsonSerializer.Serialize(new { op = "tick", prefix });
            await stdin.WriteLineAsync(req);
            await stdin.FlushAsync();

            var line = await stdout.ReadLineAsync();
            if (line is null)
                break;

            RenderTick(line, prefix);
        }

        await stdin.WriteLineAsync("""{"op":"quit"}""");
        await proc.WaitForExitAsync();
        return 0;
    }

    private static Process StartPythonServe(string python, string payloadRoot, string runtime)
    {
        var psi = new ProcessStartInfo
        {
            FileName = python,
            Arguments = $"\"{runtime}\" serve",
            WorkingDirectory = payloadRoot,
            UseShellExecute = false,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            StandardOutputEncoding = System.Text.Encoding.UTF8,
            StandardErrorEncoding = System.Text.Encoding.UTF8,
        };
        var proc = Process.Start(psi) ?? throw new InvalidOperationException("Failed to start Python");
        proc.ErrorDataReceived += (_, e) =>
        {
            if (!string.IsNullOrWhiteSpace(e.Data))
                Console.Error.WriteLine(e.Data);
        };
        proc.BeginErrorReadLine();
        return proc;
    }

    private static void RenderTick(string jsonLine, string prefix)
    {
        try
        {
            using var doc = JsonDocument.Parse(jsonLine);
            var root = doc.RootElement;
            if (root.TryGetProperty("event", out var ev) && ev.GetString() == "error")
            {
                Console.WriteLine($"\nERROR: {root.GetProperty("error").GetString()}");
                return;
            }

            var commitment = root.TryGetProperty("commitment", out var c) ? c.GetString() : "?";
            Console.WriteLine($"\n[{commitment}] prefix=\"{prefix}\"");

            if (!root.TryGetProperty("branches", out var branches))
                return;

            foreach (var branch in branches.EnumerateArray())
            {
                var lang = branch.GetProperty("language").GetString() ?? "?";
                var script = branch.TryGetProperty("script", out var sc) ? sc.GetString() : "";
                Console.WriteLine($"  {lang}/{script}:");
                if (!branch.TryGetProperty("anchors", out var anchors))
                    continue;
                var n = 0;
                foreach (var a in anchors.EnumerateArray())
                {
                    if (n++ >= 6)
                    {
                        Console.WriteLine("    …");
                        break;
                    }
                    var word = a.GetProperty("word").GetString();
                    var act = a.TryGetProperty("activation", out var av) ? av.GetDouble() : 0;
                    Console.WriteLine($"    {word} ({act:0.00})");
                }
            }
            Console.WriteLine();
        }
        catch (JsonException ex)
        {
            Console.WriteLine($"\nBad JSON: {ex.Message}");
        }
    }

    private static string ResolvePayloadRoot(string[] args)
    {
        for (var i = 0; i < args.Length - 1; i++)
        {
            if (args[i] is "--payload" or "-p")
                return Path.GetFullPath(args[i + 1]);
        }

        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var tools = Path.Combine(dir.FullName, "tools", "t9_runtime_v0.py");
            if (File.Exists(tools))
                return dir.FullName;
            dir = dir.Parent;
        }

        throw new InvalidOperationException(
            "Cannot find casa-ontology-payload root. Pass --payload <path>.");
    }
}
