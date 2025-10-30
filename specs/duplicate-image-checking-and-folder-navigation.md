# Feature: Duplicate Image Checking and Folder Navigation

## Feature Description
This feature enhances the existing image upload functionality with intelligent duplicate detection and improved folder navigation. Before adding an image to a folder, the system will check if another version of the same image already exists by comparing both filenames and actual image content using perceptual hashing. Additionally, the image gallery panel will be enhanced to display folder structures and allow users to navigate through folders to view their images, providing a more organized and intuitive image management experience.

## User Story
As a user managing images in the application
I want the system to detect and warn me about duplicate images before uploading
And I want to browse images by folder in the gallery panel
So that I can maintain a clean, organized image library without duplicates and easily find images by their folder organization

## Problem Statement
Currently, the image upload system does not check for duplicate images before storing them, which can lead to:
1. Storage waste from identical or near-identical images
2. Confusion when managing large image collections
3. Difficulty identifying which images are already uploaded

Additionally, the image gallery panel shows all images in a flat list without folder organization, making it difficult to:
1. Navigate through large collections of images organized in multiple folders
2. Understand the folder structure at a glance
3. Efficiently locate images stored in specific folders

## Solution Statement
The solution implements a two-pronged approach:

1. **Duplicate Image Detection**: Before saving any image to a folder, the system will:
   - Check for exact filename matches in the target folder
   - Compute a perceptual hash (pHash) of the uploaded image
   - Compare the pHash against existing images in the folder
   - Alert the user if a duplicate or near-duplicate is found
   - Provide options to skip, replace, or rename the duplicate

2. **Folder Navigation Enhancement**: The image gallery will be enhanced to:
   - Display a folder tree or list view showing all available folders
   - Show image counts per folder
   - Allow clicking on folders to filter and display only images from that folder
   - Provide visual indication of the currently selected folder
   - Support breadcrumb navigation for nested folder structures (future enhancement)

## Relevant Files
Use these files to implement the feature:

### Backend Files
- **app/server/core/image_processor.py** - Add duplicate detection logic, perceptual hashing functions, and folder query enhancements
  - Currently handles image storage, folder management, and basic validation
  - Will be extended with pHash computation and duplicate checking

- **app/server/core/data_models.py** - Add new models for duplicate detection responses and folder statistics
  - Currently defines ImageMetadata, ImageUploadResponse, FolderResponse
  - Will add DuplicateCheckResult, FolderStats, ImageComparisonResult models

- **app/server/server.py** - Add duplicate check endpoint and enhance folder list endpoint with image counts
  - Currently has image upload, list, delete endpoints and folder CRUD operations
  - Will add POST /api/images/check-duplicate and enhance GET /api/folders

- **app/server/tests/core/test_image_processor.py** - Add tests for duplicate detection and perceptual hashing
  - Currently tests image validation, storage, and folder operations
  - Will add tests for pHash computation, duplicate detection, and image comparison

- **app/server/tests/test_image_api.py** - Add tests for duplicate check endpoint and folder stats
  - Currently tests image upload, retrieval, deletion, and folder management
  - Will add tests for duplicate detection API and enhanced folder listings

### Frontend Files
- **app/client/src/image-upload.ts** - Add duplicate check before upload and folder navigation UI logic
  - Currently handles file upload, folder selection, image gallery display
  - Will add pre-upload duplicate checking, folder tree navigation, folder statistics display

- **app/client/src/types.d.ts** - Add TypeScript types for duplicate detection and folder stats
  - Currently defines ImageMetadata, QueryResponse, FileUploadResponse
  - Will add DuplicateCheckResult, FolderStats, ImageComparisonResult types

- **app/client/src/style.css** - Add styles for folder navigation panel and duplicate warning dialogs
  - Currently styles upload panel, image gallery, folder management modals
  - Will add folder tree/list styles, duplicate warning dialog styles, active folder indicators

- **app/client/image-upload.html** - Update layout to include folder navigation panel
  - Currently has folder dropdown, upload zone, image gallery
  - Will add dedicated folder navigation sidebar with folder tree/list

