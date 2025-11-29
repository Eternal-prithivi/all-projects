# SSH Connection Guide - Cloud Resource Optimization Platform

## Step 1: Download Your SSH Key

1. Go to **VM Cluster** page in the web interface
2. Find your assigned VM (e.g., `general-vm-1`)
3. Click the **"Download SSH Key"** button
4. The key will download as `vm_<vm-name>_<assignment-id>.pem`

## Step 2: Set Correct Permissions

SSH requires private keys to have restricted permissions:

```bash
# Move key to a secure location (optional but recommended)
mkdir -p ~/.ssh/vm-keys
mv ~/Downloads/vm_*.pem ~/.ssh/vm-keys/

# Set correct permissions (REQUIRED)
chmod 400 ~/.ssh/vm-keys/vm_*.pem
```

## Step 3: Get Your VM's IP Address

Your VM IP is shown in the web interface on the VM card. You can also check MongoDB or GCP console.

**Example from web interface:**
- VM Name: `general-vm-1`
- VM IP: `34.xxx.xxx.xxx` (shown on the card)
- SSH Username: `vmuser` (default)

## Step 4: Connect via SSH

```bash
# Basic connection
ssh -i ~/.ssh/vm-keys/vm_<vm-name>_<assignment-id>.pem vmuser@<VM_IP>

# Example:
ssh -i ~/.ssh/vm-keys/vm_general-vm-1_assign_5136d7336ba3.pem vmuser@34.123.45.67
```

## Step 5: First-Time Connection

When connecting for the first time, you'll see:

```
The authenticity of host '34.123.45.67 (34.123.45.67)' can't be established.
ED25519 key fingerprint is SHA256:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.
Are you sure you want to continue connecting (yes/no/[fingerprint])? 
```

Type **`yes`** and press Enter.

## Step 6: Disconnect from VM

When you're done working on the VM, disconnect safely:

```bash
# Method 1: Type exit command
exit

# Method 2: Press Ctrl+D (EOF signal)
# Just press: Ctrl + D
```

You'll see `logout` or `Connection to <IP> closed.` confirming you've disconnected.

**Important:** Always disconnect properly to avoid leaving orphaned sessions.

## Troubleshooting

### Error: "Permission denied (publickey)"

**Cause:** Wrong username or key not injected into VM metadata

**Solution:**
```bash
# 1. Verify you're using correct username (should be 'vmuser')
# 2. Check if VM is running:
#    - Go to GCP Console → Compute Engine → VM Instances
#    - Ensure general-vm-1 is RUNNING (green check)
# 3. Wait 30 seconds after requesting VM (for metadata to propagate)
```

### Error: "Connection timed out"

**Cause:** VM firewall or not running

**Solution:**
```bash
# 1. Verify VM is RUNNING in GCP console
# 2. Check GCP Firewall rules allow SSH (port 22)
# 3. Ensure you're using external IP, not internal
```

### Error: "WARNING: UNPROTECTED PRIVATE KEY FILE!"

**Cause:** Key permissions too open

**Solution:**
```bash
chmod 400 ~/.ssh/vm-keys/vm_*.pem
```

### Error: "Host key verification failed"

**Cause:** VM was recreated with same IP

**Solution:**
```bash
ssh-keygen -R <VM_IP>
# Then try connecting again
```

## Quick Command Reference

```bash
# Connect with verbose logging (for debugging)
ssh -v -i ~/.ssh/vm-keys/vm_*.pem vmuser@<VM_IP>

# Connect and run a command
ssh -i ~/.ssh/vm-keys/vm_*.pem vmuser@<VM_IP> "uname -a"

# Copy files to VM
scp -i ~/.ssh/vm-keys/vm_*.pem myfile.txt vmuser@<VM_IP>:/home/vmuser/

# Copy files from VM
scp -i ~/.ssh/vm-keys/vm_*.pem vmuser@<VM_IP>:/home/vmuser/data.txt ./
```

## Security Best Practices

1. **Never share your private key** (`.pem` file)
2. **Use `chmod 400`** to prevent accidental modifications
3. **Store keys in `~/.ssh/`** directory
4. **Rotate keys regularly** - request new VM assignments periodically
5. **Delete old keys** after releasing VMs

## Checking VM Status

### From Web Interface:
- Go to **VM Cluster** page
- Check VM status indicator (🟢 Running / 🔴 Stopped)
- View CPU, Memory metrics in real-time

### From Command Line (after connecting):
```bash
# Check system info
uname -a

# Check CPU usage
top

# Check disk space
df -h

# Check memory
free -h

# Check network
ip addr show
```

## Common Use Cases

### 1. Running a Web Server
```bash
# Install nginx
sudo apt update
sudo apt install nginx -y

# Start nginx
sudo systemctl start nginx

# Check if running
curl localhost
```

### 2. Running Python Scripts
```bash
# Install Python packages
pip3 install pandas numpy

# Run script
python3 my_script.py
```

### 3. Background Processes
```bash
# Run process in background
nohup python3 long_running_script.py > output.log 2>&1 &

# Check running processes
ps aux | grep python
```

## Need Help?

- **Platform Issues**: Check backend logs or MongoDB for assignment details
- **GCP Issues**: Check GCP Console → Compute Engine → VM Instances
- **SSH Issues**: Use `ssh -vvv` for maximum verbosity debugging

---

**Generated:** November 2025
**Platform:** Cloud Resource Optimization Platform (Development Branch)
