using System.Diagnostics;

namespace Casa.Act;

/// <summary>Maps ConsoleKey to W3C KeyboardEvent.code (lab adapter; full IDE uses Avalonia).</summary>
public static class ConsoleKeyMapper
{
    private static readonly Dictionary<ConsoleKey, string> Map = new()
    {
        [ConsoleKey.A] = "KeyA",
        [ConsoleKey.B] = "KeyB",
        [ConsoleKey.C] = "KeyC",
        [ConsoleKey.D] = "KeyD",
        [ConsoleKey.E] = "KeyE",
        [ConsoleKey.F] = "KeyF",
        [ConsoleKey.G] = "KeyG",
        [ConsoleKey.H] = "KeyH",
        [ConsoleKey.I] = "KeyI",
        [ConsoleKey.J] = "KeyJ",
        [ConsoleKey.K] = "KeyK",
        [ConsoleKey.L] = "KeyL",
        [ConsoleKey.M] = "KeyM",
        [ConsoleKey.N] = "KeyN",
        [ConsoleKey.O] = "KeyO",
        [ConsoleKey.P] = "KeyP",
        [ConsoleKey.Q] = "KeyQ",
        [ConsoleKey.R] = "KeyR",
        [ConsoleKey.S] = "KeyS",
        [ConsoleKey.T] = "KeyT",
        [ConsoleKey.U] = "KeyU",
        [ConsoleKey.V] = "KeyV",
        [ConsoleKey.W] = "KeyW",
        [ConsoleKey.X] = "KeyX",
        [ConsoleKey.Y] = "KeyY",
        [ConsoleKey.Z] = "KeyZ",
        [ConsoleKey.Oem2] = "Slash",
        [ConsoleKey.Spacebar] = "Space",
        [ConsoleKey.D0] = "Digit0",
        [ConsoleKey.D1] = "Digit1",
        [ConsoleKey.D2] = "Digit2",
        [ConsoleKey.D3] = "Digit3",
        [ConsoleKey.D4] = "Digit4",
        [ConsoleKey.D5] = "Digit5",
        [ConsoleKey.D6] = "Digit6",
        [ConsoleKey.D7] = "Digit7",
        [ConsoleKey.D8] = "Digit8",
        [ConsoleKey.D9] = "Digit9",
    };

    public static bool TryToKeyId(ConsoleKeyInfo key, out string keyId)
    {
        if (Map.TryGetValue(key.Key, out keyId!))
            return true;
        keyId = "";
        return false;
    }
}
