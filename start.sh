#!/bin/bash

# 获取脚本所在绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# 彩色输出定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}===================================================${NC}"
echo -e "${BLUE}     Deep Research Agent 快速一键启动开发环境       ${NC}"
echo -e "${BLUE}===================================================${NC}"

# 初始化 PID 变量
BACKEND_PID=""
FRONTEND_PID=""

# 清理资源的函数
cleanup() {
    echo -e "\n${YELLOW}🛑 正在停止所有服务进程...${NC}"
    if [ -n "$BACKEND_PID" ]; then
        echo -e "正在终止后端服务进程 (PID: $BACKEND_PID)..."
        kill -15 $BACKEND_PID 2>/dev/null
    fi
    if [ -n "$FRONTEND_PID" ]; then
        echo -e "正在终止前端服务进程 (PID: $FRONTEND_PID)..."
        kill -15 $FRONTEND_PID 2>/dev/null
    fi
    echo -e "${GREEN}✓ 所有服务已安全停止退出。${NC}"
    exit 0
}

# 绑定信号，在按下 Ctrl+C 或脚本退出时执行清理
trap cleanup SIGINT SIGTERM EXIT

# 1. 后端服务启动检查与运行
echo -e "\n${GREEN}⚙️  1. 正在准备后端服务 (FastAPI)...${NC}"
cd "$SCRIPT_DIR/backend"

# 检查 .env 配置文件是否存在
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ 错误: 未在 backend/ 目录下找到 .env 配置文件！${NC}"
    echo -e "${YELLOW}💡 请参考 backend/.env.example 或是项目 README.md 文件配置您的 API 密钥，然后再试。${NC}"
    exit 1
fi

# 检测并使用虚拟环境
if [ -d ".venv" ]; then
    echo -e "${BLUE}ℹ️  检测到虚拟环境 .venv，正在激活...${NC}"
    source .venv/bin/activate
else
    echo -e "${YELLOW}⚠️  警告: 未检测到虚拟环境 .venv，将使用系统默认 python 启动...${NC}"
fi

# 在后台启动后端进程
python -m app.main &
BACKEND_PID=$!
echo -e "${GREEN}✓ 后端已成功在后台启动 (PID: $BACKEND_PID)，端口: 8000${NC}"

# 等待后端启动和初始化数据库
sleep 1.5

# 2. 前端服务启动检查与运行
echo -e "\n${GREEN}💻  2. 正在准备前端服务 (Vue 3 + Vite)...${NC}"
cd "$SCRIPT_DIR/frontend"

# 检查 node_modules 目录
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}📦 未检测到 node_modules，正在执行 npm install 安装前端依赖，请稍候...${NC}"
    npm install
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ 错误: npm install 失败，请检查您的 Node.js 与 npm 环境后再试。${NC}"
        exit 1
    fi
fi

# 在后台启动前端开发服务器
npm run dev &
FRONTEND_PID=$!
echo -e "${GREEN}✓ 前端已成功在后台启动 (PID: $FRONTEND_PID)，端口: 5173${NC}"

echo -e "\n${BLUE}===================================================${NC}"
echo -e "${GREEN}🚀 系统已全部启动完成！${NC}"
echo -e "${BLUE}👉 前端访问地址 (Glassmorphic UI): ${YELLOW}http://localhost:5173${NC}"
echo -e "${BLUE}👉 后端 API 控制台地址:            ${YELLOW}http://localhost:8000${NC}"
echo -e "${YELLOW}💡 提示: 在此终端按下 [Ctrl+C] 可以一键安全退出前后端服务。${NC}"
echo -e "${BLUE}===================================================${NC}\n"

# 阻塞主脚本，等待后台子进程结束
# 这样 trap 会一直维持，直到用户按 Ctrl+C
wait
