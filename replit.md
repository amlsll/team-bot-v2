# Overview

Team Bot is a Telegram bot designed for automatic team formation with flexible team sizes and elastic member addition. The bot manages a queue of users and automatically forms teams every 2 days at 12:00. It features a two-stage registration process (full name + Telegram link), team confirmation system, and comprehensive admin controls.

Key features include:
- Automatic team formation with base size of 5 members + elastic expansion up to 2 additional members (6-7 total)
- Two-stage user registration with data confirmation
- Team participation confirmation with ability to decline and return to queue
- JSON-based storage with atomic writes
- Admin panel with authorization system
- Long polling by default with optional webhook support
- Auto-update system from GitHub repository
- Process monitoring and restart capabilities

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Core Architecture
The bot follows a modular architecture with clear separation of concerns:

**Bot Framework**: Built on aiogram 3.x for Telegram Bot API interaction, using long polling by default with optional webhook mode for production deployments.

**Handler System**: Organized into distinct modules for different user roles and functionalities:
- User handlers: registration, status checking, leaving queue/teams
- Admin handlers: team matching, statistics, broadcasting, user management
- Team handlers: participation confirmation/decline
- Auto-update handlers: GitHub webhook processing and update management

**Storage Layer**: JSON-based file storage with atomic write operations to prevent data corruption. Uses threading locks for concurrent access safety. The storage manages users, queue, teams, counters, admin permissions, and user questions.

**Service Layer**: Encapsulates business logic in dedicated services:
- **Storage Service**: Handles all data persistence operations
- **Matcher Service**: Implements team formation algorithm (base 5 + elastic 2)
- **Notification Service**: Formats and sends team cards and notifications
- **Scheduler Service**: Manages automatic team formation every 2 days
- **ACL Service**: Handles admin authorization and permissions
- **Auto-Update Service**: Manages GitHub integration and code updates
- **Process Lock Service**: Prevents multiple bot instances

## Team Formation Algorithm
The matcher implements a sophisticated algorithm that creates teams with a base size of 5 members and allows elastic expansion up to 2 additional members (6-7 total). It prioritizes FIFO queue ordering and distributes remaining users across existing teams before leaving anyone in the queue.

## State Management
Users progress through defined states: registering → waiting → teamed, with proper state transitions and rollback capabilities. The system maintains data consistency during all operations.

## Admin System
Two-tier admin system supporting both environment-based whitelist admins and runtime-granted admin permissions. Includes comprehensive admin commands for team management, statistics, broadcasting, and system control.

## Error Handling
Comprehensive error handling with detailed logging, graceful degradation, and automatic recovery mechanisms. All operations include proper exception handling with user-friendly error messages.

# External Dependencies

## Core Dependencies
- **aiogram**: Telegram Bot API framework (v3.x) for handling bot interactions
- **python-dotenv**: Environment variable management for configuration
- **aiohttp**: Web server for webhook mode and GitHub webhook handling
- **psutil**: System utilities for process management and conflict prevention

## Development Dependencies
- **pytest**: Testing framework with async support (pytest-asyncio)
- **ruff**: Code linting and formatting

## System Integrations
- **Telegram Bot API**: Primary interface for user interactions
- **GitHub API**: For automatic updates via webhook integration
- **File System**: JSON-based storage with atomic operations

## Optional Integrations
- **GitHub Webhooks**: Automatic deployment on code changes
- **systemd/Docker**: Process management and containerization support
- **Replit**: Cloud deployment platform with built-in webhook support

## Configuration Management
Environment-based configuration supporting development and production modes. Key variables include bot token, admin codes, webhook settings, auto-update preferences, and team formation parameters.

The system is designed to be deployment-agnostic, supporting local development, VPS deployment, Docker containers, and cloud platforms like Replit.