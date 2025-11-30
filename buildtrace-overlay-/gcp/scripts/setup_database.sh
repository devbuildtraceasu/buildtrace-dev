#!/bin/bash

# Database setup script - run after Cloud SQL instance is ready

PROJECT_ID="buildtrace"
INSTANCE_NAME="buildtrace-postgres"
DB_NAME="buildtrace_db"
DB_USER="buildtrace_user"

echo "Setting up database and user..."

# Create database
echo "Creating database: $DB_NAME"
gcloud sql databases create $DB_NAME \
    --instance=$INSTANCE_NAME \
    --project=$PROJECT_ID

# Create user
echo "Creating database user: $DB_USER"
echo "You'll be prompted to set a password. Please save it for your .env file!"
gcloud sql users create $DB_USER \
    --instance=$INSTANCE_NAME \
    --project=$PROJECT_ID

echo "Database setup complete!"
echo ""
echo "IMPORTANT: Update your .env file with:"
echo "  DB_USER=$DB_USER"
echo "  DB_PASS=<the password you just set>"
echo "  DB_NAME=$DB_NAME"
echo "  INSTANCE_CONNECTION_NAME=$PROJECT_ID:us-central1:$INSTANCE_NAME"