#!/bin/bash

# Cloudflare Manager Pages + D1 Deployment Script
# This script automates the deployment process

set -e

echo "🚀 Deploying Cloudflare Manager to Pages + D1"
echo "=============================================="

# Check if wrangler is installed
if ! command -v wrangler &> /dev/null; then
    echo "❌ Wrangler CLI not found. Installing..."
    npm install -g wrangler
fi

# Login check
echo "🔐 Checking Cloudflare authentication..."
if ! wrangler whoami &> /dev/null; then
    echo "Please login to Cloudflare:"
    wrangler login
fi

# Create D1 database if it doesn't exist
echo "🗄️  Setting up D1 database..."
if ! wrangler d1 list | grep -q "cloudflare-manager-db"; then
    echo "Creating D1 database..."
    wrangler d1 create cloudflare-manager-db
    echo "⚠️  Please update the database_id in wrangler.toml with the ID shown above"
    echo "Press any key to continue after updating wrangler.toml..."
    read -n 1 -s
fi

# Apply database schema
echo "📋 Applying database schema..."
wrangler d1 execute cloudflare-manager-db --file=./schema.sql

# Deploy to Pages
echo "📤 Deploying to Cloudflare Pages..."
wrangler pages deploy public/ --project-name=cloudflare-manager

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📋 Next steps:"
echo "1. Set environment variables in Cloudflare Dashboard:"
echo "   - CLOUDFLARE_EMAIL"
echo "   - CLOUDFLARE_API_KEY" 
echo "   - CLOUDFLARE_ACCOUNT_ID"
echo ""
echo "2. Optional: Set up Cloudflare Access for authentication"
echo ""
echo "3. Visit your deployed app and run the initial sync"
echo ""
echo "🎉 Your Cloudflare Manager is now running on Pages + D1!"