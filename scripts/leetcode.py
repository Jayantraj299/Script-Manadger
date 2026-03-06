import random

def random_number_picker():
    numbers = list(range(1, 3847))  # Create a list of numbers from 1 to 3846
    random.shuffle(numbers)         # Shuffle the list once

    for number in numbers:
        input("Press Enter to pick the next number (or Ctrl+C to stop)...")
        print(f"Picked number: {number}")

random_number_picker()
