// Exp K grade8 gold #8: average of grades
using System;

class Program
{
    static void Main()
    {
        Console.Write("How many grades: ");
        if (!int.TryParse(Console.ReadLine(), out int count) || count < 1)
            return;
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
