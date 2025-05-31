def factorial(n):
  """
  Calculates the factorial of a non-negative integer.

  Args:
    n: A non-negative integer.

  Returns:
    The factorial of n (n!), which is the product of all positive integers
    less than or equal to n.
    Returns 1 if n is 0.
    Raises ValueError if n is negative.
  """

  if n < 0:
    raise ValueError("Factorial is not defined for negative numbers.")
  elif n == 0:
    return 1
  else:
    result = 1
    for i in range(1, n + 1):
      result *= i
    return result

# Example usage:
try:
  num = int(input("Enter a non-negative integer: "))
  fact = factorial(num)
  print(f"The factorial of {num} is {fact}")
except ValueError as e:
  print(e)  # Print the error message if a ValueError is raised
except Exception as e:
  print(f"An unexpected error occurred: {e}")


# Recursive version (alternative)
def factorial_recursive(n):
  """
  Calculates the factorial of a non-negative integer recursively.

  Args:
    n: A non-negative integer.

  Returns:
    The factorial of n (n!), which is the product of all positive integers
    less than or equal to n.
    Returns 1 if n is 0.
    Raises ValueError if n is negative.
  """
  if n < 0:
    raise ValueError("Factorial is not defined for negative numbers.")
  elif n == 0:
    return 1
  else:
    return n * factorial_recursive(n - 1)

# Example usage of recursive version:
try:
  num = int(input("Enter a non-negative integer: "))
  fact = factorial_recursive(num)
  print(f"The factorial of {num} is {fact}")
except ValueError as e:
  print(e)  # Print the error message if a ValueError is raised
except Exception as e:
  print(f"An unexpected error occurred: {e}")