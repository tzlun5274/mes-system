# 使用 Node.js 作為基礎鏡像
FROM node:14

# 設定工作目錄
WORKDIR /app

# 複製 package.json 和 package-lock.json
COPY package*.json ./

# 安裝依賴
RUN npm install

# 複製源代碼到容器內
COPY . .

# 啟動後端服務
CMD ["npm", "start"]
