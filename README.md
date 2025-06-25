# Promotion Letters Tool

A Flask-based web application for generating academic promotion letters and personal statements using Claude AI.

## Features

- **Chair's Promotion Letter**: Generate comprehensive promotion letters from department chairs
- **Faculty Promotion Letter**: Create detailed faculty promotion and tenure letters
- **Personal Statement**: Craft compelling personal statements for academic applications
- **Session Management**: Maintain user sessions across pages
- **Rate Limiting**: Prevent API abuse with intelligent rate limiting
- **Docker Support**: Easy deployment with Docker containers

## Quick Start

1. **Initial Setup**
   ```bash
   make setup
   ```
   This creates a `.env` file with required environment variables.

2. **Configure Environment**
   Edit the `.env` file and add your Claude API key:
   ```bash
   CLAUDE_API_KEY=your_actual_claude_api_key_here
   ```

3. **Start the Application**
   ```bash
   make start
   ```
   This will build and start the application at `http://localhost:5000`

## Available Commands

- `make help` - Show all available commands
- `make build` - Build the Docker image
- `make up` - Start the application
- `make down` - Stop the application
- `make restart` - Restart the application
- `make logs` - View application logs
- `make shell` - Access application shell
- `make clean` - Clean up containers and images
- `make status` - Check container status

## Architecture

```
Docker Container
├── Flask Web Server (Port 5000)
├── Redis (Session storage & rate limiting)
├── Multiple Pages
│   ├── Home
│   ├── Chair's Promotion Letter
│   ├── Faculty Promotion Letter
│   └── Personal Statement
```

## File Structure

```
.
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── requirements.txt
├── app.py
├── templates/
│   ├── base.html
│   ├── home.html
│   ├── chairs_promotion_letter.html
│   ├── faculty_promotion_letter.html
│   └── personal_statement.html
├── static/
├── logs/
└── .env
```

## Security Features

- **Intranet Access**: Designed for VPN-protected intranet deployment
- **Session Management**: Secure session handling with Redis
- **Rate Limiting**: 5 requests per minute per IP for API endpoints
- **Error Handling**: Comprehensive error handling and logging

## Development

To add new pages:

1. Add a new route in `app.py`
2. Create corresponding API endpoint
3. Add HTML template in `templates/`
4. Update navigation in `base.html`

## Environment Variables

- `CLAUDE_API_KEY`: Your Claude API key (required)
- `SECRET_KEY`: Flask secret key for sessions
- `FLASK_ENV`: Environment (production/development)
- `FLASK_DEBUG`: Debug mode (true/false)
- `RATE_LIMIT_STORAGE_URL`: Redis URL for rate limiting

## Prerequisites

- Docker and Docker Compose
- Claude API key from Anthropic
- Access to the target intranet/VPN

## Support

For issues or questions, check the application logs:
```bash
make logs
```
