# Feature: Finalize Navigation Menu and Image Upload Page

## Feature Description
This feature finalizes the implementation of the navigation menu (Issue 2) and moves all image upload functionality created in Issue 3 to a dedicated "Image Upload" page. The navigation menu provides a full-page-width navigation bar above the page title with two buttons: "NL SQL" (linking to the Natural Language SQL Interface) and "IMAGE UPLOAD" (linking to the new Image Upload page). The buttons are right-justified, reflect the current page styling and color schema, and display as active when on their respective pages. The Image Upload page will host all image management functionality including image database, file upload, folder management, and support for common image file types.

## User Story
As a user of the Natural Language SQL Interface application
I want to navigate between the SQL interface and an Image Upload page using a navigation menu
So that I can easily access both data querying and image management functionality in a unified application

## Problem Statement
Currently, the application only provides a Natural Language SQL Interface without a way to manage and upload images. Issue 2 requires finalizing a navigation menu implementation, and Issue 3 requires that image upload features be accessible through a dedicated page. The navigation needs to be seamlessly integrated into both pages with proper active state indicators, and the Image Upload page needs a complete implementation including image database support, multi-file upload capabilities, folder organization, and support for common image formats.

## Solution Statement
The solution involves:
1. Finalizing the navigation menu implementation in the source files (currently only in dist)
2. Adding navigation bar styling to the main stylesheet
3. Creating a new image-upload.html page with corresponding TypeScript/JavaScript
4. Implementing backend API endpoints for image storage and retrieval
5. Building a comprehensive image upload interface with drag-and-drop, folder management, and file type validation
6. Ensuring proper routing between pages with active state indicators
7. Integrating with the existing SQLite database for image metadata storage
8. Adding comprehensive tests for both frontend and backend functionality

## Relevant Files
Use these files to implement the feature:

### Frontend Files
- **app/client/index.html** - Main HTML file for NL SQL page, needs navigation bar integration
- **app/client/src/main.ts** - Main TypeScript entry point, handles NL SQL functionality
- **app/client/src/style.css** - Main stylesheet, needs navigation bar styles added
- **app/client/src/api/client.ts** - API client, needs image upload API methods
- **app/client/src/types.d.ts** - TypeScript type definitions, needs image-related types
- **app/client/vite.config.ts** - Vite build configuration, may need multi-page setup

### Backend Files
- **app/server/server.py** - FastAPI server, needs image upload endpoints
- **app/server/core/file_processor.py** - File processing logic, needs image handling
- **app/server/core/data_models.py** - Pydantic models, needs image-related models
- **app/server/core/sql_security.py** - SQL security module, will be used for safe image metadata queries

