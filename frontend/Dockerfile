# 使用 Node 18 作為基礎鏡像
FROM node:18

# 設置工作目錄
WORKDIR /app

# 複製 package.json 並安裝依賴
COPY package.json ./
RUN npm install

# 複製其餘前端檔案並建置前端
COPY . .
RUN npm run build

# 使用 serve 提供靜態檔案
RUN npm install -g serve
CMD ["serve", "-s", "build"]
