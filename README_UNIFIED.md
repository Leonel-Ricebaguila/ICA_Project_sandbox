# ICA Project - Unified System

This is the unified version of the ICA (Identity and Access Control) project that combines user management, NFC card management, and camera monitoring into a single integrated system.

## 🏗️ System Architecture

The unified system consists of:

1. **Unified Database** (`ica_unified.db`) - Single SQLite database containing:
   - `usuarios` table - User information and camera assignments
   - `cards` table - NFC card management with user associations

2. **Unified Server** (`NFC_ServerSide/server_unified.py`) - Flask API server providing:
   - User management endpoints
   - Camera management endpoints  
   - NFC card management endpoints
   - Comprehensive logging

3. **Unified Camera Client** (`camaras_unified.py`) - Camera monitoring system that:
   - Connects to server API instead of direct database access
   - Displays multiple camera streams
   - Provides screenshot functionality
   - Shows user information overlays

## 📁 File Structure

```
ICA_Project_sandbox/
├── ica_unified.db                 # Unified database
├── unified_db.py                  # Database utilities
├── camaras_unified.py             # Camera monitoring client
├── test_unified_system.py         # Test suite
├── requirements_unified.txt       # Python dependencies
├── README_UNIFIED.md              # This file
├── NFC_ServerSide/
│   ├── server_unified.py          # Unified Flask server
│   └── ...                        # Other NFC files
└── ...                            # Other project files
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements_unified.txt
```

### 2. Database Migration

The migration has already been run, but if you need to re-run it:

```bash
python unified_db.py
```

This will:
- Create the unified database schema
- Migrate data from `usuarios.db` and `NFC_ServerSide/data.db`
- Preserve all existing data

### 3. Start the Server

```bash
python NFC_ServerSide/server_unified.py
```

The server will start on `http://localhost:8080` by default.

### 4. Run the Camera Client

```bash
python camaras_unified.py
```

## 🔧 Configuration

### Environment Variables

- `ICA_DB_PATH` - Path to unified database (default: `./ica_unified.db`)
- `HOST` - Server host (default: `0.0.0.0`)
- `PORT` - Server port (default: `8080`)

### Server Configuration

Edit `NFC_ServerSide/server_unified.py` to change:
- Database path
- Logging configuration
- API endpoints

### Camera Client Configuration

Edit `camaras_unified.py` to change:
- Server URL (`SERVER_BASE_URL`)
- Window dimensions
- Screenshot settings

## 📊 API Endpoints

### User Management
- `GET /users` - List all users
- `GET /users/{id}` - Get user by ID
- `POST /users` - Create new user
- `PUT /users/{id}` - Update user
- `DELETE /users/{id}` - Delete user

### Camera Management
- `GET /cameras` - List all cameras
- `GET /cameras/{user_id}` - Get camera for user

### NFC Card Management
- `GET /cards` - List all cards
- `GET /cards/{uid}` - Get card by UID
- `POST /cards` - Create/update card
- `DELETE /cards/{uid}` - Delete card
- `GET /lookup/{uid}` - Check card access
- `GET /users/{id}/cards` - Get user's cards

### System
- `GET /health` - Server health check

## 🔍 Logging

The system provides comprehensive logging:

- **Server logs** - API requests, errors, and system events
- **Database logs** - Database operations and migrations
- **Camera logs** - Connection status and errors

Logs are written to:
- Console output
- `ica_server.log` file (server logs)

## 🧪 Testing

Run the test suite to verify everything works:

```bash
python test_unified_system.py
```

This will test:
- Database operations
- Server API endpoints
- Camera API functionality

## 🔄 Migration from Old System

The unified system automatically migrates data from:
- `usuarios.db` → `usuarios` table in unified database
- `NFC_ServerSide/data.db` → `cards` table in unified database

### Data Mapping

**Users Table:**
- `id_usuario` - Primary key
- `nombre` - User name
- `correo` - Email (unique)
- `rol` - User role
- `ip_camara` - Camera IP/URL
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp

**Cards Table:**
- `uid` - NFC card UID (primary key)
- `id_usuario` - Foreign key to usuarios table
- `role` - Access level
- `note` - Card description
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp

## 🎯 Key Features

### Unified Database
- Single source of truth for all data
- Foreign key relationships between users and cards
- Automatic timestamp tracking
- Data integrity constraints

### Server API
- RESTful API design
- Comprehensive error handling
- Request logging and auditing
- Health monitoring

### Camera System
- Server-based camera management
- Multiple simultaneous streams
- User information overlays
- Screenshot functionality
- Real-time connection monitoring

### Logging & Monitoring
- Detailed request logging
- Error tracking and reporting
- Performance monitoring
- Audit trail for security

## 🛠️ Development

### Adding New Features

1. **Database changes** - Update `unified_db.py`
2. **API endpoints** - Add to `server_unified.py`
3. **Client features** - Modify `camaras_unified.py`

### Database Schema Changes

To modify the database schema:
1. Update the schema in `unified_db.py`
2. Create migration script if needed
3. Update API endpoints accordingly

## 🐛 Troubleshooting

### Common Issues

1. **Server won't start**
   - Check if port 8080 is available
   - Verify database file exists
   - Check Python dependencies

2. **Camera connection fails**
   - Verify camera URLs are accessible
   - Check network connectivity
   - Ensure OpenCV is properly installed

3. **Database errors**
   - Check file permissions
   - Verify database file integrity
   - Run migration script again

### Debug Mode

Enable debug logging by setting environment variable:
```bash
export DEBUG=1
```

## 📝 License

This project is part of the ICA (Identity and Access Control) system.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📞 Support

For issues and questions:
- Check the logs for error messages
- Run the test suite to identify problems
- Review the API documentation
- Check the troubleshooting section

