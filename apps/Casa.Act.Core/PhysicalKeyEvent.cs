namespace Casa.Act;

/// <summary>L0 input contract (ADR-0008): layout-neutral physical key.</summary>
public readonly record struct PhysicalKeyEvent(string KeyId, string Action = "down");

public static class PhysicalKeyEventJson
{
    public static PhysicalKeyEvent FromJson(string keyId, string? action = null) =>
        new(keyId, string.IsNullOrWhiteSpace(action) ? "down" : action);
}
