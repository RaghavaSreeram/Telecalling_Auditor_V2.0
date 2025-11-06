#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: |
  Implement a CRM Integration module with left-nav tab showing CRM → App communication for each call.
  Features: user/agent mappings, recording reference (URL/ID), transcript status, sync logs, linkage to audit records.
  RBAC: Auditor (read-only assigned records), Manager (full access + resync/export).
  
  Functional Requirements:
  1. Navigation & Routing: /crm (list), /crm/:id (detail), /crm/status (health)
  2. List View: Paginated table with filters, search, and RBAC
  3. Detail View: Rich metadata, transcript preview, sync logs, actions (resync, validate)
  4. Health Panel: Stats, trends, retry failed syncs
  5. Security: RBAC enforcement server-side

backend:
  - task: "CRM Models - Define Pydantic models for CRM records, sync logs, agent mappings, health stats"
    implemented: true
    working: true
    file: "/app/backend/crm_models.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Created CRM models with TranscriptStatus, SyncStatus, SyncAction enums and models for CRMRecord, CRMSyncLog, AgentMapping, CRMHealthStats, SyncTrendData. Fixed syntax error in AgentMapping."
  
  - task: "CRM Service - Core service for mock data generation, RBAC filtering, sync operations"
    implemented: true
    working: "NA"
    file: "/app/backend/crm_service.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Updated CRMService with seed_mock_data method to generate 50 mock CRM records with S3 URLs, agent mappings, sync logs. Includes RBAC filtering, resync, validation, health stats, and trend calculations."
  
  - task: "CRM API Endpoints - REST endpoints for CRM operations"
    implemented: true
    working: "NA"
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Added CRM endpoints: POST /api/crm/seed, GET /api/crm/calls (with filters/pagination), GET /api/crm/calls/{call_id}, POST /api/crm/calls/{call_id}/resync, POST /api/crm/calls/{call_id}/validate-mapping, GET /api/crm/health, GET /api/crm/health/trends, POST /api/crm/retry-failed. All with RBAC checks."

frontend:
  - task: "CRM Navigation - Add CRM Integration tab to left nav"
    implemented: false
    working: "NA"
    file: "/app/frontend/src/components/Layout.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Not yet implemented. Will add CRM Integration nav item with icon."
  
  - task: "CRM List View - Paginated table with filters and search"
    implemented: false
    working: "NA"
    file: "/app/frontend/src/pages/CRMList.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Not yet implemented. Will create list page with table, filters, pagination."
  
  - task: "CRM Detail View - Detail drawer/page with rich metadata"
    implemented: false
    working: "NA"
    file: "/app/frontend/src/pages/CRMDetail.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Not yet implemented. Will create detail page with sync logs, transcript preview, actions."
  
  - task: "CRM Health Panel - Health statistics and trends"
    implemented: false
    working: "NA"
    file: "/app/frontend/src/pages/CRMHealth.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Not yet implemented. Will create health panel with stats cards and trend chart."

metadata:
  created_by: "main_agent"
  version: "1.0"
  test_sequence: 0
  run_ui: false

test_plan:
  current_focus:
    - "CRM Service - Core service for mock data generation, RBAC filtering, sync operations"
    - "CRM API Endpoints - REST endpoints for CRM operations"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
  - agent: "main"
    message: |
      Backend implementation complete for CRM Integration module:
      1. Fixed syntax error in crm_models.py (missing closing parenthesis)
      2. Updated crm_service.py with seed_mock_data method and helper methods
      3. Added 9 CRM API endpoints in server.py with full RBAC enforcement
      4. Initialized crm_service in server.py
      5. Backend service restarted successfully
      
      Please test the following:
      - POST /api/crm/seed (admin only) - seed 50 mock CRM records
      - GET /api/crm/calls (all roles, RBAC filtered) - list with pagination/filters
      - GET /api/crm/calls/{call_id} (all roles, RBAC) - get detail
      - POST /api/crm/calls/{call_id}/resync (manager/admin) - resync record
      - GET /api/crm/health (manager/admin) - get health stats
      - GET /api/crm/health/trends (manager/admin) - get 7-day trends
      - POST /api/crm/retry-failed (manager/admin) - retry all failed syncs
      
      Use existing admin credentials for seeding and full access.
      Test RBAC: auditor should only see their team's records.