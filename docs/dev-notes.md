# Development Notes/Journal.

This is a personal note for the developer to reflect on. Mostly notes on design choice/language knowledge.

## Expected project structure
```python
cf-ratinglab/
  README.md
  docs/
    rating-system.md
    fft-optimization.md
    validation.md
  cpp/
    CMakeLists.txt
    src/
      rating_engine.cpp
      fft.cpp
      contest.cpp
      correction.cpp
    include/
      rating_engine.hpp
      fft.hpp
      contest.hpp
    tests/
      test_seed.cpp
      test_fft.cpp
      test_delta.cpp
    bench/
      bench_naive_vs_fft.cpp
  python/
    notebooks/
      validation.ipynb
      rating_distribution.ipynb
      what_if_analysis.ipynb
    scripts/
      fetch_cf_data.py
      validate_contests.py
      plot_benchmarks.py
  data/
    sample_contests/
  app/
    streamlit_app.py
```

## Python!

Everytime I had to use python, I always have to search up how to install venv, setup the required library etc.

For this project, Astral uv is used. Never used it but it seems like a great tool for project management.

Following are some python notes

### The \_\_init\_\_.py.

`__init__.py` is essentially a special python file used to mark a certain directory as
a **module**. When that module is imported, the file is **implicitly executed**.

### Python modules / sys.path

When using import, python searches the `sys.path`, which is a list of directory python searches for module import.

To inspect it:
```python
import sys
print(sys.path)
```

Typical output:
``` python
['', '/usr/lib/python3.x', '/usr/lib/python3.x/lib-dynload', ...]
```

Where `''` indicates the current directory (Directory where the script is executed). This is why scripts can import files in the same directory w/o any additional setup.

To import modules from another directory (not inside subdirectory), you have two options:
- Setting up a build system in `pyproject.toml`.
- Adding module directory to `sys.path` via `sys.path.insert(0, "python/src")`

### Difference between args vs kwargs

#### `*args`: Accepting an abitrary number of **positional** arguments. These arguments are referenced by their index and is passed in as a **tuple**

Example:

```python
def sum_numbers(*args):
    # args is a tuple: (1, 2, 3, 4)
    return sum(args)

print(sum_numbers(1, 2, 3, 4))  # Output: 10
```

#### `**kwargs`: Accepting an abitrary number of **keyword** (named) arguments. These elements are referenced by their keyword and is passed in as **dictionary**

Example:

```python
def show_profile(**kwargs):
    # kwargs is a dict: {"name": "Alice", "role": "Developer"}
    for key, value in kwargs.items():
        print(f"{key}: {value}")

show_profile(name="Alice", role="Developer")
```
You can always combine regular arguments, `*args`, and `**kwargs` together. The order where you are supposed to declare them are:

1. Regular arguments
2. `*args`
3. `**kwargs`

Example:
```python
def master_function(required_arg, *args, **kwargs):
    print(required_arg)  # Handles the first positional argument
    print(args)          # Catches extra positional arguments as a tuple
    print(kwargs)        # Catches extra keyword arguments as a dictionary

master_function("Required", 1, 2, 3, site="StackOverflow", status="Active")
```

### File IO

Most common way to perform File-IO is using `open()` and the `with` statement

- `open(filename, mode)` returns a File Object. You can specify which mode to use.
    - `'r'`: Read (Default mode)
    - `'w'`: Write, create a new file or overwrites the old file.
    - `'a'`: Append, open a file and append to the end. Create a new file if file doesn't exist yet.
- `with` Ensures that the file is **closed** after the execution, **even if an exception occurs**. It doesn't catch the error, instead it propagates normally after the `with` clause.

`with` is similar with `try with resource` in Java.

### Logger

the `logging` module is typically used to perform logging operations in python.

To get logger, type the following command:

```python
# __name__ is generally a naming convention to identify logger hierarchy
logging.getLogger(__name__)
```

There are 5 levels of logging (Taken straight from official documentation):
| Level | When it’s used |
| --- | --- |
| `DEBUG` | Detailed information, typically of interest only when diagnosing problems. |
| `INFO` | Confirmation that things are working as expected. |
| `WARNING` | An indication that something unexpected happened, or indicative of some problem in the near future (e.g. ‘disk space low’). The software is still working as expected. |
| `ERROR` | Due to a more serious problem, the software has not been able to perform some function. |
| `CRITICAL` | A serious error, indicating that the program itself may be unable to continue running. |

Default minimum displayed level is `WARNING`

A few relevant methods related to logger:
- `logger.setHandler()`: Setting handler, directing where log messages are printed.
- `logger.setLevel()`: Changing minimum displayed level for logs.
- `logger.basicConfig()`: Changing certain attributes of a logger (format, level, etc...)

### Subprocess