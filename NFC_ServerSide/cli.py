#!/usr/bin/env python3
"""
Interactive CLI to manage NFC UIDs and role levels.
Updated to work with unified database.

Run with Python in a bash shell:
    python3 cli.py

Environment variables:
- ICA_DB_PATH: path to unified SQLite database file (default: ../ica_unified.db)
"""

from __future__ import annotations

import os
import sys
from typing import Optional

# Add parent directory to path to import unified_db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import unified_db as db_utils


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


def prompt_user_id() -> Optional[int]:
    try:
        user_id = int(input("Enter user ID: ").strip())
        return user_id
    except ValueError:
        print("User ID must be a number.")
        return None


def prompt_camera_ip(default: str = "") -> str:
    return input(f"Enter camera IP/URL [{default}]: ").strip() or default


def action_list_cameras() -> None:
    clear_screen()
    print("Current Cameras:\n")
    try:
        users = db_utils.list_users()
        cameras = [u for u in users if u.ip_camara]
        
        if not cameras:
            print("(no cameras configured)")
        else:
            print("USER_ID\tNAME\t\tCAMERA IP/URL")
            print("-" * 60)
            for cam in cameras:
                print(f"{cam.id_usuario}\t{cam.nombre}\t\t{cam.ip_camara}")
    except Exception as e:
        print(f"Error listing cameras: {e}")
    print()
    pause()


def action_update_camera_ip() -> None:
    clear_screen()
    print("Update Camera IP Address:\n")
    
    # List current cameras
    try:
        users = db_utils.list_users()
        cameras = [u for u in users if u.ip_camara]
        
        if not cameras:
            print("No cameras currently configured.")
            pause()
            return
        
        print("Current cameras:")
        for cam in cameras:
            print(f"  {cam.id_usuario}: {cam.nombre} - {cam.ip_camara}")
        print()
        
        user_id = prompt_user_id()
        if not user_id:
            pause()
            return
        
        user = db_utils.get_user_by_id(user_id)
        if not user:
            print("User not found.")
            pause()
            return
        
        print(f"\nUpdating camera for: {user.nombre}")
        print(f"Current IP: {user.ip_camara or 'None'}")
        
        new_ip = prompt_camera_ip(user.ip_camara or "")
        if not new_ip:
            print("Camera IP cannot be empty.")
            pause()
            return
        
        success = db_utils.update_user(user_id, ip_camara=new_ip)
        if success:
            print(f"Camera IP updated successfully: {new_ip}")
        else:
            print("Failed to update camera IP.")
    except Exception as e:
        print(f"Error updating camera IP: {e}")
    pause()


def action_add_camera() -> None:
    clear_screen()
    print("Add Camera to User:\n")
    
    # List users without cameras
    try:
        users = db_utils.list_users()
        users_without_cameras = [u for u in users if not u.ip_camara]
        
        if not users_without_cameras:
            print("All users already have cameras configured.")
            pause()
            return
        
        print("Users without cameras:")
        for u in users_without_cameras:
            print(f"  {u.id_usuario}: {u.nombre} ({u.correo})")
        print()
        
        user_id = prompt_user_id()
        if not user_id:
            pause()
            return
        
        user = db_utils.get_user_by_id(user_id)
        if not user:
            print("User not found.")
            pause()
            return
        
        if user.ip_camara:
            print(f"User {user.nombre} already has a camera configured: {user.ip_camara}")
            update = input("Update existing camera? (yes/no): ").strip().lower()
            if update != "yes":
                pause()
                return
        
        camera_ip = prompt_camera_ip()
        if not camera_ip:
            print("Camera IP is required.")
            pause()
            return
        
        success = db_utils.update_user(user_id, ip_camara=camera_ip)
        if success:
            print(f"Camera added successfully for {user.nombre}: {camera_ip}")
        else:
            print("Failed to add camera.")
    except Exception as e:
        print(f"Error adding camera: {e}")
    pause()


def main_menu() -> None:
    # Set default database path to unified database
    db_path = os.environ.get("ICA_DB_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ica_unified.db"))
    
    try:
        db_utils.initialize_database(db_path)
    except Exception as e:
        print(f"Error initializing database: {e}")
        return
    
    while True:
        clear_screen()
        print("ICA Unified Management CLI")
        print("Database:", db_path)
        print("\nSelect an option:")
        print("  NFC CARDS:")
        print("    1) List UIDs")
        print("    2) Add UID")
        print("    3) Edit UID")
        print("    4) Delete UID")
        print("    5) Lookup UID")
        print("\n  CAMERAS:")
        print("    6) List Cameras")
        print("    7) Update Camera IP")
        print("    8) Add Camera to User")
        print("\n    0) Exit")
        choice = input("\nEnter choice: ").strip()
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
        elif choice == "6":
            action_list_cameras()
        elif choice == "7":
            action_update_camera_ip()
        elif choice == "8":
            action_add_camera()
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


