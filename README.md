# Test task Flex TCP-server.

## Инструкция по запуску:
### С помощью Docker:
docker build -t flex_server .
docker run -p 9000:9000 flex_server
### Локально (Без Docker):
py main.py