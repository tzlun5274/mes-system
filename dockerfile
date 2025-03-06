# 使用 Node.js 作為基礎映像
FROM node:14

# 設置工作目錄
WORKDIR /app

# 複製 package.json 和 package-lock.json（如果有）
COPY package*.json ./

# 安裝所有依賴
RUN npm install

# 複製整個項目文件
COPY . .

# 開放端口（例如 3000 端口）
EXPOSE 8080

# 啟動開發伺服器或執行打包命令
CMD ["npm", "start"]
