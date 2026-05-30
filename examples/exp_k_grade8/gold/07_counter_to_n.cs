// Exp K grade8 gold #7: print 1..N
using System;

class Program
{
    static void Main()
    {
        Console.Write("N: ");
        if (!int.TryParse(Console.ReadLine(), out int n) || n < 1)
        {
            Console.WriteLine("Bad N");
            return;
        }
        for (int i = 1; i <= n; i++)
            Console.WriteLine(i);
    }
}