### Testing Files
- **app/server/tests/** - Backend test directory, needs image upload tests
- **app/client/src/** - Frontend source, needs test fixtures (sample images)

### New Files
- **app/client/image-upload.html** - New HTML page for image upload interface
- **app/client/src/image-upload.ts** - TypeScript logic for image upload page
- **app/server/core/image_processor.py** - New module for image handling and storage
- **app/server/tests/test_images/** - Test images directory with sample files (PNG, JPG, GIF, WebP)
- **app/server/tests/core/test_image_processor.py** - Tests for image processing
- **app/server/tests/test_image_api.py** - Tests for image API endpoints

## Implementation Plan

### Phase 1: Foundation
This phase establishes the foundational work including navigation bar integration in source files, multi-page Vite configuration, and database schema for image metadata. We'll ensure the navigation works properly on both pages before adding image upload functionality.

### Phase 2: Core Implementation
This phase implements the image upload functionality including backend API endpoints for image storage and retrieval, frontend image upload interface with drag-and-drop, folder management system, and file type validation. We'll use SQLite for metadata storage and the filesystem for image files.

### Phase 3: Integration
This phase integrates the image upload page with the navigation system, ensures proper active state management, adds comprehensive error handling, implements image preview functionality, and creates end-to-end tests to validate the entire workflow.

## Step by Step Tasks

### Step 1: Add Navigation Bar to Source Files
- Update `app/client/src/style.css` to include navbar styles (copy from dist CSS or create improved version)
- Add responsive navbar styles for mobile devices
- Ensure navbar styling matches the existing design system with proper color variables

### Step 2: Integrate Navigation Bar into Main Page
- Update `app/client/index.html` to include navigation bar HTML before the h1 title
- Ensure "NL SQL" button has active state and "IMAGE UPLOAD" button is inactive
- Test navigation bar displays correctly with proper right-alignment
- Verify accessibility attributes (aria-label, role, aria-current)

### Step 3: Configure Multi-Page Build
- Update `app/client/vite.config.ts` to support multi-page builds
- Configure build input for both index.html and image-upload.html
- Ensure proper asset sharing between pages
- Test build process produces both pages correctly

### Step 4: Create Image Upload Page Structure
- Create `app/client/image-upload.html` with navigation bar and page structure
- Ensure "IMAGE UPLOAD" button has active state and "NL SQL" button is inactive
- Add placeholder sections for image upload interface
- Link stylesheet and prepare for TypeScript module

### Step 5: Define Image Data Models
- Update `app/server/core/data_models.py` with image-related Pydantic models:
  - `ImageUploadRequest` (folder_name)
  - `ImageUploadResponse` (image_id, filename, folder, size, format, url, error)
  - `ImageMetadata` (image_id, filename, folder, size, format, created_at, file_path)
  - `FolderRequest` (folder_name, new_name for renaming)
  - `FolderResponse` (folders list, error)
- Update `app/client/src/types.d.ts` with corresponding TypeScript interfaces

### Step 6: Create Database Schema for Images
- Create `app/server/core/image_processor.py` module
- Implement function to initialize images table in SQLite:
  - `images` table with columns: id, filename, folder, size, format, created_at, file_path
  - `folders` table with columns: id, name, created_at
- Add indexes for efficient querying (folder, created_at)
- Ensure SQL security best practices using existing `sql_security` module

### Step 7: Implement Backend Image Storage
- In `app/server/core/image_processor.py`, implement:
  - `save_image_to_disk(file_data, folder, filename)` - saves image to filesystem
  - `save_image_metadata(conn, metadata)` - saves metadata to database
  - `get_supported_formats()` - returns list of supported image formats (PNG, JPG, JPEG, GIF, WebP, BMP)
  - `validate_image_format(filename)` - validates file extension
- Create images storage directory: `app/server/images/{folder_name}/`
- Implement proper error handling for disk space, permissions, invalid formats

### Step 8: Implement Folder Management Backend
- In `app/server/core/image_processor.py`, implement:
  - `create_folder(conn, folder_name)` - creates folder in DB and filesystem
  - `get_folders(conn)` - retrieves all folders
  - `rename_folder(conn, old_name, new_name)` - renames folder in DB and filesystem
  - `delete_folder(conn, folder_name)` - deletes folder and moves images to "default" folder or deletes them
- Ensure folder names are sanitized using `sql_security.validate_identifier()`
- Create default "default" folder on initialization

### Step 9: Create Image Upload API Endpoints
- In `app/server/server.py`, add endpoints:
  - `POST /api/images/upload` - accepts multiple files and folder parameter
  - `GET /api/images` - returns list of all images with metadata
  - `GET /api/images/{image_id}` - returns specific image file
  - `DELETE /api/images/{image_id}` - deletes image from DB and filesystem
  - `GET /api/folders` - returns list of all folders
  - `POST /api/folders` - creates a new folder
  - `PUT /api/folders/{folder_name}` - renames a folder
  - `DELETE /api/folders/{folder_name}` - deletes a folder
- Implement proper error handling and validation
- Use `File(...)` from FastAPI for file uploads
- Return appropriate status codes (200, 201, 400, 404, 500)

### Step 10: Create API Client Methods
- Update `app/client/src/api/client.ts` with new methods:
  - `uploadImages(files: FileList, folder: string)` - uploads multiple images
  - `getImages(folder?: string)` - retrieves images, optionally filtered by folder
  - `getImage(imageId: string)` - gets specific image URL
  - `deleteImage(imageId: string)` - deletes an image
  - `getFolders()` - retrieves all folders
  - `createFolder(name: string)` - creates a folder
  - `renameFolder(oldName: string, newName: string)` - renames a folder
  - `deleteFolder(name: string)` - deletes a folder
- Implement proper error handling and TypeScript types

### Step 11: Build Image Upload Interface
- Create `app/client/src/image-upload.ts` with:
  - Initialize function that sets up drag-and-drop zone
  - File input handler for browse button (allow multiple file selection)
  - Drag-and-drop event handlers (dragover, dragleave, drop)
  - File validation for supported formats
  - Upload progress indicators
  - Error display for invalid files or upload failures
- Add UI elements to `app/client/image-upload.html`:
  - Folder dropdown/selector with options to create, rename, delete folders
  - Upload panel with drag-and-drop zone
  - Browse button for file selection
  - Accepted file types display (PNG, JPG, JPEG, GIF, WebP, BMP)
  - Upload progress/status indicators

### Step 12: Implement Folder Management UI
- In `app/client/src/image-upload.ts`, add:
  - Folder dropdown population from API
  - Create folder dialog/modal
  - Rename folder dialog/modal
  - Delete folder confirmation dialog
  - Active folder state management
- Add UI elements:
  - Folder management section with buttons
  - Modals/dialogs for folder operations
  - Active folder indicator
- Ensure folder operations update the UI immediately

### Step 13: Implement Image Gallery Display
- In `app/client/src/image-upload.ts`, add:
  - Function to fetch and display uploaded images
  - Grid layout for image thumbnails
  - Image metadata display (filename, size, date)
  - Delete button for each image
  - Filter images by selected folder
- Add CSS styles for image gallery:
  - Responsive grid layout
  - Hover effects for image cards
  - Image preview on click (modal or lightbox)
  - Thumbnail sizing and aspect ratio handling

### Step 14: Add Test Images
- Create `app/server/tests/test_images/` directory
- Add sample images of different types:
  - `sample.png` - PNG image
  - `sample.jpg` - JPEG image
  - `sample.gif` - GIF image (animated if possible)
  - `sample.webp` - WebP image
  - `sample.bmp` - BMP image
- These will be used for testing upload functionality

### Step 15: Write Backend Unit Tests
- Create `app/server/tests/core/test_image_processor.py`:
  - Test `validate_image_format()` with valid and invalid formats
  - Test `save_image_to_disk()` with mock file data
  - Test `save_image_metadata()` with database
  - Test folder creation, renaming, deletion
  - Test edge cases (duplicate names, invalid characters, etc.)
- Ensure tests use pytest fixtures for database setup/teardown

### Step 16: Write Backend API Tests
- Create `app/server/tests/test_image_api.py`:
  - Test `POST /api/images/upload` with single and multiple files
  - Test `GET /api/images` returns correct data
  - Test `DELETE /api/images/{id}` removes image
  - Test folder endpoints (create, list, rename, delete)
  - Test error cases (invalid format, missing files, etc.)
  - Test file size limits and permission errors
- Use TestClient from FastAPI for API testing

### Step 17: Write Frontend Integration Tests
- Create basic validation script in `app/client/`:
  - Manual test checklist for navigation
  - Manual test checklist for image upload
  - Manual test checklist for folder management
- Document test procedures in the plan

### Step 18: Add Accessibility Features
- Ensure all interactive elements have proper ARIA labels
- Add keyboard navigation support for image gallery
- Ensure proper focus management in modals/dialogs
- Test with screen reader (document findings)
- Add alt text support for uploaded images (optional enhancement)

### Step 19: Update Documentation
- Update README.md with new Image Upload page information
- Document image upload API endpoints
- Add image upload feature to Features section
- Update Usage section with Image Upload instructions
- Document supported image formats and limitations

### Step 20: Run Validation Commands
- Execute all validation commands to ensure zero regressions:
  - Run backend tests: `cd app/server && uv run pytest`
  - Build frontend: `cd app/client && npm run build`
  - Start backend and verify server starts without errors
  - Start frontend and verify both pages load correctly
  - Test navigation between pages
  - Test image upload end-to-end (upload, view, delete)
  - Test folder management end-to-end (create, rename, delete)
  - Verify no console errors in browser
  - Test with different image formats
  - Test with multiple file uploads
- Fix any errors or regressions discovered

## Testing Strategy

### Unit Tests
- **Backend Image Processor**: Test all image processing functions including validation, storage, metadata management, and folder operations
- **Backend API Endpoints**: Test each image and folder API endpoint with valid and invalid inputs
- **Frontend API Client**: Test API client methods with mocked responses
- **Frontend Image Upload**: Test file validation, drag-and-drop handlers, and UI state management

### Integration Tests
- **End-to-End Image Upload**: Test complete flow from file selection to storage and display
- **Navigation Flow**: Test navigation between pages with proper active state indicators
- **Folder Management Flow**: Test folder creation, renaming, deletion with image associations
- **Multi-File Upload**: Test uploading multiple images simultaneously
- **Image Gallery**: Test image retrieval, filtering by folder, and deletion

### Edge Cases
- Invalid image formats (upload .txt, .pdf, etc.)
- Empty folder name or special characters in folder names
- Duplicate image filenames in same folder
- Very large image files (test file size limits)
- Uploading to non-existent folder
- Deleting folder with images inside
- Simultaneous uploads from multiple users (if applicable)
- Network errors during upload (partial uploads)
- Disk space limitations
- Invalid image data (corrupted files)
- Browser compatibility (drag-and-drop in different browsers)
- Mobile device testing (file selection on mobile)

## Acceptance Criteria
1. Navigation bar appears on both "NL SQL" and "Image Upload" pages with proper styling and right-alignment
2. Navigation buttons correctly indicate active page with visual styling
3. Clicking navigation buttons navigates between pages without errors
4. Image Upload page has functional upload panel with drag-and-drop support
5. Users can browse and select multiple image files for upload
6. Only supported image formats (PNG, JPG, JPEG, GIF, WebP, BMP) are accepted
7. UI clearly displays accepted file types
8. Users can create, rename, and delete folders for organizing images
9. Folder dropdown shows all available folders and allows folder selection
10. Uploaded images are stored in database and filesystem correctly
11. Image gallery displays uploaded images with thumbnails and metadata
12. Users can filter images by folder
13. Users can delete individual images
14. All image operations provide appropriate success/error feedback
15. Backend API endpoints return proper status codes and error messages
16. All existing functionality (NL SQL) continues to work without regression
17. All tests pass with zero failures
18. Application builds successfully without errors
19. No console errors in browser when using either page
20. Responsive design works on mobile and desktop
21. Accessibility features are implemented (keyboard navigation, ARIA labels)
22. Documentation is updated with Image Upload feature details

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

```bash
# Backend Tests
cd app/server && uv run pytest

# Frontend Build
cd app/client && npm run build

# Start Backend Server (in separate terminal)
cd app/server && uv run python server.py

# Start Frontend Dev Server (in separate terminal)
cd app/client && npm run dev

# Manual Testing Checklist (execute and verify):
# 1. Navigate to http://localhost:5173
# 2. Verify navigation bar appears with "NL SQL" active and "IMAGE UPLOAD" inactive
# 3. Click "IMAGE UPLOAD" button and verify navigation to image upload page
# 4. Verify navigation bar appears with "IMAGE UPLOAD" active and "NL SQL" inactive
# 5. Verify upload panel displays with drag-and-drop zone and browse button
# 6. Verify folder dropdown/selector is visible with folder management options
# 7. Create a new folder named "test-folder"
# 8. Select "test-folder" from dropdown
# 9. Upload a PNG image via browse button
# 10. Upload a JPG image via drag-and-drop
# 11. Verify both images appear in the image gallery
# 12. Try uploading an invalid file type (.txt) and verify error message
# 13. Delete one uploaded image and verify it's removed from gallery
# 14. Rename "test-folder" to "renamed-folder"
# 15. Verify images still appear under renamed folder
# 16. Create another folder "folder-2"
# 17. Upload images to "folder-2"
# 18. Switch between folders and verify correct images display
# 19. Delete "folder-2" and verify proper handling of images
# 20. Navigate back to "NL SQL" page via navigation bar
# 21. Verify NL SQL functionality still works (upload data, run query)
# 22. Open browser console and verify no errors on either page
```

## Notes

### Technology Stack
- **Frontend**: Vanilla TypeScript with Vite (no frameworks per project requirements)
- **Backend**: FastAPI with Python
- **Database**: SQLite for metadata storage
- **File Storage**: Filesystem for image files

### Standard Libraries Only
Per issue requirements, we should use standard libraries and avoid adding new dependencies. This means:
- Use native Python `pathlib`, `os`, and `shutil` for file operations
- Use SQLite3 (already in use) for database operations
- Use native browser APIs for drag-and-drop (no libraries like Dropzone.js)
- Use FastAPI's built-in `UploadFile` handling

### Image Storage Strategy
- Images stored in filesystem: `app/server/images/{folder_name}/{filename}`
- Metadata stored in SQLite database
- URLs generated dynamically: `/api/images/{image_id}`
- Thumbnails can be generated on-the-fly or served as full images (keep it simple for v1)

### Security Considerations
- Use existing `sql_security` module for folder name validation
- Validate file extensions and MIME types
- Implement file size limits (e.g., 10MB per image)
- Sanitize folder names to prevent directory traversal attacks
- Use secure file naming (avoid using user-provided names directly)

### Future Enhancements (not in scope)
- Image editing capabilities
- Bulk image operations
- Image search functionality
- User authentication and per-user image libraries
- Cloud storage integration
- Automatic thumbnail generation
- Image compression
- Image metadata extraction (EXIF data)
- Shareable image links
- Image tagging and categorization

### Build Process
The current setup uses Vite with a single entry point. We'll need to configure multi-page support:
```typescript
// vite.config.ts
export default defineConfig({
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        imageUpload: resolve(__dirname, 'image-upload.html')
      }
    }
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false
      }
    }
  }
})
```

### Development Workflow
1. Implement backend first (API endpoints and image processor)
2. Test backend with pytest
3. Implement frontend (UI and API integration)
4. Test frontend manually with dev server
5. Build and test production build
6. Run full validation suite

### Git Workflow
- This feature implements Issue #5
- Create clear, descriptive commits for each major step
- Test before committing
- Include relevant issue numbers in commit messages
