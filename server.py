#!/usr/bin/env python3
"""
Kali Linux MCP Server
Runs on macOS host and controls a privileged Kali Linux Docker container
"""

import subprocess
import logging
import os
from typing import Any
from fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP(
    name="kali-security-tools",
    instructions="""
    This MCP server provides access to Kali Linux security testing tools.
    It manages a privileged Kali Linux Docker container with full capabilities.
    
    Available tools:
    - nmap: Network discovery and port scanning
    - nikto: Web server vulnerability scanning  
    - whatweb: Web technology fingerprinting
    - sqlmap: SQL injection detection and exploitation
    - Custom commands: Execute any Kali Linux tool
    
    IMPORTANT: Only use on systems you own or have explicit permission to test.
    """
)

# Container configuration
KALI_IMAGE = "kalilinux/kali-rolling"
KALI_CONTAINER = "kali-mcp-pentest"


def ensure_kali_container() -> str:
    """Ensure privileged Kali container is running and tools are installed"""
    try:
        # Check if container is running
        result = subprocess.run(
            ["docker", "ps", "-q", "-f", f"name={KALI_CONTAINER}"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.stdout.strip():
            logger.info(f"Container {KALI_CONTAINER} is running")
            return result.stdout.strip()
        
        # Check if container exists but is stopped
        result = subprocess.run(
            ["docker", "ps", "-a", "-q", "-f", f"name={KALI_CONTAINER}"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.stdout.strip():
            logger.info(f"Starting existing container {KALI_CONTAINER}")
            subprocess.run(["docker", "start", KALI_CONTAINER], check=True)
            return result.stdout.strip()
        
        # Create new privileged container
        logger.info(f"Creating new privileged Kali container: {KALI_CONTAINER}")
        
        # Create pentest network if it doesn't exist
        subprocess.run(
            ["docker", "network", "create", "pentest-net"],
            capture_output=True,
            check=False
        )
        
        create_cmd = [
            "docker", "run", "-d",
            "--name", KALI_CONTAINER,
            "--privileged",           # Full privileges
            "--cap-add", "ALL",       # All Linux capabilities
            "--network", "pentest-net",  # Custom network for container-to-container
            KALI_IMAGE,
            "tail", "-f", "/dev/null"
        ]
        
        result = subprocess.run(create_cmd, capture_output=True, text=True, check=True)
        container_id = result.stdout.strip()
        
        logger.info("Installing Kali security tools (takes 2-5 minutes on first run)...")
        
        # Install essential tools
        install_cmd = [
            "docker", "exec", container_id,
            "bash", "-c",
            "apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y kali-linux-headless"
        ]
        
        subprocess.run(install_cmd, check=True, timeout=600)
        
        logger.info("✅ Kali container ready with security tools installed!")
        return container_id
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to setup container: {e}")
        raise
    except subprocess.TimeoutExpired:
        logger.error("Tool installation timed out")
        raise


def run_in_kali(command: list[str], timeout: int = 300) -> dict[str, Any]:
    """Execute command in the privileged Kali container"""
    try:
        container_id = ensure_kali_container()
        
        logger.info(f"Executing in Kali: {' '.join(command)}")
        
        exec_cmd = ["docker", "exec", container_id] + command
        
        result = subprocess.run(
            exec_cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Command timed out after {timeout} seconds"
        }
    except Exception as e:
        logger.error(f"Error executing command: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
def check_container_permissions() -> str:
    """
    Check if the container is running with necessary privileges for security tools.
    
    Returns:
        Privilege information
    """
    
    result = run_in_kali(["id"], timeout=5)
    
    output = "🔍 Container Privilege Check:\n\n"
    
    if result["success"]:
        output += f"User info:\n{result['stdout']}\n"
        
        if "uid=0(root)" in result['stdout']:
            output += "✅ Running as root - full privileges available\n"
        else:
            output += "⚠️ Not running as root\n"
    
    # Check nmap availability
    result = run_in_kali(["which", "nmap"], timeout=5)
    if result["success"]:
        output += f"\n📍 Nmap: {result['stdout'].strip()}\n"
    
    # Test nmap can actually run
    result = run_in_kali(["nmap", "--version"], timeout=5)
    if result["success"]:
        version_line = result['stdout'].split('\n')[0]
        output += f"✅ {version_line}\n"
    
    return output


@mcp.tool()
def nmap_scan(
    target: str,
    scan_type: str = "basic",
    ports: str = ""
) -> str:
    """
    Perform network scanning with nmap.
    
    Args:
        target: Target IP, hostname, or container name (e.g., 'dvwa-test', 'host.docker.internal', '192.168.1.1')
        scan_type: Type of scan - 'basic', 'quick', 'full', 'version', 'os'
        ports: Specific ports to scan (e.g., '22,80,443' or '1-1000'). Leave empty for scan_type defaults.
    
    Returns:
        Scan results from nmap
    
    Special targets:
    - 'host.docker.internal' - scan services on your Mac host
    - Container names (e.g., 'dvwa-test') - scan other Docker containers on pentest-net
    
    IMPORTANT: Only scan systems you own or have permission to test!
    """
    
    scan_commands = {
        "basic": ["nmap", "-sn", target],  # Ping scan
        "quick": ["nmap", "-T4", "-F", target],  # Fast scan of common ports
        "full": ["nmap", "-p-", target],  # All 65535 ports
        "version": ["nmap", "-sV", target],  # Service version detection
        "os": ["nmap", "-O", target]  # OS detection
    }
    
    command = scan_commands.get(scan_type, ["nmap", target])
    
    # Override with custom ports if specified
    if ports:
        command = ["nmap", "-p", ports, target]
    
    result = run_in_kali(command, timeout=600)
    
    if result["success"]:
        output = f"✅ Nmap scan completed successfully!\n\n{result['stdout']}"
        if result['stderr']:
            output += f"\n\n📋 Additional info:\n{result['stderr']}"
        return output
    else:
        error = result.get('error') or result.get('stderr', 'Unknown error')
        return f"❌ Nmap scan failed:\n{error}\n\nStdout:\n{result.get('stdout', 'No output')}"


@mcp.tool()
def scan_host_service(port: int, scan_type: str = "version") -> str:
    """
    Scan a service running on your Mac host machine.
    
    Args:
        port: Port number to scan on the host (e.g., 8080)
        scan_type: Type of scan - 'basic', 'quick', 'version'
    
    Returns:
        Scan results from nmap
    
    This uses 'host.docker.internal' which Docker provides to access your Mac from inside containers.
    IMPORTANT: Only scan services you own!
    """
    
    target = "host.docker.internal"
    
    scan_commands = {
        "basic": ["nmap", "-p", str(port), target],
        "quick": ["nmap", "-T4", "-p", str(port), target],
        "version": ["nmap", "-sV", "-p", str(port), target]
    }
    
    command = scan_commands.get(scan_type, ["nmap", "-p", str(port), target])
    
    result = run_in_kali(command, timeout=600)
    
    if result["success"]:
        output = f"✅ Scan of host port {port} completed!\n\n{result['stdout']}"
        if result['stderr']:
            output += f"\n\n📋 Additional info:\n{result['stderr']}"
        return output
    else:
        error = result.get('error') or result.get('stderr', 'Unknown error')
        return f"❌ Scan failed:\n{error}"


@mcp.tool()
def nikto_scan(target: str, port: int = 80, ssl: bool = False) -> str:
    """
    Scan web server with Nikto vulnerability scanner.
    
    Args:
        target: Target hostname, IP, or container name (e.g., 'dvwa-test', 'host.docker.internal')
        port: Port number (default: 80)
        ssl: Use SSL/TLS (default: False)
    
    Returns:
        Nikto scan results
    
    IMPORTANT: Only scan web servers you own or have permission to test!
    """
    
    command = ["nikto", "-h", target, "-p", str(port)]
    if ssl:
        command.append("-ssl")
    
    result = run_in_kali(command, timeout=900)
    
    if result["success"]:
        return f"✅ Nikto scan completed:\n\n{result['stdout']}"
    else:
        error = result.get('error') or result.get('stderr', 'Unknown error')
        return f"❌ Nikto scan failed:\n{error}"


@mcp.tool()
def whatweb_scan(target: str, aggression: int = 1) -> str:
    """
    Identify web technologies with WhatWeb.
    
    Args:
        target: Target URL (e.g., 'http://dvwa-test', 'http://host.docker.internal:8080')
        aggression: Scan aggression level 1-4 (default: 1, passive)
    
    Returns:
        Web technology fingerprinting results
    """
    
    command = ["whatweb", f"--aggression={aggression}", target]
    result = run_in_kali(command, timeout=300)
    
    if result["success"]:
        return f"✅ WhatWeb scan completed:\n\n{result['stdout']}"
    else:
        error = result.get('error') or result.get('stderr', 'Unknown error')
        return f"❌ WhatWeb scan failed:\n{error}"


@mcp.tool()
def sqlmap_scan(url: str, method: str = "GET", data: str = "") -> str:
    """
    Test for SQL injection vulnerabilities with sqlmap.
    
    Args:
        url: Target URL with parameter (e.g., 'http://dvwa-test/login.php?id=1')
        method: HTTP method - 'GET' or 'POST' (default: GET)
        data: POST data if method is POST (e.g., 'username=admin&password=pass')
    
    Returns:
        SQLmap scan results
    
    IMPORTANT: Only test applications you own or have permission to test!
    """
    
    command = ["sqlmap", "-u", url, "--batch", "--answers", "follow=N"]
    
    if method.upper() == "POST" and data:
        command.extend(["--data", data])
    
    result = run_in_kali(command, timeout=600)
    
    if result["success"]:
        return f"✅ SQLmap scan completed:\n\n{result['stdout']}"
    else:
        error = result.get('error') or result.get('stderr', 'Unknown error')
        return f"❌ SQLmap scan failed:\n{error}"


@mcp.tool()
def run_custom_command(command: str, timeout: int = 300) -> str:
    """
    Run a custom command in the Kali Linux container.
    
    Args:
        command: Shell command to execute (e.g., 'nmap --help', 'ls -la /tmp')
        timeout: Command timeout in seconds (default: 300)
    
    Returns:
        Command output
    
    WARNING: Be careful with this tool - it executes arbitrary commands with root privileges!
    """
    
    result = run_in_kali(["bash", "-c", command], timeout=timeout)
    
    if result["success"]:
        output = f"✅ Command executed:\n\n{result['stdout']}"
        if result['stderr']:
            output += f"\n\nStderr:\n{result['stderr']}"
        return output
    else:
        error = result.get('error') or result.get('stderr', 'Unknown error')
        return f"❌ Command failed:\n{error}"


@mcp.tool()
def get_container_ip(container_name: str) -> str:
    """
    Get the IP address of a Docker container.
    
    Args:
        container_name: Name of the container (e.g., 'dvwa-test')
    
    Returns:
        Container IP address
    """
    
    try:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}", container_name],
            capture_output=True,
            text=True,
            check=True
        )
        
        ip = result.stdout.strip()
        if ip:
            return f"✅ Container '{container_name}' IP: {ip}\n\nYou can now scan this IP with nmap."
        else:
            return f"❌ Could not find IP for container '{container_name}'"
            
    except subprocess.CalledProcessError as e:
        return f"❌ Failed to get container IP: {e}"


@mcp.tool()
def list_available_tools() -> str:
    """
    List security tools available in the Kali Linux container.
    
    Returns:
        List of available tools and their purposes
    """
    
    tools = [
        "nmap - Network scanner and port scanner",
        "nikto - Web server vulnerability scanner",
        "whatweb - Web technology identifier",
        "sqlmap - SQL injection detection and exploitation",
        "dirb - Web content scanner",
        "hydra - Network logon cracker",
        "john - Password cracker",
        "metasploit - Exploitation framework",
        "burpsuite - Web application security testing",
        "wireshark - Network protocol analyzer",
        "aircrack-ng - WiFi security testing",
        "netcat - TCP/IP Swiss Army knife"
    ]
    
    output = "🛠️ Available Kali Linux Security Tools:\n\n"
    for tool in tools:
        output += f"  • {tool}\n"
    
    output += "\n💡 Tip: Use 'run_custom_command' to execute any of these tools directly."
    output += "\n\n⚠️ Remember: Only use on systems you own or have explicit permission to test!"
    
    return output


@mcp.tool()
def cleanup_kali_container() -> str:
    """
    Stop and remove the Kali Linux container.
    
    Returns:
        Cleanup status
    
    Use this when you're done testing to free up resources.
    """
    
    try:
        subprocess.run(
            ["docker", "stop", KALI_CONTAINER],
            capture_output=True,
            check=True
        )
        subprocess.run(
            ["docker", "rm", KALI_CONTAINER],
            capture_output=True,
            check=True
        )
        return f"✅ Container {KALI_CONTAINER} stopped and removed successfully"
    except subprocess.CalledProcessError as e:
        return f"❌ Cleanup failed: {e}"


if __name__ == "__main__":
    logger.info("🚀 Starting Kali Linux MCP Server (Host-based)")
    logger.info(f"📍 Running on host as UID: {os.geteuid()}")
    logger.info("🐳 Will manage privileged Kali Docker container")
    logger.info("⚠️  For authorized security testing only")
    
    mcp.run(transport="stdio")
