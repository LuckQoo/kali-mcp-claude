# kali-mcp-claude

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

步驟 2：建立 MCP 伺服器
創造server.py：

nano server.py

使其可執行：

chmod +x server.py

步驟 3：設定 Claude 桌面
編輯 Claude 的設定檔：

nano ~/Library/Application\ Support/Claude/claude_desktop_config.json

將所有內容替換為：

{
  "mcpServers": {
    "kali-security-tools": {
      "command": "/Users/YOUR_USERNAME/kali-mcp-server/venv/bin/python",
      "args": [
        "/Users/YOUR_USERNAME/kali-mcp-server/server.py"
      ]
    }
  }
}


尋找您的用戶名：

whoami

步驟 4：在本機測試 MCP 伺服器
連接 Claude 之前，請先確認伺服器運作正常：

cd ~/kali-mcp-server
source venv/bin/activate
python server.py

伺服器將等待輸入。按Ctrl+C停止。

原因：在連接到 Claude 之前，本機測試可以確認所有相依性都已安裝，且伺服器可以啟動。

步驟 5：部署存在漏洞的測試應用程式
設定 DVWA（Damn Vulnerable Web Application，該應用程式存在安全漏洞）進行測試：

# Create the pentest network
docker network create pentest-net

# Run DVWA on the pentest network
docker run -d \
  --name dvwa-test \
  --network pentest-net \
  -p 8080:80 \
  vulnerables/web-dvwa

# Wait for it to start
sleep 10

# Verify it's running
curl -I http://localhost:8080

你應該可以看到HTTP頭部資訊。造訪網址：http://localhost:8080

預設登入名：admin/password
原因： DVWA 是一款故意設計成存在漏洞的 Web 應用程序，專為安全測試練習而設計。攻擊它是安全的，並且有助於驗證您的工具是否正常運作。

步驟 6：連接 Claude 桌面
完全退出 Claude Desktop（Cmd+Q）
重新打開 Claude Desktop
在聊天視窗右下角找到🔌圖標
確認：

點擊🔌圖標
你應該可以看到“kali-security-tools”的清單。
它應該顯示為“已連接”，並帶有綠色指示器。
原因： Claude Desktop 在啟動時讀取其配置並建立與 MCP 伺服器的連線。

步驟 7：測試集成
在 Claude Desktop 中，請嘗試以下提示：

測試 1：檢查權限

"Use check_container_permissions to verify the Kali container has full privileges"

預期結果：應顯示uid=0(root)並確認 nmap 可用。

測試 2：掃描主機服務
"Use scan_host_service to check what's running on port 8080 on my Mac"

預期結果：應偵測到執行在 Apache 上的 DVWA Web 伺服器。

測試3：直接掃描容器
"Use nmap to scan the dvwa-test container on port 80 with version detection"
測試 4：網路技術指紋識別
"Use whatweb to analyze http://dvwa-test with aggression level 3"
測試 5：列出所有工具
"Use list_available_tools to show me what security tools are available"
增加更多工具
方法一：使用現有的 Kali 工具
該容器包含數百種工具。只需新增@mcp.tool()功能：

範例：新增 Dirb（目錄掃描器）
添加到server.py：
@mcp.tool()
def dirb_scan(url: str, wordlist: str = "/usr/share/wordlists/dirb/common.txt") -> str:
    """
    Scan web directories and files with Dirb.
    
    Args:
        url: Target URL (e.g., 'http://dvwa-test')
        wordlist: Path to wordlist (default: common.txt)
    
    Returns:
        Dirb scan results showing discovered directories
    
    IMPORTANT: Only scan websites you own or have permission to test!
    """
    
    command = ["dirb", url, wordlist, "-r", "-S"]
    result = run_in_kali(command, timeout=600)
    
    if result["success"]:
        return f"✅ Dirb scan completed:\n\n{result['stdout']}"
    else:
        error = result.get('error') or result.get('stderr', 'Unknown error')
        return f"❌ Dirb scan failed:\n{error}"

範例：新增 Hydra（登入暴力破解程式）
@mcp.tool()
def hydra_attack(
    target: str,
    service: str,
    username: str,
    password_file: str = "/usr/share/wordlists/rockyou.txt"
) -> str:
    """
    Perform password bruteforce attack with Hydra.
    
    Args:
        target: Target host (e.g., 'dvwa-test', 'host.docker.internal')
        service: Service to attack (e.g., 'ssh', 'ftp', 'http-post-form')
        username: Username to test
        password_file: Path to password wordlist
    
    Returns:
        Hydra attack results
    
    ⚠️  CRITICAL: Only use on systems you own! Unauthorized access is illegal!
    """
    
    command = ["hydra", "-l", username, "-P", password_file, "-f", target, service]
    result = run_in_kali(command, timeout=900)
    
    if result["success"]:
        return f"✅ Hydra completed:\n\n{result['stdout']}"
    else:
        error = result.get('error') or result.get('stderr', 'Unknown error')
        return f"❌ Hydra failed:\n{error}"

  範例：添加 Metasploit
@mcp.tool()
def metasploit_search(query: str) -> str:
    """
    Search Metasploit exploits and modules.
    
    Args:
        query: Search term (e.g., 'apache', 'windows smb')
    
    Returns:
        List of matching exploits and modules
    """
    
    command = ["msfconsole", "-q", "-x", f"search {query}; exit"]
    result = run_in_kali(command, timeout=120)
    
    if result["success"]:
        return f"✅ Metasploit search results:\n\n{result['stdout']}"
    else:
        error = result.get('error') or result.get('stderr', 'Unknown error')
        return f"❌ Search failed:\n{error}"

  方法二：安裝其他工具
如果某個工具不在清單中kali-linux-headless，請安裝它：

def install_additional_tool(tool_name: str) -> bool:
    """Helper function to install additional Kali tools"""
    try:
        container_id = ensure_kali_container()
        
        install_cmd = [
            "docker", "exec", container_id,
            "bash", "-c",
            f"DEBIAN_FRONTEND=noninteractive apt-get install -y {tool_name}"
        ]
        
        subprocess.run(install_cmd, check=True, timeout=300)
        logger.info(f"✅ Installed {tool_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to install {tool_name}: {e}")
        return False


  https://lobehub.com/zh-TW/mcp/marklechner-kali-mcp-server

  
