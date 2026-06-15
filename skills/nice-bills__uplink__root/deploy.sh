#!/bin/bash
# Quick deployment script for Genesis Fundraising Platform

echo "🚀 Genesis Fundraising Platform - Deployment Helper"
echo "=================================================="
echo ""

# Check if git repo exists
if [ ! -d .git ]; then
    echo "Initializing git repository..."
    git init
    git add .
    git commit -m "Initial commit"
    echo "✅ Git repo created"
    echo ""
fi

# Check for .env files
echo "🔒 Checking .env files..."
if [ -f .env ]; then
    echo "✅ Root .env exists (won't be committed)"
fi
if [ -f frontend-vite/.env ]; then
    echo "✅ Frontend .env exists (won't be committed)"
fi
if [ -f backend/.env ]; then
    echo "✅ Backend .env exists (won't be committed)"
fi
echo ""

# Generate secure keys if not present
echo "🔑 Generating secure keys for backend..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Install it to generate keys."
else
    echo "Run this command to generate secure keys:"
    echo "python3 -c \"import secrets; print(secrets.token_hex(32))\""
    echo ""
    echo "Add these to your backend environment variables:"
    echo "  - ADMIN_KEY"
    echo "  - AGENT_API_KEY"
    echo "  - ENCRYPTION_KEY"
fi
echo ""

# Instructions
echo "📋 Next Steps:"
echo "=============="
echo ""
echo "1. Create GitHub repository:"
echo "   - Go to https://github.com/new"
echo "   - Name it 'genesis-fundraising'"
echo "   - Don't initialize with README"
echo ""
echo "2. Push code to GitHub:"
echo "   git remote add origin https://github.com/YOUR_USERNAME/genesis-fundraising.git"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "3. Deploy Frontend (Vercel):"
echo "   - Go to https://vercel.com/new"
echo "   - Import your GitHub repo"
echo "   - Set root directory: frontend-vite"
echo "   - Add environment variables from DEPLOYMENT.md"
echo ""
echo "4. Deploy Backend (choose one):"
echo ""
echo "   Option A - Render (Easiest):"
echo "   - Go to https://dashboard.render.com/blueprints"
echo "   - Click 'New Blueprint Instance'"
echo "   - Connect your repo"
echo "   - Render will use render.yaml automatically"
echo ""
echo "   Option B - Google Cloud Run:"
echo "   gcloud builds submit --tag gcr.io/YOUR_PROJECT/genesis-backend"
echo "   gcloud run deploy genesis-backend --image gcr.io/YOUR_PROJECT/genesis-backend --platform managed"
echo ""
echo "📖 Full instructions in DEPLOYMENT.md (frontend: Vercel, backend: Render)"
echo ""
echo "Good luck with the hackathon! 🎉"
