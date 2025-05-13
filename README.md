# 通过noVNC和VNC实现远程桌面控制的DEMO

本项目是一个基于Docker的远程浏览器控制系统，使用noVNC和VNC技术实现浏览器中的远程桌面控制。通过此系统，您可以在网页中查看和控制远程的Firefox浏览器，并执行自动滚动等操作。

## 技术栈

- Docker
- Python Flask API
- Selenium
- Firefox浏览器
- VNC和noVNC
- Supervisor

## 安装和部署

### 前提条件

- 安装Docker
- 确保以下端口可用：5000 (API)、5900 (VNC)、6080 (noVNC)

### 构建Docker镜像

在项目根目录下执行：

```bash
docker build -t novnc-browser-control .
```

### 运行Docker容器

```bash
docker run -d --name browser-control -p 5000:5000 -p 5900:5900 -p 6080:6080 novnc-browser-control
```

## 使用方法

1. 启动Docker容器后，等待系统初始化（约30秒）
2. 在浏览器中打开以下URL访问控制界面：
   - http://localhost:6080/vnc.html - noVNC界面（VNC密码：password）
   - http://localhost:5000/status - 检查API服务状态

3. 或者直接打开项目中的index.html文件，通过网页界面进行控制：
   - 输入要访问的URL
   - 设置自动滚动参数（持续时间、滚动间隔、滚动幅度）
   - 点击"浏览网页并自动滚动"按钮

## API接口说明

系统提供以下REST API接口：

- `GET /status` - 获取系统状态
- `GET /scroll?url=<URL>&duration=<秒>&interval=<秒>&scroll_amount=<数量>` - 打开指定URL并自动滚动
- `POST /stop-scroll` - 停止正在进行的自动滚动

