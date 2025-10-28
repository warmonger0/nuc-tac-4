# Natural Language SQL Interface

A web application that converts natural language queries to SQL using AI, built with FastAPI and Vite + TypeScript.

## Features

- 🗣️ Natural language to SQL conversion using OpenAI or Anthropic
- 📁 Drag-and-drop file upload (.csv and .json)
- 📊 Interactive table results display
- 🖼️ Image upload and management with folder organization
- 🔒 SQL injection protection
- ⚡ Fast development with Vite and uv

## Prerequisites

- Python 3.10+
- Node.js 18+
- OpenAI API key and/or Anthropic API key
- 'gh' github cli
- astral uv

## Setup

### 1. Install Dependencies

```bash
# Backend
cd app/server
uv sync --all-extras

# Frontend
cd app/client
npm install
```

### 2. Environment Configuration

Set up your API keys in the server directory:

```bash
cp .env.sample .env
```

and

```bash
cd app/server
cp .env.sample .env
# Edit .env and add your API keys
```

## Quick Start

Use the provided script to start both services:

```bash
./scripts/start.sh
```

Press `Ctrl+C` to stop both services.

The script will:
- Check that `.env` exists in `app/server/`
- Start the backend on http://localhost:8000
- Start the frontend on http://localhost:5173
- Handle graceful shutdown when you exit

## Manual Start (Alternative)

### Backend
```bash
cd app/server
# .env is loaded automatically by python-dotenv
uv run python server.py
```

### Frontend
```bash
cd app/client
npm run dev
```

## Usage

### Natural Language SQL Interface

1. **Upload Data**: Click "Upload Data" to open the modal
   - Use sample data buttons for quick testing
   - Or drag and drop your own .csv or .json files
   - Uploading a file with the same name will overwrite the existing table
2. **Query Your Data**: Type a natural language query like "Show me all users who signed up last week"
   - Press `Cmd+Enter` (Mac) or `Ctrl+Enter` (Windows/Linux) to run the query
3. **View Results**: See the generated SQL and results in a table format
4. **Manage Tables**: Click the × button on any table to remove it

### Image Upload Page

Navigate to the Image Upload page using the "IMAGE UPLOAD" button in the navigation bar.

1. **Folder Management**:
   - Create new folders to organize your images
   - Rename existing folders (except the default folder)
   - Delete folders (images will be moved to the default folder)

2. **Upload Images**:
   - Select a folder from the dropdown
   - Drag and drop images onto the upload zone
   - Or click "Browse Files" to select images
   - Supported formats: PNG, JPG, JPEG, GIF, WebP, BMP
   - Multiple files can be uploaded at once

3. **View and Manage Images**:
   - Browse images in the gallery view
   - Click on an image to view it full-screen
   - Delete individual images using the Delete button
   - Filter images by folder using the folder dropdown

## Development

### Backend Commands
```bash
cd app/server
uv run python server.py      # Start server with hot reload
uv run pytest               # Run tests
uv add <package>            # Add package to project
uv remove <package>         # Remove package from project
uv sync --all-extras        # Sync all extras
```

### Frontend Commands
```bash
cd app/client
npm run dev                 # Start dev server
npm run build              # Build for production
npm run preview            # Preview production build
```

## Project Structure

```
.
├── app/                    # Main application
│   ├── client/             # Vite + TypeScript frontend
│   └── server/             # FastAPI backend
│
├── adws/                   # AI Developer Workflows - Core agent system
├── scripts/                # Utility scripts (start.sh, stop_apps.sh)
├── specs/                  # Feature specifications
├── ai_docs/                # AI/LLM documentation
├── agents/                 # Agent execution logging
└── logs/                   # Structured session logs
```

## ADWs

- `uv run adws/health_check.py` - Basic health check ADW
- `uv run adws/trigger_webhook.py` - React to incoming webhook trigger (be sure to setup a tunnel and your github webhook)
- `uv run adws/trigger_cron.py` - Simple cron job trigger that checks github issues every N seconds
- `uv run adws/adw_plan_build.py` - Plan -> Build AI Developer Workflow (ADW)

## API Endpoints

### Data Query Endpoints
- `POST /api/upload` - Upload CSV/JSON file
- `POST /api/query` - Process natural language query
- `GET /api/schema` - Get database schema
- `POST /api/insights` - Generate column insights
- `GET /api/health` - Health check
- `DELETE /api/table/{table_name}` - Delete a table

### Image Upload Endpoints
- `POST /api/images/upload` - Upload multiple images to a folder
- `GET /api/images` - List all images (optional folder filter)
- `GET /api/images/{image_id}` - Get a specific image file
- `DELETE /api/images/{image_id}` - Delete an image

### Folder Management Endpoints
- `GET /api/folders` - List all folders
- `POST /api/folders` - Create a new folder
- `PUT /api/folders/{folder_name}` - Rename a folder
- `DELETE /api/folders/{folder_name}` - Delete a folder

## Security

### SQL Injection Protection

The application implements comprehensive SQL injection protection through multiple layers:

1. **Centralized Security Module** (`core/sql_security.py`):
   - Identifier validation for table and column names
   - Safe query execution with parameterized queries
   - Proper escaping for identifiers using SQLite's square bracket notation
   - Dangerous operation detection and blocking

2. **Input Validation**:
   - All table and column names are validated against a whitelist pattern
   - SQL keywords cannot be used as identifiers
   - File names are sanitized before creating tables
   - User queries are validated for dangerous operations

3. **Query Execution Safety**:
   - Parameterized queries used wherever possible
   - Identifiers (table/column names) are properly escaped
   - Multiple statement execution is blocked
   - SQL comments are not allowed in queries

4. **Protected Operations**:
   - File uploads with malicious names are sanitized
   - Natural language queries cannot inject SQL
   - Table deletion uses validated identifiers
   - Data insights generation validates all inputs

### Security Best Practices for Development

When adding new SQL functionality:
1. Always use the `sql_security` module functions
2. Never concatenate user input directly into SQL strings
3. Use `execute_query_safely()` for all database operations
4. Validate all identifiers with `validate_identifier()`
5. For DDL operations, use `allow_ddl=True` explicitly

### Testing Security

Run the comprehensive security tests:
```bash
cd app/server
uv run pytest tests/test_sql_injection.py -v
```


### Additional Security Features

- CORS configured for local development only
- File upload validation (CSV and JSON only)
- Comprehensive error logging without exposing sensitive data
- Database operations are isolated with proper connection handling

## Troubleshooting

**Backend won't start:**
- Check Python version: `python --version` (requires 3.12+)
- Verify API keys are set: `echo $OPENAI_API_KEY`

**Frontend errors:**
- Clear node_modules: `rm -rf node_modules && npm install`
- Check Node version: `node --version` (requires 18+)

**CORS issues:**
- Ensure backend is running on port 8000
- Check vite.config.ts proxy settings