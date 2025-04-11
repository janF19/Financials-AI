#!/bin/bash



# Create .env file
touch .env

# Create backend directory and its subdirectories
mkdir -p backend/config backend/data backend/models backend/processors backend/routes backend/storage backend/auth backend/temp

# Create files in backend
touch backend/api.py
touch backend/main.py
touch backend/database.py
touch backend/requirements.txt

# Create files in config
touch backend/config/__init__.py
touch backend/config/settings.py

# Create files in data
touch backend/data/__init__.py

# Create files in models
touch backend/models/__init__.py
touch backend/models/user.py
touch backend/models/report.py

# Create files in processors
touch backend/processors/__init__.py
touch backend/processors/pdf_processor.py
touch backend/processors/report_generator.py
touch backend/processors/valuation_processor.py
touch backend/processors/workflow.py

# Create files in routes
touch backend/routes/__init__.py
touch backend/routes/auth.py
touch backend/routes/financials.py
touch backend/routes/dashboard.py
touch backend/routes/reports.py
touch backend/routes/health.py

# Create files in storage
touch backend/storage/__init__.py
touch backend/storage/report_archive.py

# Create files in auth
touch backend/auth/__init__.py
touch backend/auth/dependencies.py

# Create temp directory (no files needed, just a directory for temporary storage)
mkdir -p backend/temp

mkdir frontend

echo "Directory structure and empty files created successfully in financial-valuation-system/"