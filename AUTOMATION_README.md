# Myco Automation Scripts

This directory contains automation scripts to easily run the Myco Client-Server Setup for latency testing.

## Scripts Available

### 1. Python Script: `run_myco.py`
A comprehensive Python script with advanced features:

#### Features:
- ✅ Automatic server startup and readiness detection
- ✅ Real-time output monitoring
- ✅ Graceful cleanup on exit (Ctrl+C)
- ✅ Error handling and validation
- ✅ Progress indicators and colored output
- ✅ Proper signal handling

#### Usage:
```bash
python3 run_myco.py
```

### 2. Bash Script: `run_myco.sh`
A simpler bash alternative:

#### Features:
- ✅ Basic server startup with fixed delays
- ✅ Cleanup on exit
- ✅ Simple progress indicators

#### Usage:
```bash
./run_myco.sh
```

## What These Scripts Do

Both scripts automate the complete Myco latency testing workflow:

1. **Start Server2** on `0.0.0.0:3004`
2. **Start Server1** on `0.0.0.0:3002` (connects to Server2)
3. **Run Client** for latency measurements
4. **Display Results** with latency statistics
5. **Clean Up** all processes when finished

## Requirements

- **Just command runner**: `brew install just`
- **Python 3** (for the Python script)
- **Rust environment** (the project should be built with `cargo build --release`)

## Output

The scripts will show:
- Server startup logs
- Client warm-up iterations (25 iterations)
- Measurement phase (10 iterations)
- Final latency statistics:
  - Average latency
  - Min/Max latency
  - Per-iteration breakdown

## Example Output

```
🎯 Myco Client-Server Setup Automation
==================================================
🚀 Starting Server2...
✅ Server2 is ready!
🚀 Starting Server1...
✅ Server1 is ready!
🚀 Running client for latency testing...

... (client output) ...

Latency Statistics (ms):
  Average: 5676.99
  Min: 5328.43
  Max: 6051.27
  Total iterations: 10

🎉 Myco latency testing completed successfully!
```

## Troubleshooting

If you encounter issues:

1. **Check if `just` is installed**: `just --version`
2. **Ensure you're in the MYCO directory**: Should contain `justfile`
3. **Build the project first**: `cargo build --release`
4. **For Python script**: Ensure Python 3 is installed
5. **Port conflicts**: Make sure ports 3002 and 3004 are available

## Manual Commands

If you prefer to run commands manually:
```bash
# Terminal 1: Start Server2
just server2

# Terminal 2: Start Server1 (wait for Server2 to be ready)
just server1

# Terminal 3: Run Client (wait for both servers to be ready)
just client "https://localhost:3002" "https://localhost:3004"
```
