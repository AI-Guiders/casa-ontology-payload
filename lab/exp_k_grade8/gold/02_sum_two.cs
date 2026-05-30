// Exp K grade8 gold #2: sum of two integers
using System;

class Program
{
    static void Main()
    {
        Console.Write("First number: ");
        if (!int.TryParse(Console.ReadLine(), out int a))
        {
            Console.WriteLine("Not a number.");
            return;
        }
        Console.Write("Second number: ");
        if (!int.TryParse(Console.ReadLine(), out int b))
        {
            Console.WriteLine("Not a number.");
            return;
        }
        Console.WriteLine("Sum = " + (a + b));
    }
}
