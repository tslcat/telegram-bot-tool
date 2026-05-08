import os
import zipfile
import shutil
import requests
from datetime import datetime
from config import DATA_DIR, IMAGES_DIR, DB_PATH, WEBDAV_URL, WEBDAV_USERNAME, WEBDAV_PASSWORD

def create_backup_zip() -> str:
    """创建备份 zip 文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup_{timestamp}.zip"
    backup_path = os.path.join(DATA_DIR, backup_name)
    
    with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # 添加数据库
        if os.path.exists(DB_PATH):
            zipf.write(DB_PATH, arcname="bot.db")
        
        # 添加图片目录
        for root, dirs, files in os.walk(IMAGES_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, DATA_DIR)
                zipf.write(file_path, arcname=arcname)
    
    return backup_path

def upload_to_webdav(local_path: str, remote_filename: str = None) -> bool:
    """上传文件到 WebDAV"""
    if not WEBDAV_URL or not WEBDAV_USERNAME or not WEBDAV_PASSWORD:
        print("WebDAV 配置未设置，跳过上传")
        return False
    
    if remote_filename is None:
        remote_filename = os.path.basename(local_path)
    
    # 确保远程目录存在
    remote_dir = WEBDAV_URL.rstrip("/") + "/"
    
    try:
        # 创建目录（如果不存在）
        requests.request(
            "MKCOL",
            remote_dir,
            auth=(WEBDAV_USERNAME, WEBDAV_PASSWORD),
            timeout=30
        )
        
        # 上传文件
        with open(local_path, "rb") as f:
            response = requests.put(
                remote_dir + remote_filename,
                data=f,
                auth=(WEBDAV_USERNAME, WEBDAV_PASSWORD),
                timeout=300
            )
        
        if response.status_code in [200, 201, 204]:
            print(f"成功上传备份到 WebDAV: {remote_filename}")
            return True
        else:
            print(f"WebDAV 上传失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"WebDAV 上传异常: {e}")
        return False

def download_from_webdav(remote_filename: str, local_path: str) -> bool:
    """从 WebDAV 下载文件"""
    if not WEBDAV_URL or not WEBDAV_USERNAME or not WEBDAV_PASSWORD:
        return False
    
    remote_url = WEBDAV_URL.rstrip("/") + "/" + remote_filename
    
    try:
        response = requests.get(
            remote_url,
            auth=(WEBDAV_USERNAME, WEBDAV_PASSWORD),
            timeout=300,
            stream=True
        )
        
        if response.status_code == 200:
            with open(local_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"成功从 WebDAV 下载: {remote_filename}")
            return True
        else:
            print(f"WebDAV 下载失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"WebDAV 下载异常: {e}")
        return False

def backup_now() -> str:
    """执行完整备份流程"""
    print("开始创建备份...")
    zip_path = create_backup_zip()
    print(f"本地备份创建完成: {zip_path}")
    
    remote_name = os.path.basename(zip_path)
    success = upload_to_webdav(zip_path, remote_name)
    
    if success:
        # 可选：删除本地旧备份（保留最近3个）
        cleanup_old_backups()
    
    return zip_path

def cleanup_old_backups(keep: int = 3):
    """清理旧备份文件"""
    backups = sorted(
        [f for f in os.listdir(DATA_DIR) if f.startswith("backup_") and f.endswith(".zip")],
        reverse=True
    )
    for old_backup in backups[keep:]:
        try:
            os.remove(os.path.join(DATA_DIR, old_backup))
            print(f"已删除旧备份: {old_backup}")
        except Exception as e:
            print(f"删除旧备份失败: {e}")

def restore_from_zip(zip_path: str) -> bool:
    """从 zip 恢复数据"""
    try:
        # 备份当前数据
        if os.path.exists(DB_PATH):
            shutil.copy(DB_PATH, DB_PATH + ".bak")
        
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            zipf.extractall(DATA_DIR)
        
        print("数据恢复完成！")
        return True
    except Exception as e:
        print(f"恢复失败: {e}")
        return False

def list_webdav_backups() -> list:
    """列出 WebDAV 上的备份文件"""
    if not WEBDAV_URL:
        return []
    
    try:
        response = requests.request(
            "PROPFIND",
            WEBDAV_URL.rstrip("/") + "/",
            auth=(WEBDAV_USERNAME, WEBDAV_PASSWORD),
            headers={"Depth": "1"},
            timeout=30
        )
        
        if response.status_code == 207:
            # 简单解析（生产环境建议用 xml 库）
            backups = []
            for line in response.text.split("\n"):
                if "backup_" in line and ".zip" in line:
                    # 提取文件名（简化处理）
                    import re
                    match = re.search(r'backup_\d+_\d+\.zip', line)
                    if match:
                        backups.append(match.group())
            return sorted(backups, reverse=True)
    except Exception as e:
        print(f"列出 WebDAV 备份失败: {e}")
    return []