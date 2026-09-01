#!/usr/bin/env python3
"""Utility script to generate a bcrypt password hash for admin credentials."""
import getpass
import sys
import bcrypt


def main():
    if len(sys.argv) > 1:
        password = sys.argv[1]
    else:
        password = getpass.getpass("Enter Admin Password to hash: ")
        confirm = getpass.getpass("Confirm Admin Password: ")
        if password != confirm:
            print("Error: Passwords do not match.", file=sys.stderr)
            sys.exit(1)

    if not password:
        print("Error: Password cannot be empty.", file=sys.stderr)
        sys.exit(1)

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    print("\nGenerated Bcrypt Password Hash:")
    print(hashed)
    print("\nAdd this to your .env file:")
    print(f'ADMIN_PASSWORD_HASH="{hashed}"\n')


if __name__ == "__main__":
    main()
