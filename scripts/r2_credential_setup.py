#!/usr/bin/env python3
"""
Cloudflare R2 Credential Setup Guide

Helps diagnose and set up proper R2 credentials.
"""

import os

from dotenv import load_dotenv


def print_r2_setup_guide():
    """Print comprehensive R2 setup guide."""
    print("🔧 Cloudflare R2 Credential Setup Guide")
    print("=" * 60)

    load_dotenv()

    account_id = os.getenv("R2_ACCOUNT_ID", "")
    api_token = os.getenv("R2_API_TOKEN", "")
    bucket_name = os.getenv("R2_BUCKET_NAME", "")

    print("📊 Current Configuration:")
    print(f"   Account ID: {account_id}")
    print(f"   API Token Length: {len(api_token)} chars")
    print(f"   Bucket Name: {bucket_name}")
    print()

    if len(api_token) == 40:
        print("⚠️  ISSUE DETECTED: Your API token has 40 characters")
        print("   This suggests you're using a regular Cloudflare API token")
        print("   R2 requires specific R2 API tokens or S3-compatible credentials")
        print()

    print("🛠️  SOLUTION: Create R2 API Tokens")
    print("=" * 40)
    print()
    print("**Method 1: R2 API Tokens (Recommended)**")
    print("1. Go to: https://dash.cloudflare.com/profile/api-tokens")
    print("2. Click 'Create Token'")
    print("3. Choose 'R2 Read and Write' template")
    print("4. Configure permissions:")
    print("   • Account: Your account")
    print("   • Zone Resources: All zones (or specific)")
    print("   • Permissions: Cloudflare R2:Edit")
    print("5. Create and copy the token")
    print()
    print("**Method 2: S3 API Credentials (Alternative)**")
    print("1. Go to R2 dashboard: https://dash.cloudflare.com/[account]/r2/api-tokens")
    print("2. Click 'Create API token'")
    print("3. Select 'R2 Token' type")
    print("4. Choose permissions: Object Read & Write")
    print("5. This will give you Access Key ID and Secret Access Key")
    print("6. Update your .env file with:")
    print("   R2_ACCESS_KEY=your_access_key_here")
    print("   R2_SECRET_KEY=your_secret_key_here")
    print()
    print("🔄 **Current Issue Analysis**")
    print(
        f"Your token: {api_token[:10]}...{api_token[-10:] if len(api_token) > 20 else api_token}"
    )
    print(f"Length: {len(api_token)} (expected: 32 for R2 tokens)")
    print()
    print("💡 **Next Steps:**")
    print("1. Create proper R2 API tokens using Method 1 or 2 above")
    print("2. Update your .env file with the new credentials")
    print("3. Re-run the data pipeline test")
    print()
    print("🚨 **Security Note:**")
    print("Make sure to:")
    print("• Keep your API tokens secure")
    print("• Use minimal required permissions")
    print("• Rotate tokens regularly")


if __name__ == "__main__":
    print_r2_setup_guide()
