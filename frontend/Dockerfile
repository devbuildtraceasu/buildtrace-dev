FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# Accept NEXT_PUBLIC_API_URL as build argument
ARG NEXT_PUBLIC_API_URL=http://localhost:5001
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build
ENV PORT=3000
EXPOSE 3000
CMD ["sh", "-c", "next start -p ${PORT:-3000}"]
