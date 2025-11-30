#!/bin/bash

PROJECT_ID="buildtrace"
INSTANCE_NAME="buildtrace-postgres"
DB_NAME="buildtrace_db"
DB_USER="buildtrace_user"

echo "BuildTrace Database Setup - Fixed Version"
echo "=========================================="
echo ""

# Check if database exists
echo "Checking if database exists..."
DB_EXISTS=$(gcloud sql databases list --instance=$INSTANCE_NAME --project=$PROJECT_ID --format="value(name)" | grep -c "^${DB_NAME}$")

if [ "$DB_EXISTS" -eq 1 ]; then
    echo "✅ Database '$DB_NAME' already exists"
else
    echo "Creating database: $DB_NAME"
    gcloud sql databases create $DB_NAME \
        --instance=$INSTANCE_NAME \
        --project=$PROJECT_ID
fi

# Generate a secure password
echo ""
echo "Generating secure password for database user..."
DB_PASSWORD=$(openssl rand -base64 32)

# Check if user exists
echo "Checking if user exists..."
USER_EXISTS=$(gcloud sql users list --instance=$INSTANCE_NAME --project=$PROJECT_ID --format="value(name)" | grep -c "^${DB_USER}$")

if [ "$USER_EXISTS" -eq 1 ]; then
    echo "User '$DB_USER' already exists. Setting new password..."
    gcloud sql users set-password $DB_USER \
        --instance=$INSTANCE_NAME \
        --password="$DB_PASSWORD" \
        --project=$PROJECT_ID
else
    echo "Creating database user: $DB_USER"
    gcloud sql users create $DB_USER \
        --instance=$INSTANCE_NAME \
        --password="$DB_PASSWORD" \
        --project=$PROJECT_ID
fi

echo ""
echo "✅ Database setup complete!"
echo ""
echo "=========================================="
echo "IMPORTANT - Save these credentials:"
echo "=========================================="
echo ""
echo "Database Password: $DB_PASSWORD"
echo ""
echo "Add these to your .env file:"
echo "----------------------------"
echo "DB_USER=$DB_USER"
echo "DB_PASS=$DB_PASSWORD"
echo "DB_NAME=$DB_NAME"
echo "DB_HOST=localhost"
echo "DB_PORT=5432"
echo "INSTANCE_CONNECTION_NAME=$PROJECT_ID:us-central1:$INSTANCE_NAME"
echo "USE_CLOUD_SQL_AUTH_PROXY=true"
echo ""
echo "=========================================="
echo ""
echo "Would you like to automatically update your .env file? (y/n)"
read -r response

if [[ "$response" == "y" || "$response" == "Y" ]]; then
    # Update .env file
    if [ -f .env ]; then
        # Update existing values or add if not present
        sed -i '' "s/^DB_USER=.*/DB_USER=$DB_USER/" .env
        sed -i '' "s/^DB_PASS=.*/DB_PASS=$DB_PASSWORD/" .env
        sed -i '' "s/^DB_NAME=.*/DB_NAME=$DB_NAME/" .env
        sed -i '' "s/^DB_HOST=.*/DB_HOST=localhost/" .env
        sed -i '' "s/^DB_PORT=.*/DB_PORT=5432/" .env
        sed -i '' "s/^INSTANCE_CONNECTION_NAME=.*/INSTANCE_CONNECTION_NAME=$PROJECT_ID:us-central1:$INSTANCE_NAME/" .env
        sed -i '' "s/^USE_CLOUD_SQL_AUTH_PROXY=.*/USE_CLOUD_SQL_AUTH_PROXY=true/" .env

        echo "✅ .env file updated successfully!"
    else
        echo "❌ .env file not found. Please create it from .env.example first."
    fi
else
    echo "Please manually update your .env file with the credentials above."
fi

echo ""
echo "Next steps:"
echo "1. Start Cloud SQL Proxy in a new terminal:"
echo "   ./cloud-sql-proxy --instances=$PROJECT_ID:us-central1:$INSTANCE_NAME=tcp:5432"
echo ""
echo "2. Initialize database tables:"
echo "   python migrations/init_database.py"