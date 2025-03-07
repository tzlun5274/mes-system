# 使用 Node.js 官方映像檔
FROM node:18

# 設定工作目錄
WORKDIR /app

# 複製 package.json 並安裝依賴
COPY package.json ./
RUN npm install

# 複製其他程式碼
COPY . .

# 監聽 5000 端口
EXPOSE 5000

# 啟動後端服務
CMD ["node", "app.js"]
