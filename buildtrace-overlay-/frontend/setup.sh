#!/bin/bash

echo "🚀 Setting up BuildTrace Frontend"
echo "================================="

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Create environment file
if [ ! -f .env.local ]; then
    echo "🔧 Creating .env.local file..."
    cp .env.local.example .env.local
    echo "✅ Created .env.local with production backend URL"
else
    echo "ℹ️  .env.local already exists"
fi

# Show current configuration
echo ""
echo "📋 Current Configuration:"
echo "------------------------"
if [ -f .env.local ]; then
    grep "NEXT_PUBLIC_API_URL" .env.local
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Your frontend will connect to:"
echo "✅ Production Cloud Run Backend"
echo "✅ Cloud SQL Database with real data"
echo "✅ Google Cloud Storage for files"
echo "✅ OpenAI API for AI analysis"
echo ""
echo "To start the development server:"
echo "  npm run dev"
echo ""
echo "The app will be available at http://localhost:3000"
echo ""
echo "Note: The backend already has authentication disabled for testing."
echo "You can start using the app immediately!"