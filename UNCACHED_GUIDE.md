# Uncached Downloading Support - Implementation Guide

## Overview

This implementation adds comprehensive uncached downloading support to the blackhole project, based on the [Priky-one fork](https://github.com/Priky-one/scripts/tree/dev). The system automatically handles torrents that are not cached by prioritizing cached content first, then seamlessly falling back to uncached downloads with full progress tracking and state persistence.

## Features Implemented

### 🎯 Core Features
- **Automatic Fallback**: When cached downloads fail, automatically processes as uncached
- **Parallel Processing**: Configurable limits for concurrent downloads
- **Real-time Progress**: Discord webhook integration with download percentages
- **State Persistence**: Downloads resume automatically after restarts
- **Smart Organization**: Intelligent folder structure based on parsed content

### 🔧 Technical Features
- **RTN Integration**: Advanced torrent name parsing for proper categorization
- **Thread Safety**: Proper locking mechanisms for concurrent operations
- **Error Handling**: Comprehensive retry logic and graceful degradation
- **Backward Compatibility**: Existing functionality remains unchanged

## New Environment Variables

Add to your `.env` file:

```bash
# Uncached download configuration
BLACKHOLE_WAIT_FOR_PROGRESS_CHANGE=720  # Seconds to wait for download progress before timeout
```

## File Structure

The implementation adds the following directory structure:

```
blackhole/
├── Movies/
│   ├── completed/          # Existing cached downloads
│   ├── processing/         # Existing processing folder
│   └── uncached/          # NEW: Uncached downloads
│       └── {Movie Title}/
│           └── movie.torrent
└── TV Shows/
    ├── completed/          # Existing cached downloads
    ├── processing/         # Existing processing folder
    └── uncached/          # NEW: Uncached downloads
        └── {Show Title}/
            ├── {episode_num}/     # Single episodes
            │   └── episode.torrent
            └── seasonpack/        # Season packs
                └── {seasons}/
                    └── season.torrent
```

## New Files Added

### 1. `blackhole_downloader.py`
Main uncached download processing module:
- Handles torrent submission and monitoring
- Manages Discord progress updates
- Processes completed downloads and creates symlinks
- Handles file cleanup and error recovery

### 2. Enhanced `shared/discord.py`
- Added `discordStatusUpdate()` function for real-time progress tracking
- Supports create, edit, and delete operations for status messages
- Thread-safe status management

### 3. Updated `blackhole.py`
- Added `resumeUncached()` function for restart persistence
- Enhanced `fail()` function with uncached processing support
- Integrated RTN parsing for intelligent categorization
- Added global state management with `shared_dict` and `download_lock`

## Usage Workflow

### Cached Downloads (Existing)
1. Torrent file dropped into watch folder
2. System checks cache availability
3. If cached: Downloads immediately (existing behavior)

### Uncached Downloads (NEW)
1. Torrent file dropped into watch folder
2. System checks cache availability
3. If not cached: Moves to uncached processing
4. Parses torrent name using RTN
5. Organizes into appropriate uncached folder structure
6. Submits for uncached download with progress tracking
7. Creates symlinks when complete
8. Sends Discord notifications with real-time progress

### Restart Behavior (NEW)
1. Application starts
2. Scans uncached folders for incomplete downloads
3. Resumes processing automatically
4. Continues Discord progress updates

## Discord Integration

The enhanced Discord integration provides:

### Status Updates
- Real-time download progress (e.g., "Downloading 45%")
- Multiple concurrent download tracking
- Automatic cleanup when downloads complete

### Error Notifications
- Failed download alerts
- Timeout notifications
- Service availability issues

### Success Messages
- Download completion notifications
- Processing time statistics
- Availability confirmations

## Configuration Examples

### Basic Setup
```bash
# Required for uncached downloads
BLACKHOLE_WAIT_FOR_PROGRESS_CHANGE=720

# Enable Discord for progress tracking
DISCORD_ENABLED=true
DISCORD_UPDATE_ENABLED=true
DISCORD_WEBHOOK_URL=your_webhook_url_here
```

### Advanced Setup
```bash
# Faster timeout for testing
BLACKHOLE_WAIT_FOR_PROGRESS_CHANGE=300

# Standard blackhole settings
BLACKHOLE_FAIL_IF_NOT_CACHED=false  # Enables uncached fallback
BLACKHOLE_WAIT_FOR_TORRENT_TIMEOUT=3600  # Extended timeout for uncached
```

## Monitoring and Troubleshooting

### Log Messages
- `[filename] Pushing to uncached downloader` - Torrent moved to uncached processing
- `Processing uncached downloads` - Startup resume process
- `Successfully processed {filename}` - Download completed

### Discord Messages
- `Downloading Status: Current downloading - X` - Active downloads count
- `{filename}: Downloading Y%` - Individual progress updates
- `Successfully processed {filename}` - Completion notifications

### Folder Monitoring
- Check `uncached/` folders for stuck downloads
- Monitor `processing/` for active cached attempts
- Verify `completed/` for successful downloads

## Performance Considerations

### Parallel Limits
- Default: 4 concurrent downloads per category
- Configurable via environment variables
- Automatic throttling based on service limits

### Resource Usage
- Minimal CPU overhead for monitoring
- Network bandwidth based on concurrent downloads
- Storage: temporary files in uncached folders

### Service Integration
- Works with existing Real-Debrid and Torbox integration
- Respects service rate limits
- Automatic account switching for load balancing

## Migration from Existing Setup

The implementation is fully backward compatible:

1. **No configuration changes required** - uncached support is automatic
2. **Existing downloads continue working** - cached behavior unchanged
3. **Optional Discord enhancements** - progress tracking is opt-in
4. **Gradual adoption** - can be enabled per service

## Troubleshooting

### Common Issues

**Downloads stuck in uncached folder:**
- Check service API keys and connectivity
- Verify mount paths are accessible
- Review Discord logs for error messages

**Missing progress updates:**
- Verify Discord webhook URL is correct
- Check `DISCORD_UPDATE_ENABLED=true`
- Ensure network connectivity to Discord

**Downloads not resuming:**
- Check file permissions in uncached folders
- Verify RTN parsing is working correctly
- Review logs for parsing errors

### Debug Mode
Enable verbose logging by setting environment variables:
```bash
PYTHONUNBUFFERED=TRUE
```

## Dependencies

New dependencies added:
- `rank-torrent-name` - Advanced torrent name parsing
- Existing dependencies remain unchanged

## Security Considerations

- No new network endpoints exposed
- Uses existing service authentication
- Thread-safe concurrent operations
- Proper file permission handling

## Future Enhancements

The implementation provides a foundation for:
- Custom download prioritization rules
- Advanced retry strategies
- Multi-service load balancing
- Performance analytics
- Custom notification channels

## Support

For issues or questions:
1. Check logs for error messages
2. Verify environment configuration
3. Test with Discord webhook enabled
4. Review uncached folder structure
5. Submit issues with relevant log excerpts

The uncached downloading implementation provides a robust, production-ready solution for handling non-cached content while maintaining the existing blackhole functionality.