### Test Resources
- **app/server/tests/test_images/** - Add test images for duplicate detection testing
  - Currently contains sample.png, sample.jpg, sample.gif, sample.webp, sample.bmp
  - Will add duplicate variations (identical, slightly modified, different) for testing

### New Files
- **app/server/core/image_hasher.py** - New module for perceptual hashing and image comparison algorithms
  - Will implement pHash computation using DCT (Discrete Cosine Transform)
  - Will provide similarity comparison functions
  - Will handle hash storage and retrieval from database

## Implementation Plan

### Phase 1: Foundation
Establish the foundational infrastructure for duplicate detection by implementing perceptual hashing algorithms, updating the database schema to store image hashes, and creating comprehensive test fixtures for duplicate detection scenarios. This phase focuses on the backend core functionality without user-facing changes.

### Phase 2: Core Implementation
Implement the duplicate detection logic that runs before image upload, create API endpoints for checking duplicates, enhance folder listing to include image counts and statistics, and build the folder navigation UI components. This phase brings the duplicate detection and folder navigation features to life.

### Phase 3: Integration
Integrate duplicate detection into the upload workflow with appropriate user prompts and confirmations, connect the folder navigation UI to the gallery display with filtering capabilities, add comprehensive error handling for edge cases, and implement end-to-end tests validating the complete user flow from folder selection through duplicate detection to final upload.

## Step by Step Tasks

### Step 1: Install Image Processing Library
- Add `imagehash` library for perceptual hashing: `cd app/server && uv add imagehash pillow`
- The `imagehash` library provides robust pHash implementation using PIL/Pillow
- Pillow is required for image loading and processing
- Document the new dependencies in the notes section

### Step 2: Create Image Hashing Module
- Create `app/server/core/image_hasher.py` with the following functions:
  - `compute_phash(image_data: bytes) -> str` - computes perceptual hash of image
  - `compare_hashes(hash1: str, hash2: str) -> float` - returns similarity score (0-1)
  - `compute_and_store_hash(conn, image_id, image_data)` - computes and saves hash to DB
  - `find_similar_images(conn, phash, folder, threshold=0.95)` - finds images with similar hashes
- Use DCT-based perceptual hashing for rotation/scale invariance
- Handle various image formats (PNG, JPG, GIF, WebP, BMP)
- Add comprehensive error handling for corrupted images

### Step 3: Update Database Schema for Image Hashes
- Modify `app/server/core/image_processor.py` to add `phash` column to images table:
  - Update `initialize_image_database()` to include `phash TEXT` column
  - Add index on phash column for efficient duplicate lookups
  - Create migration to add column to existing databases (ALTER TABLE)
- Ensure backward compatibility with existing image records (phash can be NULL initially)
- Update `save_image_metadata()` to accept and store phash value

### Step 4: Implement Duplicate Detection Logic
- In `app/server/core/image_processor.py`, add function:
  - `check_for_duplicates(conn, file_data, folder, filename) -> List[DuplicateMatch]`
- The function should:
  1. Compute pHash of the uploaded image
  2. Check for exact filename matches in the target folder
  3. Query database for images with similar pHashes in the folder
  4. Return list of potential duplicates with similarity scores
  5. Include metadata for each duplicate (id, filename, similarity)
- Use configurable similarity threshold (default 95%)

### Step 5: Update Data Models
- In `app/server/core/data_models.py`, add new models:
  - `DuplicateMatch` - image_id, filename, folder, similarity_score, phash
  - `DuplicateCheckRequest` - folder, filename (for API)
  - `DuplicateCheckResponse` - is_duplicate, matches: List[DuplicateMatch], error
  - `FolderStats` - name, image_count, total_size, created_at
  - `FolderListResponse` - folders: List[FolderStats], total_folders, error
- Update TypeScript types in `app/client/src/types.d.ts` to mirror these models

### Step 6: Add Duplicate Check API Endpoint
- In `app/server/server.py`, add endpoint:
  - `POST /api/images/check-duplicate` - accepts file data and folder name
  - Computes hash and checks for duplicates without saving
  - Returns DuplicateCheckResponse with list of matches
  - Include similarity scores for each match
- Add proper error handling for invalid images or missing folders
- Use FastAPI's UploadFile for file handling

### Step 7: Enhance Folder List Endpoint
- Update `GET /api/folders` endpoint in `app/server/server.py`:
  - Query database to count images per folder
  - Calculate total size of images per folder
  - Return FolderListResponse with FolderStats for each folder
  - Include folder creation date
- Optimize query to avoid N+1 problem (use SQL JOINs or aggregation)

### Step 8: Update Upload Endpoint to Store Hashes
- Modify `POST /api/images/upload` in `app/server/server.py`:
  - Compute pHash for each uploaded image
  - Store hash in database alongside metadata
  - Optionally perform automatic duplicate check (based on query parameter)
  - Return enhanced response indicating if duplicates were detected
- Ensure backward compatibility with existing upload workflow

### Step 9: Write Backend Unit Tests for Hashing
- Create tests in `app/server/tests/core/test_image_hasher.py`:
  - Test `compute_phash()` with various image formats
  - Test that identical images produce identical hashes
  - Test that similar images produce similar hashes
  - Test that different images produce different hashes
  - Test hash comparison with various similarity thresholds
  - Test error handling for corrupted images
- Create test fixtures with duplicate and non-duplicate images

### Step 10: Write Backend Tests for Duplicate Detection
- Add tests to `app/server/tests/core/test_image_processor.py`:
  - Test `check_for_duplicates()` with exact duplicates
  - Test with similar images (slightly modified)
  - Test with completely different images
  - Test filename collision detection
  - Test folder-specific duplicate checking
  - Test performance with large number of images
- Use sample test images from test_images directory

### Step 11: Write API Tests for Duplicate Check
- Add tests to `app/server/tests/test_image_api.py`:
  - Test `POST /api/images/check-duplicate` with duplicate image
  - Test with non-duplicate image
  - Test with invalid image data
  - Test with non-existent folder
  - Test response format and similarity scores
  - Test that check-duplicate does not save images
- Verify API returns correct HTTP status codes

### Step 12: Implement Frontend Duplicate Check
- Update `app/client/src/image-upload.ts`:
  - Add function `checkForDuplicates(files: FileList, folder: string)`
  - Call API for each file before upload
  - Show duplicate warning dialog if matches found
  - Provide options: Skip, Replace, Rename, Upload Anyway
  - Display thumbnail of original and duplicate for comparison
- Implement batch duplicate checking for multiple files

### Step 13: Create Duplicate Warning Dialog
- Add HTML structure to `app/client/image-upload.html`:
  - Modal dialog showing duplicate information
  - Display both original and new image thumbnails
  - Show similarity score and existing filename
  - Action buttons: Skip, Replace, Rename, Upload Anyway
  - Support for reviewing multiple duplicates in sequence
- Add CSS styles in `app/client/src/style.css` for the dialog

### Step 14: Implement Folder Navigation Panel
- Update `app/client/image-upload.html`:
  - Add sidebar for folder navigation (left side of gallery)
  - Include folder list with expand/collapse functionality
  - Show image count badge for each folder
  - Add "All Images" option to show unfiltered view
  - Include visual indicator for currently selected folder
- Make responsive for mobile (collapsible sidebar)

### Step 15: Style Folder Navigation Panel
- Add CSS to `app/client/src/style.css`:
  - Folder list container styles (sidebar layout)
  - Folder item styles with hover effects
  - Active folder indicator (highlight, border, or background)
  - Image count badge styles
  - Expand/collapse icons for nested folders (future enhancement)
  - Mobile responsive styles (hamburger menu or bottom sheet)
- Ensure consistent styling with existing design system

### Step 16: Implement Folder Navigation Logic
- Update `app/client/src/image-upload.ts`:
  - Add function `renderFolderNavigation(folders: FolderStats[])`
  - Handle folder click events to filter image gallery
  - Update active folder indicator when selection changes
  - Load images for selected folder using existing API
  - Add "All Images" filter that shows images from all folders
  - Update gallery title to show current folder or "All Images"
- Maintain state of selected folder across operations

### Step 17: Enhance API Client
- Update `app/client/src/api/client.ts`:
  - Add `checkDuplicate(file: File, folder: string)` method
  - Update `getFolders()` to return FolderStats instead of string[]
  - Add error handling for duplicate check failures
  - Implement proper TypeScript typing for all new methods
- Ensure backward compatibility with existing API calls

### Step 18: Add Integration Tests
- Create end-to-end test scenarios:
  - Upload image -> Upload same image -> Verify duplicate warning
  - Upload to folder1 -> Upload same to folder2 -> Verify no duplicate (different folders)
  - Create multiple folders -> Navigate between folders -> Verify correct images displayed
  - Upload multiple images -> Check folder counts -> Verify accuracy
  - Test duplicate detection with various similarity levels
- Document test procedures for manual validation

### Step 19: Handle Edge Cases
- Implement error handling for:
  - Hash computation failures (corrupted images)
  - Database errors during duplicate check
  - Missing folder when checking duplicates
  - Very large images (memory constraints)
  - Images without clear perceptual features (solid colors)
  - Concurrent uploads of the same image
  - Network failures during duplicate check
- Add appropriate error messages and user guidance

### Step 20: Update Documentation
- Update README.md with new features:
  - Document duplicate detection capability
  - Explain how perceptual hashing works (user-friendly explanation)
  - Document folder navigation panel
  - Add screenshots or diagrams if possible
  - Update API documentation with new endpoints
  - Document configuration options (similarity threshold)
- Add troubleshooting section for duplicate detection issues

### Step 21: Run Validation Commands
- Execute all validation commands to ensure zero regressions:
  - `cd app/server && uv run pytest` - Run all backend tests
  - `cd app/client && npm run build` - Build frontend
  - Start backend and frontend servers
  - Manual testing:
    - Upload image to folder A
    - Upload same image to folder A -> Verify duplicate warning
    - Upload same image to folder B -> Verify no warning (different folder)
    - Modify image slightly (crop, resize) -> Verify duplicate detected if similarity high
    - Navigate between folders in gallery -> Verify correct images shown
    - Check folder image counts -> Verify accuracy
    - Test with all supported image formats
    - Test with multiple duplicate scenarios
- Fix any errors or regressions discovered

## Testing Strategy

### Unit Tests
- **Image Hashing Module**: Test perceptual hash computation with various image formats, test hash comparison algorithms, test edge cases (solid colors, very small images, corrupted data)
- **Duplicate Detection Logic**: Test exact duplicates, near-duplicates, non-duplicates, filename collision handling, folder-specific detection
- **Folder Statistics**: Test image counting, size calculation, folder filtering
- **API Endpoints**: Test duplicate check endpoint with valid/invalid inputs, test enhanced folder list with statistics

### Integration Tests
- **End-to-End Upload with Duplicate Detection**: Upload image -> Attempt duplicate upload -> Verify warning -> Test skip/replace/rename options
- **Folder Navigation Workflow**: Create folders -> Upload to different folders -> Navigate gallery by folder -> Verify correct filtering
- **Multi-file Upload with Duplicates**: Upload batch of files with some duplicates -> Verify individual handling of each duplicate
- **Cross-folder Detection**: Verify same image in different folders is not considered duplicate (folder-specific detection)

### Edge Cases
- Uploading exact duplicate (100% similarity)
- Uploading near-duplicate (90-99% similarity) - cropped, resized, format-converted
- Uploading same image to different folders (should not trigger duplicate)
- Uploading images with identical filenames but different content
- Uploading very large images (test memory handling)
- Uploading solid color images (minimal features for hashing)
- Uploading corrupted images (hash computation should fail gracefully)
- Concurrent upload of same image by multiple users
- Database failure during duplicate check
- Hash computation timeout for very large images
- Folder with thousands of images (performance testing)
- Animated GIFs (test first frame hashing)
- Images with EXIF orientation (test rotation handling)

## Acceptance Criteria
1. System computes perceptual hash (pHash) for every uploaded image
2. Before saving, system checks if similar image exists in target folder
3. Duplicate check compares both filename and image content (pHash)
4. User receives clear warning when duplicate is detected with similarity score
5. Duplicate warning shows thumbnail comparison of original and new image
6. User can choose to: Skip upload, Replace existing, Rename new, or Upload anyway
7. Duplicate detection is folder-specific (same image in different folders is allowed)
8. Folder list in navigation panel shows image count for each folder
9. Clicking a folder in navigation panel filters gallery to show only that folder's images
10. Active folder is visually indicated in navigation panel
11. "All Images" option shows images from all folders
12. Duplicate check completes within 2 seconds for typical images (<10MB)
13. System handles corrupted images gracefully without crashing
14. All existing image upload functionality continues to work without regression
15. API endpoints return appropriate status codes and error messages
16. All backend tests pass with 100% success rate
17. Frontend builds without errors
18. No console errors in browser during normal operation
19. Duplicate detection works for all supported image formats
20. Folder navigation is responsive and works on mobile devices
21. Documentation is updated with new features and usage instructions
22. Performance is acceptable with folders containing 100+ images

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

```bash
# Backend Tests
cd app/server && uv run pytest -v

# Specific test for image hashing
cd app/server && uv run pytest tests/core/test_image_hasher.py -v

# Specific test for duplicate detection
cd app/server && uv run pytest tests/test_image_api.py::TestDuplicateDetection -v

# Frontend Build
cd app/client && npm run build

# Start Backend Server (in separate terminal)
cd app/server && uv run python server.py

# Start Frontend Dev Server (in separate terminal)
cd app/client && npm run dev

# Manual Testing Checklist:
# 1. Navigate to http://localhost:5173/image-upload.html
# 2. Verify folder navigation panel is visible on left side
# 3. Verify each folder shows image count badge
# 4. Create a new folder "test-duplicates"
# 5. Upload sample.png to "test-duplicates" folder
# 6. Verify upload succeeds and image appears in gallery
# 7. Attempt to upload the same sample.png to "test-duplicates" again
# 8. Verify duplicate warning dialog appears
# 9. Verify similarity score is shown (should be 100%)
# 10. Verify thumbnail comparison shows both images
# 11. Click "Skip" and verify image is not uploaded again
# 12. Attempt upload again and click "Upload Anyway"
# 13. Verify second copy is uploaded with unique filename
# 14. Create folder "test-different"
# 15. Upload same sample.png to "test-different"
# 16. Verify NO duplicate warning (different folder)
# 17. Click on "test-duplicates" in folder navigation
# 18. Verify only images from that folder are displayed
# 19. Click on "test-different" in folder navigation
# 20. Verify only images from that folder are displayed
# 21. Click "All Images" option
# 22. Verify images from all folders are displayed
# 23. Verify image count badges are accurate
# 24. Upload a modified version of sample.png (cropped or resized)
# 25. Verify duplicate detection triggers based on similarity threshold
# 26. Test with all image formats (PNG, JPG, GIF, WebP, BMP)
# 27. Open browser console and verify no errors
# 28. Test on mobile viewport (if available)
# 29. Return to NL SQL page and verify functionality works
# 30. Return to image upload and verify state is preserved
```

## Notes

### Technology Choices

**Perceptual Hashing Library**
- Using `imagehash` library for robust pHash implementation
- Based on DCT (Discrete Cosine Transform) algorithm
- Provides rotation, scale, and minor modification invariance
- Well-tested and widely used in production systems
- Alternative considered: implementing custom pHash (rejected for complexity)

**Hash Storage**
- Storing pHash as TEXT in SQLite (hex string representation)
- Index on phash column for efficient similarity searches
- Similarity comparison done in Python (not SQL) for accuracy
- Consider moving to approximate nearest neighbor (ANN) for large scale

### Similarity Threshold Configuration
Default threshold is 95% similarity for duplicate detection, but this should be configurable:
- Exact duplicates: 100% similarity
- Near-duplicates (cropped, resized): 90-98% similarity
- Different images: <80% similarity

The threshold can be adjusted based on user preferences or use case requirements.

### Performance Considerations
- Hash computation time: ~100-500ms for typical images (1-5MB)
- Database query time: <50ms for folders with <1000 images
- Total duplicate check time: <2 seconds for typical scenarios
- For very large folders (10,000+ images), consider:
  - Implementing approximate nearest neighbor (ANN) search
  - Using specialized vector databases (e.g., FAISS, Milvus)
  - Caching frequently compared hashes

### Folder-Specific Detection
Duplicate detection is intentionally folder-specific to allow the same image in different contexts:
- Same image in "Logos" and "Backgrounds" folders is allowed
- Prevents false positives for images used in multiple categories
- Users can still upload same image to multiple folders if needed
- Future enhancement: Global duplicate detection option

### Duplicate Handling Options
When duplicate is detected, provide four options:
1. **Skip**: Don't upload, keep only existing image
2. **Replace**: Delete existing image, upload new one (preserves name)
3. **Rename**: Upload new image with modified name (e.g., image_copy.png)
4. **Upload Anyway**: Force upload despite duplicate (user override)

### Database Migration
Adding phash column to existing images table requires migration:
```sql
ALTER TABLE images ADD COLUMN phash TEXT;
CREATE INDEX idx_images_phash ON images(phash);
```

Existing images without phash will have NULL value. Consider background job to compute hashes for existing images.

### Future Enhancements (Not in Scope)
- Global duplicate detection across all folders
- Bulk duplicate removal tool
- Visual duplicate browser (show all duplicates in UI)
- Configurable similarity threshold in UI
- Duplicate detection during bulk import
- Similar image recommendations
- Reverse image search
- Duplicate detection for video files
- Content-based image clustering
- Machine learning-based image similarity (beyond pHash)

### Security Considerations
- Validate image format before computing hash (prevent malicious files)
- Limit hash computation time to prevent DoS attacks (timeout)
- Sanitize folder names in duplicate check endpoint
- Rate limit duplicate check API to prevent abuse
- Ensure hash comparison doesn't leak information about other users' images (if multi-tenant)

### User Experience Considerations
- Show progress indicator during hash computation
- Provide clear explanation of "similarity score"
- Allow users to see side-by-side comparison of duplicates
- Don't block upload flow - make duplicate check optional or async
- Cache duplicate check results temporarily (avoid re-checking same file)
- Provide undo option after replacing or skipping duplicates

### Accessibility
- Duplicate warning dialog must be keyboard navigable
- Screen readers should announce duplicate detection
- Thumbnail comparisons need alt text
- Folder navigation must support arrow key navigation
- Active folder indication must be perceivable (not just color)

### Mobile Considerations
- Folder navigation panel collapses to hamburger menu on small screens
- Duplicate warning dialog adapts to mobile viewport
- Touch-friendly buttons and interactions
- Consider bottom sheet for folder selection on mobile
- Optimize image hashing for mobile upload speeds

### Testing Data Requirements
Create test image set with:
- Identical duplicates (exact copies)
- Format conversions (PNG to JPG of same image)
- Resized versions (50%, 75%, 150% scale)
- Cropped versions (10%, 25% crop)
- Rotated versions (90°, 180° rotation)
- Color-adjusted versions (brightness, contrast)
- Compressed versions (different quality levels)
- Completely different images for negative tests

### Documentation Requirements
Update the following sections in README.md:
- Features: Add "Duplicate Image Detection" bullet point
- Image Upload Page section: Document duplicate detection workflow
- API Endpoints: Add POST /api/images/check-duplicate documentation
- API Endpoints: Update GET /api/folders with new response format
- Troubleshooting: Add section on duplicate detection issues

### Dependencies Added
```bash
# Backend dependencies
uv add imagehash  # Perceptual hashing library
uv add pillow     # Image processing (required by imagehash)
```

Both libraries are mature, well-maintained, and have minimal additional dependencies.
