#!/bin/bash

# KiotProxy Manager - Setup Script

set -e

echo "========================================="
echo "KiotProxy Manager - Setup"
echo "========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp env.example .env
    
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env file with your settings:"
    echo ""
    echo "   1. Set your DOMAIN (e.g., yourdomain.com)"
    echo "   2. Change ADMIN_PASSWORD to a secure password"
    echo "   3. Generate a SECRET_KEY (use: openssl rand -hex 32)"
    echo "   4. Set your SSL_EMAIL for Let's Encrypt"
    echo ""
    echo "Press Enter after you've edited .env..."
    read
else
    echo "✅ .env file already exists"
fi

# Create necessary directories
echo ""
echo "📁 Creating directories..."
mkdir -p data
mkdir -p traefik/dynamic
mkdir -p letsencrypt

echo "✅ Directories created"
echo ""

# Generate secret key if not set
if grep -q "your-secret-key-here-change-this" .env; then
    echo "🔑 Generating SECRET_KEY..."
    SECRET_KEY=$(openssl rand -hex 32)
    sed -i.bak "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
    rm -f .env.bak
    echo "✅ SECRET_KEY generated"
    echo ""
fi

# Check DNS configuration
echo "🌐 DNS Configuration Check"
echo ""
echo "Please ensure your DNS is configured:"
echo ""
DOMAIN=$(grep DOMAIN= .env | cut -d'=' -f2)
echo "   A     $DOMAIN         → YOUR_SERVER_IP"
echo "   A     *.$DOMAIN       → YOUR_SERVER_IP"
echo ""
echo "Have you configured DNS? (y/n)"
read dns_configured

if [ "$dns_configured" != "y" ]; then
    echo ""
    echo "⚠️  Please configure DNS before starting the application"
    echo "   For local testing, you can add entries to /etc/hosts"
    exit 1
fi

# Build and start services
echo ""
echo "🚀 Building and starting services..."
echo ""
docker-compose up -d --build

echo ""
echo "========================================="
echo "✅ Setup Complete!"
echo "========================================="
echo ""
echo "Your KiotProxy Manager is starting up..."
echo ""
echo "Access the web UI at:"
echo "   http://app.$DOMAIN"
echo ""
echo "Default login:"
echo "   Username: $(grep ADMIN_USERNAME= .env | cut -d'=' -f2)"
echo "   Password: $(grep ADMIN_PASSWORD= .env | cut -d'=' -f2)"
echo ""
echo "⚠️  IMPORTANT: Change the default password after first login!"
echo ""
echo "Useful commands:"
echo "   docker-compose ps              - Check status"
echo "   docker-compose logs -f         - View logs"
echo "   docker-compose restart         - Restart services"
echo "   docker-compose down            - Stop services"
echo ""
echo "For troubleshooting, see README.md"
echo ""

