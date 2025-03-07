# 使用 Node.js 官方映像
FROM node:18

# 設定工作目錄
WORKDIR /app

# 複製 package.json 並安裝依賴
COPY package.json ./
RUN npm install

# 確保 react-scripts 存在
RUN npm install react-scripts

# 複製其餘檔案並建置前端
COPY . .
RUN npm run build

# 使用 serve 提供靜態檔案
RUN npm install -g serve
CMD ["serve", "-s", "build", "-l", "3000"]
