FROM golang:1.24 AS builder
WORKDIR /app
COPY . .
RUN go mod download

RUN go build -o gopie main.go

# Install goose for database migrations
RUN go install github.com/pressly/goose/v3/cmd/goose@latest

FROM ubuntu:jammy AS runtime

ENV USER=gopie
ENV HOME_DIR=/home/$USER
ENV DATA_DIR=$HOME_DIR/dataful

RUN apt-get update && apt-get install -y ca-certificates gcc musl-dev g++

COPY --from=builder /app/gopie /usr/local/bin
COPY --from=builder /go/bin/goose /usr/local/bin
RUN chmod 777 /usr/local/bin/gopie
RUN chmod 777 /usr/local/bin/goose

RUN groupadd -g 1001 gopie \
  && useradd -m -u 1001 -s /bin/sh -g gopie gopie

RUN mkdir -p $DATA_DIR
RUN chown -R $USER:$USER $HOME_DIR

WORKDIR $HOME_DIR
USER gopie

CMD gopie serve
