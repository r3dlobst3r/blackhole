import asyncio
import os
import glob
from shared.discord import discordError, discordUpdate, discordStatusUpdate
from shared.shared import blackhole
import re
webhook = None

async def downloader(torrent, file, arr, torrentFile, shared_dict, lock):
    from blackhole import refreshArr
    global webhook

    while True:
        # Check if we have capacity for more downloads
        # For now, simplified version without available host checking
        try:
            # Check if torrent already exists
            # For simplified implementation, directly proceed with adding
            torrentName = file.fileInfo.filenameWithoutExt
            
            # Add torrent
            if not torrent.submitTorrent():
                remove_file(torrentFile, lock, shared_dict, "", current=True)
                return
                
            info = await torrent.getInfo(refresh=True)
            if info and 'filename' in info:
                torrentName = info['filename']
            
            lock.acquire()
            try:
                shared_dict.update({torrentName: "added"})
                webhook = discordStatusUpdate(shared_dict, webhook, edit=True if webhook else False)
            finally:
                lock.release()
            break
        except Exception as e:
            print(f"Error adding torrent: {e}")
            await asyncio.sleep(60)
    
    count = 0
    progress = 0
    waitForProgress = 0
    while True:
        count += 1
        info = await torrent.getInfo(refresh=True)
        if not info or "status" not in info:
            remove_file(torrentFile, lock, shared_dict, torrentName, current=True)
            return
        status = info['status']
        
        # Update torrent name if it changed
        if 'filename' in info and torrentName != info['filename']:
            lock.acquire()
            try:
                if torrentName in shared_dict:
                    del shared_dict[torrentName]
                if shared_dict and webhook and hasattr(webhook, 'id'):
                    webhook = discordStatusUpdate(shared_dict, webhook, edit=True)
                elif not shared_dict and webhook and hasattr(webhook, 'id'):
                    webhook = discordStatusUpdate(shared_dict, webhook, delete=True)
            finally:
                lock.release()
            torrentName = info['filename']

        print('status:', status)
        if not os.path.exists(torrentFile):
            torrent.delete()
            break
        if status == torrent.STATUS_WAITING_FILES_SELECTION:
            if not await torrent.selectFiles():
                torrent.delete()
                break
        elif status in ['magnet_conversion', 'queued', 'compressing', 'uploading']:
            await asyncio.sleep(1)
        elif status == torrent.STATUS_DOWNLOADING:
            if 'progress' in info:
                if progress != info['progress']:
                    progress = info['progress']
                    waitForProgress = 0
                elif waitForProgress >= blackhole['waitForProgressChange']:
                    torrent.delete()
                    remove_file(torrentFile, lock, shared_dict, torrentName, current=True)
                    return
                else:
                    waitForProgress += 1
                print(f"Progress: {progress}%")
                lock.acquire()
                try:
                    shared_dict.update({torrentName: f"Downloading {progress}%"})
                    webhook = discordStatusUpdate(shared_dict, webhook, edit=True if webhook else False)
                finally:
                    lock.release()
            await asyncio.sleep(60)
        elif status in ['magnet_error', 'error', 'dead', 'virus']:
            discordError(f"Error: {file.fileInfo.filenameWithoutExt}", info)
            torrent.delete()
            break
        elif status == torrent.STATUS_COMPLETED:
            existsCount = 0
            print('Waiting for folders to refresh...')

            # Get the torrent path
            folderPathMountTorrent = await torrent.getTorrentPath()
            
            if folderPathMountTorrent and os.path.exists(folderPathMountTorrent):
                multiSeasonRegex1 = r'(?<=[\W_][Ss]eason[\W_])[\d][\W_][\d]{1,2}(?=[\W_])'
                multiSeasonRegex2 = r'(?<=[\W_][Ss])[\d]{2}[\W_][Ss]?[\d]{2}(?=[\W_])'
                multiSeasonRegexCombined = f'{multiSeasonRegex1}|{multiSeasonRegex2}'

                multiSeasonMatch = re.search(multiSeasonRegexCombined, file.fileInfo.filenameWithoutExt)

                for root, dirs, files in os.walk(folderPathMountTorrent):
                    relRoot = os.path.relpath(root, folderPathMountTorrent)
                    for filename in files:
                        source_path = os.path.join(root, filename)
                        
                        if multiSeasonMatch:
                            seasonMatch = re.search(r'S([\d]{2})E[\d]{2}', filename)
                            
                            if seasonMatch:
                                season = seasonMatch.group(1)
                                seasonShort = season[1:] if season[0] == '0' else season

                                seasonFolderPathCompleted = re.sub(multiSeasonRegex1, seasonShort, file.fileInfo.folderPathCompleted)
                                seasonFolderPathCompleted = re.sub(multiSeasonRegex2, season, seasonFolderPathCompleted)

                                os.makedirs(os.path.join(seasonFolderPathCompleted, relRoot), exist_ok=True)
                                target_path = os.path.join(seasonFolderPathCompleted, relRoot, filename)
                                if os.path.exists(target_path):
                                    os.remove(target_path)
                                os.symlink(source_path, target_path)
                                print('Season Recursive:', f"{target_path} -> {source_path}")
                                continue

                        target_path = os.path.join(file.fileInfo.folderPathCompleted, relRoot, filename)
                        os.makedirs(os.path.join(file.fileInfo.folderPathCompleted, relRoot), exist_ok=True)
                        if os.path.exists(target_path):
                            os.remove(target_path)
                        os.symlink(source_path, target_path)
                        print('Recursive:', f"{target_path} -> {source_path}")
                
                print('Refreshed')
                discordUpdate(f"Successfully processed {file.fileInfo.filenameWithoutExt}", f"Now available for immediate consumption!")
                
                await refreshArr(arr)
                break
            else:
                existsCount += 1
                if existsCount >= blackhole['rdMountRefreshSeconds'] + 1:
                    print(f"Torrent folder not found in filesystem: {file.fileInfo.filenameWithoutExt}")
                    discordError("Torrent folder not found in filesystem", file.fileInfo.filenameWithoutExt)
                    return False
                await asyncio.sleep(1)
    
        if count >= blackhole['waitForTorrentTimeout']:
            print(f"infoCount == {blackhole['waitForTorrentTimeout']} - Timing out")
            torrent.delete()
            break
    
    remove_file(torrentFile, lock, shared_dict, torrentName)
    
def remove_file(torrentFile, lock, shared_dict, torrentName, current=False):
    """Remove torrent file and update Discord status"""
    if os.path.exists(torrentFile):
        try:
            os.remove(torrentFile)
            print(f"Removed: {torrentFile}")
        except Exception as e:
            print(f"Error removing {torrentFile}: {e}")

        # Try to remove parent directory if empty
        folder_path = os.path.dirname(torrentFile)
        try:
            if os.path.exists(folder_path) and not os.listdir(folder_path):
                os.rmdir(folder_path)
                print(f"Removed empty folder: {folder_path}")
        except Exception as e:
            print(f"Error removing folder {folder_path}: {e}")
    else:
        print("The file does not exist.")

    # Update Discord status
    lock.acquire()
    try:
        global webhook
        if torrentName in shared_dict:
            del shared_dict[torrentName]
        if shared_dict and webhook and hasattr(webhook, 'id'):
            webhook = discordStatusUpdate(shared_dict, webhook, edit=True)
        elif not shared_dict and webhook and hasattr(webhook, 'id'):
            webhook = discordStatusUpdate(shared_dict, webhook, delete=True)
    finally:
        lock.release()