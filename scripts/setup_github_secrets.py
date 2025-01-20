import os
import base64
import json
import requests
from nacl import encoding, public
from dotenv import load_dotenv


class GitHubSecretsManager:
    def __init__(self, token, repo_owner, repo_name):
        self.token = token
        self.owner = repo_owner
        self.repo = repo_name
        self.base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {token}",
        }

    def get_public_key(self):
        """Get GitHub's public key for secret encryption"""
        url = f"{self.base_url}/actions/secrets/public-key"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def encrypt_secret(self, public_key: str, secret_value: str) -> str:
        """Encrypt a secret using GitHub's public key"""
        public_key_bytes = base64.b64decode(public_key)
        sealed_box = public.SealedBox(public.PublicKey(public_key_bytes))
        encrypted = sealed_box.encrypt(secret_value.encode())
        return base64.b64encode(encrypted).decode()

    def set_secret(self, secret_name: str, secret_value: str):
        """Set a GitHub repository secret"""
        # Get public key
        key_data = self.get_public_key()

        # Encrypt secret
        encrypted_value = self.encrypt_secret(key_data["key"], secret_value)

        # Create or update secret
        url = f"{self.base_url}/actions/secrets/{secret_name}"
        data = {
            "encrypted_value": encrypted_value,
            "key_id": key_data["key_id"]
        }

        response = requests.put(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.status_code == 201 or response.status_code == 204


def get_ssh_private_key():
    """Get SSH private key from PEM file"""
    # First try environment variable
    ssh_key_path = os.getenv("SSH_KEY_PATH")

    if not ssh_key_path:
        # If not in env, ask user for the path
        ssh_key_path = input("Enter the path to your AWS PEM key file: ").strip()

    # Expand user path (handles ~/ in path)
    ssh_key_path = os.path.expanduser(ssh_key_path)

    if not os.path.exists(ssh_key_path):
        raise ValueError(f"SSH key file not found at: {ssh_key_path}")

    try:
        with open(ssh_key_path, 'r') as f:
            key_content = f.read().strip()

        # Validate the key format
        if not key_content.startswith("-----BEGIN") or not key_content.endswith("-----"):
            raise ValueError("Invalid PEM key format")

        return key_content
    except Exception as e:
        raise ValueError(f"Error reading SSH key: {str(e)}")


def setup_secrets():
    # Load environment variables
    load_dotenv()

    # GitHub configuration
    github_token = os.getenv("GITHUB_TOKEN")
    repo_owner = os.getenv("GITHUB_OWNER")
    repo_name = os.getenv("GITHUB_REPO")

    if not all([github_token, repo_owner, repo_name]):
        raise ValueError("Missing required GitHub configuration")

    # Initialize secrets manager
    secrets_manager = GitHubSecretsManager(github_token, repo_owner, repo_name)

    # Get SSH private key
    try:
        ssh_private_key = get_ssh_private_key()
        print("✓ Successfully loaded SSH private key")
    except ValueError as e:
        print(f"Warning: {str(e)}")
        proceed = input("Do you want to continue without SSH key? (y/n): ")
        if proceed.lower() != 'y':
            raise ValueError("Setup cancelled by user")
        ssh_private_key = None

    # Define development secrets
    dev_secrets = {
        # Backend Development Secrets
        "DEV_DB_SERVER": os.getenv("DB_SERVER"),
        "DEV_DB_NAME": os.getenv("DB_NAME"),
        "DEV_DB_USER": os.getenv("DB_USER"),
        "DEV_DB_PASSWORD": os.getenv("DB_PASSWORD"),
        "DEV_AWS_BUCKET_NAME": os.getenv("AWS_BUCKET_NAME"),
        "DEV_CORS_ORIGINS": os.getenv("CORS_ORIGINS"),
        "DEV_FRONTEND_URL": os.getenv("DEV_FRONTEND_URL"),

        # Development Microsoft SSO Configuration
        "DEV_MICROSOFT_SSO_ENABLED": os.getenv("DEV_MICROSOFT_SSO_ENABLED", "true"),
        "DEV_MICROSOFT_CLIENT_ID": os.getenv("DEV_MICROSOFT_CLIENT_ID"),
        "DEV_MICROSOFT_CLIENT_SECRET": os.getenv("DEV_MICROSOFT_CLIENT_SECRET"),
        "DEV_MICROSOFT_TENANT_ID": os.getenv("DEV_MICROSOFT_TENANT_ID"),
        "DEV_MICROSOFT_REDIRECT_URI": os.getenv("DEV_MICROSOFT_REDIRECT_URI"),
        "DEV_MICROSOFT_DOMAIN_HINT": os.getenv("DEV_MICROSOFT_DOMAIN_HINT"),
    }

    # Define production secrets
    prod_secrets = {
        # Backend Production Secrets
        "PROD_DB_SERVER": os.getenv("PROD_DB_SERVER"),
        "PROD_DB_NAME": os.getenv("PROD_DB_NAME"),
        "PROD_DB_USER": os.getenv("PROD_DB_USER"),
        "PROD_DB_PASSWORD": os.getenv("PROD_DB_PASSWORD"),
        "PROD_AWS_BUCKET_NAME": os.getenv("PROD_AWS_BUCKET_NAME"),
        "PROD_CORS_ORIGINS": os.getenv("PROD_CORS_ORIGINS"),
        "PROD_FRONTEND_URL": os.getenv("PROD_FRONTEND_URL"),

        # Production Microsoft SSO Configuration
        "PROD_MICROSOFT_SSO_ENABLED": os.getenv("PROD_MICROSOFT_SSO_ENABLED", "true"),
        "PROD_MICROSOFT_CLIENT_ID": os.getenv("PROD_MICROSOFT_CLIENT_ID"),
        "PROD_MICROSOFT_CLIENT_SECRET": os.getenv("PROD_MICROSOFT_CLIENT_SECRET"),
        "PROD_MICROSOFT_TENANT_ID": os.getenv("PROD_MICROSOFT_TENANT_ID"),
        "PROD_MICROSOFT_REDIRECT_URI": os.getenv("PROD_MICROSOFT_REDIRECT_URI"),
        "PROD_MICROSOFT_DOMAIN_HINT": os.getenv("PROD_MICROSOFT_DOMAIN_HINT"),
    }

    # Define shared secrets
    shared_secrets = {
        # AWS Credentials
        "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_KEY_ID"),
        "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_SECRET_ACCESS_KEY"),

        # EC2 Configuration
        "EC2_HOST": os.getenv("EC2_HOST"),
        "EC2_USERNAME": os.getenv("EC2_USERNAME"),

        # Firebase Configuration
        "FIREBASE_PROJECT_ID": os.getenv("FIREBASE_PROJECT_ID"),
        "FIREBASE_PRIVATE_KEY_ID": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
        "FIREBASE_PRIVATE_KEY": os.getenv("FIREBASE_PRIVATE_KEY"),
        "FIREBASE_CLIENT_EMAIL": os.getenv("FIREBASE_CLIENT_EMAIL"),
        "FIREBASE_CLIENT_ID": os.getenv("FIREBASE_CLIENT_ID"),
        "FIREBASE_AUTH_URI": os.getenv("FIREBASE_AUTH_URI"),
        "FIREBASE_TOKEN_URI": os.getenv("FIREBASE_TOKEN_URI"),
    }

    # Add SSH private key if available
    if ssh_private_key:
        shared_secrets["SSH_PRIVATE_KEY"] = ssh_private_key

    # Combine all secrets
    all_secrets = {**dev_secrets, **prod_secrets, **shared_secrets}

    # Group secrets by category for validation
    required_groups = {
        "AWS Credentials": [
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY"
        ],
        "EC2 Configuration": [
            "EC2_HOST",
            "EC2_USERNAME",
            "SSH_PRIVATE_KEY"
        ],
        "Development Database": [
            "DEV_DB_SERVER",
            "DEV_DB_NAME",
            "DEV_DB_USER",
            "DEV_DB_PASSWORD"
        ],
        "Development Frontend": [
            "DEV_FRONTEND_URL",
            "DEV_CORS_ORIGINS"
        ],
        "Firebase Configuration": [
            "FIREBASE_PROJECT_ID",
            "FIREBASE_PRIVATE_KEY",
            "FIREBASE_CLIENT_EMAIL",
            "FIREBASE_PRIVATE_KEY_ID",
            "FIREBASE_CLIENT_ID",
            "FIREBASE_AUTH_URI",
            "FIREBASE_TOKEN_URI"
        ],
        "Microsoft SSO": [
            "DEV_MICROSOFT_SSO_ENABLED",
            "DEV_MICROSOFT_CLIENT_ID",
            "DEV_MICROSOFT_CLIENT_SECRET",
            "DEV_MICROSOFT_TENANT_ID",
            "DEV_MICROSOFT_REDIRECT_URI",
            "DEV_MICROSOFT_DOMAIN_HINT"
        ]
    }

    # Optional groups that won't block deployment
    optional_groups = {
        "Production Database": [
            "PROD_DB_SERVER",
            "PROD_DB_NAME",
            "PROD_DB_USER",
            "PROD_DB_PASSWORD"
        ],
        "Production Frontend": [
            "PROD_FRONTEND_URL",
            "PROD_CORS_ORIGINS"
        ],
        "Production Microsoft SSO": [
            "PROD_MICROSOFT_SSO_ENABLED",
            "PROD_MICROSOFT_CLIENT_ID",
            "PROD_MICROSOFT_CLIENT_SECRET",
            "PROD_MICROSOFT_TENANT_ID",
            "PROD_MICROSOFT_REDIRECT_URI",
            "PROD_MICROSOFT_DOMAIN_HINT"
        ]
    }

    # Validate required secrets by group
    missing_by_group = {}
    for group, secrets in required_groups.items():
        missing = [s for s in secrets if not all_secrets.get(s)]
        if missing:
            missing_by_group[group] = missing

    # Show missing required secrets by group
    if missing_by_group:
        print("\nMissing required secrets by category:")
        for group, missing in missing_by_group.items():
            print(f"\n{group}:")
            for secret in missing:
                print(f"  - {secret}")

        raise ValueError("Required secrets are missing. Please set them in your .env file.")

    # Show missing optional secrets
    missing_optional = {}
    for group, secrets in optional_groups.items():
        missing = [s for s in secrets if not all_secrets.get(s)]
        if missing:
            missing_optional[group] = missing

    if missing_optional:
        print("\nMissing optional secrets (these won't block deployment):")
        for group, missing in missing_optional.items():
            print(f"\n{group}:")
            for secret in missing:
                print(f"  - {secret}")

        proceed = input("\nDo you want to continue with available secrets? (y/n): ")
        if proceed.lower() != 'y':
            raise ValueError("Setup cancelled by user")

    # Set each secret
    print("\nSetting up secrets...")
    for secret_name, secret_value in all_secrets.items():
        if secret_value:  # Only set secrets that have values
            try:
                success = secrets_manager.set_secret(secret_name, secret_value)
                print(f"✓ Secret {secret_name} {'created' if success else 'updated'}")
            except Exception as e:
                print(f"✗ Failed to set {secret_name}: {str(e)}")


if __name__ == "__main__":
    try:
        setup_secrets()
        print("\nSecrets setup completed successfully!")
    except Exception as e:
        print(f"\nError setting up secrets: {str(e)}")
