# BuildTrace AI - Outstanding Questions

This document tracks questions and clarifications needed for the project implementation.

## User Interface & Experience

### Q1: DWG/DXF File Rendering
**Status:** Open  
**Priority:** Medium  
**Question:** Should DWG and DXF files be rendered natively in the browser, or is it acceptable to treat them as upload-only formats with conversion to PDF for viewing?

**Context:** Native CAD file rendering in browsers requires specialized libraries (like AutoCAD's Forge Viewer) which may have licensing costs and complexity. Alternative approaches:
1. Convert to PDF server-side for viewing
2. Show file information only without preview
3. Use a third-party service for rendering

**Impact:** Affects the PDF service interface design and user experience for CAD file workflows.

---

### Q2: Debug Info Button Functionality
**Status:** Open  
**Priority:** Low  
**Question:** What specific information should the "Debug Info" button expose? Should it show raw comparison result JSON, processing logs, or both?

**Context:** The UI includes a Debug Info button in the comparison toolbar, but the specific content isn't defined.

**Options:**
1. Raw JSON of the comparison result
2. Processing timeline and performance metrics
3. File metadata and processing parameters
4. All of the above in a structured dialog

---

### Q3: View Mode Overlay Slider Behavior
**Status:** Open  
**Priority:** Low  
**Question:** In overlay mode, should the opacity slider affect both images or just the revised drawing over the baseline?

**Current Implementation:** Slider controls revised drawing opacity over baseline.  
**Alternative:** Crossfade between baseline and revised with slider controlling the blend ratio.

---

## Technical Implementation

### Q4: File Size Limits for Production
**Status:** Open  
**Priority:** Medium  
**Question:** Are the 50MB file size limits appropriate for production use? Should different limits apply to different file types?

**Context:** Construction drawings can be very large, especially DWG files with complex geometry.

**Considerations:**
- Network bandwidth for uploads
- Server storage costs
- Processing time constraints
- Browser memory limits for rendering

---

### Q5: Real-time Processing Updates
**Status:** Open  
**Priority:** Low  
**Question:** Should the comparison processing show detailed progress updates (e.g., "Parsing baseline...", "Analyzing differences...") or just a simple progress bar?

**Current Implementation:** Simple progress bar with generic "Processing..." message.

---

### Q6: Export Report Customization
**Status:** Open  
**Priority:** Medium  
**Question:** What level of customization should be available for PDF reports? Should users be able to:
- Select which sections to include
- Choose from multiple report templates
- Add custom notes or annotations
- Include/exclude specific changes

**Current Implementation:** Fixed report format with all available data.

---

## Data Management

### Q7: Recent Comparisons Persistence
**Status:** Open  
**Priority:** Medium  
**Question:** How long should recent comparisons be stored? Should there be a limit on the number of items?

**Current Implementation:** Stored indefinitely in localStorage.

**Considerations:**
- Browser storage limits
- User privacy preferences
- Performance with large datasets

---

### Q8: File Cleanup Strategy
**Status:** Open  
**Priority:** High  
**Question:** When should uploaded files and generated thumbnails be cleaned up? How should we handle:
- User navigating away during upload
- Browser crashes or connection losses
- Completed comparisons after N days

**Impact:** Affects memory usage and storage costs.

---

## Integration & Deployment

### Q9: Authentication Requirements
**Status:** Open  
**Priority:** High  
**Question:** What authentication method should be implemented for production?

**Options:**
1. Simple username/password
2. OAuth with Google/Microsoft
3. Enterprise SSO integration
4. No authentication (public access)

**Impact:** Affects the overall architecture and deployment strategy.

---

### Q10: API Rate Limiting
**Status:** Open  
**Priority:** Medium  
**Question:** Should the application implement rate limiting for comparison operations? What would be appropriate limits?

**Context:** AI-powered comparison operations may be resource-intensive.

**Considerations:**
- Processing time per comparison
- Server capacity
- User experience balance
- Abuse prevention

---

## Blocking Issues

Currently no blocking issues. All questions have reasonable defaults implemented that can be adjusted based on clarification.

---

## Resolution Process

1. **High Priority:** Requires immediate clarification before production deployment
2. **Medium Priority:** Should be clarified during development cycle
3. **Low Priority:** Can be addressed in future iterations

**Contact:** Add questions to this document and they will be addressed in the next planning meeting.
