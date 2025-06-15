#!/bin/bash

echo "🚀 Installing MCP Servers for Enhanced Claude Functionality"
echo "=========================================================="

# Sequential Thinking
echo "📝 Installing Sequential Thinking MCP Server..."
claude mcp add sequential-thinking -s user -- npx -y u/modelcontextprotocol/server-sequential-thinking

# Filesystem
echo "📁 Installing Filesystem MCP Server..."
claude mcp add filesystem -s user -- npx -y u/modelcontextprotocol/server-filesystem ~/Documents ~/Desktop ~/Downloads ~/Projects

# Puppeteer
echo "🎭 Installing Puppeteer MCP Server..."
claude mcp add puppeteer -s user -- npx -y u/modelcontextprotocol/server-puppeteer

# Web Fetching
echo "🌐 Installing Web Fetch MCP Server..."
claude mcp add fetch -s user -- npx -y u/kazuph/mcp-fetch

# Browser Tools
echo "🔧 Installing Browser Tools MCP Server..."
claude mcp add browser-tools -s user -- npx -y u/agentdeskai/browser-tools-mcp@1.2.1

echo ""
echo "✅ MCP Server Installation Complete!"
echo ""

# Check what's been installed
echo "📋 Checking installed MCP servers..."
claude mcp list

echo ""
echo "🎉 Setup complete! Enhanced Claude functionality now available."
echo ""
echo "💡 These MCP servers will enhance VectorCraft 2.0 development with:"
echo "   • Sequential thinking for complex algorithm design"
echo "   • Enhanced filesystem operations"
echo "   • Web automation for testing"
echo "   • Advanced web scraping capabilities"
echo "   • Browser automation for UI testing"
echo ""
echo "🤔 Life choices questioned successfully! ✓"