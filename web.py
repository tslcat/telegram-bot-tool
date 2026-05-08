from flask import Flask, send_from_directory, abort
import os
from config import IMAGES_DIR, WEB_PORT

app = Flask(__name__)

@app.route('/images/<filename>')
def serve_image(filename):
    """提供图片访问"""
    try:
        return send_from_directory(IMAGES_DIR, filename)
    except FileNotFoundError:
        abort(404)

@app.route('/images/')
def list_images():
    """简单图片列表页面"""
    files = os.listdir(IMAGES_DIR)
    html = "<h1>图床图片列表</h1><ul>"
    for f in sorted(files, reverse=True):
        html += f'<li><a href="/images/{f}">{f}</a></li>'
    html += "</ul>"
    return html

@app.route('/')
def index():
    return """
    <h1>Telegram 工具箱 - 图床服务</h1>
    <p>图片访问路径: <code>/images/文件名</code></p>
    <p>完整链接示例: https://yourdomain.com/images/abc123.jpg</p>
    <p>Bot 管理请在 Telegram 中使用</p>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=WEB_PORT, debug=False)