FROM node:22 AS client-build

ARG VUE_APP_OAUTH_CLIENT_ID
ARG VUE_APP_API_ROOT
ARG VUE_APP_OAUTH_API_ROOT

WORKDIR /app
COPY client .
RUN npm install && npm run build

FROM python:3.12 AS docs-build

WORKDIR /work
COPY mkdocs.yml .
COPY docs ./docs
RUN pip install mkdocs mkdocs-material
RUN mkdocs build

FROM nginx:1.27 AS nginx
RUN mkdir /client
COPY --from=client-build /app/dist /client
COPY --from=docs-build /work/site /client/docs
COPY prod/nginx.conf /etc/nginx.conf

EXPOSE 80
EXPOSE 443
CMD ["nginx", "-c", "/etc/nginx.conf", "-g", "daemon off;"]
