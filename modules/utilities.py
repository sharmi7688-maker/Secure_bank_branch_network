import os


def clear_screen():
    """
    Clears the terminal screen.
    Works on both Windows and Linux/macOS.
    """
    os.system("cls" if os.name == "nt" else "clear")


def print_header():
    """
    Displays the Secure Bank project header.
    """
    print("=" * 60)
    print("                SECURE BANK")
    print("          BRANCH NETWORK SYSTEM")
    print("=" * 60)