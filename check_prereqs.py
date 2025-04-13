#!/usr/bin/env python3
"""
Prerequisite checker for Potion Email Security.
This script verifies that all required components are properly configured.
"""

import os
import sys
import json
import socket
import platform
import subprocess
from pathlib import Path
from dotenv import load_dotenv

def print_status(component, status, details=None):
    """Print a formatted status message."""
    status_color = '\033[92m' if status else '\033[91m'  # Green or Red
    reset_color = '\033[0m'
    status_text = "✓ PASS" if status else "✗ FAIL"
    
    print(f"{component:30} {status_color}{status_text}{reset_color}")
    if details and not status:
        print(f"  → {details}")
    
    return status

def check_dotenv():
    """Check if .env file exists and is properly configured."""
    env_file = Path('.env')
    if not env_file.exists():
        return print_status(".env file", False, "File not found. Run 'cp .env.example .env' and edit it.")
    
    load_dotenv()
    
    # Check if Neo4j is running with authentication disabled
    try:
        result = subprocess.run(
            ['docker', 'exec', 'neo4j-local-analyzer', 'env'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False
        )
        neo4j_auth_none = 'NEO4J_AUTH=none' in result.stdout
    except Exception:
        neo4j_auth_none = False
    
    # If Neo4j is running without authentication, we don't need NEO4J_PASSWORD
    required_vars = [
        'GOOGLE_SERVICE_ACCOUNT_FILE',
        'GOOGLE_GEMINI_API_KEY',
        'TARGET_GMAIL_ADDRESS',
    ]
    
    # Only require password if Neo4j authentication is enabled
    if not neo4j_auth_none:
        required_vars.append('NEO4J_PASSWORD')
    
    missing = []
    default_values = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing.append(var)
        elif any(default in value for default in ['YOUR_', 'your-']):
            default_values.append(var)
    
    if missing:
        return print_status("Environment variables", False, 
                          f"Missing variables: {', '.join(missing)}")
    
    if default_values:
        return print_status("Environment variables", False, 
                          f"Default values need to be changed: {', '.join(default_values)}")
    
    return print_status("Environment variables", True)

def check_oauth_credentials():
    """Check if OAuth credentials file exists and token pickle if available."""
    credentials_file = Path('credentials.json')
    if not credentials_file.exists():
        return print_status("OAuth credentials", False, 
                          "credentials.json not found. Download OAuth credentials from Google Cloud Console.")
    
    # Check file format (should be a valid JSON)
    try:
        with open(credentials_file, 'r') as f:
            credentials = json.load(f)
        
        # Basic validation of OAuth credentials file
        if 'installed' not in credentials and 'web' not in credentials:
            return print_status("OAuth credentials", False, 
                              "Invalid OAuth credentials format. Download OAuth credentials from Google Cloud Console.")
        
        # Look for token.pickle (optional)
        token_file = Path('token.pickle')
        if token_file.exists():
            print("  → OAuth token found (token.pickle). Authentication should be cached.")
        else:
            print("  → No OAuth token found. Browser will open for authentication on first run.")
        
        return print_status("OAuth credentials", True)
    except json.JSONDecodeError:
        return print_status("OAuth credentials", False, 
                          "credentials.json is not valid JSON")
    except Exception as e:
        return print_status("OAuth credentials", False, str(e))

def check_gemini_api_key():
    """Check if Gemini API key is set and valid format."""
    api_key = os.getenv('GOOGLE_GEMINI_API_KEY')
    
    if not api_key:
        return print_status("Gemini API key", False, 
                          "GOOGLE_GEMINI_API_KEY environment variable not set")
    
    if 'YOUR_GEMINI_API_KEY_HERE' in api_key:
        return print_status("Gemini API key", False, 
                          "Default value needs to be replaced with a real API key")
    
    # Basic format check (actual validation would require an API call)
    if len(api_key) < 10:
        return print_status("Gemini API key", False, 
                          "API key appears too short to be valid")
    
    return print_status("Gemini API key", True)

def check_docker_status():
    """Check if Docker is running and the Neo4j container is available."""
    try:
        # Try to run docker command to check status
        subprocess.run(['docker', 'info'], 
                       stdout=subprocess.DEVNULL, 
                       stderr=subprocess.DEVNULL, 
                       check=True)
        docker_running = True
    except (subprocess.SubprocessError, FileNotFoundError):
        docker_running = False
    
    if not docker_running:
        return print_status("Docker status", False, 
                         "Docker engine is not running or not installed. Please start Docker.")
    
    # Check if we're on ARM architecture
    is_arm = platform.machine() in ['arm64', 'aarch64']
    if is_arm:
        print("  → Running on ARM architecture (Apple Silicon or similar)")
    
    # Check if Neo4j container is running
    try:
        result = subprocess.run(
            ['docker', 'ps', '--filter', 'name=neo4j-local-analyzer', '--format', '{{.Status}}'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False
        )
        
        if 'Up ' in result.stdout:
            return print_status("Docker status", True)
        else:
            container_cmd = "docker-compose up -d neo4j" if os.path.exists('/usr/local/bin/docker-compose') else "docker compose up -d neo4j"
            return print_status("Docker status", False, 
                            f"Neo4j container is not running. Start it with: {container_cmd}")
    except Exception as e:
        return print_status("Docker status", False, f"Error checking Neo4j container: {e}")

def check_neo4j_connection():
    """Check if Neo4j is running and accessible."""
    # First check if Docker and container are running
    docker_status = check_docker_status()
    if not docker_status:
        return False
    
    host = os.getenv('NEO4J_URI', 'bolt://localhost:7687').replace('bolt://', '')
    
    # Extract host and port
    if ':' in host:
        host, port_str = host.split(':')
        port = int(port_str)
    else:
        port = 7687  # Default Neo4j Bolt port
    
    # Check Neo4j HTTP port first (more likely to be ready before Bolt)
    http_port = 7474
    neo4j_ready = False
    
    try:
        # First try HTTP port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)  # 2 seconds timeout
        http_result = sock.connect_ex((host, http_port))
        sock.close()
        
        # Then try Bolt port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)  # 2 seconds timeout
        bolt_result = sock.connect_ex((host, port))
        sock.close()
        
        if http_result == 0 and bolt_result == 0:
            # Check if Neo4j container has authentication disabled
            try:
                result = subprocess.run(
                    ['docker', 'exec', 'neo4j-local-analyzer', 'env'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False
                )
                
                if 'NEO4J_AUTH=none' in result.stdout:
                    print("  → Neo4j is running without authentication (NEO4J_AUTH=none)")
                    # Update environment variables check to not require NEO4J_PASSWORD
                    return print_status("Neo4j connection", True)
            except Exception:
                pass
                
            neo4j_ready = True
        elif http_result == 0 and bolt_result != 0:
            print("  → Neo4j HTTP interface is accessible, but Bolt port is not ready yet")
            print("  → This is normal during startup. Try again in 30 seconds")
            neo4j_ready = False
        elif http_result != 0:
            print("  → Neo4j HTTP interface is not accessible")
            neo4j_ready = False
            
        if neo4j_ready:
            return print_status("Neo4j connection", True)
        else:
            # Check for common Docker issues
            is_arm = platform.machine() in ['arm64', 'aarch64']
            docker_info = "If you're on Apple Silicon (M1/M2/M3), make sure docker-compose.yml has platform: linux/amd64 set for Neo4j."
            
            msg = f"Neo4j not fully accessible at {host}:{port} yet. Container might still be starting up or has crashed."
            if is_arm:
                msg += f"\n  → {docker_info}"
            return print_status("Neo4j connection", False, msg)
    except Exception as e:
        return print_status("Neo4j connection", False, str(e))

def main():
    """Run all checks and report results."""
    print("\n=== Potion Email Security - Prerequisite Check ===\n")
    
    checks = [
        check_dotenv(),
        check_oauth_credentials(),
        check_gemini_api_key(),
        check_neo4j_connection()
    ]
    
    print("\nSummary:")
    if all(checks):
        print("\n✅ All prerequisites checks passed! You're ready to run the application.")
        print("   Run 'python main.py' to start analyzing emails.")
        return 0
    else:
        print("\n❌ Some prerequisite checks failed. Please fix the issues above before running the application.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 