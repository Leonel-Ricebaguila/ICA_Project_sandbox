"""
CLI Command Additions for NFC Management

These functions should be ADDED to app/cli.py

They provide command-line utilities for:
- Registering NFC devices
- Assigning NFC cards to users
- Listing NFC devices
- Revoking NFC cards

Instructions:
1. Open app/cli.py in IAM_Backend
2. Add these functions at the end of the file
3. Register them with your CLI framework (Click, argparse, etc.)
"""

# ============================================================
# IMPORTS (add these if not already present)
# ============================================================

"""
Add these imports to the top of app/cli.py if not already there:
"""

import secrets
import hashlib
from .models import Usuario, NFCDevice
from .db import SessionLocal
from .time_utils import now_cst


# ============================================================
# CLI FUNCTIONS TO ADD
# ============================================================

def register_nfc_device(name: str, location: str = ""):
    """
    Register a new NFC device and generate credentials
    
    Usage:
        python -m app.cli register-nfc-device --name "Reader 1" --location "Main Entrance"
    
    Returns:
        (device_id, device_secret) tuple
    """
    # Generate unique device ID
    device_id = f"NFC-READER-{secrets.randbelow(1000):03d}"
    device_secret = secrets.token_urlsafe(32)
    
    db = SessionLocal()
    try:
        # Check if device_id already exists (unlikely but possible)
        existing = db.query(NFCDevice).filter(NFCDevice.device_id == device_id).first()
        if existing:
            # Try again with different number
            device_id = f"NFC-READER-{secrets.randbelow(9999):04d}"
        
        # Create device
        device = NFCDevice(
            device_id=device_id,
            name=name,
            location=location,
            device_secret=device_secret,
            status="pending",  # Will become "active" after first successful auth
            registered_at=now_cst()
        )
        db.add(device)
        db.commit()
        
        print("=" * 60)
        print("✅ NFC Device Registered Successfully!")
        print("=" * 60)
        print(f"Device ID:     {device_id}")
        print(f"Device Secret: {device_secret}")
        print(f"Name:          {name}")
        print(f"Location:      {location}")
        print("=" * 60)
        print("⚠️  IMPORTANT: Save these credentials securely!")
        print("   They cannot be retrieved later.")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Enter these credentials in the Android app")
        print("2. Activate the device (it will change to 'active' on first auth)")
        print("3. Assign NFC cards to users")
        print("=" * 60)
        
        return device_id, device_secret
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error registering device: {e}")
        return None, None
    finally:
        db.close()


def assign_nfc_card(user_uid: str, nfc_uid: str = None):
    """
    Assign NFC card to user
    
    Usage:
        # Interactive mode (prompts for card tap):
        python -m app.cli assign-nfc --uid EMP-001
        
        # Direct mode (provide UID):
        python -m app.cli assign-nfc --uid EMP-001 --nfc-uid 04A3B2C1D4E5F6
    
    Returns:
        bool: True if successful
    """
    db = SessionLocal()
    try:
        # Find user
        user = db.query(Usuario).filter(Usuario.uid == user_uid).first()
        
        if not user:
            print(f"❌ Error: User '{user_uid}' not found")
            print(f"\nAvailable users:")
            users = db.query(Usuario).limit(10).all()
            for u in users:
                print(f"  - {u.uid}: {u.nombre} {u.apellido} ({u.email})")
            return False
        
        # If NFC UID not provided, prompt user to scan card
        if not nfc_uid:
            print("=" * 60)
            print(f"👤 Assigning NFC card to:")
            print(f"   UID:   {user.uid}")
            print(f"   Name:  {user.nombre} {user.apellido}")
            print(f"   Email: {user.email}")
            print(f"   Role:  {user.rol}")
            print("=" * 60)
            print("📱 Please tap NFC card on reader...")
            print("   (or type 'cancel' to abort)")
            print("=" * 60)
            
            nfc_uid = input("Enter NFC UID: ").strip()
            
            if nfc_uid.lower() in ['cancel', 'exit', 'quit', '']:
                print("❌ Cancelled")
                return False
        
        # Remove any separators from UID (colons, spaces, dashes)
        nfc_uid = nfc_uid.replace(':', '').replace(' ', '').replace('-', '').upper()
        
        # Validate UID format (should be hex)
        try:
            int(nfc_uid, 16)
        except ValueError:
            print(f"❌ Error: Invalid NFC UID format (must be hexadecimal)")
            print(f"   Provided: {nfc_uid}")
            return False
        
        # Check if NFC UID is already assigned to another user
        existing = db.query(Usuario).filter(Usuario.nfc_uid == nfc_uid).first()
        if existing and existing.uid != user_uid:
            print(f"❌ Error: NFC UID already assigned to user '{existing.uid}'")
            print(f"   User: {existing.nombre} {existing.apellido}")
            print(f"\n   To reassign:")
            print(f"   1. Revoke from {existing.uid}: python -m app.cli revoke-nfc --uid {existing.uid}")
            print(f"   2. Then assign to {user_uid}")
            return False
        
        # Assign NFC card
        user.nfc_uid = nfc_uid
        user.nfc_uid_hash = hashlib.sha256(nfc_uid.encode()).hexdigest()
        user.nfc_card_id = nfc_uid  # Can be customized to physical card ID
        user.nfc_status = "active"
        user.nfc_issued_at = now_cst()
        user.nfc_revoked_at = None  # Clear any previous revocation
        
        db.commit()
        
        print("=" * 60)
        print("✅ NFC Card Assigned Successfully!")
        print("=" * 60)
        print(f"User:        {user.uid} ({user.nombre} {user.apellido})")
        print(f"NFC UID:     {nfc_uid}")
        print(f"Card ID:     {user.nfc_card_id}")
        print(f"Status:      {user.nfc_status}")
        print(f"Issued at:   {user.nfc_issued_at}")
        print("=" * 60)
        print("\n✅ User can now use this card at NFC readers")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error assigning NFC card: {e}")
        return False
    finally:
        db.close()


