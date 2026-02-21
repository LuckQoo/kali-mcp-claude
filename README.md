# kali-mcp-claude

先決條件
系統需求：
macOS（已在 Apple Silicon 測試）
已安裝並執行Docker Desktop 4.47+
Python 3.13+
已安裝Claude 桌面應用程式
核實先決條件：

# Check Docker
docker --version
# Should show: Docker version 28.4.x or higher

# Check Python
python3 --version
# Should show: Python 3.13.x or higher

# Check Claude Desktop is installed
ls -la ~/Library/Application\ Support/Claude/
# Should show claude_desktop_config.json

逐步設定
步驟 1：建立專案目錄

# Create project folder
mkdir -p ~/kali-mcp-server
cd ~/kali-mcp-server

# Create Python virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install MCP dependencies
pip install mcp fastmcp

