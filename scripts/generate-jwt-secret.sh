#!/bin/bash
# Generates a random JWT secret and adds it to .env

ENV_FILE=".env"

# Generate 64-character random secret
JWT_SECRET=$(openssl rand -hex 32 2>/dev/null || head -c 64 /dev/urandom | xxd -p | head -c 64)

if [ -f "$ENV_FILE" ]; then
    # Check if already exists
    if grep -q "^DOCASSIST_AUTH__JWT_SECRET=" "$ENV_FILE"; then
        echo "✅ JWT secret already exists in .env"
        exit 0
    fi
    # Append to existing .env
    echo "" >> "$ENV_FILE"
    echo "# Auto-generated JWT secret" >> "$ENV_FILE"
    echo "DOCASSIST_AUTH__JWT_SECRET=$JWT_SECRET" >> "$ENV_FILE"
else
    # Create new .env
    cat > "$ENV_FILE" << EOF
# Auto-generated JWT secret
DOCASSIST_AUTH__JWT_SECRET=$JWT_SECRET
EOF
fi

echo "✅ JWT secret generated and saved to .env"
echo "   Secret: ${JWT_SECRET:0:16}... (hidden for security)"
