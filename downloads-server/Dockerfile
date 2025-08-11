FROM golang:1.24.5 AS builder

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .

RUN go build -o downloads-server .

FROM ubuntu:jammy AS runtime

ENV USER=downloads-server
ENV HOME_DIR=/home/$USER

RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/downloads-server /usr/local/bin/

RUN groupadd -g 1001 ${USER} && \
    useradd -m -u 1001 -s /bin/sh -g ${USER} ${USER}

RUN chown -R ${USER}:${USER} ${HOME_DIR}

WORKDIR ${HOME_DIR}

USER ${USER}

EXPOSE 8000

CMD ["downloads-server", "serve"]
