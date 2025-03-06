# 使用 Node.js 14 作為基礎映像
FROM node:14

# 設定工作目錄
WORKDIR /app

# 複製後端專案的 package.json 和 package-lock.json
COPY package*.json ./

# 安裝後端依賴
RUN npm install

# 複製後端代碼
COPY . .

# 開放後端 API 端口
EXPOSE 5000

# 啟動後端應用
CMD ["node", "server.js"]
