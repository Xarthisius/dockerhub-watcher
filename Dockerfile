FROM python:3.12-slim
LABEL maintainer="Kacper Kowalik <xarthisius.kk@gmail.com>"

ENV DEBIAN_FRONTEND=noninteractive \
  LANG=en_US.UTF-8 \
  LC_ALL=C.UTF-8

RUN apt-get update -qy \
  && apt-get install -yq --no-install-recommends \
    tini \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1000 ubuntu && useradd -g 1000 -G 1000 -u 1000 -m -s /bin/bash ubuntu

COPY . /app
WORKDIR /app
RUN pip --no-cache-dir install -r requirements.txt

USER ubuntu
EXPOSE 8081
ENTRYPOINT ["/usr/bin/tini", "--", "python", "app.py"]
