#!/bin/bash

# Myco Client-Server Setup Automation Script
# This script automates running the Myco latency testing setup

echo "🎯 Myco Client-Server Setup Automation"
echo "======================================"

# Function to cleanup background processes
cleanup() {
    echo -e "\n🔄 Cleaning up processes..."
    if [ ! -z "$SERVER2_PID" ]; then
        echo "   Stopping Server2 (PID: $SERVER2_PID)"
        kill $SERVER2_PID 2>/dev/null
    fi
    if [ ! -z "$SERVER1_PID" ]; then
        echo "   Stopping Server1 (PID: $SERVER1_PID)"
        kill $SERVER1_PID 2>/dev/null
    fi
    echo "✅ Cleanup completed"
    exit 0
}

# Set up trap for cleanup on script exit
trap cleanup EXIT INT TERM

# Check if just command is available
if ! command -v just &> /dev/null; then
    echo "❌ Error: 'just' command not found. Please install just first."
    echo "   Installation: brew install just"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "justfile" ]; then
    echo "❌ Error: justfile not found. Please run this script from the MYCO directory."
    exit 1
fi

echo "🚀 Starting Server2..."
just server2 &
SERVER2_PID=$!
echo "   Server2 started with PID: $SERVER2_PID"

# Wait for Server2 to be ready
echo "⏳ Waiting for Server2 to be ready..."
sleep 5

echo "🚀 Starting Server1..."
just server1 &
SERVER1_PID=$!
echo "   Server1 started with PID: $SERVER1_PID"

# Wait for Server1 to establish connections to Server2
echo "⏳ Waiting for Server1 to establish connections..."
sleep 10

echo "🚀 Running client for latency testing..."
echo "📊 Client output:"
echo "--------------------------------------------------"

# Run the client with the correct HTTPS URLs
if just client "https://localhost:3002" "https://localhost:3004"; then
    echo "--------------------------------------------------"
    echo "✅ Client completed successfully!"
    echo "🎉 Myco latency testing completed successfully!"
else
    echo "--------------------------------------------------"
    echo "❌ Client failed!"
    exit 1
fi