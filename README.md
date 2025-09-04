# 🌈 Bifrost-Minion

> **Part of the Vardr Bifrost Ecosystem** - A high-performance dependency download and packaging service

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://python.org)
[![Node.js](https://img.shields.io/badge/Node.js-22-green.svg)](https://nodejs.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)
[![FastStream](https://img.shields.io/badge/FastStream-RabbitMQ-orange.svg)](https://faststream.airt.ai)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 📋 Table of Contents

- [🌈 Bifrost-Minion](#-bifrost-minion)
  - [📋 Table of Contents](#-table-of-contents)
  - [🚀 Overview](#-overview)
  - [🏗️ Architecture](#️-architecture)
  - [✨ Features](#-features)
  - [🛠️ Supported Processors](#️-supported-processors)
  - [📦 Installation](#-installation)
    - [🐳 Docker (Recommended)](#-docker-recommended)
    - [🐍 Local Development](#-local-development)
  - [⚙️ Configuration](#️-configuration)
  - [🚀 Quick Start](#-quick-start)
  - [📊 API Reference](#-api-reference)
  - [🔧 Development](#-development)
  - [📁 Project Structure](#-project-structure)
  - [🔍 Monitoring & Logging](#-monitoring--logging)
  - [🤝 Contributing](#-contributing)
  - [📄 License](#-license)

## 🚀 Overview

**Bifrost-Minion** is a specialized microservice within the **Vardr Bifrost** ecosystem, designed to handle the download, packaging, and distribution of various software dependencies. Acting as a bridge between different package ecosystems, it processes requests asynchronously through RabbitMQ and delivers packaged artifacts to downstream systems.

### 🎯 Purpose

The Bifrost-Minion serves as the **dependency acquisition layer** in air-gapped or controlled environments, enabling organizations to:

- **Centralize dependency management** across multiple technology stacks
- **Package and standardize** artifacts from various sources
- **Maintain security** through controlled download processes  
- **Enable offline operations** by pre-downloading dependencies

### 🔄 Processing Pipeline

Each dependency follows a consistent **three-step pipeline**:

1. **📥 Download Step**: Fetch the dependency from its source
2. **📦 Packaging Step**: Package into a standardized tarball format  
3. **🚀 Sending Step**: Deliver to the configured HTTP endpoint

For more information about the complete Vardr Bifrost ecosystem, see the [Bifrost API Documentation](https://github.com/SPJDevOps/vardr-Bifrost-API).

## 🏗️ Architecture

Bifrost-Minion uses a **modular processor architecture** built on FastStream and RabbitMQ:

```mermaid
graph TD
    A[RabbitMQ Queue] --> B[Download Router]
    B --> C{Processor Type}
    C -->|DOCKER| D[Docker Processor]
    C -->|MAVEN| E[Maven Processor] 
    C -->|PYTHON| F[Python Processor]
    C -->|NPM| G[NPM Processor]
    C -->|HELM| H[Helm Processor]
    C -->|FILE| I[File Processor]
    C -->|WEBSITE| J[Website PDF Processor]
    
    D --> K[Base Processor Pipeline]
    E --> K
    F --> K
    G --> K
    H --> K
    I --> K
    J --> K
    
    K --> L[Download Step]
    L --> M[Package Step]
    M --> N[Send Step]
    N --> O[NiFi HTTP Endpoint]
    
    K --> P[Status Updates]
    P --> Q[RabbitMQ Status Queue]
```

## ✨ Features

- 🚀 **High-Performance Async Processing** - Built on FastStream for maximum throughput
- 🔄 **Multiple Dependency Types** - Support for 7+ different package ecosystems
- 🛡️ **Robust Error Handling** - Automatic retry logic with proper error categorization
- 📦 **Standardized Output** - All artifacts packaged as tarballs for consistency
- 🔒 **Security-First** - Non-root containers, input validation, and secure defaults
- 📊 **Comprehensive Monitoring** - Built-in health checks and status reporting
- 🐳 **Container-Ready** - Optimized Docker images with Python 3.13 + Node.js 22
- ⚡ **Non-Blocking Operations** - Thread pool execution for CPU-intensive tasks

## 🛠️ Supported Processors

| Processor | Description | Input Format | Output |
|-----------|-------------|--------------|--------|
| **Docker** | Pull and package Docker images | `nginx:latest` | Image tarball |
| **Maven** | Download Maven artifacts | `org.apache:commons-lang3:3.12.0` | JAR + dependencies |
| **Python** | Download Python packages | `requests==2.31.0` | Wheel files |
| **NPM** | Download NPM packages | `express@4.18.2` | Package tarballs |
| **Helm** | Download Helm charts | `https://charts.helm.sh/stable` | Chart archives |
| **File** | Download files from URLs | `https://example.com/file.zip` | Raw files |
| **Website** | Convert websites to PDF | `https://docs.python.org` | PDF documents |

---

## 📦 Installation

### 🐳 Docker (Recommended)

The fastest way to get started is using Docker Compose:

```bash
# Clone the repository
git clone <repository-url>
cd bifrost-minion

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f download-minion
```

**What's included:**
- ✅ Bifrost-Minion service
- ✅ RabbitMQ with management UI
- ✅ Pre-configured networking
- ✅ Persistent volumes

### 🐍 Local Development

For development or customization:

```bash
# Prerequisites
# - Python 3.13+
# - Node.js 22+
# - Java 17+ (for Maven)
# - Docker (for Docker processor)

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Install dependencies

pip install -r requirements.txt

# Run the application
python run.py
```

## ⚙️ Configuration

Configure Bifrost-Minion using environment variables:

### 🔧 Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `RABBITMQ_HOST` | `amqp://guest:guest@localhost:5672/` | RabbitMQ connection string |
| `RABBITMQ_DOWNLOAD_REQUEST_QUEUE` | `private.hyperloop.download_requests` | Input queue name |
| `RABBITMQ_DOWNLOAD_STATUS_QUEUE` | `private.hyperloop.download_status` | Status update queue |
| `NIFI_LISTEN_HTTP_ENDPONT` | `http://localhost:9099/hyperloop` | Target HTTP endpoint |

### 🐳 Docker Environment

```bash
# .env file for docker-compose
RABBITMQ_HOST=amqp://guest:guest@rabbitmq:5672/
NIFI_LISTEN_HTTP_ENDPONT=http://nifi:9099/hyperloop
```

### 🔒 Security Configuration

```bash
# Production settings
RABBITMQ_HOST=amqps://user:pass@secure-rabbitmq:5671/
NIFI_LISTEN_HTTP_ENDPONT=https://secure-nifi:8443/hyperloop
```

## 🚀 Quick Start

### 1. Start the Services

```bash
# Using Docker Compose
docker-compose up -d

# Or locally (requires RabbitMQ running)
python run.py
```

### 2. Send a Download Request

```bash
# Example: Download a Docker image
curl -X POST http://localhost:15672/api/exchanges/%2f/amq.default/publish \
  -u guest:guest \
  -H "Content-Type: application/json" \
  -d '{
    "properties": {},
    "routing_key": "private.hyperloop.download_requests",
    "payload": "{\"type\": \"DOCKER\", \"dependency\": \"nginx:latest\", \"id\": \"req-001\"}"
  }'
```

### 3. Monitor Progress

- **RabbitMQ Management**: http://localhost:15672 (guest/guest)
- **Application Logs**: `docker-compose logs -f download-minion`
- **Status Queue**: Monitor `private.hyperloop.download_status` for updates

## 📊 API Reference

### Message Format

All download requests follow this JSON structure:

```json
{
  "type": "DOCKER|MAVEN|PYTHON|NPM|HELM|FILE|WEBSITE",
  "dependency": "dependency-identifier",
  "id": "unique-request-id"
}
```

### Request Examples

#### Docker Image
```json
{
  "type": "DOCKER",
  "dependency": "nginx:1.21-alpine",
  "id": "docker-nginx-001"
}
```

#### Maven Artifact
```json
{
  "type": "MAVEN", 
  "dependency": "org.springframework:spring-core:5.3.21",
  "id": "maven-spring-001"
}
```

#### Python Package
```json
{
  "type": "PYTHON",
  "dependency": "fastapi==0.68.0",
  "id": "python-fastapi-001"
}
```

### Status Updates

Status updates are published to the status queue with this format:

```json
{
  "id": "unique-request-id",
  "type": "DOCKER",
  "dependency": "nginx:latest", 
  "status": "DOWNLOADING|SENDING|DONE|FAILED"
}
```

## 🔧 Development

### Local Development Setup

```bash
# 1. Start RabbitMQ (using Docker)
docker run -d --name rabbitmq \
  -p 5672:5672 -p 15672:15672 \
  rabbitmq:3.13-management-alpine

# 2. Set environment variables
export RABBITMQ_HOST="amqp://guest:guest@localhost:5672/"
export NIFI_LISTEN_HTTP_ENDPONT="http://localhost:9099/hyperloop"

# 3. Start the application with auto-reload
python run.py
```

### Testing Individual Processors

```bash
# Test Docker processor
python -c "
import asyncio
from app.processors.docker_processor import DockerProcessor
from app.models.hyperloop_download import HyperloopDownload

async def test():
    download = HyperloopDownload(type='DOCKER', dependency='hello-world:latest', id='test-001')
    processor = DockerProcessor(None, 'test-queue')
    await processor._download_dependency(download)

asyncio.run(test())
"
```

### Code Quality

```bash
# Install development dependencies
pip install black flake8 pytest

# Format code
black app/

# Lint code
flake8 app/

# Run tests
pytest tests/
```

## 📁 Project Structure

```
bifrost-minion/
├── app/
│   ├── helpers/
│   │   └── nifi_uploader.py          # HTTP upload functionality
│   ├── models/
│   │   ├── download_status.py        # Status enumeration
│   │   ├── exceptions.py             # Custom exceptions
│   │   └── hyperloop_download.py     # Download request model
│   ├── processors/
│   │   ├── base_processor.py         # Shared processor logic
│   │   ├── docker_processor.py       # Docker image handling
│   │   ├── download_router.py        # Message routing
│   │   ├── file_download_processor.py # File downloads
│   │   ├── helm_chart_processor.py   # Helm chart handling
│   │   ├── maven_processor.py        # Maven artifact handling
│   │   ├── npm_package_processor.py  # NPM package handling
│   │   ├── python_package_processor.py # Python package handling
│   │   └── website_pdf_processor.py  # Website to PDF conversion
│   └── main.py                       # FastStream application
├── docker-compose.yml               # Development environment
├── Dockerfile                       # Container definition
├── requirements.txt                 # Python dependencies
└── run.py                          # Application entry point
```

## 🔍 Monitoring & Logging

### Health Checks

The Docker container includes built-in health checks:

```bash
# Check container health
docker inspect --format='{{.State.Health.Status}}' bifrost-minion
```

### Logging

Application logs are structured and include:

- **Request Processing**: Download start/completion
- **Error Handling**: Detailed error messages with context
- **Performance Metrics**: Processing times and queue depths

```bash
# View logs
docker-compose logs -f download-minion

# Filter specific processor logs
docker-compose logs download-minion | grep "Docker"
```

### Metrics

Monitor key metrics:

- **Queue Depth**: RabbitMQ management UI
- **Processing Time**: Application logs
- **Success Rate**: Status queue messages
- **Error Rate**: Failed status updates

## 🤝 Contributing

We welcome contributions to the Bifrost-Minion project! Here's how you can help:

### 🐛 Bug Reports

1. **Check existing issues** before creating new ones
2. **Use the issue template** and provide detailed information
3. **Include logs and error messages** when applicable

### 💡 Feature Requests

1. **Describe the use case** and business value
2. **Provide examples** of the desired functionality  
3. **Consider compatibility** with the existing architecture

### 🔧 Development Contributions

1. **Fork the repository** and create a feature branch
2. **Follow code standards**: Black formatting, type hints, docstrings
3. **Add tests** for new functionality
4. **Update documentation** as needed
5. **Submit a pull request** with a clear description

### 🏗️ Adding New Processors

To add support for a new dependency type:

1. **Extend BaseProcessor**: Create a new processor class
2. **Implement _download_dependency**: Add the download logic
3. **Add to router**: Register in `download_router.py`
4. **Add tests**: Ensure functionality works correctly
5. **Update documentation**: Add to supported processors table

Example processor template:

```python
from app.processors.base_processor import BaseProcessor
from app.models.exceptions import DependencyNotFoundError, InternalError

class MyProcessor(BaseProcessor):
    def __init__(self, broker, status_queue):
        super().__init__(broker, status_queue, "/tmp/my-processor/")
    
    async def _download_dependency(self, download):
        """Download logic for my processor"""
        # Implementation here
        pass
```

## 📄 License

This project is part of the **Vardr Bifrost** ecosystem and is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## 🔗 Related Projects

- **[Vardr Bifrost API](https://github.com/SPJDevOps/vardr-Bifrost-API)** - Main API gateway and orchestration layer
- **Bifrost-UI** - Web interface for managing downloads (coming soon)
- **Bifrost-Scanner** - Security scanning integration (coming soon)

## 📞 Support

- **Documentation**: [Bifrost API Docs](https://github.com/SPJDevOps/vardr-Bifrost-API/blob/main/README.md)
- **Issues**: [GitHub Issues](https://github.com/SPJDevOps/vardr-Bifrost-API/issues)
- **Discussions**: [GitHub Discussions](https://github.com/SPJDevOps/vardr-Bifrost-API/discussions)

---

<div align="center">

**Built with ❤️ for the DevOps community**

*Part of the Vardr Bifrost Ecosystem*

</div>
