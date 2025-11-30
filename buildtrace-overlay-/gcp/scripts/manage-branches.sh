#!/bin/bash

# Management script for branch deployments
# Lists all deployed branch services and provides cleanup options

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

PROJECT_ID="buildtrace"
REGION="us-central1"

echo -e "${BLUE}🌿 BuildTrace Branch Deployment Manager${NC}"
echo "========================================="

# Function to list all services
list_services() {
    echo -e "${CYAN}📋 Fetching deployed services...${NC}"
    echo ""

    # Get all services that start with buildtrace-overlay
    SERVICES=$(gcloud run services list \
        --project=${PROJECT_ID} \
        --region=${REGION} \
        --format="table(name,metadata.annotations.'branch':label='BRANCH',status.url:label='URL',metadata.creationTimestamp.date('%Y-%m-%d %H:%M'):label='CREATED')" \
        --filter="metadata.name:buildtrace-overlay*" 2>/dev/null || echo "")

    if [ -z "$SERVICES" ]; then
        echo -e "${YELLOW}No services found or authentication required.${NC}"
        echo "Please run: gcloud auth login"
        return 1
    fi

    echo "$SERVICES"
    echo ""
}

# Function to delete a service
delete_service() {
    local SERVICE_NAME=$1

    if [ "$SERVICE_NAME" = "buildtrace-overlay" ]; then
        echo -e "${RED}⚠️  Cannot delete production service!${NC}"
        return 1
    fi

    echo -e "${YELLOW}🗑️  Deleting service: $SERVICE_NAME${NC}"
    gcloud run services delete ${SERVICE_NAME} \
        --region=${REGION} \
        --project=${PROJECT_ID} \
        --quiet

    echo -e "${GREEN}✅ Service deleted successfully${NC}"
}

# Function to get service details
service_details() {
    local SERVICE_NAME=$1

    echo -e "${CYAN}📊 Service Details: $SERVICE_NAME${NC}"
    echo ""

    gcloud run services describe ${SERVICE_NAME} \
        --region=${REGION} \
        --project=${PROJECT_ID} \
        --format="yaml(metadata.name,metadata.annotations,spec.template.spec.containers[0].image,status.url,status.traffic)"
}

# Main menu
show_menu() {
    echo "Choose an action:"
    echo "  1) List all branch deployments"
    echo "  2) Delete a branch deployment"
    echo "  3) Delete all non-production deployments"
    echo "  4) Show service details"
    echo "  5) Exit"
    echo ""
}

# Main loop
while true; do
    show_menu
    read -p "Enter choice [1-5]: " choice

    case $choice in
        1)
            list_services
            ;;
        2)
            list_services
            read -p "Enter service name to delete (or 'cancel' to abort): " SERVICE_TO_DELETE
            if [ "$SERVICE_TO_DELETE" != "cancel" ] && [ -n "$SERVICE_TO_DELETE" ]; then
                read -p "Are you sure you want to delete $SERVICE_TO_DELETE? (yes/no): " CONFIRM
                if [ "$CONFIRM" = "yes" ]; then
                    delete_service "$SERVICE_TO_DELETE"
                fi
            fi
            ;;
        3)
            echo -e "${RED}⚠️  WARNING: This will delete ALL branch deployments except production!${NC}"
            read -p "Are you sure? (yes/no): " CONFIRM
            if [ "$CONFIRM" = "yes" ]; then
                SERVICES=$(gcloud run services list \
                    --project=${PROJECT_ID} \
                    --region=${REGION} \
                    --format="value(name)" \
                    --filter="metadata.name:buildtrace-overlay-*" 2>/dev/null || echo "")

                if [ -n "$SERVICES" ]; then
                    for SERVICE in $SERVICES; do
                        delete_service "$SERVICE"
                    done
                else
                    echo -e "${YELLOW}No branch deployments found.${NC}"
                fi
            fi
            ;;
        4)
            list_services
            read -p "Enter service name for details: " SERVICE_NAME
            if [ -n "$SERVICE_NAME" ]; then
                service_details "$SERVICE_NAME"
            fi
            ;;
        5)
            echo -e "${GREEN}Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option. Please try again.${NC}"
            ;;
    esac

    echo ""
    echo "Press Enter to continue..."
    read
    clear
done