// Exp K grade8 gold #6: simple console menu
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
            if (!int.TryParse(Console.ReadLine(), out int choice))
                continue;
            switch (choice)
            {
                case 1:
                    Console.WriteLine("Hi!");
                    break;
                case 2:
                    Console.WriteLine(DateTime.Now);
                    break;
                case 0:
                    return;
                default:
                    Console.WriteLine("Unknown");
                    break;
            }
        }
    }
}
