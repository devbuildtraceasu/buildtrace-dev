# Fix Git Authentication Issue

## Problem
```
remote: Permission to devbuildtraceasu/buildtrace-dev.git denied to shekharashishraj.
fatal: unable to access 'https://github.com/devbuildtraceasu/buildtrace-dev.git/': The requested URL returned error: 403
```

## Solutions

### Option 1: Use SSH Authentication (Recommended)

**Step 1: Generate SSH Key**
```bash
ssh-keygen -t ed25519 -C "shekharashishraj@gmail.com"
# Press Enter to accept default location (~/.ssh/id_ed25519)
# Enter a passphrase (optional but recommended)
```

**Step 2: Add SSH Key to SSH Agent**
```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

**Step 3: Copy Public Key**
```bash
cat ~/.ssh/id_ed25519.pub
# Copy the entire output
```

**Step 4: Add Key to GitHub**
1. Go to: https://github.com/settings/keys
2. Click "New SSH key"
3. Paste your public key
4. Click "Add SSH key"

**Step 5: Change Remote to SSH**
```bash
cd /Users/ashishrajshekhar/Desktop/Job_interview_tasks/Job_trial/buildtrace-dev
git remote set-url origin git@github.com:devbuildtraceasu/buildtrace-dev.git
git remote -v  # Verify it changed
```

**Step 6: Test Connection**
```bash
ssh -T git@github.com
# Should see: "Hi devbuildtraceasu! You've successfully authenticated..."
```

**Step 7: Push**
```bash
git push origin main
```

---

### Option 2: Use Personal Access Token (HTTPS)

**Step 1: Create Personal Access Token**
1. Go to: https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Name it: "BuildTrace Dev"
4. Select scopes: `repo` (full control of private repositories)
5. Click "Generate token"
6. **COPY THE TOKEN** (you won't see it again!)

**Step 2: Update Git Credentials**
```bash
# Clear old credentials from macOS Keychain
git credential-osxkeychain erase
host=github.com
protocol=https
# Press Enter twice

# Or remove from Keychain Access app:
# Open Keychain Access → Search "github.com" → Delete entries
```

**Step 3: Push (will prompt for credentials)**
```bash
cd /Users/ashishrajshekhar/Desktop/Job_interview_tasks/Job_trial/buildtrace-dev
git push origin main
# Username: shekharashishraj (or devbuildtraceasu)
# Password: <paste your personal access token>
```

**Step 4: Store Credentials (Optional)**
```bash
# Store token in credential helper
git config --global credential.helper osxkeychain
```

---

### Option 3: Check Repository Access

**If you don't have access to the repository:**

1. **Verify you're a collaborator:**
   - Go to: https://github.com/devbuildtraceasu/buildtrace-dev/settings/access
   - Check if your account (`shekharashishraj`) is listed

2. **If not, ask repository owner to:**
   - Go to repository Settings → Collaborators
   - Add `shekharashishraj` as a collaborator with Write access

3. **Or fork the repository:**
   ```bash
   # Fork on GitHub first, then:
   git remote set-url origin https://github.com/shekharashishraj/buildtrace-dev.git
   git push origin main
   ```

---

## Quick Fix Script (SSH Method)

Run these commands in order:

```bash
# 1. Generate SSH key (if not exists)
if [ ! -f ~/.ssh/id_ed25519 ]; then
    ssh-keygen -t ed25519 -C "shekharashishraj@gmail.com" -f ~/.ssh/id_ed25519 -N ""
    eval "$(ssh-agent -s)"
    ssh-add ~/.ssh/id_ed25519
    echo "✅ SSH key generated!"
    echo "📋 Copy this public key and add it to GitHub:"
    cat ~/.ssh/id_ed25519.pub
    echo ""
    echo "After adding to GitHub, press Enter to continue..."
    read
fi

# 2. Change remote to SSH
cd /Users/ashishrajshekhar/Desktop/Job_interview_tasks/Job_trial/buildtrace-dev
git remote set-url origin git@github.com:devbuildtraceasu/buildtrace-dev.git

# 3. Test connection
echo "Testing SSH connection..."
ssh -T git@github.com

# 4. Push
echo "Pushing to repository..."
git push origin main
```

---

## Troubleshooting

### "Permission denied (publickey)"
- Make sure SSH key is added to GitHub
- Test with: `ssh -T git@github.com`

### "Repository not found"
- Check if you have access to `devbuildtraceasu/buildtrace-dev`
- Verify repository exists and is accessible

### "Authentication failed"
- For HTTPS: Use Personal Access Token, not password
- For SSH: Make sure key is added to GitHub and SSH agent

### Clear Cached Credentials
```bash
# macOS Keychain
git credential-osxkeychain erase <<EOF
host=github.com
protocol=https
EOF

# Or use Keychain Access app to delete github.com entries
```

---

## Recommended: Use SSH

SSH is more secure and doesn't require entering credentials repeatedly. Follow Option 1 above.

