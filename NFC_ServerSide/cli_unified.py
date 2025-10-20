#!/usr/bin/env python3
"""
Unified Interactive CLI for ICA Project.
Manages NFC UIDs, user accounts, and camera IP addresses.

Run with Python:
    python3 cli_unified.py

Environment variables:
- ICA_DB_PATH: path to unified SQLite database file (default: ../ica_unified.db)
"""

from __future__ import annotations

import os
import sys
from typing import Optional

# Add parent directory to path to import unified_db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import unified_db


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


def prompt_user_id() -> Optional[int]:
    try:
        user_id = int(input("Enter user ID: ").strip())
        return user_id
    except ValueError:
        print("User ID must be a number.")
        return None


def prompt_camera_ip(default: str = "") -> str:
    return input(f"Enter camera IP/URL [{default}]: ").strip() or default


# NFC Card Management Functions
def action_list_cards() -> None:
    clear_screen()
    print("Current NFC Cards:\n")
    try:
        records = unified_db.list_cards()
        if not records:
            print("(no records)")
        else:
            print("UID\t\t\tUSER_ID\tROLE\tNOTE")
            print("-" * 60)
            for r in records:
                user_info = f"{r.id_usuario}" if r.id_usuario else "None"
                print(f"{r.uid}\t{user_info}\t\t{r.role}\t{r.note}")
    except Exception as e:
        print(f"Error listing cards: {e}")
    print()
    pause()


def action_add_card() -> None:
    clear_screen()
    print("Add or update NFC card:\n")
    uid = prompt_uid()
    if not uid:
        pause()
        return
    role = prompt_role()
    if role is None:
        pause()
        return
    note = prompt_note()
    
    # Ask for user association (optional)
    print("\nAssociate with user? (optional)")
    associate = input("Enter user ID (or press Enter to skip): ").strip()
    user_id = int(associate) if associate.isdigit() else None
    
    try:
        unified_db.upsert_card(uid=uid, role=role, note=note, id_usuario=user_id)
        print("Card saved successfully.")
    except Exception as e:
        print(f"Error saving card: {e}")
    pause()


def action_edit_card() -> None:
    clear_screen()
    print("Edit existing NFC card:\n")
    uid = prompt_uid()
    if not uid:
        pause()
        return
    
    try:
        rec = unified_db.get_card(uid)
        if not rec:
            print("Card not found.")
            pause()
            return
        
        print(f"Current card: UID={rec.uid}, Role={rec.role}, Note={rec.note}, User={rec.id_usuario}")
        
        role = prompt_role(default=rec.role)
        if role is None:
            pause()
            return
        note = prompt_note(default=rec.note)
        
        # Ask for user association update
        print(f"\nCurrent user association: {rec.id_usuario}")
        associate = input("Enter new user ID (or press Enter to keep current): ").strip()
        user_id = int(associate) if associate.isdigit() else rec.id_usuario
        
        unified_db.upsert_card(uid=uid, role=role, note=note, id_usuario=user_id)
        print("Card updated successfully.")
    except Exception as e:
        print(f"Error updating card: {e}")
    pause()


def action_delete_card() -> None:
    clear_screen()
    print("Delete NFC card:\n")
    uid = prompt_uid()
    if not uid:
        pause()
        return
    
    try:
        removed = unified_db.delete_card(uid)
        print("Card deleted." if removed else "Card not found.")
    except Exception as e:
        print(f"Error deleting card: {e}")
    pause()


def action_lookup_card() -> None:
    clear_screen()
    print("Lookup NFC card:\n")
    uid = prompt_uid()
    if not uid:
        pause()
        return
    
    try:
        rec = unified_db.get_card(uid)
        if not rec:
            print("Card not found - Access denied.")
        else:
            print(f"Access granted - Role: {rec.role}, Note: {rec.note}")
            if rec.id_usuario:
                user = unified_db.get_user_by_id(rec.id_usuario)
                if user:
                    print(f"Associated user: {user.nombre} ({user.correo})")
    except Exception as e:
        print(f"Error looking up card: {e}")
    pause()


# User Management Functions
def action_list_users() -> None:
    clear_screen()
    print("Current Users:\n")
    try:
        users = unified_db.list_users()
        if not users:
            print("(no users)")
        else:
            print("ID\tNAME\t\tEMAIL\t\t\t\tROLE\t\tCAMERA IP")
            print("-" * 90)
            for u in users:
                camera_ip = u.ip_camara if u.ip_camara else "None"
                print(f"{u.id_usuario}\t{u.nombre}\t\t{u.correo}\t\t{u.rol}\t\t{camera_ip}")
    except Exception as e:
        print(f"Error listing users: {e}")
    print()
    pause()


def action_add_user() -> None:
    clear_screen()
    print("Add new user:\n")
    
    nombre = input("Enter name: ").strip()
    if not nombre:
        print("Name is required.")
        pause()
        return
    
    correo = input("Enter email: ").strip()
    if not correo:
        print("Email is required.")
        pause()
        return
    
    rol = input("Enter role: ").strip()
    if not rol:
        print("Role is required.")
        pause()
        return
    
    ip_camara = input("Enter camera IP/URL (optional): ").strip() or None
    
    try:
        user_id = unified_db.create_user(nombre, correo, rol, ip_camara)
        print(f"User created successfully with ID: {user_id}")
    except Exception as e:
        print(f"Error creating user: {e}")
    pause()