def list_nfc_devices():
    """
    List all registered NFC devices
    
    Usage:
        python -m app.cli list-nfc-devices
    """
    db = SessionLocal()
    try:
        devices = db.query(NFCDevice).all()
        
        if not devices:
            print("No NFC devices registered")
            print("\nTo register a device:")
            print("  python -m app.cli register-nfc-device --name 'Device Name' --location 'Location'")
            return
        
        print("\n" + "=" * 100)
        print("NFC DEVICES")
        print("=" * 100)
        print(f"{'ID':<5} {'Device ID':<20} {'Name':<30} {'Status':<10} {'Location':<20} {'Last Seen'}")
        print("-" * 100)
        
        for device in devices:
            last_seen = device.last_seen.strftime("%Y-%m-%d %H:%M") if device.last_seen else "Never"
            location = (device.location or "")[:20]
            name = (device.name or "")[:30]
            
            # Color-code status
            status_icon = {
                "active": "✅",
                "pending": "⏳",
                "inactive": "❌",
                "error": "⚠️"
            }.get(device.status, "❓")
            
            print(f"{device.id:<5} {device.device_id:<20} {name:<30} {status_icon} {device.status:<8} {location:<20} {last_seen}")
        
        print("=" * 100)
        print(f"Total devices: {len(devices)}")
        
        # Show stats
        active_count = sum(1 for d in devices if d.status == "active")
        pending_count = sum(1 for d in devices if d.status == "pending")
        
        print(f"Active: {active_count} | Pending: {pending_count}")
        print("=" * 100)
        
    except Exception as e:
        print(f"❌ Error listing devices: {e}")
    finally:
        db.close()


def revoke_nfc_card(user_uid: str):
    """
    Revoke NFC card from user
    
    Usage:
        python -m app.cli revoke-nfc --uid EMP-001
    
    Returns:
        bool: True if successful
    """
    db = SessionLocal()
    try:
        user = db.query(Usuario).filter(Usuario.uid == user_uid).first()
        
        if not user:
            print(f"❌ Error: User '{user_uid}' not found")
            return False
        
        if not user.nfc_uid:
            print(f"⚠️  User '{user_uid}' does not have an NFC card assigned")
            return False
        
        print("=" * 60)
        print(f"⚠️  REVOKING NFC CARD")
        print("=" * 60)
        print(f"User:        {user.uid} ({user.nombre} {user.apellido})")
        print(f"NFC UID:     {user.nfc_uid}")
        print(f"Current Status: {user.nfc_status}")
        print("=" * 60)
        
        confirm = input("Are you sure? (yes/no): ").strip().lower()
        
        if confirm not in ['yes', 'y']:
            print("❌ Cancelled")
            return False
        
        # Revoke card (keep UID for records, but mark as revoked)
        user.nfc_status = "revoked"
        user.nfc_revoked_at = now_cst()
        
        db.commit()
        
        print("=" * 60)
        print("✅ NFC Card Revoked Successfully!")
        print("=" * 60)
        print(f"User:        {user.uid}")
        print(f"NFC UID:     {user.nfc_uid}")
        print(f"Status:      {user.nfc_status}")
        print(f"Revoked at:  {user.nfc_revoked_at}")
        print("=" * 60)
        print("\n⚠️  User can NO LONGER use this card at NFC readers")
        print("\nTo re-activate this card:")
        print(f"  python -m app.cli activate-nfc --uid {user_uid}")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error revoking NFC card: {e}")
        return False
    finally:
        db.close()


