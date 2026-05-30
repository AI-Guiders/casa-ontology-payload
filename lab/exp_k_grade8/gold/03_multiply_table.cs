// Exp K grade8 gold #3: multiplication table for one number
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
