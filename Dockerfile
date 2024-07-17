FROM golang:1.22 as builder
WORKDIR /app
COPY . .
RUN go mod download

RUN go build -o gopie main.go

FROM ubuntu:jammy as runtime

ENV USER=gopie
ENV HOME_DIR=/home/$USER
ENV DATA_DIR=$HOME_DIR/dataful

RUN apt-get update && apt-get install -y ca-certificates gcc musl-dev g++

COPY --from=builder /app/gopie /usr/local/bin
RUN chmod 777 /usr/local/bin/gopie

RUN groupadd -g 1001 gopie \
  && useradd -m -u 1001 -s /bin/sh -g gopie gopie

RUN mkdir -p $DATA_DIR
RUN chown -R $USER:$USER $HOME_DIR

WORKDIR $HOME_DIR
USER gopie

# COPY 
# RUN gopie migrate
# ENTRYPOINT ["gopie"]
CMD gopie migrate && gopie serve
