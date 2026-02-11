FROM node:20-alpine

WORKDIR /app

# Instalar dependencias
COPY package*.json ./
RUN npm install

# Copiar código
COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
