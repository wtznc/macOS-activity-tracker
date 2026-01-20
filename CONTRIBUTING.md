# Contributing to macOS Activity Tracker

Thank you for your interest in contributing! We welcome bug reports, feature requests, and pull requests.

## Development Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/wtznc/macOS-activity-tracker.git
    cd macOS-activity-tracker
    ```

2.  **Install dependencies (requires Python 3.9+):**
    We use a `Makefile` to simplify common tasks.
    ```bash
    make install-dev
    ```
    This creates a virtual environment in `.venv` and installs all development dependencies.

3.  **Activate the virtual environment:**
    ```bash
    source .venv/bin/activate
    ```

## Common Tasks

-   **Run Tests:**
    ```bash
    make test
    ```
    
-   **Linting & Formatting:**
    ```bash
    make lint
    ```
    We use `flake8` for linting, `black` for formatting, `isort` for import sorting, and `mypy` for static type checking.

-   **Security Check:**
    ```bash
    make security
    ```

-   **Run the App (Dev Mode):**
    ```bash
    python -m activity_tracker.menu_bar
    ```

## Pull Request Process

1.  **Fork** the repo and create your branch from `main`.
2.  If you've added code, please add **tests**.
3.  Ensure the test suite passes (`make test`).
4.  Ensure code style is consistent (`make lint`).
5.  Open a Pull Request!

## Reporting Bugs

Please use the [Bug Report Template](https://github.com/wtznc/macOS-activity-tracker/issues/new?template=bug_report.md) and include:
-   macOS version
-   Python version
-   Steps to reproduce
-   Expected vs. actual behavior

## License

By contributing, you agree that your contributions will be licensed under the project's [MIT License](LICENSE).
