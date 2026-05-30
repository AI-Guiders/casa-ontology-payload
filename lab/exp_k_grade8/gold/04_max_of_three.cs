// Exp K grade8 gold #4: maximum of three integers
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
