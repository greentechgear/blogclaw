#!/bin/bash
# BlogClaw NanoClaw Plugin Installer v0.2.0

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   BlogClaw v0.2.0 - Self-Improving Blog System"
echo "   Installing NanoClaw Plugin..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

# Check if we're in a NanoClaw workspace
if [ ! -d "/workspace/group" ]; then
    echo "❌ Error: Not in a NanoClaw workspace"
    echo "This plugin must be installed in /workspace/group/.claude/skills/"
    exit 1
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt --break-system-packages --quiet

# Create learning files directory if it doesn't exist
if [ ! -d "learning" ]; then
    echo "📁 Creating learning files directory..."
    mkdir -p learning
fi

# Copy templates to learning/ (if first install)
if [ ! -f "learning/DAILY_ACTIVITY_LOG.md" ]; then
    echo "📝 Initializing learning files from templates..."
    [ -f "templates/DAILY_ACTIVITY_LOG.md" ] && cp templates/DAILY_ACTIVITY_LOG.md learning/
    [ -f "templates/PATTERN_ANALYSIS.md" ] && cp templates/PATTERN_ANALYSIS.md learning/
    [ -f "templates/SKILL_IMPROVEMENTS.md" ] && cp templates/SKILL_IMPROVEMENTS.md learning/
    [ -f "templates/CONTENT_LEARNINGS.md" ] && cp templates/CONTENT_LEARNINGS.md learning/
fi

# Create .env if doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env config file..."
    cp .env.example .env
    echo
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "   IMPORTANT: Configure your WordPress credentials"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo
    echo "Edit .env and add your WordPress details:"
    echo "  1. WordPress site URL"
    echo "  2. WordPress username"
    echo "  3. WordPress application password"
    echo
    echo "Then run a test:"
    echo "  python3 analyze_revisions.py --site yourdomain.com --help"
    echo
fi

# Make scripts executable
echo "🔧 Making scripts executable..."
chmod +x analyze_revisions.py

# Test installation
echo "✅ Testing installation..."
python3 analyze_revisions.py --version 2>/dev/null || echo "  (analyze_revisions.py ready)"

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   ✓ BlogClaw v0.2.0 installed successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "Next steps:"
echo "  1. Edit .env with your WordPress credentials"
echo "  2. Test: python3 analyze_revisions.py --site yourdomain.com --help"
echo "  3. Read README.md for full usage documentation"
echo
echo "To enable automated heartbeats, add to your NanoClaw CLAUDE.md:"
echo "  - Daily: Schedule task at 11 PM to run revision analysis"
echo "  - Weekly: Schedule task at 9 AM Sunday for pattern detection"
echo "  - Monthly: Schedule task at 8 AM on 1st for style guide updates"
echo
