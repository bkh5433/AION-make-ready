# AION Vista

AION Vista is a full-stack application designed for viewing work order completion data, generating detailed break-even
reports, and facilitating operational decision-making.

## Author

Created and maintained by Brandon Hightower

[//]: # (© 2024 AION Management  )
Built for AION Management Data Analytics and Operations

## Features

- **Property Search**: Advanced real-time search and filtering with debounced API calls
- **Work Order Analytics**: Comprehensive KPI monitoring including:
    - Completion rates with severity indicators
    - Task status tracking
- **Dynamic Report Generation**:
    - Customized Excel reports with conditional formatting
    - Batch report generation capabilities
    - Progress tracking for large downloads
- **User Authentication**:
    - JWT-based secure authentication
    - Role-based access control (admin/user)
    - Automatic token refresh
- **Admin Tools**:
    - User management dashboard
    - System performance monitoring
    - Cache control operations
    - Data freshness indicators

## Architecture

### Backend Layer

Flask-based backend with comprehensive data processing capabilities:

- **Core Components**:
    - `app.py`: Application initialization with route configuration
    - `db_connection.py`: Database connection pooling and management
    - `sql_queries.py`: SQL queries for retrieving raw property data
    - `excel_generator.py`: Advanced Excel report generation
    - `auth_middleware.py`: JWT authentication handling
    - `monitoring.py`: Performance metrics tracking
    - `cache_module.py`: Advanced caching system with the following features:
        - Configurable refresh intervals with dynamic adjustment
        - Non-blocking concurrent refresh mechanism
        - Version-based staleness detection
        - Fallback to stale data during errors
        - Comprehensive metrics tracking
        - Health monitoring with data freshness indicators
        - Retry mechanism with configurable attempts
    - `property_search.py`: Efficient property search implementation:
        - In-memory indexing for fast lookups
        - Case-insensitive name-based search
        - Property key-based direct access
        - Built-in analytics calculation
        - Error handling and validation
        - Performance metrics logging
        - Flexible date parsing

- **Key Functions**:
    - Token-based route protection
    - Efficient property search with caching
    - Asynchronous report generation
    - Real-time data freshness monitoring

### Frontend Layer

React-based UI with Tailwind CSS styling:

- **Key Components**:
    - `PropertyReportGenerator.jsx`: Main property management interface
    - `DownloadManager.jsx`: File download progress tracking
    - `DataFreshnessIndicator.jsx`: Real-time data status display
    - `FloatingDownloadButton.jsx`: Dynamic download progress indicator
    - `PropertyRow.jsx`: Individual property display and management

- **Features**:
    - Dark/light theme support
    - Real-time search with debouncing
    - Dynamic download management
    - Toast notifications for user feedback

### Database Layer

SQL-based data management:

- **Core Features**:
    - Connection pooling for performance
    - Parameterized queries for security
    - Efficient data retrieval patterns

### Cache System

Advanced caching implementation for optimal performance:

- **Configuration Management**:
    - Dynamic refresh intervals based on RealPage data update patterns
    - Configurable base refresh interval (default: 300s)
    - Maximum refresh interval for force updates
    - Customizable retry attempts and delays
    - Update window configuration for expected data changes

- **Concurrent Access Handling**:
    - Non-blocking refresh mechanism
    - Waiters management for concurrent requests
    - Thread-safe operations with proper locking
    - Stale data serving during updates
    - Optimized version checking with minimal database load

- **Health Monitoring**:
    - Comprehensive metrics tracking:
        - Access counts and patterns
        - Refresh success/failure rates
        - Cache age and staleness
        - Concurrent access statistics
        - Average refresh and wait times
    - Real-time health status reporting
    - Data freshness indicators
    - Performance analytics

### Property Search System

Efficient property search implementation with advanced features:

- **Search Capabilities**:
    - Fast in-memory indexing
    - Case-insensitive name matching
    - Direct property key lookups
    - Combined search criteria support
    - Partial name matching

- **Data Processing**:
    - Automatic property model validation
    - Work order metrics calculation
    - Analytics generation on demand
    - Flexible date parsing for multiple formats
    - Error handling with detailed logging

- **Performance Features**:
    - Optimized data structure for quick lookups
    - Minimal memory footprint
    - Performance metrics tracking
    - Search execution timing
    - Success rate monitoring

### Reporting Layer

Advanced Excel report generation with sophisticated features:

- **Excel Generator**:
    - Template-based report generation
    - Multi-property report support
    - Dynamic worksheet creation
    - Comprehensive formatting:
        - Custom fonts and styles
        - Conditional formatting
        - Cell alignment and wrapping
        - Border customization
    - Error handling and logging
    - Progress tracking
    - Batch processing capabilities

- **What-If Analysis**:
    - Dynamic table generation
    - Break-even calculations
    - Performance projections
    - Real-time metric updates:
        - Daily completion rates
        - Monthly projections
        - Break-even targets
        - Current output analysis
    - Visual indicators:
        - Color-coded status
        - Performance thresholds
        - Target highlighting
    - Formula evaluation engine:
        - Excel formula parsing
        - Range calculations
        - Cell reference resolution
        - Mathematical operations

- **Report Features**:
    - Customized Excel formatting
    - Dynamic date ranges
    - Work order metrics:
        - Open work orders
        - Completion rates
        - Processing times
        - Performance indicators
    - Automated calculations
    - Data validation
    - Error tracking

- **Output Management**:
    - Organized file structure (/reports/YYYY/MM/DD/)
    - Timestamped outputs
    - Multi-sheet support
    - Template preservation
    - File cleanup handling

### Auth System

Comprehensive authentication and authorization system:

- **Core Security Features**:
    - JWT-based authentication with secure token generation
    - Firebase integration for user management
    - Role-based access control (RBAC)
    - Password hashing with salt using SHA-256
    - Automatic token expiration (24-hour validity)

- **User Management**:
    - Secure user creation and storage
    - Role management (admin/user)
    - Last login tracking
    - Password change requirements
    - User activity status monitoring

- **Authentication Flow**:
    - Username/password verification
    - JWT token generation and validation
    - Automatic token refresh handling
    - Session management
    - Secure token storage

- **Authorization Features**:
    - Route protection with decorators
    - Role-based route access
    - Admin-only operations
    - Firebase Firestore integration
    - Real-time role verification

- **Security Measures**:
    - Secure password storage with salting
    - Token-based API protection
    - Environment-based configuration
    - Comprehensive error handling
    - Detailed security logging

### Admin Layer

Advanced system management tools:

- **Capabilities**:
    - User CRUD operations
    - System metrics monitoring
    - Cache management
    - Data refresh controls
    - Performance tracking

## Tech Stack

### Backend

- **Framework**: Flask
- **Database**: SQL with connection pooling
- **Task Processing**: Custom async queue system
- **Libraries**:
    - openpyxl: Excel generation
    - apscheduler: Task scheduling
    - JWT: Authentication
- **Monitoring**:
    - Custom logging system
    - Health check endpoints

### Frontend

- **Framework**: React
- **Styling**:
    - Tailwind CSS
    - Dark/light theme support
- **State Management**:
    - React hooks
    - Context API
- **Components**:
    - Custom UI components
    - Real-time indicators
    - Progress tracking

## User Workflow

### 1. Authentication & Access

- User logs in with credentials
- System validates and generates JWT token
- Role-based access determines available features
- Session remains active for 24 hours with auto-refresh

### 2. Property Search & Selection

- Real-time property search with debouncing
- Filter properties by name or property key
- View property details and current metrics
- Select properties for report generation

### 3. Data Analysis

- System retrieves property data with caching
- Real-time calculation of key metrics:
    - Work order completion rates
    - Break-even analysis
    - Performance indicators
- Data freshness indicators show latest updates

### 4. Report Generation

- Select single or multi-property report
- System generates Excel reports with:
    - Current performance metrics
    - What-If analysis tables
    - Break-even calculations
    - Visual performance indicators
- Progress tracking for large reports
- Organized output in dated folders

### 5. Monitoring & Updates

- Real-time data freshness monitoring
- Cache updates based on data changes
- Performance metrics tracking
- System health monitoring
- Admin tools for system management

### 6. Data Management

- Automatic data refresh cycles
- Version-based staleness detection
- Error handling with fallback options
- Comprehensive logging
- Data validation and cleanup