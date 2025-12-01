# RoboBurn Web Interface

A web-based control panel for monitoring and controlling the RoboBurn system, featuring real-time temperature monitoring and PID control.

## Features

- Real-time oil and turkey temperature monitoring
- Interactive temperature graph with historical data
- PID-controlled burner management
- Responsive design for desktop and mobile
- Offline-capable with local asset management

## Code Quality and Linting

Install optional development tools:

```bash
# Install dev dependencies defined in pyproject.toml
uv sync --extra dev
```

Run tools:

```bash
# Format code
uv run ruff format .

# Lint and auto-fix (includes import sorting)
uv run ruff check --fix .

# Run tests
uv run pytest
```

## Prerequisites

- Python 3.8+
- Node.js 16+ (for frontend dependencies)
- [uv](https://github.com/astral-sh/uv) (Python package and environment manager)
- npm (comes with Node.js)

## Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/roboburn-pi-webapp.git
   cd roboburn-pi-webapp
   ```

2. **Set up Python environment with uv**
   ```bash
   # Install Python dependencies (uv creates and manages .venv automatically)
   uv sync
   
   # Optional: include development tools (black, isort, flake8, pytest)
   uv sync --extra dev
   ```

3. **Install frontend dependencies**
   ```bash
   npm install
   ```

## Running the Application

### Development Mode

```bash
# Set Flask to development mode
export FLASK_APP=app.py
export FLASK_ENV=development

# Install development dependencies
uv sync

# Run the development server
uv run flask assets build
uv run flask run --host=0.0.0.0
```

## Project Structure

```
roboburn-pi-webapp/
├── static/               # Static files (CSS, JS, images)
│   └── gen/              # Generated assets (auto-created)
├── templates/            # HTML templates
├── app.py               # Main application
├── pyproject.toml      # Python project configuration
├── webassets_config.py  # Asset management configuration
├── package.json         # Node.js dependencies
└── .gitignore          # Git ignore rules
```

## Asset Management

This project uses `webassets` with `flask-assets` for managing frontend dependencies:

- **Adding new CSS/JS**: Update the bundles in `app.py`
- **Rebuilding assets**: Run `flask assets build`

## License

[Your License Here]

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Support

For support, please open an issue in the GitHub repository.
