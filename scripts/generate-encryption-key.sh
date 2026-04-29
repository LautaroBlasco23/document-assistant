#!/bin/bash
# Generates a Fernet encryption key and adds it to .env

ENV_FILE=".env"

# Generate a Fernet-compatible 32-byte url-safe base64 key
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

if [ -f "$ENV_FILE" ]; then
    # Check if already exists
    if grep -q "^DOCASSIST_AUTH__ENCRYPTION_KEY=" "$ENV_FILE"; then
        echo "✅ Encryption key already exists in .env"
        exit 0
    fi
    # Append to existing .env
    echo "" >> "$ENV_FILE"
    echo "# Auto-generated Fernet encryption key" >> "$ENV_FILE"
    echo "DOCASSIST_AUTH__ENCRYPTION_KEY=$ENCRYPTION_KEY" >> "$ENV_FILE"
else
    # Create new .env
    cat > "$ENV_FILE" << EOF
# Auto-generated Fernet encryption key
DOCASSIST_AUTH__ENCRYPTION_KEY=$ENCRYPTION_KEY
EOF
fi

echo "✅ Encryption key generated and saved to .env"
echo "   Key: ${ENCRYPTION_KEY:0:16}... (hidden for security)"
