# C# — canonical: guess the number (console)

**doc_id:** `kb-csharp-guess-number-canonical`  
**lang:** ru queries / en code samples

## Game rules (claims)

- Игра «угадай число»: загадать целое в диапазоне, игрок вводит число, ответ **больше**, **меньше** или **угадал**.
- Диапазон по умолчанию: **1..100** включительно (`Random.Next(1, 101)` в C#).
- Цикл до правильного ответа; после «угадал» — выход.

## C# building blocks

- `System.Random` — `var rnd = new Random(); int secret = rnd.Next(1, 101);`
- `Console.Write` / `Console.WriteLine` — подсказки игроку.
- `Console.ReadLine` + `int.TryParse` — ввод и проверка числа.
- Сравнение: `if (guess < secret)` → «Higher» / «больше»; `else if (guess > secret)` → «Lower» / «меньше»; `else` → победа.

## Structure

- Один файл `Program.cs`, `static void Main()`, top-level не обязателен в v0 bench.
- `using System;` достаточно для console + Random.

## Reference

Полный эталон: `lab/exp_k_guess_number/gold/Program.cs` в lab repo.
