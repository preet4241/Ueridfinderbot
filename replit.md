# Telegram Bot Project

## Overview
A Telegram bot built with Python that provides user information lookup, chat/channel info retrieval, and admin panel features for the bot owner.

## Features
- User profile lookup (including premium status, language, bio)
- Chat/Channel information retrieval
- Admin panel for owner (user statistics, ban/unban, broadcast, user list export)
- PostgreSQL database for user storage

## Required Environment Variables
- `TELEGRAM_BOT_TOKEN` - Bot token from @BotFather on Telegram
- `OWNER_ID` - Telegram user ID of the bot owner (for admin panel access)

## Tech Stack
- Python 3.11
- python-telegram-bot (v22.5)
- PostgreSQL with psycopg2-binary

## Project Structure
- `main.py` - Main bot application with all handlers and database functions

## Running the Bot
The bot runs via the "Run Telegram Bot" workflow which executes `python main.py`.

## Recent Changes
- 2026-01-20: Initial project import and setup
