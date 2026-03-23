FROM node:20-alpine as build-stage

WORKDIR /app

COPY . .

RUN yarn install --frozen-lockfile

RUN yarn quasar build

FROM nginx:alpine as production-stage

COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=build-stage /app/dist/spa /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]