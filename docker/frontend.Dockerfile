# Frontend Dockerfile


FROM node:18-slim AS build
ARG VITE_APP_WS_URL
ENV VITE_APP_WS_URL=$VITE_APP_WS_URL
ARG VITE_API_BASE
ENV VITE_API_BASE=$VITE_API_BASE
WORKDIR /app
COPY src/user_interfaces/ /app/
WORKDIR /app/web_app/client
RUN npm install && npm run build

FROM nginx:alpine
COPY --from=build /app/web_app/client/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
