# 使用 Node.js 官方映像檔
FROM node:18

# 設定工作目錄
WORKDIR /app

# 複製 package.json 並安裝依賴
COPY package.json ./
RUN npm install

# 複製其他程式碼
COPY . .

# 構建 React 專案
RUN npm run build

# 使用 serve 提供靜態檔案
RUN npm install -g serve
CMD ["serve", "-s", "build"]

# 監聽 3000 端口
EXPOSE 3000