def activate_nfc_card(user_uid: str):
    """
    Re-activate a revoked NFC card
    
    Usage:
        python -m app.cli activate-nfc --uid EMP-001
    
    Returns:
        bool: True if successful
    """
    db = SessionLocal()
    try:
        user = db.query(Usuario).filter(Usuario.uid == user_uid).first()
        
        if not user:
            print(f"❌ Error: User '{user_uid}' not found")
            return False
        
        if not user.nfc_uid:
            print(f"⚠️  User '{user_uid}' does not have an NFC card assigned")
            return False
        
        if user.nfc_status == "active":
            print(f"ℹ️  NFC card for user '{user_uid}' is already active")
            return True
        
        # Reactivate card
        user.nfc_status = "active"
        user.nfc_revoked_at = None
        
        db.commit()
        
        print("=" * 60)
        print("✅ NFC Card Reactivated Successfully!")
        print("=" * 60)
        print(f"User:        {user.uid} ({user.nombre} {user.apellido})")
        print(f"NFC UID:     {user.nfc_uid}")
        print(f"Status:      {user.nfc_status}")
        print("=" * 60)
        print("\n✅ User can now use this card at NFC readers")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error activating NFC card: {e}")
        return False
    finally:
        db.close()


def list_nfc_users():
    """
    List all users with NFC cards assigned
    
    Usage:
        python -m app.cli list-nfc-users
    """
    db = SessionLocal()
    try:
        users = db.query(Usuario).filter(Usuario.nfc_uid.isnot(None)).all()
        
        if not users:
            print("No users with NFC cards assigned")
            print("\nTo assign a card:")
            print("  python -m app.cli assign-nfc --uid EMP-001")
            return
        
        print("\n" + "=" * 120)
        print("USERS WITH NFC CARDS")
        print("=" * 120)
        print(f"{'UID':<15} {'Name':<30} {'Email':<30} {'NFC UID':<20} {'Status':<10} {'Issued'}")
        print("-" * 120)
        
        for user in users:
            name = f"{user.nombre} {user.apellido}"[:30]
            email = (user.email or "")[:30]
            nfc_uid = (user.nfc_uid or "")[:20]
            issued = user.nfc_issued_at.strftime("%Y-%m-%d") if user.nfc_issued_at else ""
            
            # Color-code status
            status_icon = {
                "active": "✅",
                "inactive": "⏸️",
                "revoked": "❌",
                "lost": "⚠️"
            }.get(user.nfc_status, "❓")
            
            print(f"{user.uid:<15} {name:<30} {email:<30} {nfc_uid:<20} {status_icon} {user.nfc_status:<8} {issued}")
        
        print("=" * 120)
        print(f"Total users with NFC cards: {len(users)}")
        
        # Show stats
        active_count = sum(1 for u in users if u.nfc_status == "active")
        revoked_count = sum(1 for u in users if u.nfc_status == "revoked")
        
        print(f"Active: {active_count} | Revoked: {revoked_count}")
        print("=" * 120)
        
    except Exception as e:
        print(f"❌ Error listing users: {e}")
    finally:
        db.close()


# ============================================================
# EXAMPLE CLI INTEGRATION (using Click framework)
# ============================================================

"""
If your cli.py uses Click, add these command definitions:

import click

@click.command()
@click.option('--name', required=True, help='Device name')
@click.option('--location', default='', help='Device location')
def register_nfc_device_cmd(name, location):
    register_nfc_device(name, location)

@click.command()
@click.option('--uid', required=True, help='User UID')
@click.option('--nfc-uid', default=None, help='NFC card UID (optional, will prompt if not provided)')
def assign_nfc_cmd(uid, nfc_uid):
    assign_nfc_card(uid, nfc_uid)

@click.command()
def list_nfc_devices_cmd():
    list_nfc_devices()

@click.command()
@click.option('--uid', required=True, help='User UID')
def revoke_nfc_cmd(uid):
    revoke_nfc_card(uid)

@click.command()
@click.option('--uid', required=True, help='User UID')
def activate_nfc_cmd(uid):
    activate_nfc_card(uid)

@click.command()
def list_nfc_users_cmd():
    list_nfc_users()

# Then register these commands in your CLI group
"""

# ============================================================
# USAGE EXAMPLES
# ============================================================

"""
After adding these functions to cli.py:

# Register new NFC device
python -m app.cli register-nfc-device --name "Entrance Reader" --location "Building A"

# List all NFC devices
python -m app.cli list-nfc-devices

# Assign NFC card to user (interactive)
python -m app.cli assign-nfc --uid EMP-001

# Assign NFC card to user (direct)
python -m app.cli assign-nfc --uid EMP-001 --nfc-uid 04A3B2C1D4E5F6

# List all users with NFC cards
python -m app.cli list-nfc-users

# Revoke NFC card
python -m app.cli revoke-nfc --uid EMP-001

# Reactivate NFC card
python -m app.cli activate-nfc --uid EMP-001
"""


