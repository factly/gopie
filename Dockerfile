FROM golang:1.22-alpine

WORKDIR /app

COPY . .

RUN apk add gcc musl-dev
RUN go mod download

RUN go install github.com/githubnemo/CompileDaemon@latest

ENTRYPOINT CompileDaemon -exclude-dir=.git -exclude-dir=docs --build="go build main.go" --command="./main serve"
