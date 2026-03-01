# Changelog

All notable changes to the Agent Task Manager project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive documentation:
  - `docs/INSTALLATION.md` - Step-by-step installation guide
  - `docs/API.md` - Complete REST API reference
  - `docs/CLI.md` - Command-line interface guide
  - `docs/AGENTS.md` - AI agent integration guide
  - `docs/DEPLOYMENT.md` - Production deployment guide
- Example workflow script: `examples/basic_workflow.py`
- Contribution guidelines: `CONTRIBUTING.md`
- This changelog: `CHANGELOG.md`

### Changed
- Updated README.md with improved navigation and documentation links
- Enhanced project structure documentation

### Fixed
- (No fixes in this release)

## [1.0.0] - 2026-03-01

### Added
- Initial release of Agent Task Manager
- Core features:
  - Custom Kanban board with drag-and-drop
  - Multi-project support
  - AI agent coordination (Ren, Aki, Kuro, Shin, Sora)
  - Crash recovery with heartbeat system
  - Real-time updates via Server-Sent Events
  - Command-line interface (CLI)
  - RESTful API with FastAPI
  - Self-contained SQLite database

### Components
- **Backend**: FastAPI application with SQLite database
- **Frontend**: Vanilla JavaScript HTML interface
- **CLI**: Python-based command-line tool
- **Documentation**: Architecture and basic usage guides

### Known Issues
- No authentication for local development
- Limited to SQLite database
- Basic error handling

---

## Versioning

- **Major version (1.0.0)**: Initial stable release
- **Minor version (1.1.0)**: New features, backward compatible
- **Patch version (1.0.1)**: Bug fixes, backward compatible

## How to Update

When updating between versions:

1. Check the changelog for breaking changes
2. Backup your database: `cp backend/agent_tasks.db backend/agent_tasks.db.backup`
3. Update the code: `git pull origin main`
4. Run any migration scripts if provided
5. Restart the application

---

*This changelog was started on 2026-03-01 to track future changes.*