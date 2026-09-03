"""Maintenance CLI for the encrypted-at-rest clock feature files.

Usage (from the project root):

    python scripts/protect_clock_features.py --init
        Generates the encryption key at .secrets/clock_features.key if missing.

    python scripts/protect_clock_features.py --encrypt [--remove-plaintext]
        Encrypts every file in PROTECTED_DATA_FILES to <name>.enc. With
        --remove-plaintext the original readable CSV is deleted afterwards
        (this is what you want on a deployed server).

    python scripts/protect_clock_features.py --decrypt
        Writes the plaintext CSVs back next to the .enc files. For maintenance
        only - delete them again afterwards.

    python scripts/protect_clock_features.py --status
        Shows, per file, whether the encrypted and/or plaintext version exists.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cryptography.fernet import Fernet  # noqa: E402

from backend.services.secure_features_service import (  # noqa: E402
    DEFAULT_KEY_PATH,
    ENCRYPTED_SUFFIX,
    PROTECTED_DATA_FILES,
    _resolve,
    decrypt_file,
    encrypt_file,
    get_key,
)


def init_key() -> bytes:
    """Creates the key file if it does not exist yet and returns the key."""
    if os.path.exists(DEFAULT_KEY_PATH):
        print(f"Key already exists: {DEFAULT_KEY_PATH}")
        with open(DEFAULT_KEY_PATH, "rb") as f:
            return f.read().strip()

    os.makedirs(os.path.dirname(DEFAULT_KEY_PATH), exist_ok=True)
    key = Fernet.generate_key()
    with open(DEFAULT_KEY_PATH, "wb") as f:
        f.write(key)
    print(f"Generated new key: {DEFAULT_KEY_PATH}")
    print("Back this key up somewhere safe - without it the encrypted clock")
    print("feature files cannot be read, and the built-in clocks stop working.")
    return key


def cmd_encrypt(remove_plaintext: bool) -> None:
    key = get_key()
    for name in PROTECTED_DATA_FILES:
        path = _resolve(name)
        if not os.path.exists(path):
            if os.path.exists(path + ENCRYPTED_SUFFIX):
                print(f"[skip]      {name} (already encrypted, no plaintext present)")
            else:
                print(f"[MISSING]   {name}")
            continue
        encrypt_file(path, key)
        print(f"[encrypted] {name} -> {name}{ENCRYPTED_SUFFIX}")
        if remove_plaintext:
            os.remove(path)
            print(f"[removed]   {name} (plaintext)")


def cmd_decrypt() -> None:
    key = get_key()
    for name in PROTECTED_DATA_FILES:
        encrypted_path = _resolve(name) + ENCRYPTED_SUFFIX
        if not os.path.exists(encrypted_path):
            print(f"[MISSING]   {name}{ENCRYPTED_SUFFIX}")
            continue
        decrypt_file(encrypted_path, key)
        print(f"[decrypted] {name}{ENCRYPTED_SUFFIX} -> {name}")


def cmd_status() -> None:
    print(f"key file: {DEFAULT_KEY_PATH} "
          f"({'present' if os.path.exists(DEFAULT_KEY_PATH) else 'MISSING'})")
    for name in PROTECTED_DATA_FILES:
        path = _resolve(name)
        enc = "yes" if os.path.exists(path + ENCRYPTED_SUFFIX) else "no "
        plain = "YES (readable!)" if os.path.exists(path) else "no"
        print(f"  encrypted: {enc}   plaintext: {plain:<15} {name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--init", action="store_true", help="generate the encryption key")
    group.add_argument("--encrypt", action="store_true", help="encrypt the protected files")
    group.add_argument("--decrypt", action="store_true", help="decrypt the protected files")
    group.add_argument("--status", action="store_true", help="show the state of each file")
    parser.add_argument("--remove-plaintext", action="store_true",
                        help="with --encrypt: delete the readable CSV after encrypting")
    args = parser.parse_args()

    if args.init:
        init_key()
    elif args.encrypt:
        cmd_encrypt(args.remove_plaintext)
    elif args.decrypt:
        cmd_decrypt()
    else:
        cmd_status()


if __name__ == "__main__":
    main()
