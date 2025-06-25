#!/usr/bin/env python3
"""
Myco Client-Server Setup Automation Script

This script automates the process of running the Myco latency testing setup:
1. Starts Server2
2. Starts Server1 (connects to Server2)
3. Runs the client for latency measurements
4. Handles cleanup when finished

Usage:
    python3 run_myco.py
"""

import subprocess
import time
import signal
import sys
import os
from typing import List, Optional

class MycoRunner:
    def __init__(self):
        self.processes: List[subprocess.Popen] = []
        self.server2_process: Optional[subprocess.Popen] = None
        self.server1_process: Optional[subprocess.Popen] = None
        
    def cleanup_ports(self):
        """Kill any processes using the Myco ports - enhanced version"""
        ports = [3002, 3004]
        killed_any = False
        
        for port in ports:
            try:
                # Method 1: Use lsof to find processes using the port
                result = subprocess.run(
                    ["lsof", "-ti", f":{port}"], 
                    capture_output=True, 
                    text=True,
                    check=False
                )
                if result.returncode == 0 and result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        if pid.strip():
                            print(f"   Killing process {pid} using port {port}")
                            subprocess.run(["kill", "-9", pid.strip()], capture_output=True, check=False)
                            killed_any = True
                            time.sleep(0.1)  # Brief pause between kills
                            
                # Method 2: Also try netstat approach as backup
                try:
                    result = subprocess.run(
                        ["netstat", "-tulpn"], 
                        capture_output=True, 
                        text=True,
                        check=False
                    )
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if f":{port}" in line and "LISTEN" in line:
                                # Extract PID from netstat output (format varies)
                                parts = line.split()
                                for part in parts:
                                    if '/' in part:
                                        pid = part.split('/')[0]
                                        if pid.isdigit():
                                            print(f"   Killing process {pid} listening on port {port}")
                                            subprocess.run(["kill", "-9", pid], capture_output=True, check=False)
                                            killed_any = True
                except (OSError, subprocess.SubprocessError):
                    pass
                    
            except (OSError, subprocess.SubprocessError):
                # lsof might not be available or other issues
                pass
        
        # Method 3: Kill any rpc_server processes regardless
        try:
            result = subprocess.run(["pgrep", "-f", "rpc_server"], capture_output=True, text=True, check=False)
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid.strip():
                        print(f"   Killing rpc_server process {pid}")
                        subprocess.run(["kill", "-9", pid.strip()], capture_output=True, check=False)
                        killed_any = True
        except (OSError, subprocess.SubprocessError):
            pass
            
        # Method 4: Also kill any cargo processes that might be running our servers
        try:
            result = subprocess.run(["pgrep", "-f", "cargo run.*rpc_server"], capture_output=True, text=True, check=False)
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid.strip():
                        print(f"   Killing cargo process {pid}")
                        subprocess.run(["kill", "-9", pid.strip()], capture_output=True, check=False)
                        killed_any = True
        except (OSError, subprocess.SubprocessError):
            pass
            
        if killed_any:
            print("   Waiting for processes to terminate...")
            time.sleep(2)  # Give time for processes to actually terminate

    def check_ports_free(self) -> bool:
        """Check if ports 3002 and 3004 are free"""
        ports = [3002, 3004]
        for port in ports:
            try:
                result = subprocess.run(
                    ["lsof", "-ti", f":{port}"], 
                    capture_output=True, 
                    text=True,
                    check=False
                )
                if result.returncode == 0 and result.stdout.strip():
                    print(f"⚠️  Port {port} is still in use")
                    return False
            except (OSError, subprocess.SubprocessError):
                pass
        return True

    def cleanup(self):
        """Clean up all running processes"""
        print("\n🔄 Cleaning up processes...")
        
        # First, try to terminate our tracked processes gracefully
        for process in self.processes:
            if process.poll() is None:  # Process is still running
                print(f"   Terminating process {process.pid}")
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    print(f"   Force killing process {process.pid}")
                    process.kill()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        pass
        
        # Then, kill any remaining processes on our ports
        self.cleanup_ports()
        
        # Also kill any rpc_server processes that might be lingering
        try:
            subprocess.run(["pkill", "-f", "rpc_server"], capture_output=True, check=False)
        except (OSError, subprocess.SubprocessError):
            pass
            
        print("✅ Cleanup completed")

    def signal_handler(self, signum, _frame):
        """Handle Ctrl+C gracefully"""
        print(f"\n⚠️  Received signal {signum}")
        self.cleanup()
        sys.exit(0)

    def wait_for_server_ready(self, server_name: str, expected_output: str, process: subprocess.Popen, timeout: int = 30) -> bool:
        """Wait for a server to be ready by monitoring its output"""
        print(f"⏳ Waiting for {server_name} to be ready...")
        
        start_time = time.time()
        output_buffer = ""
        
        while time.time() - start_time < timeout:
            if process.poll() is not None:
                print(f"❌ {server_name} process terminated unexpectedly")
                return False
                
            # Read available output
            try:
                if process.stdout is not None:
                    line = process.stdout.readline()
                    if line:
                        line_str = line.decode('utf-8').strip()
                        output_buffer += line_str + "\n"
                        print(f"   {server_name}: {line_str}")
                        
                        if expected_output in line_str:
                            print(f"✅ {server_name} is ready!")
                            return True
            except (OSError, UnicodeDecodeError) as e:
                print(f"   Error reading from {server_name}: {e}")
                
            time.sleep(0.1)
        
        print(f"❌ {server_name} did not become ready within {timeout} seconds")
        return False

    def start_server2(self) -> bool:
        """Start Server2"""
        print("🚀 Starting Server2...")
        try:
            cmd = ["just", "server2"]
            self.server2_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=False,
                bufsize=0
            )
            self.processes.append(self.server2_process)
            
            # Wait for Server2 to be ready
            return self.wait_for_server_ready(
                "Server2", 
                "Server2 listening on", 
                self.server2_process
            )
            
        except (OSError, subprocess.SubprocessError) as e:
            print(f"❌ Failed to start Server2: {e}")
            return False

    def start_server1(self) -> bool:
        """Start Server1"""
        print("🚀 Starting Server1...")
        try:
            cmd = ["just", "server1"]
            self.server1_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=False,
                bufsize=0
            )
            self.processes.append(self.server1_process)
            
            # Wait for Server1 to be ready
            return self.wait_for_server_ready(
                "Server1", 
                "Server1 listening on", 
                self.server1_process,
                timeout=60  # Server1 needs more time to establish connections
            )
            
        except (OSError, subprocess.SubprocessError) as e:
            print(f"❌ Failed to start Server1: {e}")
            return False

    def run_client(self) -> bool:
        """Run the client for latency testing"""
        print("🚀 Running client for latency testing...")
        try:
            cmd = ["just", "client", "https://localhost:3002", "https://localhost:3004"]
            client_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            print("📊 Client output:")
            print("-" * 50)
            
            # Stream client output in real-time
            if client_process.stdout is not None:
                for line in client_process.stdout:
                    print(line.rstrip())
            
            client_process.wait()
            
            if client_process.returncode == 0:
                print("-" * 50)
                print("✅ Client completed successfully!")
                return True
            else:
                print(f"❌ Client failed with return code: {client_process.returncode}")
                return False
                
        except (OSError, subprocess.SubprocessError) as e:
            print(f"❌ Failed to run client: {e}")
            return False

    def run(self):
        """Main execution flow"""
        print("🎯 Myco Client-Server Setup Automation")
        print("=" * 50)
        
        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Clean up any existing processes on our ports before starting
        print("🧹 Cleaning up any existing processes on ports 3002 and 3004...")
        self.cleanup_ports()
        
        # Check if ports are actually free now
        if not self.check_ports_free():
            print("❌ Ports are still in use after cleanup. Trying more aggressive cleanup...")
            # Try a more aggressive cleanup
            subprocess.run(["pkill", "-9", "-f", "rpc_server"], capture_output=True, check=False)
            subprocess.run(["pkill", "-9", "-f", "cargo.*rpc_server"], capture_output=True, check=False)
            time.sleep(1)
            self.cleanup_ports()
            
            if not self.check_ports_free():
                print("❌ Unable to free ports. You may need to manually kill processes or restart.")
                return False
        
        try:
            # Step 1: Start Server2
            if not self.start_server2():
                print("❌ Failed to start Server2. Exiting.")
                return False
            
            # Step 2: Start Server1
            if not self.start_server1():
                print("❌ Failed to start Server1. Exiting.")
                return False
            
            # Step 3: Run client
            client_success = self.run_client()
            
            return client_success
            
        except KeyboardInterrupt:
            print("\n⚠️  Interrupted by user")
            return False
        except (OSError, subprocess.SubprocessError, RuntimeError) as e:
            print(f"❌ Unexpected error: {e}")
            return False
        finally:
            self.cleanup()

def main():
    """Entry point"""
    # Check if we're in the right directory
    if not os.path.exists("justfile"):
        print("❌ Error: justfile not found. Please run this script from the MYCO directory.")
        sys.exit(1)
    
    # Check if just command is available
    try:
        subprocess.run(["just", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Error: 'just' command not found. Please install just first.")
        print("   Installation: brew install just")
        sys.exit(1)
    
    runner = MycoRunner()
    success = runner.run()
    
    if success:
        print("\n🎉 Myco latency testing completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Myco latency testing failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
