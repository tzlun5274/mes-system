# 使用 Node.js 14 作為基礎映像
FROM node:14

# 設定工作目錄
WORKDIR /app

# 複製前端專案的 package.json 和 package-lock.json
COPY package*.json ./

# 安裝前端依賴
RUN npm install

# 複製前端代碼
COPY . .

# 建構 React 應用
RUN npm run build

# 設定容器開放的端口
EXPOSE 3000

# 啟動 React 應用
CMD ["npm", "start"]