def action_edit_user() -> None:
    clear_screen()
    print("Edit existing user:\n")
    user_id = prompt_user_id()
    if not user_id:
        pause()
        return
    
    try:
        user = unified_db.get_user_by_id(user_id)
        if not user:
            print("User not found.")
            pause()
            return
        
        print(f"Current user: {user.nombre} ({user.correo}) - {user.rol}")
        print(f"Current camera IP: {user.ip_camara or 'None'}")
        
        nombre = input(f"Enter new name [{user.nombre}]: ").strip() or user.nombre
        correo = input(f"Enter new email [{user.correo}]: ").strip() or user.correo
        rol = input(f"Enter new role [{user.rol}]: ").strip() or user.rol
        ip_camara = input(f"Enter new camera IP [{user.ip_camara or 'None'}]: ").strip()
        if ip_camara == "None" or not ip_camara:
            ip_camara = None
        
        success = unified_db.update_user(user_id, nombre, correo, rol, ip_camara)
        if success:
            print("User updated successfully.")
        else:
            print("Failed to update user.")
    except Exception as e:
        print(f"Error updating user: {e}")
    pause()


def action_delete_user() -> None:
    clear_screen()
    print("Delete user:\n")
    user_id = prompt_user_id()
    if not user_id:
        pause()
        return
    
    try:
        user = unified_db.get_user_by_id(user_id)
        if not user:
            print("User not found.")
            pause()
            return
        
        print(f"Warning: This will delete user '{user.nombre}' and all associated cards.")
        confirm = input("Are you sure? (yes/no): ").strip().lower()
        if confirm == "yes":
            success = unified_db.delete_user(user_id)
            if success:
                print("User deleted successfully.")
            else:
                print("Failed to delete user.")
        else:
            print("Deletion cancelled.")
    except Exception as e:
        print(f"Error deleting user: {e}")
    pause()


# Camera Management Functions
def action_list_cameras() -> None:
    clear_screen()
    print("Current Cameras:\n")
    try:
        users = unified_db.list_users()
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
        users = unified_db.list_users()
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
        
        user = unified_db.get_user_by_id(user_id)
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
        
        success = unified_db.update_user(user_id, ip_camara=new_ip)
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
        users = unified_db.list_users()
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
        
        user = unified_db.get_user_by_id(user_id)
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
        
        success = unified_db.update_user(user_id, ip_camara=camera_ip)
        if success:
            print(f"Camera added successfully for {user.nombre}: {camera_ip}")
        else:
            print("Failed to add camera.")
    except Exception as e:
        print(f"Error adding camera: {e}")
    pause()


def action_remove_camera() -> None:
    clear_screen()
    print("Remove Camera from User:\n")
    
    try:
        users = unified_db.list_users()
        cameras = [u for u in users if u.ip_camara]
        
        if not cameras:
            print("No cameras currently configured.")
            pause()
            return
        
        print("Users with cameras:")
        for cam in cameras:
            print(f"  {cam.id_usuario}: {cam.nombre} - {cam.ip_camara}")
        print()
        
        user_id = prompt_user_id()
        if not user_id:
            pause()
            return
        
        user = unified_db.get_user_by_id(user_id)
        if not user:
            print("User not found.")
            pause()
            return
        
        if not user.ip_camara:
            print(f"User {user.nombre} doesn't have a camera configured.")
            pause()
            return
        
        print(f"Remove camera from {user.nombre}?")
        print(f"Current camera IP: {user.ip_camara}")
        confirm = input("Are you sure? (yes/no): ").strip().lower()
        if confirm == "yes":
            success = unified_db.update_user(user_id, ip_camara=None)
            if success:
                print("Camera removed successfully.")
            else:
                print("Failed to remove camera.")
        else:
            print("Camera removal cancelled.")
    except Exception as e:
        print(f"Error removing camera: {e}")
    pause()


def main_menu() -> None:
    # Set default database path
    db_path = os.environ.get("ICA_DB_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ica_unified.db"))
    
    try:
        unified_db.initialize_database(db_path)
    except Exception as e:
        print(f"Error initializing database: {e}")
        return
    
    while True:
        clear_screen()
        print("ICA Unified Management CLI")
        print("Database:", db_path)
        print("\nSelect a category:")
        print("  NFC CARDS:")
        print("    1) List NFC Cards")
        print("    2) Add NFC Card")
        print("    3) Edit NFC Card")
        print("    4) Delete NFC Card")
        print("    5) Lookup NFC Card")
        print("\n  USERS:")
        print("    6) List Users")
        print("    7) Add User")
        print("    8) Edit User")
        print("    9) Delete User")
        print("\n  CAMERAS:")
        print("   10) List Cameras")
        print("   11) Update Camera IP")
        print("   12) Add Camera to User")
        print("   13) Remove Camera from User")
        print("\n    0) Exit")
        
        choice = input("\nEnter choice: ").strip()
        
        if choice == "1":
            action_list_cards()
        elif choice == "2":
            action_add_card()
        elif choice == "3":
            action_edit_card()
        elif choice == "4":
            action_delete_card()
        elif choice == "5":
            action_lookup_card()
        elif choice == "6":
            action_list_users()
        elif choice == "7":
            action_add_user()
        elif choice == "8":
            action_edit_user()
        elif choice == "9":
            action_delete_user()
        elif choice == "10":
            action_list_cameras()
        elif choice == "11":
            action_update_camera_ip()
        elif choice == "12":
            action_add_camera()
        elif choice == "13":
            action_remove_camera()
        elif choice == "0":
            print("Goodbye!")
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

