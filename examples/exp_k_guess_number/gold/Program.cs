// Exp K gold: guess-the-number console game (C#)
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
            var line = Console.ReadLine();
            if (!int.TryParse(line, out int guess))
            {
                Console.WriteLine("Enter a number.");
                continue;
            }

            if (guess < secret)
                Console.WriteLine("Higher");
            else if (guess > secret)
                Console.WriteLine("Lower");
            else
            {
                Console.WriteLine("Correct!");
                break;
            }
        }
    }
}
