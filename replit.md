# Replit.md

## Overview

This is a Telegram bot application built with Python. The bot responds to the `/start` command by displaying user information (name, username, ID, language) and presenting an inline keyboard with various navigation options for users, groups, channels, and account management.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Bot Framework
- **Framework**: python-telegram-bot library (async version)
- **Pattern**: Command handler architecture using `ApplicationBuilder` pattern
- **Rationale**: The python-telegram-bot library provides a clean async interface for building Telegram bots with minimal boilerplate

### Application Structure
- **Single-file architecture**: Currently a monolithic `main.py` containing all bot logic
- **Command handlers**: Uses decorator-less handler registration pattern
- **Async design**: All handlers are async functions for non-blocking I/O operations

### Current Features
- `/start` command handler that displays user profile information
- Inline keyboard with placeholder buttons for future functionality (User, Premium, Bot, Group, Channel, Forum navigation)

### Future Considerations
- Callback query handlers need to be implemented for the inline keyboard buttons
- The main execution block appears incomplete (missing application build and run logic)
- Consider modularizing into separate files as features grow (handlers, keyboards, utils)

## External Dependencies

### Required Libraries
- **python-telegram-bot**: Core Telegram Bot API wrapper
- **python-telegram-bot[ext]**: Extended features including `ContextTypes` and `ApplicationBuilder`

### Environment Variables
- **TELEGRAM_BOT_TOKEN**: Required for bot authentication (accessed via `os` module, though not currently used in visible code)

### External Services
- **Telegram Bot API**: Primary external service for bot functionality