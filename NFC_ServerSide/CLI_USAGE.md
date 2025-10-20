# ICA Unified CLI Usage Guide

The CLI has been updated to work with the unified database and includes camera IP management functionality.

## 🚀 Quick Start

### Running the CLI

```bash
# From the NFC_ServerSide directory
python cli.py

# Or use the enhanced unified CLI
python cli_unified.py
```

## 📋 Available Commands

### NFC Card Management
- **List UIDs** - Show all NFC cards in the system
- **Add UID** - Add a new NFC card
- **Edit UID** - Modify an existing NFC card
- **Delete UID** - Remove an NFC card
- **Lookup UID** - Check if a card has access

### Camera Management (NEW!)
- **List Cameras** - Show all users with configured cameras
- **Update Camera IP** - Change the IP address of a user's camera
- **Add Camera to User** - Assign a camera to a user who doesn't have one

## 🎯 Camera IP Management

### Method 1: Using the CLI (Recommended)

1. **Start the CLI**:
   ```bash
   python cli.py
   ```

2. **List current cameras**:
   - Select option `6` to see all configured cameras
   - This shows: User ID, Name, and Current Camera IP

3. **Update a camera IP**:
   - Select option `7` to update camera IP
   - Enter the User ID of the person whose camera you want to update
   - Enter the new camera IP/URL

4. **Add camera to a user**:
   - Select option `8` to add a camera to a user
   - Choose from users who don't have cameras yet
   - Enter the camera IP/URL

### Method 2: Direct Database Access

```bash
# View current camera IPs
sqlite3 ../ica_unified.db "SELECT id_usuario, nombre, ip_camara FROM usuarios WHERE ip_camara IS NOT NULL;"

# Update a specific user's camera IP
sqlite3 ../ica_unified.db "UPDATE usuarios SET ip_camara = 'http://192.168.1.100:8080/video' WHERE id_usuario = 1;"
```

### Method 3: Using Python Script

```python
import sys
sys.path.append('..')
import unified_db

# Update camera IP for user ID 1
unified_db.update_user(1, ip_camara="http://192.168.1.100:8080/video")
```

## 🔧 Common Camera IP Formats

- **HTTP Stream**: `http://192.168.1.100:8080/video`
- **HTTPS Stream**: `https://192.168.1.100:8080/video`
- **RTSP Stream**: `rtsp://192.168.1.100:554/stream`
- **MJPEG Stream**: `http://192.168.1.100:8080/mjpeg`

## 📊 Example Workflow

1. **Check current cameras**:
   ```
   Select option 6: List Cameras
   Output:
   USER_ID  NAME    CAMERA IP/URL
   1        Nico    https://192.168.100.25:8080/video
   2        Diego   https://192.168.100.31:8080/video
   ```

2. **Update Nico's camera IP**:
   ```
   Select option 7: Update Camera IP
   Enter user ID: 1
   Enter new IP: http://192.168.1.100:8080/video
   ```

3. **Verify the update**:
   ```
   Select option 6: List Cameras
   Output:
   USER_ID  NAME    CAMERA IP/URL
   1        Nico    http://192.168.1.100:8080/video
   2        Diego   https://192.168.100.31:8080/video
   ```

## ⚠️ Important Notes

- **Database Path**: The CLI automatically uses the unified database (`../ica_unified.db`)
- **User IDs**: You need to know the User ID to update camera IPs
- **IP Format**: Include the full URL with protocol (http:// or https://)
- **Testing**: Always test camera connections after updating IPs
- **Backup**: Consider backing up the database before making changes

## 🐛 Troubleshooting

### Common Issues

1. **"User not found"**:
   - Check that the User ID exists
   - Use option 6 to list all users and their IDs

2. **"No cameras currently configured"**:
   - No users have camera IPs set
   - Use option 8 to add cameras to users

3. **"Failed to update camera IP"**:
   - Check database permissions
   - Ensure the database file exists and is accessible

### Debug Mode

Set environment variable for more detailed output:
```bash
set ICA_DB_PATH=C:\path\to\ica_unified.db
python cli.py
```

## 🔄 Integration with Server

The CLI works alongside the Flask server:
- **Server running**: CLI can be used while server is active
- **Database sharing**: Both use the same unified database
- **Real-time updates**: Changes made in CLI are immediately available to the server
- **Logging**: Server logs all database changes made through CLI

## 📝 Environment Variables

- `ICA_DB_PATH`: Path to the unified database (default: `../ica_unified.db`)
- `HOST`: Server host (for server integration)
- `PORT`: Server port (for server integration)

