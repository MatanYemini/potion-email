#!/bin/bash

# Potion Email Security - Setup Script

echo "Setting up Potion Email Security environment..."

# Check if Python 3.11 is installed
PYTHON_CMD="python3.11"
if ! command -v $PYTHON_CMD &> /dev/null; then
    PYTHON_CMD="python3"
    # Check if Python 3 version is at least 3.11
    python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
    if [[ $(echo "$python_version" | cut -d. -f1,2) < "3.11" ]]; then
        echo "Error: Python 3.11 or higher is required. Current version: $python_version"
        echo "Please install Python 3.11 or higher and try again."
        exit 1
    fi
fi

echo "Using Python: $($PYTHON_CMD --version)"

# Create and activate virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  $PYTHON_CMD -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
  echo "Warning: Docker is not installed. Docker is required to run Neo4j."
  echo "Please install Docker Desktop from https://www.docker.com/products/docker-desktop/"
else
  echo "Docker is installed. Good!"
  
  # Check if running on ARM architecture
  arch=$(uname -m)
  if [[ "$arch" == "arm64" ]] || [[ "$arch" == "aarch64" ]]; then
    echo "Detected ARM64 architecture. Using emulation for Neo4j container."
    echo "Note: Performance may be slightly reduced due to emulation."
  fi
  
  # Check for Docker Compose 
  if ! command -v docker-compose &> /dev/null; then
    if ! command -v docker compose &> /dev/null; then
      echo "Warning: Docker Compose not found. Newer Docker installations include this by default."
      echo "If you're using an older Docker version, please install Docker Compose."
    else
      echo "Docker Compose plugin is installed. Good!"
    fi
  else
    echo "Docker Compose is installed. Good!"
  fi
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
  echo "Creating .env file from template..."
  cp .env.example .env
  echo "Please edit the .env file with your API keys and configuration."
fi

# Start Neo4j container if Docker is installed
if command -v docker &> /dev/null; then
  echo "Would you like to start the Neo4j container now? (y/n)"
  read -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Check if Neo4j password is set in .env
    NEO4J_PASSWORD=$(grep NEO4J_PASSWORD .env | cut -d "=" -f2- | tr -d "'" | tr -d '"')
    if [[ $NEO4J_PASSWORD == "YOUR_STRONG_NEO4J_PASSWORD" ]]; then
      echo "Please set a strong password for Neo4j in the .env file first."
      exit 1
    fi
    
    echo "Starting Neo4j container using Docker Compose..."
    export NEO4J_PASSWORD
    
    # Choose the appropriate docker compose command
    if command -v docker-compose &> /dev/null; then
      docker-compose up -d neo4j
    else
      docker compose up -d neo4j
    fi
    
    echo "Neo4j started! You can access the Neo4j Browser at http://localhost:7474"
    echo "Log in with username 'neo4j' and the password you set in your .env file."
    echo "Note: First startup might take a minute or two, especially on ARM-based Macs."
  fi
fi

echo ""
echo "Setup complete! To run the application:"
echo "1. Make sure you have configured your .env file with the correct credentials"
echo "2. Make sure Neo4j is running (check with 'docker-compose ps' or 'docker ps')"
echo "3. Run 'python main.py'"
echo "" 