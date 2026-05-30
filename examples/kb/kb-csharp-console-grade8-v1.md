# C# — консольные программы, уровень «8 класс» (v1)

**doc_id:** `kb-csharp-console-grade8-v1`  
**audience:** школьник / начинающий; цель — **понять синтаксис** и писать **простые консольные** программы без фреймворков.  
**lang:** объяснения на русском; примеры кода — C#; запросы агента часто на русском.  
**Не заменяет:** [`kb-dotnet-fundamentals-v1.md`](kb-dotnet-fundamentals-v1.md) (TFM, SDK, enterprise).  
**Связь:** угадай число — lab `kb-csharp-guess-number-canonical.md` + §16 ниже.

**Внешние опоры (для учителя/агента):** [Tour of C#](https://learn.microsoft.com/en-us/dotnet/csharp/tour-of-csharp/overview), [Console](https://learn.microsoft.com/en-us/dotnet/api/system.console), [Random](https://learn.microsoft.com/en-us/dotnet/api/system.random).

---

## 0. Педагогика курса (как учить «школьника»)

- **Куррикулярность:** сначала вывод текста, потом ввод, потом ветвления, потом циклы, потом методы и `Random`; не смешивать всё в первом уроке.
- **Спираль:** каждая новая тема опирается на предыдущую (например, цикл `while` в игре — после отдельного упражнения «счётчик до N»).
- **Рабочая память:** одна программа — один файл `Program.cs`, один `Main`; не вводить классы с полями и наследование в v1.
- **Формативная обратная связь:** компилятор — «учитель»: читать текст ошибки (`CS...`), исправлять **одну** ошибку за раз, снова `dotnet build`.
- **Эталон + вариация:** сначала разбор эталона построчно, потом задание «сделай похожее, но с другими числами/текстом».
- **Проверка понимания:** ученик (или агент) должен уметь **объяснить словами**, что делает каждая строка в `Main`, не только скопировать.
- **Ошибки — норма:** типичные ошибки (точка с запятой, типы, границы `Random.Next`) закрепляются отдельным блоком §16.
- **Мотивация:** программа должна что-то «делать» в консоли (диалог, игра, таблица), а не печатать абстрактные числа без смысла.
- **Роутер агента:** запросы «напиши консоль на C#», «объясни while», «исправь ошибку компиляции» — подтягивать этот документ; профессиональные TFM/playbook — только если явно спросили про SDK/деплой.

*Связь с исследовательской педагогикой CASA:* слоистое обучение, редкие семантические коррекции (компилятор + разбор), среда «действие → результат» — см. `research-training-developmental-pedagogy-v1.md` (метафора, не биология).

---

## 1. Что такое программа на C#

- **Программа** — текст на языке C#, который **компилятор** превращает в команды для компьютера.
- **Консольное приложение** — программа без окон: ввод и вывод идут в **терминал** (чёрное окно / встроенный терминал IDE).
- Файл с кодом обычно называется `Program.cs`; точка входа — метод **`static void Main()`**.
- Строка `using System;` подключает базовые типы (`Console`, `String`, `Int32` и др.).
- Команды в C# заканчиваются **точкой с запятой** `;`.
- Блок кода в фигурных скобках `{ }` — «тело» метода, цикла, ветки `if`.
- Регистр букв важен: `Console` и `console` — не одно и то же.
- Комментарий `//` до конца строки; многострочный `/* ... */` — для длинных пояснений.
- Сборка: `dotnet build`; запуск: `dotnet run` (из папки проекта с `.csproj`).
- **Успех урока 1:** программа печатает одну строку и завершается без ошибки сборки.

```csharp
using System;
class Program
{
    static void Main()
    {
        Console.WriteLine("Hello, world!");
    }
}
```

---

## 2. Вывод в консоль: Write и WriteLine

- `Console.WriteLine("текст");` — печатает строку и **переводит строку** (курсор на новую строку).
- `Console.Write("текст");` — печатает **без** перевода строки (удобно для приглашения «Введите имя: »).
- В кавычках — **строковый литерал**; внутри строки кавычку экранируют: `\"`.
- Склеивание строк: `"Привет, " + name` или интерполяция `$"Привет, {name}!"` (оба допустимы на этом уровне).
- Число можно вывести: `Console.WriteLine(42);` или `Console.WriteLine(sum);`.
- Пустая строка: `Console.WriteLine();` — просто перевод строки.
- **Типичная ошибка:** забыть `;` после `WriteLine` → ошибка компилятора около строки.

---

## 3. Переменные и типы (int, string, bool)

- **Переменная** — именованная «ячейка» в памяти: `int age = 14;`
- **`int`** — целое число (−2 147 483 648 … 2 147 483 647).
- **`string`** — текст; литерал в двойных кавычках: `string name = "Аня";`
- **`bool`** — логическое: `true` или `false`.
- Объявление с типом: `int x = 10;` Ключевое слово **`var`** — компилятор выводит тип: `var n = 5;` → `int`.
- Присваивание меняет значение: `x = x + 1;` или кратко `x++;` (увеличить на 1).
- Имена переменных — `camelCase` (первая буква строчная): `userName`, `totalSum`.
- Нельзя использовать зарезервированные слова как имена: `int`, `class`, `string`.
- **Сравнение чисел:** `==`, `!=`, `<`, `>`, `<=`, `>=` — результат типа `bool`.
- **Логика:** `&&` (и), `||` (или), `!` (не).

---

## 4. Ввод с клавиатуры: ReadLine и TryParse

- `string line = Console.ReadLine();` — читает строку до Enter (может быть `null` в редких случаях; на учебном уровне проверять пустую строку).
- Текст **не является числом** автоматически: `"42"` — string, не int.
- Безопасное преобразование: `int.TryParse(line, out int value)` → `true`, если удалось; иначе `false`.
- Паттерн ввода числа:

```csharp
Console.Write("Введите число: ");
var line = Console.ReadLine();
if (!int.TryParse(line, out int n))
{
    Console.WriteLine("Это не число.");
    return; // или continue в цикле
}
```

- Для **двух чисел** — два раза `ReadLine` + два `TryParse`, или один разделитель (позже).
- **Педагогика:** сначала научить выводить подсказку `Write`, потом читать `ReadLine`.

---

## 5. Ветвление: if, else if, else

- `if (условие) { ... }` — выполнить блок, только если условие **истинно**.
- `else { ... }` — иначе (взаимоисключающая ветка).
- `else if (другое_условие) { ... }` — цепочка проверок (как «иначе если»).
- Фигурные скобки обязательны для ясности на учебном уровне, даже для одной строки.
- Вложенные `if` допустимы, но лучше не углубляться больше 2–3 уровней — вынести в метод (§10).
- **Тернарный оператор** (опционально): `int max = (a > b) ? a : b;`
- Сравнение строк: `name == "Аня"` или `string.Equals(a, b)`; для учебника часто достаточно `==`.

---

## 6. Цикл while

- `while (условие) { тело }` — повторять, пока условие **true**.
- Бесконечный цикл: `while (true)` + выход через `break` при нужном событии.
- `break` — немедленно выйти из цикла; `continue` — перейти к следующей итерации.
- Перед циклом инициализировать счётчик/флаг; внутри — менять переменные, иначе зацикливание.
- **Счётчик:** `int i = 0; while (i < 10) { ...; i++; }`

---

## 7. Цикл for

- `for (инициализация; условие; шаг) { тело }` — когда **известно число повторений**.
- Классика: `for (int i = 1; i <= 10; i++)` — `i` от 1 до 10 включительно.
- Переменная `i` в заголовке `for` видна только внутри цикла (область видимости).
- Таблица умножения одной строки: цикл по множителю 1..10.
- `for` и `while` взаимозаменяемы; `for` удобнее для счётчиков, `while` — «пока не угадал».

---

## 8. switch и простое меню

- `switch (переменная)` — выбор по **дискретным** значениям (часто `int` или `string`).
- Каждая ветка: `case 1:` … `break;` Иначе — `default:`.
- **Меню:** напечатать варианты, `ReadLine`/`TryParse` выбор, `switch` по номеру, `break` из внешнего `while` для выхода (например, пункт 0).
- Забытый `break` после `case` → ошибка компилятора (намеренно строго).

```csharp
switch (choice)
{
    case 1:
        Console.WriteLine("Пункт 1");
        break;
    case 2:
        Console.WriteLine("Пункт 2");
        break;
    default:
        Console.WriteLine("Неизвестный пункт");
        break;
}
```

---

## 9. Случайные числа: System.Random

- `var rnd = new Random();` — генератор псевдослучайных чисел.
- `rnd.Next(1, 101)` — целое **от 1 включительно до 100 включительно** (верхняя граница **исключается**).
- Диапазон 1..100: всегда писать `Next(1, 101)`, не `Next(100)`.
- `rnd.Next(0, 2)` — 0 или 1 (монетка).
- Один объект `Random` на программу — достаточно для учебных задач.
- **Игра «угадай число»:** одно `secret`, цикл `while`, сравнение `guess` с `secret`, подсказки «больше»/«меньше».

---

## 10. Методы static (подпрограммы)

- **Метод** — именованный блок кода: `static int Add(int a, int b) { return a + b; }`
- `static` — вызывать из `Main` без создания объекта класса (достаточно для 8 класса).
- `void` — метод ничего не возвращает; `int`, `string` и др. — тип возвращаемого значения + `return значение;`
- Вызов: `int s = Add(2, 3);`
- Параметры — копии значений для `int`/`bool`; для учебника не углубляться в `ref`/`out` кроме `TryParse`.
- Вынос повторяющегося кода в метод улучшает читаемость (например, `PrintMenu()`).

---

## 11. Массив и среднее (минимум для оценок)

- Массив фиксированной длины: `int[] grades = { 5, 4, 5 };` или `int[] g = new int[3];`
- Длина: `grades.Length`; элемент: `grades[i]` (индекс с **0**).
- Сумма в цикле: `int sum = 0; for (int i = 0; i < grades.Length; i++) sum += grades[i];`
- Среднее: `double avg = (double)sum / grades.Length;` — приведение типа, иначе целочисленное деление.
- Альтернатива без массива на первом проходе: три переменные `g1,g2,g3` — допустимо для K0, массив — шаг вперёд.

---

## 12. Эталон 1: Hello, имя

**Задача:** спросить имя, поздороваться.  
**Навыки:** `Write`, `ReadLine`, конкатенация или `$"..."`.

```csharp
using System;
class Program
{
    static void Main()
    {
        Console.Write("Your name: ");
        var name = Console.ReadLine();
        Console.WriteLine("Hello, " + name + "!");
    }
}
```

- Gold (lab): `examples/exp_k_grade8/gold/01_hello_name.cs`
- Вариация для ученика: изменить приветствие на русский; добавить проверку пустого имени.

---

## 13. Эталон 2: Сумма двух чисел

**Задача:** ввести два целых, вывести сумму.  
**Навыки:** два `TryParse`, арифметика `+`.

```csharp
using System;
class Program
{
    static void Main()
    {
        Console.Write("First number: ");
        if (!int.TryParse(Console.ReadLine(), out int a)) { Console.WriteLine("Not a number."); return; }
        Console.Write("Second number: ");
        if (!int.TryParse(Console.ReadLine(), out int b)) { Console.WriteLine("Not a number."); return; }
        Console.WriteLine("Sum = " + (a + b));
    }
}
```

- Gold: `examples/exp_k_grade8/gold/02_sum_two.cs`

---

## 14. Эталон 3: Таблица умножения (одно число, 1..10)

**Задача:** напечатать строки `7 x 1 = 7` … `7 x 10 = 70`.  
**Навыки:** `for`, умножение.

```csharp
using System;
class Program
{
    static void Main()
    {
        int n = 7;
        for (int i = 1; i <= 10; i++)
            Console.WriteLine(n + " x " + i + " = " + (n * i));
    }
}
```

- Gold: `examples/exp_k_grade8/gold/03_multiply_table.cs`
- Вариация: `n` ввести с клавиатуры после `TryParse`.

---

## 15. Эталон 4: Максимум из трёх чисел

**Задача:** ввести три числа, вывести наибольшее.  
**Навыки:** цепочка `if / else if`, или вложенные сравнения.

```csharp
using System;
class Program
{
    static void Main()
    {
        Console.Write("a: ");
        int.TryParse(Console.ReadLine(), out int a);
        Console.Write("b: ");
        int.TryParse(Console.ReadLine(), out int b);
        Console.Write("c: ");
        int.TryParse(Console.ReadLine(), out int c);
        int max = a;
        if (b > max) max = b;
        if (c > max) max = c;
        Console.WriteLine("Max = " + max);
    }
}
```

- Gold: `examples/exp_k_grade8/gold/04_max_of_three.cs`

---

## 16. Эталон 5: Угадай число (1..100)

**Правила:** загадать `secret`, игрок вводит `guess`, ответ **Higher** / **Lower** / **Correct**, цикл до победы.

- `int secret = rnd.Next(1, 101);`
- `while (true)` + `break` при угадывании.
- `if (guess < secret)` → «больше» (число загадано выше вводимого).
- `if (!int.TryParse(...))` → «Enter a number» и `continue`.

```csharp
using System;
class Program
{
    static void Main()
    {
        var rnd = new Random();
        int secret = rnd.Next(1, 101);
        while (true)
        {
            Console.Write("Guess (1-100): ");
            if (!int.TryParse(Console.ReadLine(), out int guess))
            { Console.WriteLine("Enter a number."); continue; }
            if (guess < secret) Console.WriteLine("Higher");
            else if (guess > secret) Console.WriteLine("Lower");
            else { Console.WriteLine("Correct!"); break; }
        }
    }
}
```

- Gold: `examples/exp_k_guess_number/gold/Program.cs` (тот же эталон в Exp K).

---

## 17. Эталон 6: Меню с циклом

**Задача:** показывать меню 1/2/0 (выход), повторять до выхода.  
**Навыки:** `while`, `switch`, `TryParse` для выбора.

```csharp
using System;
class Program
{
    static void Main()
    {
        while (true)
        {
            Console.WriteLine("1 - Say hi");
            Console.WriteLine("2 - Show date");
            Console.WriteLine("0 - Exit");
            Console.Write("Choice: ");
            if (!int.TryParse(Console.ReadLine(), out int choice)) continue;
            switch (choice)
            {
                case 1: Console.WriteLine("Hi!"); break;
                case 2: Console.WriteLine(DateTime.Now); break;
                case 0: return;
                default: Console.WriteLine("Unknown"); break;
            }
        }
    }
}
```

- Нужен `using System;` для `DateTime` — допустимое расширение после базового курса.
- Gold: `examples/exp_k_grade8/gold/06_menu.cs`

---

## 18. Эталон 7: Счётчик от 1 до N

**Задача:** ввести `N`, напечатать числа 1, 2, …, N.  
**Навыки:** `for`, ввод.

```csharp
using System;
class Program
{
    static void Main()
    {
        Console.Write("N: ");
        if (!int.TryParse(Console.ReadLine(), out int n) || n < 1) { Console.WriteLine("Bad N"); return; }
        for (int i = 1; i <= n; i++)
            Console.WriteLine(i);
    }
}
```

- Gold: `examples/exp_k_grade8/gold/07_counter_to_n.cs`

---

## 19. Эталон 8: Среднее оценок

**Задача:** ввести количество оценок, затем оценки, вывести среднее.  
**Навыки:** массив или цикл накопления суммы.

```csharp
using System;
class Program
{
    static void Main()
    {
        Console.Write("How many grades: ");
        if (!int.TryParse(Console.ReadLine(), out int count) || count < 1) return;
        int sum = 0;
        for (int i = 0; i < count; i++)
        {
            Console.Write("Grade: ");
            int.TryParse(Console.ReadLine(), out int g);
            sum += g;
        }
        double avg = (double)sum / count;
        Console.WriteLine("Average = " + avg);
    }
}
```

- Gold: `examples/exp_k_grade8/gold/08_average_grades.cs`

---

## 20. Типичные ошибки компиляции (учить читать сообщение)

| Симптом / CS | Частая причина | Что сделать |
|--------------|----------------|-------------|
| `; expected` | Нет `;` в конце оператора | Добавить `;` |
| `The name 'X' does not exist` | Опечатка, нет `using`, переменная вне области | Проверить имя и `{}` |
| `Cannot implicitly convert type` | Присвоили string в int | `TryParse` или `Convert` |
| `Use of unassigned local variable` | Читали переменную до присвоения | Инициализировать или ветка `if` |
| `No overload for 'Next' takes 1 arguments` | Путаница `Next(max)` vs `Next(min,max)` | Для 1..100: `Next(1, 101)` |
| Бесконечный вывод | `while` без изменения условия | Менять счётчик или `break` |
| `break` вне цикла | `break` не в `while`/`for`/`switch` | Перенести внутрь цикла |

- **Педагогика:** не менять десять строк сразу — исправить **первую** ошибку в списке компилятора, пересобрать.
- Агент при emit: после `dotnet build` подставлять digest из §20 + фрагмент кода вокруг строки из сообщения.

---

## 21. Чеклист «понял ли ученик» (для агента / преподавателя)

- Может написать Hello + ввод имени без копирования эталона целиком.
- Объясняет разницу `Write` и `WriteLine`.
- Вводит число через `TryParse`, а не `int.Parse` без обработки (на учебном уровне — знать риск исключения).
- Пишет `if/else` для сравнения трёх чисел.
- Пишет `for` для таблицы и `while` для игры.
- Знает границы `Random.Next(min, maxExclusive)`.
- Собирает проект командой `dotnet build` и интерпретирует одну ошибку CS.
- **K4 (Exp K):** не менее **6 из 8** эталонных задач (§12–19) — build OK по gold-логике.

---

## 22. Операционное использование в CASA / Exp K

- Store: `code-agent-lab-v0`; bundle stem `kb-csharp-console-grade8-v1`.
- Recall (K0): запросы про `Console`, `TryParse`, `while`, `Random`, «напиши сумму двух чисел».
- Emit (K2+): digest из top claims + эталон ближайшей задачи; не смешивать с `kb-dotnet-fundamentals-v1` без запроса.
- Профессиональный стиль кода — [`code-writing-principles-v1.md`](../software-authoring/code-writing-principles-v1.md) — **после** того как программа компилируется.

**Версия:** v1 · 2026-05-29
