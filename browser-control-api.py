from flask import Flask, request, jsonify
import subprocess
import os
import time
from flask_cors import CORS
import threading
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
import logging

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
os.environ['DISPLAY'] = ':1'  # 修改为与Dockerfile中设置的DISPLAY一致

# 在应用初始化时启动一个受控浏览器
browser = None

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("api_debug.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def init_browser():
    global browser
    options = Options()
    options.headless = False  # 需要显示浏览器窗口
    browser = webdriver.Firefox(options=options)
    print("浏览器已初始化")

@app.route('/open', methods=['POST'])
def open_url():
    data = request.json
    url = data.get('url')
    duration = data.get('duration', 10)  # 默认10秒后关闭
    
    if not url:
        return jsonify({"error": "URL不能为空"}), 400
    
    try:
        # 使用线程运行浏览器操作，避免阻塞API
        def run_browser():
            try:
                # 尝试关闭现有Firefox窗口
                subprocess.run(['pkill', '-f', 'firefox'], check=False)
                time.sleep(1)
                
                # 以全屏模式启动Firefox
                browser_process = subprocess.Popen(['firefox', '--new-window', '--kiosk', url])
                
                # 等待指定时间后关闭浏览器
                time.sleep(duration)
                browser_process.terminate()
            except Exception as e:
                logger.error(f"浏览器操作失败: {str(e)}")
        
        # 启动浏览器线程
        threading.Thread(target=run_browser).start()
        
        return jsonify({
            "success": True, 
            "message": f"已在远程浏览器打开: {url}，将在{duration}秒后自动关闭"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/scroll', methods=['GET'])
def scroll_page():
    logger.debug("收到滚动请求")
    
    # 获取所有查询参数
    url = request.args.get('url', '')
    direction = request.args.get('direction', 'down')
    duration = request.args.get('duration', '60')
    interval = request.args.get('interval', '1.5')
    scroll_amount = request.args.get('scroll_amount', '1')
    return_html = request.args.get('return_html', 'false').lower() == 'true'
    
    logger.debug(f"参数: url={url}, direction={direction}, duration={duration}, interval={interval}, scroll_amount={scroll_amount}, return_html={return_html}")
    
    html_content = None
    browser_instance = None
    browser_process = None
    
    # 如果提供了URL，先打开它
    if url:
        try:
            logger.debug(f"打开URL: {url}")
            # 如果需要返回HTML，使用Selenium打开
            if return_html:
                try:
                    logger.debug("使用Selenium打开页面以获取HTML")
                    options = Options()
                    options.headless = False
                    options.add_argument("--start-maximized")  # 最大化窗口
                    browser_instance = webdriver.Firefox(options=options)
                    browser_instance.get(url)
                    time.sleep(3)  # 等待页面加载
                    # 确保窗口最大化
                    browser_instance.maximize_window()
                    time.sleep(1)  # 等待最大化完成
                    html_content = browser_instance.page_source
                    logger.debug("已获取HTML内容")
                except Exception as e:
                    logger.error(f"使用Selenium获取HTML失败: {str(e)}")
                    # 如果Selenium失败，使用普通方式打开
                    browser_process = subprocess.Popen(['firefox', '--new-window', url])
                    time.sleep(3)
                    # 使用xdotool确保窗口最大化和激活
                    subprocess.run('xdotool search --onlyvisible --class Firefox windowactivate', shell=True)
                    subprocess.run('xdotool key F11', shell=True)
            else:
                # 使用Firefox打开URL
                browser_process = subprocess.Popen(['firefox', '--new-window', url])
                time.sleep(3)  # 等待页面加载
                
                # 确保窗口最大化 - 修复方法
                try:
                    # 查找Firefox窗口并激活
                    subprocess.run('xdotool search --onlyvisible --class Firefox windowactivate', shell=True)
                    # 发送F11键切换全屏
                    subprocess.run('xdotool key F11', shell=True)
                    logger.debug("已发送F11命令最大化窗口")
                except Exception as e:
                    logger.error(f"最大化窗口失败: {str(e)}")
        except Exception as e:
            logger.error(f"打开URL失败: {str(e)}")
            return jsonify({"error": f"打开URL失败: {str(e)}"}), 500
    
    # 直接使用xdotool执行滚动
    try:
        # 获取滚动次数
        scroll_times = int(float(duration)) // int(float(interval))
        scroll_amount_int = int(scroll_amount)
        
        logger.debug(f"计划滚动{scroll_times}次，每次{scroll_amount_int}步")
        
        # 在后台启动滚动线程
        def do_scroll():
            try:
                logger.debug("开始执行滚动")
                for i in range(scroll_times):
                    # 重新激活Firefox窗口确保滚动命令生效
                    subprocess.run('xdotool search --onlyvisible --class Firefox windowactivate', shell=True)
                    for j in range(scroll_amount_int):
                        subprocess.run(['xdotool', 'key', 'Page_Down'])
                    time.sleep(float(interval))
                logger.debug("滚动完成")
                
                # 只有在获取HTML内容的情况下才关闭浏览器
                if return_html:
                    if browser_instance:
                        try:
                            browser_instance.quit()
                        except:
                            pass
            except Exception as e:
                logger.error(f"滚动执行错误: {str(e)}")
        
        # 启动滚动线程
        scroll_thread = threading.Thread(target=do_scroll)
        scroll_thread.daemon = False  # 确保线程不会随主线程退出而终止
        scroll_thread.start()
        
        # 准备响应
        response = {
            "success": True,
            "message": f"已打开页面并开始滚动，持续{duration}秒，间隔{interval}秒"
        }
        
        # 如果请求了HTML内容且已获取，添加到响应中
        if return_html and html_content:
            response["html_content"] = html_content
        
        return jsonify(response)
    except Exception as e:
        logger.error(f"启动滚动失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/get-html/<int:html_id>', methods=['GET'])
def get_html_by_id(html_id):
    """获取指定ID的HTML内容"""
    # 查找匹配的HTML文件
    html_files = [f for f in os.listdir('.') if f.startswith(f'page_html_{html_id}')]
    
    if not html_files:
        # 检查是否仍在处理中
        if os.path.exists(f"/tmp/get_html_{html_id}.js"):
            return jsonify({"status": "processing"}), 202
        return jsonify({"error": "HTML内容不存在"}), 404
    
    # 返回HTML内容
    with open(html_files[0], "r", encoding="utf-8") as f:
        html_content = f.read()
    
    return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}

@app.route('/auto-scroll', methods=['POST'])
def auto_scroll():
    data = request.json
    duration = data.get('duration', 10)  # 默认滚动10秒
    interval = data.get('interval', 1)   # 默认每1秒滚动一次
    
    try:
        # 启动一个新进程来执行自动滚动，避免阻塞API
        cmd = f"""
        python3 -c '
import subprocess
import time
for i in range({duration}):
    subprocess.run(["xdotool", "key", "Page_Down"])
    time.sleep({interval})
'
        """
        subprocess.Popen(cmd, shell=True)
        
        return jsonify({
            "success": True, 
            "message": f"自动滚动已启动，持续{duration}秒，间隔{interval}秒"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/status', methods=['GET'])
def status():
    return jsonify({"status": "running"})

@app.route('/config', methods=['POST'])
def config_browser():
    """配置浏览器自动启动的行为"""
    data = request.json
    url = data.get('url', 'about:blank')
    duration = data.get('duration', 10)
    
    try:
        # 创建新的启动脚本
        script_content = f"""#!/bin/bash
firefox --new-window --kiosk {url} &
sleep {duration} && pkill -f firefox && sleep 1 && firefox --new-window --kiosk {url} &
sleep infinity
"""
        with open('/app/start-firefox.sh', 'w') as f:
            f.write(script_content)
        
        # 重启Firefox服务
        subprocess.run(["supervisorctl", "restart", "firefox"])
        
        return jsonify({
            "success": True,
            "message": f"已更新浏览器配置: URL={url}, 自动重启周期={duration}秒"
        })
    except Exception as e:
        logger.error(f"更新配置失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

# 确保应用退出时关闭浏览器
@app.teardown_appcontext
def shutdown_browser(exception=None):
    global browser
    if browser:
        browser.quit()
        browser = None

if __name__ == '__main__':
    # 不再自动初始化浏览器
    logger.info("API服务启动中，浏览器将在接收到请求时启动")
    
    app.run(host='0.0.0.0', port=5000)
