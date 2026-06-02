# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Build & Dev Commands
- Python: `poetry install` - Install dependencies
- Python: `python main.py` - Run the application
- Client: `cd client && npm install` - Install client dependencies
- Client: `cd client && npm run dev` - Start development server
- Client: `cd client && npm run build` - Build for production
- Client: `cd client && npm run lint` - Run ESLint
- Client: `cd client && npm run test` - Run tests

## Code Style

### Python
- Use snake_case for variables, functions; PascalCase for classes
- Order imports: standard library → third-party → local
- Use type hints for parameters and return values
- Document functions with triple-quote docstrings (Args/Returns)
- Handle exceptions with specific except blocks and proper logging

### TypeScript/React
- Use camelCase for variables/functions; PascalCase for components
- Functional components with explicit typing (React.FC<Props>)
- Use React hooks (useState, useEffect) with proper dependency arrays
- Service classes for API and data management
- Strong typing with interfaces and types

## Project Structure
- `/api` - FastAPI endpoints and utilities
- `/client` - React frontend application
- `/core` - Core Python application logic
- `/data` - Data files and storage
- `/services` - Backend services