#!/bin/bash
# Test SSH connection to GitHub

echo "Testing SSH connection to GitHub..."
output=$(ssh -T git@github.com 2>&1)
exit_code=$?

# GitHub returns exit code 1 even on success (because it doesn't provide shell access)
# But the message contains "successfully authenticated" on success
if echo "$output" | grep -q "successfully authenticated"; then
    echo ""
    echo "✅ SSH connection successful!"
    echo "You can now push with: git push origin main"
    exit 0
else
    echo ""
    echo "❌ SSH connection failed. Make sure you've added your SSH key to GitHub."
    echo "Go to: https://github.com/settings/keys"
    echo ""
    echo "Error output:"
    echo "$output"
    exit 1
fi

