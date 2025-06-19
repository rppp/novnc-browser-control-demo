FROM ubuntu:22.04

# 避免交互式提示
ENV DEBIAN_FRONTEND=noninteractive

# 设置显示变量
ENV DISPLAY=:1

# 设置语言环境
ENV LANG=zh_CN.UTF-8
ENV LANGUAGE=zh_CN:zh
ENV LC_ALL=zh_CN.UTF-8

# 添加 Mozilla PPA 用于安装 Firefox
RUN apt-get update && apt-get install -y software-properties-common apt-transport-https ca-certificates curl gnupg
RUN add-apt-repository ppa:mozillateam/ppa -y

# 设置 Mozilla 仓库优先级
RUN echo 'Package: firefox*\nPin: release o=LP-PPA-mozillateam\nPin-Priority: 1001' > /etc/apt/preferences.d/mozilla-firefox

# 安装基础软件、VNC服务器和依赖
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    firefox \
    xvfb \
    xdotool \
    wget \
    curl \
    unzip \
    dbus-x11 \
    libgtk-3-0 \
    libdbus-glib-1-2 \
    libasound2 \
    libx11-xcb1 \
    x11vnc \
    xfce4 \
    xfce4-terminal \
    xterm \
    net-tools \
    novnc \
    supervisor \
    locales \
    fonts-noto-cjk \
    fonts-wqy-microhei \
    fonts-wqy-zenhei

# 配置中文支持
RUN locale-gen zh_CN.UTF-8 && \
    update-locale LANG=zh_CN.UTF-8 LANGUAGE=zh_CN:zh LC_ALL=zh_CN.UTF-8

# 安装 geckodriver (Firefox WebDriver)
RUN wget https://github.com/mozilla/geckodriver/releases/download/v0.33.0/geckodriver-v0.33.0-linux64.tar.gz \
    && tar -xvzf geckodriver-v0.33.0-linux64.tar.gz \
    && mv geckodriver /usr/local/bin/ \
    && chmod +x /usr/local/bin/geckodriver \
    && rm geckodriver-v0.33.0-linux64.tar.gz

# 设置VNC密码
RUN mkdir -p /root/.vnc && \
    x11vnc -storepasswd "password" /root/.vnc/passwd

# 设置工作目录
WORKDIR /app

# 复制应用代码
COPY browser-control-api.py /app/
COPY requirements.txt /app/

# 安装Python依赖
RUN pip3 install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com

# 创建启动Firefox的脚本
RUN echo '#!/bin/bash\necho "Firefox服务启动，等待API指令..."\nsleep infinity' > /app/start-firefox.sh && \
    chmod +x /app/start-firefox.sh

# 创建 supervisord 配置文件
RUN echo "[supervisord]\nnodaemon=true\n\n\
[program:xvfb]\ncommand=/usr/bin/Xvfb :1 -screen 0 1920x1080x24\nautorestart=true\n\n\
[program:xfce]\ncommand=/usr/bin/startxfce4\nenvironment=DISPLAY=:1\nautorestart=true\n\n\
[program:x11vnc]\ncommand=/usr/bin/x11vnc -forever -nopw -shared -rfbport 5900 -display :1\nautorestart=true\n\n\
[program:novnc]\ncommand=/usr/share/novnc/utils/launch.sh --vnc localhost:5900 --listen 6080\nautorestart=true\n\n\
[program:firefox-setup]\ncommand=bash -c 'mkdir -p /root/.mozilla && sleep 5'\nstartsecs=0\nautorestart=false\n\n\
[program:firefox]\ncommand=/app/start-firefox.sh\nenvironment=DISPLAY=:1\nautorestart=true\n\n\
[program:flask]\ncommand=python3 /app/browser-control-api.py\nenvironment=DISPLAY=:1\nautorestart=true\n" > /etc/supervisor/conf.d/supervisord.conf

# 暴露端口
EXPOSE 5000 5900 6080

# 添加到 Dockerfile 中
RUN mkdir -p /root/.mozilla/firefox/ && \
    echo '[Profile0]\nName=default\nIsRelative=1\nPath=default\nDefault=1\n\n[General]\nStartWithLastProfile=1\nVersion=2' > /root/.mozilla/firefox/profiles.ini && \
    mkdir -p /root/.mozilla/firefox/default/

# 设置Firefox首选项以支持中文
RUN mkdir -p /root/.mozilla/firefox/default/ && \
    echo 'user_pref("intl.accept_languages", "zh-CN,zh,en-US,en");' > /root/.mozilla/firefox/default/prefs.js

# 启动服务
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
