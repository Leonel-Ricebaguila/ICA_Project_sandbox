#!/usr/bin/env python3
"""
Interactive CLI to manage NFC UIDs and role levels.

Run with Python in a bash shell:
    python3 cli.py

Environment variables:
- NFC_DB_PATH: path to SQLite database file (default: ./data.db)
"""

from __future__ import annotations

import os
import sys
from typing import Optional

import db as db_utils


def clear_screen() -> None:
    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")


def pause(msg: str = "Press Enter to continue...") -> None:
    try:
        input(msg)
    except EOFError:
        pass


def prompt_uid(default: Optional[str] = None) -> Optional[str]:
    uid = input(f"Enter UID{f' [{default}]' if default else ''}: ").strip() or (default or "")
    if not uid:
        print("UID cannot be empty.")
        return None
    return uid


def prompt_role(default: Optional[int] = None) -> Optional[int]:
    role_str = input(f"Enter role (integer){f' [{default}]' if default is not None else ''}: ").strip()
    if not role_str and default is not None:
        return default
    try:
        return int(role_str)
    except ValueError:
        print("Role must be an integer.")
        return None


def prompt_note(default: str = "") -> str:
    return input(f"Enter note [{default}]: ").strip() or default


def action_list() -> None:
    clear_screen()
    print("Current cards:\n")
    records = db_utils.list_cards()
    if not records:
        print("(no records)")
    else:
        print("UID\tROLE\tNOTE")
        for r in records:
            print(f"{r.uid}\t{r.role}\t{r.note}")
    print()
    pause()


def action_add() -> None:
    clear_screen()
    print("Add or update card:\n")
    uid = prompt_uid()
    if not uid:
        pause()
        return
    role = prompt_role()
    if role is None:
        pause()
        return
    note = prompt_note()
    db_utils.upsert_card(uid=uid, role=role, note=note)
    print("Saved.")
    pause()


def action_edit() -> None:
    clear_screen()
    print("Edit existing card:\n")
    uid = prompt_uid()
    if not uid:
        pause()
        return
    rec = db_utils.get_card(uid)
    if not rec:
        print("Record not found.")
        pause()
        return
    role = prompt_role(default=rec.role)
    if role is None:
        pause()
        return
    note = prompt_note(default=rec.note)
    db_utils.upsert_card(uid=uid, role=role, note=note)
    print("Updated.")
    pause()


def action_delete() -> None:
    clear_screen()
    print("Delete card:\n")
    uid = prompt_uid()
    if not uid:
        pause()
        return
    removed = db_utils.delete_card(uid)
    print("Deleted." if removed else "Not found.")
    pause()


def action_lookup() -> None:
    clear_screen()
    print("Lookup card:\n")
    uid = prompt_uid()
    if not uid:
        pause()
        return
    rec = db_utils.get_card(uid)
    if not rec:
        print("Not allowed.")
    else:
        print(f"Allowed. Role={rec.role}, Note={rec.note}")
    pause()


def main_menu() -> None:
    db_utils.initialize_database()
    while True:
        clear_screen()
        print("NFC Access Control - CLI")
        print("DB:", os.environ.get("NFC_DB_PATH", os.path.join(os.getcwd(), "data.db")))
        print("\nSelect an option:")
        print("  1) List UIDs")
        print("  2) Add UID")
        print("  3) Edit UID")
        print("  4) Delete UID")
        print("  5) Lookup UID")
        print("  0) Exit")
        choice = input("Enter choice: ").strip()
        if choice == "1":
            action_list()
        elif choice == "2":
            action_add()
        elif choice == "3":
            action_edit()
        elif choice == "4":
            action_delete()
        elif choice == "5":
            action_lookup()
        elif choice == "0":
            print("Bye.")
            return
        else:
            print("Invalid choice.")
            pause()


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)


